from fastapi import FastAPI, Request, File, UploadFile, Header, HTTPException, Form
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
from pymongo import MongoClient
from datetime import datetime, timedelta
from bson import ObjectId
import uuid
import re

from app.config import get_settings
from app.services.pdf_service import PDFService
from app.services.ai_service import AIService
from app.services.storage_service import StorageService
from app.services.auth_service import AuthService

# --- Keep-Alive Route ---
@app.get("/health")
def health_check():
    return {"status": "OK"}
# ------------------------

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

def check_rate_limit(user_id: str) -> bool:
    """Check if user has exceeded 2 reviews per hour"""
    one_hour_ago = datetime.now() - timedelta(hours=1)
    recent_count = resumes_collection.count_documents({
        'user_id': user_id,
        'created_at': {'$gte': one_hour_ago}
    })
    return recent_count < 2

def extract_score(feedback: str) -> int:
    """Extract numerical score from AI feedback"""
    patterns = [
        r'score[:\s]+(\d+)\s*/\s*100',
        r'(\d+)\s*/\s*100',
        r'score[:\s]+(\d+)',
        r'rating[:\s]+(\d+)'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, feedback, re.IGNORECASE)
        if match:
            score = int(match.group(1))
            return min(max(score, 0), 100)
    
    return 75  # Default score

