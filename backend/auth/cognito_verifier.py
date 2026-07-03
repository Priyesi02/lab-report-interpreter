import os
import jwt
import requests
from fastapi import HTTPException, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from dotenv import load_dotenv

load_dotenv()

security = HTTPBearer()

REGION = os.getenv("COGNITO_REGION")
USER_POOL_ID = os.getenv("COGNITO_USER_POOL_ID")
# Cognito public keys URL used to cryptographically verify tokens
JWKS_URL = f"https://cognito-idp.{REGION}.amazonaws.com/{USER_POOL_ID}/.well-known/jwks.json"

# Download the public JSON Web Keys (JWK) from AWS Cognito
try:
    jwks = requests.get(JWKS_URL).json()
except Exception:
    jwks = {"keys": []}

def verify_cognito_token(credentials: HTTPAuthorizationCredentials = Security(security)):
    token = credentials.credentials
    try:
        # 1. Extract token headers to find the correct key ID (kid)
        unverified_header = jwt.get_unverified_header(token)
        kid = unverified_header.get("kid")
        
        # 2. Match the 'kid' against the downloaded AWS keys
        public_key = None
        for key in jwks.get("keys", []):
            if key.get("kid") == kid:
                public_key = jwt.algorithms.RSAAlgorithm.from_jwk(key)
                break
                
        if not public_key:
            raise HTTPException(status_code=401, detail="Invalid token signature metadata")
            
        # 3. Cryptographically decode and validate the token expiration
        payload = jwt.decode(
            token,
            public_key,
            algorithms=["RS256"],
            audience=os.getenv("COGNITO_APP_CLIENT_ID")
        )
        return payload  # This contains user_id, email, age, sex, etc.
        
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired. Please log in again.")
    except jwt.InvalidTokenError as e:
        raise HTTPException(status_code=401, detail=f"Invalid Authentication Token: {str(e)}")