FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY *.py ./

# Copy ML models
COPY models/ /models/

# Run the application
CMD ["python", "-u", "app.py"]
