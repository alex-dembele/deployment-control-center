from fastapi import FastAPI
from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from .models import SessionLocal, User
from .utils import hash_password, verify_password
from pydantic import BaseModel
from typing import Dict
import yaml
import requests  # Pour DockerHub API
import base64    # Pour encoding secrets

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

class SecretInput(BaseModel):
    service: str
    env: str  # dev/stag/prod
    vars: Dict[str, str]  # { "NXH_DATABASE_HOST": "value", ... }
    secrets: list[str]  # Liste des keys qui sont secrets

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

@app.post("/generate-secret")
def generate_secret(input: SecretInput):
    data = {}
    for key, value in input.vars.items():
        if key in input.secrets:
            data[key] = base64.b64encode(value.encode()).decode()
        else:
            data[key] = base64.b64encode(value.encode()).decode()  # Encode tout pour YAML, mais seulement secrets masqués UI

    yaml_content = {
        "apiVersion": "v1",
        "kind": "Secret",
        "metadata": {
            "name": f"nxh-{input.service}-db-secr-{input.env}",
            "namespace": f"nxh-internal-services-ns-{input.env}"
        },
        "type": "Opaque",
        "data": data
    }

    # Sauvegarde en fichier exemple (pour Git plus tard)
    file_path = f"generated/{input.service}-secret.yaml"
    os.makedirs("generated", exist_ok=True)
    with open(file_path, "w") as f:
        yaml.dump(yaml_content, f)

    return {"yaml": yaml_content, "file": file_path}