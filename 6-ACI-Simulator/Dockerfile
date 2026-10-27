# ACI Simulator als Container:
#   docker build -t aci-sim .
#   docker run -d -p 8080:8080 -v aci-sim-data:/app/data --name aci-sim aci-sim
FROM python:3.12-slim
WORKDIR /app
COPY aci_sim ./aci_sim
COPY static ./static
COPY labs ./labs
EXPOSE 8080
VOLUME /app/data
CMD ["python3", "-m", "aci_sim", "--host", "0.0.0.0", "--port", "8080", "--data", "/app/data"]
