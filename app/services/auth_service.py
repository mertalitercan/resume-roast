import firebase_admin
from firebase_admin import credentials, auth
from app.config import get_settings

settings = get_settings()

# Initialize Firebase Admin
cred_dict = {
    "type": "service_account",
    "project_id": settings.firebase_project_id,
    "private_key": settings.firebase_private_key.replace('\\n', '\n'),
    "client_email": settings.firebase_client_email,
    "token_uri": "https://oauth2.googleapis.com/token",
}

cred = credentials.Certificate(cred_dict)
firebase_admin.initialize_app(cred)

class AuthService:
    @staticmethod
    def verify_token(id_token: str) -> dict:
        """
        Verify Firebase ID token.
        Returns: User info dict
        """
        try:
            decoded_token = auth.verify_id_token(id_token)
            return {
                'uid': decoded_token['uid'],
                'email': decoded_token.get('email'),
                'name': decoded_token.get('name')
            }
        except Exception as e:
            raise Exception(f"Token verification failed: {str(e)}")
