# Use the official Python 3.12 slim image as the base
FROM python:3.12-slim

# Prevent Python from writing .pyc files and buffering stdout/stderr
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set the working directory
WORKDIR /app

# Install system dependencies (optional: add your own as needed)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy only requirements first (for better caching)
COPY requirements.txt .

# Install Python dependencies
RUN pip install --upgrade pip && \
    pip install -r requirements.txt && \
    rm -rf /root/.cache /var/lib/apt/lists/*

# Copy the rest of the application
COPY . .

# Create a non-root user and switch to it
RUN useradd -m appuser
USER appuser


# Expose the port your app runs on (optional)
EXPOSE 8086

# Run the application (adjust as needed)
CMD ["python", "server.py"]
 