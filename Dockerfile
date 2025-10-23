FROM python:3.9-slim

WORKDIR /app

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy simplified job script
COPY src/run_job.py ./src/

# Set environment variables
ENV PYTHONUNBUFFERED=1

# Run the job (once and exit)
CMD ["python", "src/run_job.py"]