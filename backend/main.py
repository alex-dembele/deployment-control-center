from fastapi import FastAPI
import requests  # Pour DockerHub API
import base64    # Pour encoding secrets

app = FastAPI()

@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/suggest-tags/{repo}")
def suggest_tags(repo: str):
    # Exemple: Query DockerHub API (ajoute auth plus tard)
    url = f"https://hub.docker.com/v2/repositories/{repo}/tags?page_size=10"
    response = requests.get(url)
    if response.status_code == 200:
        tags = [tag['name'] for tag in response.json()['results']]
        return {"tags": tags}
    return {"error": "Failed to fetch tags"}