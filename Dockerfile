FROM python:3.9-slim

WORKDIR /app

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy all source modules
COPY src/*.py ./src/

# Set environment variables
ENV PYTHONUNBUFFERED=1

# Run the main job orchestrator (once and exit)
CMD ["python", "src/main.py"]