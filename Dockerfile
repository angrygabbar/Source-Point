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
# Increased timeout to prevent network hangups on slow connections
RUN pip install --no-cache-dir --default-timeout=100 -r requirements.txt

# 6. Copy the rest of the application code
COPY . .

# 7. Expose the port the app runs on
EXPOSE 5000

# 8. Define the command to run the application
CMD ["gunicorn", "--worker-class", "gevent", "--workers", "1", "--bind", "0.0.0.0:5000", "app:app"]