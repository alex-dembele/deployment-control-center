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
from typing import Dict, List
import bcrypt
from kubernetes import config
from .templates import get_service_template, get_service_env_keys, update_appset_yaml

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

Base.metadata.create_all(bind=engine)

# Utils
def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(plain_password.encode(), hashed_password.encode())

# Load kubeconfig with retries
@retry(stop=stop_after_attempt(3), wait=wait_fixed(5))
def load_kubeconfig(env: str):
    kubeconfig_path = os.getenv("KUBE_CONFIG_PATH", f"~/.kube/{env}.yaml")
    try:
        config.load_kube_config(config_file=kubeconfig_path)
    except Exception as e:
        raise HTTPException(500, f"Failed to load kubeconfig for {env}: {str(e)}")

# Pydantic Models
class UserCreate(BaseModel):
    username: str
    password: str

class UserLogin(BaseModel):
    username: str
    password: str

class SecretInput(BaseModel):
    service: str
    env: str
    vars: Dict[str, str]
    secrets: List[str]
    namespace_type: str

class DeployInput(BaseModel):
    service: str
    tag: str
    env: str
    vars: Dict[str, str]
    secrets: List[str]
    namespace_type: str

class NotifyInput(BaseModel):
    service: str
    env: str
    pr_url: str
    status: str

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

    login_url = "https://hub.docker.com/v2/users/login"
    login_data = {"username": username, "password": token}
    login_res = requests.post(login_url, json=login_data)
    if login_res.status_code != 200:
        return {"error": "DockerHub login failed"}
    jwt = login_res.json()["token"]

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
    return {"msg": "Login successful", "user": user.username}

@app.post("/generate-secret")
def generate_secret(input: SecretInput):
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
    file_path = f"generated/{input.service}-secret.yaml"
    os.makedirs("generated", exist_ok=True)
    with open(file_path, "w") as f:
        yaml.dump(yaml_content, f)
    return {"yaml": yaml_content, "file": file_path}

@app.get("/services")
def get_services():
    services = [
        {"name": "contract-api", "envs": ["dev", "stag"], "current_tag_dev": "v1.0.4", "current_tag_stag": "v0.9.0"},
        {"name": "contract-web-admin", "envs": ["dev"], "current_tag_dev": "v1.0.2"},
        {"name": "retail-api", "envs": ["dev", "stag"], "current_tag_dev": "v1.0.14", "current_tag_stag": "v1.0.10"},
        {"name": "retail-web-admin", "envs": ["dev"], "current_tag_dev": "v1.0.3"}
    ]
    return {"services": services}

@app.get("/service-env-keys/{service}")
def get_service_env_keys_endpoint(service: str):
    return {"keys": get_service_env_keys(service)}

@retry(stop=stop_after_attempt(3), wait=wait_fixed(5))
@app.post("/deploy")
def deploy(input: DeployInput, db: Session = Depends(get_db)):
    try:
        # Load kubeconfig
        load_kubeconfig(input.env)

        gh = Github(os.getenv("GITHUB_TOKEN"))
        repo_name = f"nxh-applications-{input.env}"
        gh_repo = gh.get_repo(f"nexahub/{repo_name}")

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

        # Générer values.yaml
        template = get_service_template(input.service, input.tag)
        values_path = f"{clone_path}/04-nxh-services-ms/nxh-{input.service}-ms-values.yaml"
        os.makedirs(os.path.dirname(values_path), exist_ok=True)
        with open(values_path, "w") as f:
            yaml.dump(template, f)

        # Mettre à jour ApplicationSet
        appset_path = f"{clone_path}/01-nxh-applications-appset/nxh-applications-appset-{input.env}.yaml"
        update_appset_yaml(appset_path, input.service, input.env)

        repo.git.add(all=True)
        repo.git.commit('-m', f"Deploy {input.service} {input.tag} to {input.env}")
        repo.git.push('--set-upstream', 'origin', branch_name)

        pr = gh_repo.create_pull(title=f"Auto Deploy: {input.service} to {input.tag}", body="Automated deployment", head=branch_name, base="main")

        # Log déploiement dans DB
        # TODO: Créer table deployments si besoin
        if input.env in ["stag", "prod"]:
            # TODO: Créer demande approbation dans DB
            notify({"service": input.service, "env": input.env, "pr_url": pr.html_url, "status": "pending"})

        return {"pr_url": pr.html_url}
    except Exception as e:
        raise HTTPException(500, str(e))

@app.get("/pr-status/{pr_id}")
def get_pr_status(pr_id: int):
    gh = Github(os.getenv("GITHUB_TOKEN"))
    repo_name = "nxh-applications-dev"  # TODO: Dynamique par env
    repo = gh.get_repo(f"nexahub/{repo_name}")
    pr = repo.get_pull(pr_id)
    return {"status": pr.state, "merged": pr.merged, "url": pr.html_url}

@app.post("/notify")
def notify(input: NotifyInput):
    slack_webhook = os.getenv("SLACK_WEBHOOK_URL")
    smtp_server = os.getenv("SMTP_SERVER")
    if slack_webhook:
        requests.post(slack_webhook, json={
            "text": f"Deployment {input.status} for {input.service} in {input.env}: {input.pr_url}"
        })
    if smtp_server:
        # TODO: Implémenter envoi email via smtplib
        pass
    return {"msg": "Notification sent"}