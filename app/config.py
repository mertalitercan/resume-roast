from pydantic_settings import BaseSettings
from functools import lru_cache

class Settings(BaseSettings):
    # MongoDB
    mongodb_uri: str
    
    # AWS
    aws_access_key_id: str
    aws_secret_access_key: str
    aws_region: str = "us-east-1"
    s3_bucket_name: str
    
    # OpenAI
    openai_api_key: str
    
    # Firebase
    firebase_project_id: str
    firebase_private_key: str
    firebase_client_email: str
    firebase_api_key: str
    firebase_auth_domain: str
    
    class Config:
        env_file = ".env"

@lru_cache()
def get_settings():
    return Settings()
