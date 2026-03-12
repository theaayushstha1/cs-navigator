FROM python:3.12-slim

WORKDIR /app

RUN pip install --no-cache-dir google-adk==1.23.0

COPY cs_navigator_unified/ ./cs_navigator_unified/

EXPOSE 8080

CMD ["python", "-m", "google.adk.cli", "web", ".", "--port", "8080", "--host", "0.0.0.0"]
