# backend/middleware/auth.py
import os
import firebase_admin
from firebase_admin import auth, credentials
from fastapi import HTTPException, Security, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

# Initialize Firebase Admin once at module load
_cred_path = os.getenv("FIREBASE_SERVICE_ACCOUNT_PATH", "serviceAccountKey.json")
if not firebase_admin._apps:
    if os.path.exists(_cred_path):
        cred = credentials.Certificate(_cred_path)
        firebase_admin.initialize_app(cred)
    else:
        # Allow dev mode without a real key (returns a mock user)
        firebase_admin.initialize_app()

security = HTTPBearer(auto_error=False)

async def verify_firebase_token(
    credentials: HTTPAuthorizationCredentials = Security(security),
) -> dict:
    """
    FastAPI dependency. Validates the Firebase ID token from the
    Authorization: Bearer <token> header.
    Returns the decoded token dict (includes uid, email, etc).
    """
    if credentials is None:
        raise HTTPException(
            status_code=401,
            detail="Authorization header missing.",
        )
    token = credentials.credentials
    try:
        decoded = auth.verify_id_token(token)
        return decoded
    except auth.ExpiredIdTokenError:
        raise HTTPException(status_code=401, detail="Token expired.")
    except auth.InvalidIdTokenError:
        raise HTTPException(status_code=401, detail="Invalid token.")
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Authentication failed: {str(e)}")