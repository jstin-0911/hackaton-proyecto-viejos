FROM python:3.12-slim
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1
RUN pip install --no-cache-dir pytest==8.3.4 requests==2.32.3 psycopg2-binary==2.9.10
WORKDIR /app
COPY . .
CMD ["pytest", "-q", "--junitxml=/app/test-results/junit.xml"]
