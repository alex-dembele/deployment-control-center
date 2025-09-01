FROM python:3.12
WORKDIR /app
COPY requirements.txt .
RUN apt-get update && apt-get install -y libpq-dev
RUN pip install -r requirements.txt
COPY . .
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]