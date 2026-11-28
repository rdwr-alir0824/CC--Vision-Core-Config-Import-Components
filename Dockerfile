
FROM python:3.13-slim AS base

ENV PYTHONPATH=/app/src \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# CCV Core application
FROM base AS core

COPY src/cc_vision_import/__init__.py \
     src/cc_vision_import/_contract_validation.py \
     src/cc_vision_import/_json.py \
     src/cc_vision_import/authentication.py \
     src/cc_vision_import/backup_policy.py \
     src/cc_vision_import/ccv.py \
     src/cc_vision_import/client.py \
     src/cc_vision_import/config.py \
     src/cc_vision_import/contracts.py \
     src/cc_vision_import/files.py \
     src/cc_vision_import/http_backend.py \
     src/cc_vision_import/objects.py \
     src/cc_vision_import/tls_policy.py \
     src/cc_vision_import/transport.py \
     /app/src/cc_vision_import/

WORKDIR /data

USER 10001:10001

ENTRYPOINT ["python", "-m", "cc_vision_import.ccv"]

# Preserve the existing default build
FROM base AS existing

COPY master.py ./
COPY src/ ./src/
COPY examples/offline-controller/ ./examples/offline-controller/

USER 10001:10001

ENTRYPOINT ["python", "/app/master.py"]