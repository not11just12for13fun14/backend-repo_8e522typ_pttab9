import os
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import FastAPI, Depends, HTTPException, status, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel, EmailStr
from jose import JWTError, jwt
from passlib.context import CryptContext

from database import db

app = FastAPI(title="FSM Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

SECRET_KEY = os.getenv("JWT_SECRET", "dev-secret-change-me")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"

class TokenData(BaseModel):
    email: Optional[str] = None

class UserPublic(BaseModel):
    id: Optional[str] = None
    name: str
    email: EmailStr
    role: str = "owner"
    is_active: bool = True
    organization: Optional[str] = None

class UserCreate(BaseModel):
    name: str
    email: EmailStr
    password: str
    organization: Optional[str] = None

class JobCreate(BaseModel):
    title: str
    customer_name: str
    customer_phone: str
    address: str
    scheduled_at: Optional[str] = None
    technician: Optional[str] = None


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def get_user_by_email(email: str):
    if db is None:
        raise HTTPException(status_code=500, detail="Database not configured")
    return db["authuser"].find_one({"email": email})


def get_current_user(token: str = Depends(oauth2_scheme)) -> UserPublic:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
        token_data = TokenData(email=email)
    except JWTError:
        raise credentials_exception
    user = get_user_by_email(token_data.email)
    if user is None:
        raise credentials_exception
    return UserPublic(
        id=str(user.get("_id")),
        name=user.get("name"),
        email=user.get("email"),
        role=user.get("role", "owner"),
        is_active=user.get("is_active", True),
        organization=user.get("organization"),
    )


@app.get("/")
def read_root():
    return {"message": "FSM Backend Running"}


@app.get("/test")
def test_database():
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": None,
        "database_name": None,
        "connection_status": "Not Connected",
        "collections": []
    }
    try:
        from database import db as _db
        if _db is not None:
            response["database"] = "✅ Available"
            response["database_url"] = "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set"
            response["database_name"] = _db.name
            response["connection_status"] = "Connected"
            try:
                collections = _db.list_collection_names()
                response["collections"] = collections[:10]
                response["database"] = "✅ Connected & Working"
            except Exception as e:
                response["database"] = f"⚠️ Connected but Error: {str(e)[:50]}"
        else:
            response["database"] = "⚠️ Available but not initialized"
    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:50]}"
    return response


@app.post("/auth/register", response_model=UserPublic)
def register(user: UserCreate):
    if db is None:
        raise HTTPException(500, "Database not configured")
    existing = get_user_by_email(user.email)
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    doc = {
        "name": user.name,
        "email": user.email,
        "password_hash": get_password_hash(user.password),
        "role": "owner",
        "is_active": True,
        "organization": user.organization,
    }
    new_id = db["authuser"].insert_one(doc).inserted_id
    return UserPublic(id=str(new_id), name=user.name, email=user.email, role="owner", is_active=True, organization=user.organization)


@app.post("/auth/login", response_model=Token)
async def login(username: str = Form(...), password: str = Form(...)):
    user = get_user_by_email(username)
    if not user or not verify_password(password, user.get("password_hash", "")):
        raise HTTPException(status_code=400, detail="Incorrect email or password")
    access_token = create_access_token({"sub": user["email"]})
    return Token(access_token=access_token)


@app.get("/auth/me", response_model=UserPublic)
def me(current_user: UserPublic = Depends(get_current_user)):
    return current_user


@app.post("/jobs")
def create_job(job: JobCreate, current_user: UserPublic = Depends(get_current_user)):
    if db is None:
        raise HTTPException(500, "Database not configured")
    data = job.model_dump()
    data.update({
        "status": "scheduled",
        "created_by": current_user.email,
        "organization": current_user.organization,
    })
    job_id = db["job"].insert_one(data).inserted_id
    return {"id": str(job_id), "message": "Job created"}


@app.get("/jobs")
def list_jobs(current_user: UserPublic = Depends(get_current_user)):
    if db is None:
        raise HTTPException(500, "Database not configured")
    query = {"organization": current_user.organization} if current_user.organization else {"created_by": current_user.email}
    jobs = list(db["job"].find(query).limit(50))
    for j in jobs:
        j["id"] = str(j.pop("_id"))
    return {"items": jobs}


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
