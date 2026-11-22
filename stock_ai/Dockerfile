FROM python:3.11-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates libgomp1 \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --system app \
    && useradd --system --gid app --create-home app

WORKDIR /app

COPY requirements.txt ./
ARG PREBUILT_WHEELS=0
COPY .docker-wheelhouse /wheelhouse
RUN if [ "$PREBUILT_WHEELS" = "1" ]; then \
        pip install --no-index --find-links=/wheelhouse -r requirements.txt && \
        pip install --no-index --find-links=/wheelhouse --no-deps xgboost==3.2.0; \
    else \
        pip install --no-cache-dir -r requirements.txt && \
        pip install --no-cache-dir --no-deps xgboost==3.2.0; \
    fi \
    && rm -rf /wheelhouse

COPY --chown=app:app *.py ./
COPY --chown=app:app templates ./templates
COPY --chown=app:app stock_ai_brain_v2.pkl ./
RUN mkdir -p /app/models && chown app:app /app/models
USER app

EXPOSE 5001

CMD ["sh", "-c", "python db_manager.py && exec python app.py"]
