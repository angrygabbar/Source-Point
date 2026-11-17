# Build context: coinback-finder directory in the SourcePoint repository.
FROM python:3.12-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /srv/backend

COPY backend/requirements.txt ./requirements.txt
RUN pip install --index-url=https://pypi.tuna.tsinghua.edu.cn/simple --default-timeout=120 --retries=10 -r requirements.txt

COPY backend/ /srv/backend/
COPY database/ /srv/database/

RUN useradd --create-home --uid 10001 app && chown -R app:app /srv
USER app

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=4).status == 200 else 1)"

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2", "--proxy-headers"]
