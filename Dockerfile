FROM python:3.13-rc-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Make sure your custom modules are accessible
ENV PYTHONPATH "${PYTHONPATH}:/app"

CMD ["python", "main.py"]