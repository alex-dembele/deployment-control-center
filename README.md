# Deployment Platform

The Deployment Platform is a web-based application designed to streamline the deployment of microservices to Kubernetes clusters using ArgoCD. It provides a user-friendly interface for managing deployments, secrets, and approvals, with integration to GitHub for pull requests and DockerHub for image tags. The platform supports real-time status updates via WebSocket, notifications via Slack/Email, and a comprehensive deployment history.

## Table of Contents
- [Deployment Platform](#deployment-platform)
  - [Table of Contents](#table-of-contents)
  - [Features](#features)
  - [Architecture](#architecture)
  - [Prerequisites](#prerequisites)
  - [Installation](#installation)
  - [Configuration](#configuration)
  - [Usage](#usage)
    - [Backend Endpoints](#backend-endpoints)
    - [Frontend Interface](#frontend-interface)
  - [Testing](#testing)
  - [Contributing](#contributing)

## Features
- **Service Deployment**: Deploy microservices to DEV, STAG, or PROD environments with automated GitHub PR creation.
- **Secret Management**: Generate Kubernetes secrets for environment variables.
- **Approval Workflow**: Require approvals for STAG/PROD deployments with PR merge integration.
- **Real-Time Status**: WebSocket-based updates for PR and deployment status with Mermaid diagrams.
- **Deployment History**: Paginated history with filters by service and environment.
- **DockerHub Integration**: Fetch available tags for service images.
- **Notifications**: Slack and Email notifications for deployment events (pending, approved, rejected).
- **Error Handling**: Robust validation, Git conflict detection, and kubeconfig retries.

## Architecture
- **Backend**: FastAPI application with PostgreSQL for user and deployment data, integrated with GitHub, DockerHub, and Kubernetes.
- **Frontend**: React application with Material-UI, featuring a deployment wizard, approvals, and history views.
- **Infrastructure**:
  - Docker Compose for local development (backend, frontend, PostgreSQL).
  - ArgoCD for Kubernetes deployments, using ApplicationSet templates.
  - GitHub for configuration management (`nxh-applications-{env}` repos).
- **Workflow**:
  1. User logs in and initiates deployment via UI.
  2. Backend validates input, generates secrets/values YAML, updates ApplicationSet.
  3. GitHub PR created, logged in DB, and notified via Slack/Email (STAG/PROD requires approval).
  4. Real-time status updates via WebSocket.
  5. Post-approval, PR is merged, and ArgoCD syncs the deployment.

## Prerequisites
- **Docker** and **Docker Compose** for local development.
- **Python 3.12** for backend dependencies.
- **Node.js 18+** and **npm** for frontend.
- **GitHub Token** with repo access (`repo` scope).
- **DockerHub Credentials** for private image access.
- **Kubernetes Configs** (`~/.kube/{env}.yaml` for DEV/STAG/PROD).
- **PostgreSQL** database (local or remote).
- Optional: Slack Webhook URL and SMTP server for notifications.

## Installation
1. **Clone the Repository**:
   ```bash
   git clone https://github.com/nexahub/deployment-control-center.git
   cd deployment-control-center
   ```

2. **Set Up Environment Variables**:
   Copy `.env.example` to `.env` and fill in:
   ```bash
   cp .env.example .env
   ```
   Example `.env`:
   ```env
   DATABASE_URL=postgresql://user:pass@localhost:5432/deployment_db
   GITHUB_TOKEN=your_github_token
   DOCKERHUB_USERNAME=your_dockerhub_username
   DOCKERHUB_TOKEN=your_dockerhub_token
   KUBE_CONFIG_PATH=/root/.kube/{env}.yaml
   SLACK_WEBHOOK_URL=your_slack_webhook_url
   SMTP_SERVER=your_smtp_server
   SMTP_PORT=587
   SMTP_USER=your_smtp_user
   SMTP_PASSWORD=your_smtp_password
   SMTP_FROM=your_email@example.com
   SMTP_TO=recipient@example.com
   ```

3. **Build and Run with Docker Compose**:
   ```bash
   docker-compose build --no-cache
   docker-compose up -d
   ```

4. **Initialize Database**:
   ```bash
   docker-compose exec backend python -m models
   ```

5. **Access the Application**:
   - Backend: `http://localhost:8000`
   - Frontend: `http://localhost:3000`

## Configuration
- **Kubeconfigs**: Ensure `~/.kube/dev.yaml`, `~/.kube/stag.yaml`, and `~/.kube/prod.yaml` exist and are accessible to the backend container (mounted via Docker Compose).
- **GitHub Repositories**: Configure `nxh-applications-dev`, `nxh-applications-stag`, and `nxh-applications-prod` with write access for the `GITHUB_TOKEN`.
- **DockerHub**: Verify `DOCKERHUB_USERNAME` and `DOCKERHUB_TOKEN` have access to `nexah/*` repositories.
- **Notifications**: Provide `SLACK_WEBHOOK_URL` or SMTP settings for notifications.
- **Services**: Update `backend/templates.py` to add new services and their environment variables.

## Usage
### Backend Endpoints
- **Health Check**: `GET /health`
  - Returns: `{"status": "ok"}`
- **Suggest Tags**: `GET /suggest-tags/{org}/{repo}`
  - Example: `curl http://localhost:8000/suggest-tags/nexah/contract-api`
  - Returns available DockerHub tags.
- **Register User**: `POST /register`
  - Payload: `{"username": "test", "password": "pass"}`
- **Login**: `POST /login`
  - Payload: `{"username": "test", "password": "pass"}`
- **Generate Secret**: `POST /generate-secret`
  - Payload: `{"service": "contract-api", "env": "dev", "vars": {"NXH_DATABASE_HOST": "myhost"}, "secrets": ["NXH_DATABASE_HOST"], "namespace_type": "internal"}`
- **List Services**: `GET /services`
  - Returns available services and their environments.
- **Get Service Env Keys**: `GET /service-env-keys/{service}`
  - Example: `curl http://localhost:8000/service-env-keys/contract-api`
- **Deploy**: `POST /deploy`
  - Payload: `{"service": "contract-api", "tag": "v1.0.5", "env": "dev", "vars": {"NXH_DATABASE_HOST": "myhost", ...}, "secrets": ["NXH_DATABASE_HOST"], "namespace_type": "internal"}`
  - Creates PR, logs deployment, and notifies for STAG/PROD.
- **PR Status**: `GET /pr-status/{pr_id}`
  - Example: `curl http://localhost:8000/pr-status/123`
- **WebSocket Status**: `ws://localhost:8000/ws/pr-status/{deploy_id}`
  - Streams PR and deployment status updates.
- **List Pending Deployments**: `GET /deployments`
  - Returns pending STAG/PROD deployments.
- **Get Deployment**: `GET /deployments/{deploy_id}`
  - Returns deployment status.
- **Approve/Reject**: `POST /approve`
  - Payload: `{"deploy_id": 1, "approved": true}`
- **Deployment History**: `GET /deployments/history?service={service}&env={env}&page={page}&per_page={per_page}`
  - Example: `curl http://localhost:8000/deployments/history?service=contract-api&env=dev&page=1&per_page=10`

### Frontend Interface
- **Login**: Enter credentials to access the dashboard.
- **Services Tab**: View available services and initiate deployments.
- **Deploy Wizard**: Select service, tag, environment, and input vars/secrets.
- **Approvals Tab**: Approve/reject pending STAG/PROD deployments.
- **History Tab**: View deployment history with filters and pagination.
- **Status View**: Real-time updates via WebSocket with Mermaid diagrams.

## Testing
1. **Start Services**:
   ```bash
   docker-compose up -d
   ```
2. **Test Backend**:
   ```bash
   curl -X POST http://localhost:8000/register -d '{"username": "test", "password": "pass"}' -H "Content-Type: application/json"
   curl -X POST http://localhost:8000/login -d '{"username": "test", "password": "pass"}' -H "Content-Type: application/json"
   curl http://localhost:8000/services
   curl -X POST http://localhost:8000/deploy -d '{"service": "contract-api", "tag": "v1.0.5", "env": "dev", "vars": {"NXH_DATABASE_HOST": "myhost", "NXH_DATABASE_PORT": "5432", "NXH_DATABASE_NAME": "db", "NXH_DATABASE_USER": "user", "NXH_DATABASE_PASSWORD": "pass", "NXH_SHORTY_API_URL": "url", "NXH_SHORTY_API_KEY": "key", "NXH_SMS_API_URL": "url", "NXH_SMS_API_TOKEN": "token", "NXH_AWS_ACCESS_KEY_ID": "id", "NXH_AWS_SECRET_ACCESS_KEY": "key", "NXH_AWS_DEFAULT_REGION": "region", "NXH_AWS_BUCKET": "bucket", "NXH_AWS_USE_PATH_STYLE_ENDPOINT": "true", "NXH_AWS_SUPPRESS_PHP_DEPRECATION_WARNING": "true", "NXH_ORG_API_URL": "url", "NXH_AUTH_API_URL": "url", "NXH_APP_SLUG": "slug", "NXH_APP_ID": "id"}, "secrets": ["NXH_DATABASE_HOST"], "namespace_type": "internal"}' -H "Content-Type: application/json"
   ```
3. **Test Frontend**:
   - Open `http://localhost:3000`
   - Login, deploy a service, check status, approve a STAG deployment, and view history.
4. **Test WebSocket**:
   - Use a WebSocket client (e.g., Postman) to connect to `ws://localhost:8000/ws/pr-status/<deploy_id>`.

## Contributing
1. Fork the repository.
2. Create a feature branch (`git checkout -b feature/my-feature`).
3. Commit changes (`git commit -m "Add my feature"`).
4. Push to the branch (`git push origin feature/my-feature`).
5. Create a Pull Request.

