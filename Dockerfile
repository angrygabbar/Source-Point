# Full Python image includes the compiler and build tools needed by dependencies.
FROM python:3.11-bookworm

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set work directory
WORKDIR /app

# Copy requirements file
COPY requirements.txt .

# Install Python dependencies
# Upgrade pip first to avoid JSONDecodeError with old pip
RUN pip install --upgrade pip
# Increased timeout to prevent network hangups on slow connections
RUN pip install --no-cache-dir --default-timeout=300 --retries=5 -r requirements.txt

# Copy the rest of the application code
COPY . .
RUN chmod +x /app/docker-entrypoint.sh

# Expose the port the app runs on
EXPOSE 5000

# Ensure database schema is ready, then run the application command
ENTRYPOINT ["/app/docker-entrypoint.sh"]
CMD ["gunicorn", "--worker-class", "gevent", "--workers", "3", "--timeout", "300", "--graceful-timeout", "60", "--keep-alive", "5", "--max-requests", "1000", "--max-requests-jitter", "100", "--bind", "0.0.0.0:5000", "app:app"]
