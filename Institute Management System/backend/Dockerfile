FROM python:3.12.8-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends libpq5 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
ARG PREBUILT_WHEELS=0
COPY .docker-wheelhouse /wheelhouse
RUN if [ "$PREBUILT_WHEELS" = "1" ]; then \
      pip install --no-index --find-links /wheelhouse -r requirements.txt; \
    else \
      pip install -r requirements.txt; \
    fi \
    && rm -rf /wheelhouse

RUN groupadd --system app && useradd --system --gid app --home /app app
COPY --chown=app:app . .

USER app
EXPOSE 8000

CMD ["gunicorn", "app.main:app", "-k", "uvicorn.workers.UvicornWorker", "-w", "3", "-b", "0.0.0.0:8000"]
