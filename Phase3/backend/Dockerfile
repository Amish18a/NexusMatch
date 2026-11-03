FROM python:3.12-slim

WORKDIR /app

COPY Phase2/requirements-docker.txt /app/Phase2/requirements-docker.txt
RUN pip install --no-cache-dir -r /app/Phase2/requirements-docker.txt
RUN pip install --no-cache-dir fastapi==0.115.12 uvicorn[standard]==0.34.2 pydantic==2.11.4

COPY Phase2/inference /app/Phase2/inference
COPY Phase2/ml/artifacts/final_trust_model.joblib /app/Phase2/ml/artifacts/final_trust_model.joblib
COPY Phase3/backend /app/Phase3/backend

ENV PYTHONPATH=/app
ENV NEXUSMATCH_DATA_DIR=/app/data
EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--app-dir", "/app/Phase3/backend", "--host", "0.0.0.0", "--port", "8000"]
