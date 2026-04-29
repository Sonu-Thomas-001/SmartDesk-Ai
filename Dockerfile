FROM python:3.12-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Create directories for persistent data
RUN mkdir -p chroma_data

EXPOSE 8000

CMD ["python", "-m", "flask", "--app", "app.main:app", "run", "--host", "0.0.0.0", "--port", "8000"]
