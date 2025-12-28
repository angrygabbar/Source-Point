# 1. Use the same Python version as your server
FROM python:3.12-slim

# 2. Set the working directory inside the container
WORKDIR /app

# 3. Install system dependencies (required for some Python packages like Postgres/Pillow)
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
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
# (We use 0.0.0.0 to make it accessible outside the container)
CMD ["gunicorn", "--workers", "3", "--bind", "0.0.0.0:5000", "app:app"]