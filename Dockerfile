# 1. Use the same Python version as your server
FROM python:3.12-slim

# 2. Set the working directory inside the container
WORKDIR /app

# 3. Install system dependencies (required for some Python packages like Postgres/Pillow)
# Added 'libmagic1' which is often needed for file type detection in Python
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    libmagic1 \
    && rm -rf /var/lib/apt/lists/*

# 4. Copy requirements first (optimizes build speed)
COPY requirements.txt .

# 5. Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# 6. Copy the rest of the application code
COPY . .

# 7. Expose the port used by Flask/Gunicorn
EXPOSE 5000

# 8. Command to run the app using Gunicorn
# OPTIMIZATION: Increased workers from 3 to 12
# Formula: (2 x CPUs) + 1. Assuming 4+ vCPUs on a 12GB server, 9-12 workers is safe.
# This allows 12 concurrent requests to be processed instantly.
CMD ["gunicorn", "--workers", "12", "--bind", "0.0.0.0:5000", "app:app"]