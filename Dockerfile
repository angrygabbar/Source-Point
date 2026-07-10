# --- USE FULL IMAGE (Pre-includes gcc & build tools to save RAM) ---
FROM python:3.11

# 1. Install runtime dependencies only
# (gcc and libpq-dev are already in this image, so we only need libmagic)
RUN apt-get update && apt-get install -y \
    libmagic1 \
    && rm -rf /var/lib/apt/lists/*

# 2. Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# 3. Set work directory
WORKDIR /app

# 4. Copy requirements file
COPY requirements.txt .

# 5. Install Python dependencies
# Upgrade pip first to avoid JSONDecodeError with old pip
RUN pip install --upgrade pip
# Increased timeout to prevent network hangups on slow connections
RUN pip install --no-cache-dir --default-timeout=300 --retries=5 -r requirements.txt

# 6. Copy the rest of the application code
COPY . .
RUN chmod +x /app/docker-entrypoint.sh

# 7. Expose the port the app runs on
EXPOSE 5000

# 8. Ensure database schema is ready, then run the application command
ENTRYPOINT ["/app/docker-entrypoint.sh"]
CMD ["gunicorn", "--worker-class", "gevent", "--workers", "3", "--timeout", "300", "--graceful-timeout", "60", "--keep-alive", "5", "--max-requests", "1000", "--max-requests-jitter", "100", "--bind", "0.0.0.0:5000", "app:app"]
