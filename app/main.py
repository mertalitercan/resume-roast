from fastapi import FastAPI, Request, File, UploadFile, Header, HTTPException
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
from pymongo import MongoClient
from datetime import datetime
from bson import ObjectId
import uuid

from app.config import get_settings
from app.services.pdf_service import PDFService
from app.services.ai_service import AIService
from app.services.storage_service import StorageService
from app.services.auth_service import AuthService

# Initialize
app = FastAPI(title="ResumeRoast")
settings = get_settings()
templates = Jinja2Templates(directory="app/templates")

# Services
pdf_service = PDFService()
ai_service = AIService()
storage_service = StorageService()
auth_service = AuthService()

# MongoDB
mongo_client = MongoClient(settings.mongodb_uri)
db = mongo_client["resumeroast"]
users_collection = db["users"]
resumes_collection = db["resumes"]

async def get_current_user(authorization: str = Header(None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid token")
    
    token = authorization.split("Bearer ")[1]
    try:
        user_info = auth_service.verify_token(token)
        
        # Save/Update user in MongoDB
        users_collection.update_one(
            {'uid': user_info['uid']},
            {'$set': {
                'email': user_info['email'],
                'name': user_info.get('name'),
                'last_login': datetime.now()
            }},
            upsert=True
        )
        
        return user_info
    except Exception as e:
        raise HTTPException(status_code=401, detail=str(e))


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse("index.html", {
        "request": request,
        "firebase_api_key": settings.firebase_api_key,
        "firebase_auth_domain": settings.firebase_auth_domain,
        "firebase_project_id": settings.firebase_project_id
    })


@app.post("/api/analyze")
async def analyze_resume(
    file: UploadFile = File(...),
    authorization: str = Header(None)
):
    """
    Main endpoint: Upload resume and get AI feedback.
    """
    # Verify user
    user = await get_current_user(authorization)
    
    # Validate file
    if not file.filename.endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files allowed")
    
    # Read file bytes
    file_bytes = await file.read()
    
    if len(file_bytes) > 5 * 1024 * 1024:  # Limit: 5MB
        raise HTTPException(status_code=400, detail="File too large (max 5MB)")
    
    try:
        # 1. Extract text from PDF
        pdf_data = pdf_service.extract_text(file_bytes)
        
        # 2. Upload to S3
        s3_key = storage_service.upload_resume(
            file_bytes, 
            user['uid'], 
            file.filename
        )
        
        # Analyze with AI
        feedback = ai_service.analyze_resume(pdf_data['text'])
        
        # Save to MongoDB
        resume_id = str(uuid.uuid4())
        resume_doc = {
            '_id': resume_id,
            'user_id': user['uid'],
            'filename': file.filename,
            's3_key': s3_key,
            'feedback': feedback,
            'page_count': pdf_data['page_count'],
            'word_count': pdf_data['word_count'],
            'created_at': datetime.now()
        }
        resumes_collection.insert_one(resume_doc)
        
        # 5. Return feedback
        return JSONResponse({
            'success': True,
            'resume_id': resume_id,
            'feedback': feedback,
            'page_count': pdf_data['page_count'],
            'word_count': pdf_data['word_count']
        })
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/history")
async def get_history(authorization: str = Header(None)):
    """Get user's resume analysis history."""
    user = await get_current_user(authorization)
    
    resumes = list(resumes_collection.find(
        {'user_id': user['uid']},
        {'feedback': 0}  # Exclude full feedback for list view
    ).sort('created_at', -1).limit(10))
    
    # Convert ObjectId to string
    for resume in resumes:
        resume['_id'] = str(resume['_id'])
        resume['created_at'] = resume['created_at'].isoformat()
    
    return JSONResponse({'resumes': resumes})


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}
