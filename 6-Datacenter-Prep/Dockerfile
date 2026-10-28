# Datacenter Prep als Container:
#   docker build -t dcprep .
#   docker run -d -p 8080:8080 -v dcprep-data:/app/data --name dcprep dcprep
FROM python:3.12-slim
WORKDIR /app
COPY dcprep ./dcprep
COPY static ./static
COPY labs ./labs
COPY start.py ./
EXPOSE 8080
VOLUME /app/data
CMD ["python3", "start.py", "--host", "0.0.0.0", "--port", "8080", "--data", "/app/data", "--no-browser"]
