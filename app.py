from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import requests
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# ✅ Fix CORS issue (Allows frontend requests)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins (change to ["http://localhost:5173"] in production)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ✅ Replace with your OpenRouter API Key
OPENROUTER_API_KEY = "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"

class ReportRequest(BaseModel):
    findings: str

@app.post("/generate-report")
async def generate_report(request: ReportRequest):
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }
    
    # ✅ Ensure correct OpenRouter Model
    payload = {
        "model": "mistralai/mistral-7b-instruct:free",  # Change if using another free model
        "messages": [
            {"role": "system", "content": "You are an AI-powered radiology assistant."},
            {"role": "user", "content": f"""
                Findings: {request.findings}

                Please provide:
                1. **Differential Diagnosis** (Possible conditions related to the findings)
                2. **Concise Impression** (Summary of key findings)
            """}
        ]
    }

    try:
        response = requests.post("https://openrouter.ai/api/v1/chat/completions", json=payload, headers=headers)
        response.raise_for_status()
        
        data = response.json()
        
        if "choices" not in data or not data["choices"]:
            raise HTTPException(status_code=500, detail="⚠ OpenRouter API returned no content.")
        
        # ✅ Extract AI response text
        ai_response = data["choices"][0]["message"]["content"]
        
        # ✅ Extract Differential Diagnosis and Concise Impression Separately
        diagnosis_text = ""
        impression_text = ""

        if "**Differential Diagnosis**" in ai_response and "**Concise Impression**" in ai_response:
            parts = ai_response.split("**Concise Impression**")
            diagnosis_text = parts[0].replace("**Differential Diagnosis**", "").strip()
            impression_text = parts[1].strip()
        else:
            diagnosis_text = "Error: Could not extract differential diagnosis."
            impression_text = "Error: Could not extract concise impression."

        return {
            "differential_diagnosis": diagnosis_text,
            "concise_impression": impression_text
        }
    
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=500, detail=f"⚠ OpenRouter API Error: {str(e)}")

