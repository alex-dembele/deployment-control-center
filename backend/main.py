from fastapi import FastAPI, Depends, HTTPException, status
import requests
import base64
import yaml
import os
from git import Repo
from github import Github
from tenacity import retry, stop_after_attempt, wait_fixed
from sqlalchemy import create_engine, Column, Integer, String, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from pydantic import BaseModel
from typing import Dict
import bcrypt

app = FastAPI()

# Database Setup
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://user:pass@localhost:5432/deployment_db")
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    is_active = Column(Boolean, default=True)

# Create tables if not exist
Base.metadata.create_all(bind=engine)

# Utils for hashing
def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(plain_password.encode(), hashed_password.encode())

# Pydantic Models
class UserCreate(BaseModel):
    username: str
    password: str

class UserLogin(BaseModel):
    username: str
    password: str

class SecretInput(BaseModel):
    service: str
    env: str  # dev/stag/prod
    vars: Dict[str, str]  # { "NXH_DATABASE_HOST": "value", ... }
    secrets: list[str]  # Liste des keys qui sont secrets
    namespace_type: str  # "internal" or "external"

class DeployInput(BaseModel):
    service: str
    tag: str
    env: str
    vars: Dict[str, str]
    secrets: list[str]
    namespace_type: str  # "internal" or "external"

# DB Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Endpoints

@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/suggest-tags/{org}/{repo}")
def suggest_tags(org: str, repo: str):
    username = os.getenv("DOCKERHUB_USERNAME")
    token = os.getenv("DOCKERHUB_TOKEN")
    if not username or not token:
        return {"error": "DockerHub credentials missing"}

    # Login pour JWT
    login_url = "https://hub.docker.com/v2/users/login"
    login_data = {"username": username, "password": token}
    login_res = requests.post(login_url, json=login_data)
    if login_res.status_code != 200:
        return {"error": "DockerHub login failed"}
    jwt = login_res.json()["token"]

    # Query tags avec auth
    url = f"https://hub.docker.com/v2/repositories/{org}/{repo}/tags?page_size=10"
    headers = {"Authorization": f"JWT {jwt}"}
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        tags = [tag['name'] for tag in response.json()['results']]
        return {"tags": tags}
    return {"error": f"Failed to fetch tags: {response.text}"}

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
    return {"msg": "Login successful", "user": user.username}  # Ajoute JWT plus tard

@app.post("/generate-secret")
def generate_secret(input: SecretInput):
    data = {}
    for key, value in input.vars.items():
        data[key] = base64.b64encode(value.encode()).decode()  # Encode tout en Base64 comme dans l'exemple

    namespace = f"nxh-{input.namespace_type}-services-ns-{input.env}"  # internal ou external

    yaml_content = {
        "apiVersion": "v1",
        "kind": "Secret",
        "metadata": {
            "name": f"nxh-{input.service}-db-secr-{input.env}",
            "namespace": namespace
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

@app.get("/services")
def get_services():
    # Hardcoded exemple ; plus tard DB ou scan Git
    services = [
        {"name": "validation-api", "envs": ["dev", "stag"], "current_tag_dev": "v1.0.0", "current_tag_stag": "v0.9.0"},
        {"name": "billing-api", "envs": ["dev"], "current_tag_dev": "v2.1.0"},
        # Ajoute plus basés sur tes micros
    ]
    return {"services": services}

@retry(stop=stop_after_attempt(3), wait=wait_fixed(5))
@app.post("/deploy")
def deploy(input: DeployInput):
    try:
        gh = Github(os.getenv("GITHUB_TOKEN"))
        repo_name = f"nxh-applications-{input.env}"  # dev ou stag
        gh_repo = gh.get_repo(f"nexahub/{repo_name}")

        # Clone local
        clone_url = f"https://github.com/nexahub/{repo_name}.git"
        clone_path = f"clones/{repo_name}"
        if not os.path.exists(clone_path):
            Repo.clone_from(clone_url, clone_path)

        repo = Repo(clone_path)
        branch_name = f"auto-deploy/{input.service}-{input.tag}"
        repo.git.checkout('-b', branch_name)

        # Générer secret.yaml
        data = {k: base64.b64encode(v.encode()).decode() for k, v in input.vars.items()}
        namespace = f"nxh-{input.namespace_type}-services-ns-{input.env}"
        yaml_content = {
            "apiVersion": "v1",
            "kind": "Secret",
            "metadata": {
                "name": f"nxh-{input.service}-db-secr-{input.env}",
                "namespace": namespace
            },
            "type": "Opaque",
            "data": data
        }
        secrets_path = f"{clone_path}/02-nxh-database-config/nxh-{input.service}-db-secr-{input.env}.yaml"
        os.makedirs(os.path.dirname(secrets_path), exist_ok=True)
        with open(secrets_path, "w") as f:
            yaml.dump(yaml_content, f)

        # Ajoute values.yaml et ApplicationSet (TODO: implémenter templates complets)
        # Pour l'instant, placeholder
        # values_path = f"{clone_path}/path/to/values.yaml"
        # with open(values_path, "w") as f:
        #     yaml.dump({"image": {"tag": input.tag}}, f)

        repo.git.add(all=True)
        repo.git.commit('-m', f"Deploy {input.service} {input.tag} to {input.env}")
        repo.git.push('--set-upstream', 'origin', branch_name)

        # Créer PR
        pr = gh_repo.create_pull(title=f"Auto Deploy: {input.service} to {input.tag}", body="Automated deployment", head=branch_name, base="main")

        return {"pr_url": pr.html_url}
    except Exception as e:
        raise HTTPException(500, str(e))