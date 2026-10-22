FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip uninstall -y google-generativeai google-api-core googleapis-common-protos google || true
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
CMD ["python", "main.py"]
