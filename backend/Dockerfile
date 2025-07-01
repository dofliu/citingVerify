# backend/Dockerfile
FROM python:3.11

WORKDIR /app

# Install Chinese fonts
RUN apt-get update && apt-get install -y fonts-wqy-zenhei
# Set environment variable for matplotlib to find fonts
ENV MATPLOTLIBRC=/etc/matplotlibrc

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
