import boto3
from datetime import datetime
from app.config import get_settings

settings = get_settings()

class StorageService:
    def __init__(self):
        self.s3_client = boto3.client(
            's3',
            aws_access_key_id=settings.aws_access_key_id,
            aws_secret_access_key=settings.aws_secret_access_key,
            region_name=settings.aws_region
        )
        self.bucket = settings.s3_bucket_name
    
    def upload_resume(self, file_bytes: bytes, user_id: str, filename: str) -> str:
        """
        Upload resume to S3.
        Returns: S3 object key (path)
        """
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            object_key = f"resumes/{user_id}/{timestamp}_{filename}"
            
            self.s3_client.put_object(
                Bucket=self.bucket,
                Key=object_key,
                Body=file_bytes,
                ContentType='application/pdf'
            )
            
            return object_key
        
        except Exception as e:
            raise Exception(f"S3 upload failed: {str(e)}")
    
    def get_resume_url(self, object_key: str) -> str:
        """Generate presigned URL for resume download."""
        return self.s3_client.generate_presigned_url(
            'get_object',
            Params={'Bucket': self.bucket, 'Key': object_key},
            ExpiresIn=3600  # 1 hour
        )
