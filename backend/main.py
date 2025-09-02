from fastapi import FastAPI, Depends, HTTPException, status, WebSocket
import requests
import base64
import yaml
import os
from git import Repo
from github import Github
from tenacity import retry, stop_after_attempt, wait_fixed
from sqlalchemy import create_engine, Column, Integer, String, Boolean, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from pydantic import BaseModel
from typing import Dict, List
import bcrypt
from kubernetes import config
from .templates import get_service_template, get_service_env_keys, update_appset_yaml, get_services
from datetime import datetime
from git.exc import GitCommandError
import asyncio
import json


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

class Deployment(Base):
    __tablename__ = "deployments"
    id = Column(Integer, primary_key=True, index=True)
    service = Column(String)
    env = Column(String)
    tag = Column(String)
    pr_url = Column(String)
    status = Column(String, default="pending")
    created_at = Column(DateTime, default=datetime.utcnow)
    approved_by = Column(String, nullable=True)

Base.metadata.create_all(bind=engine)

# Utils
def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(plain_password.encode(), hashed_password.encode())

@retry(stop=stop_after_attempt(3), wait=wait_fixed(5))
def load_kubeconfig(env: str):
    kubeconfig_path = os.getenv("KUBE_CONFIG_PATH", f"/root/.kube/{env}.yaml")
    if not os.path.exists(kubeconfig_path):
        raise HTTPException(400, f"Kubeconfig not found: {kubeconfig_path}")
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

    class Config:
        extra = "forbid"

class DeployInput(BaseModel):
    service: str
    tag: str
    env: str
    vars: Dict[str, str]
    secrets: List[str]
    namespace_type: str

    class Config:
        extra = "forbid"

    def validate(self):
        if self.env not in ["dev", "stag", "prod"]:
            raise HTTPException(400, f"Invalid env: {self.env}")
        if self.namespace_type not in ["internal", "external"]:
            raise HTTPException(400, f"Invalid namespace_type: {self.namespace_type}")
        # Pas de validation stricte sur vars/secrets pour permettre custom projects
        if not all(s in self.vars for s in self.secrets):
            raise HTTPException(400, "Secrets must be a subset of vars")

class NotifyInput(BaseModel):
    service: str
    env: str
    pr_url: str
    status: str

class ApproveInput(BaseModel):
    deploy_id: int
    approved: bool

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
def generate_secret(input: SecretInput, db: Session = Depends(get_db)):
    input.validate()
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
def get_services_endpoint():
    return {"services": get_services()}

@app.get("/service-env-keys/{service}")
def get_service_env_keys_endpoint(service: str):
    return {"keys": get_service_env_keys(service)}

@retry(stop=stop_after_attempt(3), wait=wait_fixed(5))
@app.post("/deploy")
def deploy(input: DeployInput, db: Session = Depends(get_db)):
    input.validate()
    try:
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
        try:
            repo.git.checkout(branch_name)
            repo.git.pull('origin', branch_name)
        except GitCommandError:
            repo.git.checkout('-b', branch_name)
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
        template = get_service_template(input.service, input.tag, input.namespace_type)
        values_path = f"{clone_path}/nxh-{input.service}-ms-values.yaml"  # À la racine
        with open(values_path, "w") as f:
            yaml.dump(template, f)
        appset_path = f"{clone_path}/01-nxh-applications-appset/nxh-applications-appset-{input.env}.yaml"
        update_appset_yaml(appset_path, input.service, input.env)
        repo.git.add(all=True)
        repo.git.commit('-m', f"Deploy {input.service} {input.tag} to {input.env}", allow_empty=True)
        try:
            repo.git.push('--set-upstream', 'origin', branch_name)
        except GitCommandError as e:
            if "push declined" in str(e).lower():
                raise HTTPException(400, "Push declined: possible conflict or permissions issue")
            raise
        try:
            pr = gh_repo.create_pull(title=f"Auto Deploy: {input.service} to {input.tag}", body="Automated deployment", head=branch_name, base="main")
        except Exception as e:
            if "already exists" in str(e).lower():
                raise HTTPException(400, f"PR already exists for {branch_name}")
            raise
        deployment = Deployment(
            service=input.service,
            env=input.env,
            tag=input.tag,
            pr_url=pr.html_url,
            status="pending" if input.env in ["stag", "prod"] else "approved"
        )
        db.add(deployment)
        db.commit()
        if input.env in ["stag", "prod"]:
            notify({"service": input.service, "env": input.env, "pr_url": pr.html_url, "status": "pending"})
        return {"pr_url": pr.html_url, "deploy_id": deployment.id}
    except Exception as e:
        raise HTTPException(500, str(e))

