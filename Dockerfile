# Full Python image includes the compiler and build tools needed by dependencies.
FROM python:3.11-bookworm

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set work directory
WORKDIR /app

# Render and OCR image-only bank schedules locally inside the app container.
RUN apt-get update \
    && apt-get install -y --no-install-recommends poppler-utils tesseract-ocr \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements file
COPY requirements.txt .

# Install prebuilt Python wheels in production without requiring network access
# in BuildKit. Local builds can install directly from PyPI.
ARG PREBUILT_WHEELS=0
COPY .docker-wheelhouse /wheelhouse
RUN if [ "$PREBUILT_WHEELS" = "1" ]; then \
        python -m pip install --no-index --find-links=/wheelhouse -r requirements.txt; \
    else \
        python -m pip install --no-cache-dir --default-timeout=300 --retries=5 -r requirements.txt; \
    fi \
    && rm -rf /wheelhouse

# Copy the rest of the application code
COPY . .
RUN chmod +x /app/docker-entrypoint.sh

# Expose the port the app runs on
EXPOSE 5000

# Ensure database schema is ready, then run the application command
ENTRYPOINT ["/app/docker-entrypoint.sh"]
CMD ["gunicorn", "--worker-class", "gevent", "--workers", "3", "--timeout", "300", "--graceful-timeout", "60", "--keep-alive", "5", "--max-requests", "1000", "--max-requests-jitter", "100", "--bind", "0.0.0.0:5000", "app:app"]