async def get_current_user(authorization: str = Header(None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid token")
    
    token = authorization.split("Bearer ")[1]
    try:
        user_info = auth_service.verify_token(token)
        
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
    job_description: str = Form(None),
    job_role: str = Form(None),
    authorization: str = Header(None)
):
    user = await get_current_user(authorization)
    
    # Check rate limit
    if not check_rate_limit(user['uid']):
        raise HTTPException(
            status_code=429, 
            detail="Rate limit exceeded. You can only analyze 2 resumes per hour. Please try again later."
        )
    
    if not file.filename.endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files allowed")
    
    file_bytes = await file.read()
    
    if len(file_bytes) > 5 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File too large (max 5MB)")
    
    try:
        pdf_data = pdf_service.extract_text(file_bytes)
        s3_key = storage_service.upload_resume(file_bytes, user['uid'], file.filename)
        
        feedback = ai_service.analyze_resume(
            pdf_data['text'],
            job_description=job_description,
            job_role=job_role
        )
        
        score = extract_score(feedback)
        
        resume_id = str(uuid.uuid4())
        resume_doc = {
            '_id': resume_id,
            'user_id': user['uid'],
            'filename': file.filename,
            's3_key': s3_key,
            'feedback': feedback,
            'score': score,
            'page_count': pdf_data['page_count'],
            'word_count': pdf_data['word_count'],
            'job_description': job_description,
            'job_role': job_role,
            'created_at': datetime.now()
        }
        resumes_collection.insert_one(resume_doc)
        
        return JSONResponse({
            'success': True,
            'resume_id': resume_id,
            'feedback': feedback,
            'score': score,
            'page_count': pdf_data['page_count'],
            'word_count': pdf_data['word_count']
        })
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/history")
async def get_history(authorization: str = Header(None)):
    user = await get_current_user(authorization)
    
    resumes = list(resumes_collection.find(
        {'user_id': user['uid']}
    ).sort('created_at', -1).limit(20))
    
    for resume in resumes:
        resume['_id'] = str(resume['_id'])
        resume['created_at'] = resume['created_at'].isoformat()
    
    return JSONResponse({'resumes': resumes})

@app.get("/api/rate-limit-status")
async def rate_limit_status(authorization: str = Header(None)):
    user = await get_current_user(authorization)
    
    one_hour_ago = datetime.now() - timedelta(hours=1)
    recent_reviews = list(resumes_collection.find({
        'user_id': user['uid'],
        'created_at': {'$gte': one_hour_ago}
    }).sort('created_at', -1))
    
    remaining = max(0, 2 - len(recent_reviews))
    next_available = None
    
    if remaining == 0 and recent_reviews:
        oldest_review = recent_reviews[-1]
        next_available = (oldest_review['created_at'] + timedelta(hours=1)).isoformat()
    
    return JSONResponse({
        'remaining': remaining,
        'total': 2,
        'next_available': next_available
    })

# Admin Dashboard Endpoints

def is_admin(user_email: str) -> bool:
    """Check if user is admin"""
    return user_email.lower() == settings.admin_email.lower()

@app.get("/admin", response_class=HTMLResponse)
async def admin_page(request: Request):
    """Admin dashboard page"""
    return templates.TemplateResponse("admin.html", {
        "request": request,
        "firebase_api_key": settings.firebase_api_key,
        "firebase_auth_domain": settings.firebase_auth_domain,
        "firebase_project_id": settings.firebase_project_id,
        "admin_email": settings.admin_email
    })

@app.get("/api/admin/stats")
async def admin_stats(authorization: str = Header(None)):
    """Get statistics for admin dashboard"""
    user = await get_current_user(authorization)
    
    if not is_admin(user['email']):
        raise HTTPException(status_code=403, detail="Access denied. Admin only.")
    
    # Total stats
    total_resumes = resumes_collection.count_documents({})
    total_users = users_collection.count_documents({})
    
    # Score stats
    all_resumes = list(resumes_collection.find({}, {'score': 1}))
    scores = [r['score'] for r in all_resumes if 'score' in r]
    
    avg_score = sum(scores) / len(scores) if scores else 0
    max_score = max(scores) if scores else 0
    min_score = min(scores) if scores else 0
    
    # Recent activity (last 24 hours)
    from datetime import timedelta
    yesterday = datetime.now() - timedelta(days=1)
    recent_count = resumes_collection.count_documents({
        'created_at': {'$gte': yesterday}
    })
    
    return JSONResponse({
        'total_resumes': total_resumes,
        'total_users': total_users,
        'average_score': round(avg_score, 1),
        'highest_score': max_score,
        'lowest_score': min_score,
        'reviews_last_24h': recent_count
    })

@app.get("/api/admin/resumes")
async def admin_get_resumes(authorization: str = Header(None)):
    """Get all resumes for admin dashboard"""
    user = await get_current_user(authorization)
    
    if not is_admin(user['email']):
        raise HTTPException(status_code=403, detail="Access denied. Admin only.")
    
    # Get all resumes with user email
    resumes = list(resumes_collection.find().sort('created_at', -1))
    
    # Join with user emails
    result = []
    for resume in resumes:
        user_doc = users_collection.find_one({'uid': resume['user_id']})
        user_email = user_doc['email'] if user_doc else 'Unknown'
        
        result.append({
            '_id': str(resume['_id']),
            'filename': resume['filename'],
            'user_email': user_email,
            'score': resume.get('score', 'N/A'),
            'job_role': resume.get('job_role', 'Not specified'),
            'page_count': resume.get('page_count', 'N/A'),
            'word_count': resume.get('word_count', 'N/A'),
            'created_at': resume['created_at'].isoformat(),
            's3_key': resume['s3_key'],
            'feedback': resume['feedback']
        })
    
    return JSONResponse({'resumes': result})

@app.get("/api/admin/download/{resume_id}")
async def admin_download_resume(resume_id: str, authorization: str = Header(None)):
    """Get presigned URL to download resume PDF"""
    user = await get_current_user(authorization)
    
    if not is_admin(user['email']):
        raise HTTPException(status_code=403, detail="Access denied. Admin only.")
    
    resume = resumes_collection.find_one({'_id': resume_id})
    if not resume:
        raise HTTPException(status_code=404, detail="Resume not found")
    
    # Generate presigned URL
    download_url = storage_service.get_resume_url(resume['s3_key'])
    
    return JSONResponse({'download_url': download_url})

@app.get("/health")
async def health_check():
    return {"status": "healthy"}