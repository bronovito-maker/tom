FROM python:3.11-slim

# Install system dependencies for WeasyPrint
RUN apt-get update && apt-get install -y \
    libpango-1.0-0 \
    libharfbuzz0b \
    libpangoft2-1.0-0 \
    libharfbuzz-subset0 \
    libffi-dev \
    libjpeg-dev \
    libopenjp2-7-dev \
    shared-mime-info \
    libcairo2 \
    libgdk-pixbuf2.0-0 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Set up application directory
WORKDIR /app

# Copy requirements and install python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source code
COPY . .

# Expose port and start command
EXPOSE 3000
CMD ["uvicorn", "app:api", "--host", "0.0.0.0", "--port", "3000"]