@app.get("/pr-status/{pr_id}")
def get_pr_status(pr_id: int):
    gh = Github(os.getenv("GITHUB_TOKEN"))
    repo_name = "nxh-applications-dev"  # TODO: Dynamique par env
    repo = gh.get_repo(f"nexahub/{repo_name}")
    try:
        pr = repo.get_pull(pr_id)
        return {"status": pr.state, "merged": pr.merged, "url": pr.html_url}
    except Exception:
        raise HTTPException(404, f"PR {pr_id} not found")

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

@app.get("/deployments")
def get_deployments(db: Session = Depends(get_db)):
    deployments = db.query(Deployment).filter(Deployment.status == "pending").all()
    return {"deployments": [{"id": d.id, "service": d.service, "env": d.env, "tag": d.tag, "pr_url": d.pr_url} for d in deployments]}

@app.get("/deployments/{deploy_id}")
def get_deployment(deploy_id: int, db: Session = Depends(get_db)):
    deployment = db.query(Deployment).filter(Deployment.id == deploy_id).first()
    if not deployment:
        raise HTTPException(404, "Deployment not found")
    return {"status": deployment.status}

@app.post("/approve")
def approve_deployment(input: ApproveInput, db: Session = Depends(get_db)):
    deployment = db.query(Deployment).filter(Deployment.id == input.deploy_id).first()
    if not deployment:
        raise HTTPException(404, "Deployment not found")
    if deployment.status != "pending":
        raise HTTPException(400, "Deployment already processed")
    deployment.status = "approved" if input.approved else "rejected"
    deployment.approved_by = "admin"  # TODO: Récupérer user depuis auth
    db.commit()
    if input.approved:
        gh = Github(os.getenv("GITHUB_TOKEN"))
        repo_name = f"nxh-applications-{deployment.env}"
        repo = gh.get_repo(f"nexahub/{repo_name}")
        try:
            pr = repo.get_pull(int(deployment.pr_url.split('/')[-1]))
            pr.merge()
            notify({"service": deployment.service, "env": deployment.env, "pr_url": deployment.pr_url, "status": "approved"})
        except Exception as e:
            raise HTTPException(500, f"Failed to merge PR: {str(e)}")
    else:
        notify({"service": deployment.service, "env": deployment.env, "pr_url": deployment.pr_url, "status": "rejected"})
    return {"msg": "Deployment processed"}

@app.websocket("/ws/pr-status/{deploy_id}")
async def websocket_pr_status(websocket: WebSocket, deploy_id: int, db: Session = Depends(get_db)):
    await websocket.accept()
    try:
        while True:
            deployment = db.query(Deployment).filter(Deployment.id == deploy_id).first()
            if not deployment:
                await websocket.send_json({"error": "Deployment not found"})
                break
            gh = Github(os.getenv("GITHUB_TOKEN"))
            repo_name = f"nxh-applications-{deployment.env}"
            repo = gh.get_repo(f"nexahub/{repo_name}")
            try:
                pr = repo.get_pull(int(deployment.pr_url.split('/')[-1]))
                status = {"status": pr.state, "merged": pr.merged, "url": pr.html_url, "deploy_status": deployment.status}
            except Exception:
                status = {"error": f"PR not found for deploy_id {deploy_id}", "deploy_status": deployment.status}
            await websocket.send_json(status)
            await asyncio.sleep(5)
    except Exception as e:
        await websocket.send_json({"error": str(e)})
    finally:
        await websocket.close()