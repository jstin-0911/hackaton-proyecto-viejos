FROM python:3.12-slim
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1
RUN pip install --no-cache-dir psycopg2-binary==2.9.10
WORKDIR /app
COPY gateway ./gateway
COPY adapter ./adapter
RUN mkdir -p /app/logs /data
EXPOSE 8082
CMD ["python", "-m", "gateway.main"]
