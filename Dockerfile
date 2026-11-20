FROM python:3.11-slim
RUN apt-get update && apt-get install -y ffmpeg && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
RUN sed -i 's|os.path.expanduser("~/omni_work")|"/tmp/omni_work"|g' app.py
RUN sed -i 's|os.path.expanduser("~/omni_sessions.db")|"/tmp/omni_sessions.db"|g' app.py
RUN mkdir -p /tmp/omni_work && cp brand_logo.png /tmp/omni_work/ 2>/dev/null || true
EXPOSE 7860
CMD ["gunicorn", "-b", "0.0.0.0:7860", "--workers", "2", "--threads", "4", "--timeout", "120", "app:app"]
