from fastapi import FastAPI
import requests  # Pour DockerHub API
import base64    # Pour encoding secrets
from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from .models import SessionLocal, User
from .utils import hash_password, verify_password

app = FastAPI()

class UserCreate(BaseModel):
    username: str
    password: str

class UserLogin(BaseModel):
    username: str
    password: str

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/suggest-tags/{repo}")
def suggest_tags(repo: str):
    
    url = f"https://hub.docker.com/v2/repositories/{repo}/tags?page_size=10"
    response = requests.get(url)
    if response.status_code == 200:
        tags = [tag['name'] for tag in response.json()['results']]
        return {"tags": tags}
    return {"error": "Failed to fetch tags"}

@app.post("/register")
def register(user: UserCreate, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.username == user.username).first()
    if existing:
        raise HTTPException(status_code=400, detail="Username exists")
    hashed = hash_password(user.password)
    new_user = User(username=user.username, hashed_password=hashed)
    db.add(new_user)
    db.commit()
    return {"msg": "User created"}

@app.post("/login")
def login(user: UserLogin, db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.username == user.username).first()
    if not db_user or not verify_password(user.password, db_user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    return {"msg": "Login successful", "user": user.username}