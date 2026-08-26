from jinja2.nodes import List
from fastapi import Form, File
from fastapi.responses import HTMLResponse
from fastapi import UploadFile
import shutil
from pathlib import Path
from fastapi import Request
from fastapi.templating import Jinja2Templates
from fastapi import FastAPI,HTTPException
from fastapi.responses import FileResponse
import base64
import os
import requests
from dotenv import load_dotenv

load_dotenv(override=True)
app = FastAPI()

OPENAI_APIKEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_URL = os.getenv("OPENAI_URL", "")

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-flash-latest")
GEMINI_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent?key={GEMINI_API_KEY}"



# DATABASE
DATABASES = {
    'default': {
        'ENGINE': os.getenv("DB_ENGINE", "django.db.backends.postgresql"),
        'NAME': os.getenv("DB_NAME", "postgres"),
        'USER': os.getenv("DB_USER", ""),
        'PASSWORD': os.getenv("DB_PASSWORD", ""),
        'HOST': os.getenv("DB_HOST", ""),
        'PORT': os.getenv("DB_PORT", "5432"),
    }
}

templates=Jinja2Templates(directory="templates")

@app.get("/")
def read_root(request: Request):
    return templates.TemplateResponse(request=request, name="index.html")

chat_history: List[dict]=[]

@app.get("/models")
def get_history():
    return {"history": chat_history}

@app.get("/chatbot")
def get_chatbot(request: Request):
    return templates.TemplateResponse(request=request, name="chatbot.html", context={"user_input": None, "bot_reply": None})

chat_history=[]

@app.post("/chat", response_class=HTMLResponse)
def chat(request: Request, user_input: str = Form(...)):
    payload = {
        "contents": [{
            "role": "user",
            "parts": [{"text": user_input}]
        }]
    }
    try:
        response = requests.post(GEMINI_URL, json=payload, timeout=30).json()
        if "candidates" in response and response["candidates"]:
            bot_reply = response["candidates"][0]["content"]["parts"][0]["text"]
        else:
            error_message = response.get("error", {}).get("message", "Unexpected API response")
            bot_reply = f"Error: {error_message}"
            print("Gemini API Error Response:", response)
    except Exception as e:
        bot_reply = f"Error: {str(e)}"

    chat_history.append({"user": user_input, "bot": bot_reply})

    return templates.TemplateResponse(
        request=request,
        name="chatbot.html",
        context={"user_input": user_input, "bot_reply": bot_reply}
    )


UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)  # Creates folder if it doesn't exist

@app.post("/resume-analyzer")
def analyze_resume(request: Request, file: UploadFile = File(...)):

    # 1. Read file bytes and convert to base64
    file_bytes = file.file.read()
    base64_data = base64.b64encode(file_bytes).decode("utf-8")

    # 2. Build the Gemini payload
    payload = {
        "contents": [
            {
                "parts": [
                    {
                        "inline_data": {
                            "mime_type": file.content_type or "application/pdf",
                            "data": base64_data,
                        }
                    },
                    {
                        "text": "Analyze this resume. Give a quick summary, skills, strengths, and areas for improvement, in 200 words, line-by-line and point wise if needed, precise and professional."
                    },
                ]
            }
        ]
    }
# 3. Send POST request using standard requests library
    response = requests.post(GEMINI_URL, json=payload)

    if response.status_code != 200:
        raise HTTPException(status_code=response.status_code, detail=response.text)

    data = response.json()
    result_text = data["candidates"][0]["content"]["parts"][0]["text"]


    return templates.TemplateResponse(request=request, name="resume-analyzer.html", context={"analysis":True, "result_text":result_text})

@app.get("/resume-analyzer")
def resume_form(request: Request):
    return templates.TemplateResponse(request=request, name="resume-analyzer.html", context={"analysis":False, "result_text":None})

# @app.get("/gemini/models")
# def gemini_models():
#     return {"message": "Listing Gemini models"}

# @app.post("/gemini/prompt")
# def gemini_prompt():
#     return {"message": "Gemini Prompt"}

# @app.get("/gemini/resume")
# def gemini_resume():
#     return {"message": "Gemini Resume"}

# @app.get("/openai/models")
# def gemini_models():
#     return {"message": "OpenAI models"}

# @app.post("/openai/prompt")
# def gemini_prompt():
#     return {"message": "OpenAI Prompt"}

