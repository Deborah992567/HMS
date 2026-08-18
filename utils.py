from passlib.context import CryptContext
from datetime import datetime, timedelta
from jose import jwt, JWTError
try:
    import stripe
except Exception:
    stripe = None
from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from models import Staff, Patient
from database import get_db

# --- Auth ---
SECRET_KEY = "your_secret_key"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60
# No refresh tokens: JWT-only authentication
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

def verify_password(plain, hashed):
    return pwd_context.verify(plain, hashed)

def get_password_hash(password):
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta=None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)




def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("user_id")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid token")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
    user = db.query(Staff).filter(Staff.id == user_id).first()
    if user is None:
        raise HTTPException(status_code=401, detail="User not found")
    return user

def get_current_patient(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        patient_id = payload.get("patient_id")
        if patient_id is None:
            raise HTTPException(status_code=401, detail="Patient sign-in required")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
    patient = db.query(Patient).filter(Patient.id == patient_id).first()
    if patient is None:
        raise HTTPException(status_code=401, detail="Patient not found")
    return patient

def require_roles(*roles):
    def wrapper(user: Staff = Depends(get_current_user)):
        user_roles = [r.name for r in user.roles]
        if not any(role in user_roles for role in roles):
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        return user
    return wrapper

# --- Payment ---
if stripe:
    stripe.api_key = "your_stripe_secret_key"

def create_payment_intent(amount: float, currency="usd"):
    if stripe is None:
        # Stripe not installed in this environment (tests/dev). Return a dummy client secret.
        return "test_client_secret"
    try:
        intent = stripe.PaymentIntent.create(
            amount=int(amount*100),
            currency=currency
        )
        return intent.client_secret
    except Exception:
        raise HTTPException(status_code=500, detail="Payment provider error")
