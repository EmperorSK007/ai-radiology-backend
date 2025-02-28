from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import requests
import json
import re

# 🔹 Set your OpenRouter API Key
OPENROUTER_API_KEY = "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"  # Replace with your real key

# OpenRouter API URL
OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"

# Initialize FastAPI app
app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all HTTP methods
    allow_headers=["*"],  # Allows all headers
)


# Define input model for API request
class ReportRequest(BaseModel):
    findings: str

@app.post("/generate-report")
async def generate_report(request: ReportRequest):
    if not OPENROUTER_API_KEY:
        raise HTTPException(status_code=500, detail="⚠ OpenRouter API Key is missing.")

    findings_text = request.findings

    prompt = f"""
    You are an AI-powered radiology assistant. Given these radiology findings:
    {findings_text}

    Generate:
    1. **Differential Diagnoses**: List possible conditions related to the findings.
    2. **Concise Impression**: Provide a structured radiology summary.

    Return your response in JSON format with keys "differential_diagnosis" and "concise_impression".
    """

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }

    data = {
        "model": "mistralai/mistral-7b-instruct",  # Ensure this model name is correct
        "messages": [
            {"role": "system", "content": "You are an AI radiology assistant with expertise in analyzing medical images."},
            {"role": "user", "content": prompt}
        ]
    }

    try:
        response = requests.post(OPENROUTER_API_URL, json=data, headers=headers)
        
        # Check if API response is empty
        if response.status_code == 204 or not response.text.strip():
            raise HTTPException(status_code=500, detail="⚠ OpenRouter API returned an empty response.")

        response_json = response.json()

        # If response does not contain "choices", throw an error
        if "choices" not in response_json or not response_json["choices"]:
            raise HTTPException(status_code=500, detail="⚠ OpenRouter API returned no content.")

        # Extract AI response text
        ai_response = response_json["choices"][0]["message"]["content"]

        # Try to parse the response as JSON
        try:
            structured_response = json.loads(ai_response)
            differential_diagnosis = structured_response.get("differential_diagnosis", "No diagnosis found.")
            concise_impression = structured_response.get("concise_impression", "No impression found.")
        except json.JSONDecodeError:
            # If AI response is not in JSON format, extract manually
            diagnosis_match = re.search(r"Differential Diagnoses:\s*(.*?)\n", ai_response, re.DOTALL)
            impression_match = re.search(r"Concise Impression:\s*(.*)", ai_response, re.DOTALL)

            differential_diagnosis = diagnosis_match.group(1).strip() if diagnosis_match else "No diagnosis found."
            concise_impression = impression_match.group(1).strip() if impression_match else "No impression found."

        return {
            "differential_diagnosis": differential_diagnosis,
            "concise_impression": concise_impression
        }

    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=500, detail=f"⚠ Network Error: {str(e)}")
    except KeyError:
        raise HTTPException(status_code=500, detail="⚠ Unexpected API response format.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"⚠ OpenRouter API Error: {str(e)}")
