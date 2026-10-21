FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 5427
CMD ["gunicorn", "-k", "gthread", "--workers", "1", "--threads", "32", "--timeout", "300", "-b", "0.0.0.0:5427", "main_for_paping_tcptrace:app"]
