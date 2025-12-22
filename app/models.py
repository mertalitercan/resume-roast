from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class ResumeAnalysis(BaseModel):
    resume_id: str
    user_id: str
    filename: str
    s3_key: str
    feedback: str
    page_count: int
    word_count: int
    created_at: datetime

class User(BaseModel):
    uid: str
    email: str
    name: Optional[str] = None
    created_at: datetime
