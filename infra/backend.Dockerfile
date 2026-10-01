FROM python:3.11-slim
WORKDIR /app
ENV PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
COPY backend/requirements.txt /tmp/requirements.txt
RUN pip install -r /tmp/requirements.txt && pip install torch --index-url https://download.pytorch.org/whl/cpu && pip install 'monai>=1.4,<2'
COPY backend backend
COPY ml ml
COPY src src
COPY scripts scripts
COPY alembic.ini pyproject.toml ./
RUN mkdir -p storage data
EXPOSE 8000
