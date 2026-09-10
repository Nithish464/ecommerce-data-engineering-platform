FROM python:3.11-slim

WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy FastAPI application
COPY app ./app

# Copy ETL pipeline
COPY pipeline.py ./pipeline.py

# Copy startup script
COPY start.sh ./start.sh

# Make startup script executable
RUN chmod +x ./start.sh

EXPOSE 8000

CMD ["/bin/sh", "./start.sh"]