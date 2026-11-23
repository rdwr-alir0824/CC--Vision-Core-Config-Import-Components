FROM python:3.13-slim

ENV PYTHONPATH=/app/src \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY master.py ./
COPY src/ ./src/
COPY examples/offline-controller/ ./examples/offline-controller/

USER 10001:10001

ENTRYPOINT ["python", "/app/master.py"]
