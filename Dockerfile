FROM python:3.9-slim-buster  # Explicitly use Python 3.9 on Debian Buster

WORKDIR /app

# Install system dependencies including distutils
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    gcc \
    python3-dev \
    python3-distutils \  # Explicitly install distutils
    && rm -rf /var/lib/apt/lists/*

# Ensure pip is upgraded first
RUN python -m pip install --upgrade pip==23.1.2 setuptools==65.5.1 wheel==0.38.4

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

RUN mkdir -p templates  # Ensure templates directory exists

COPY . .

CMD ["gunicorn", "--bind", "0.0.0.0:10000", "app:app"]