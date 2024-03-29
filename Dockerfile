FROM python:3.11-slim

WORKDIR /app

COPY . /app

RUN pip install --no-cache-dir -r requirements.txt

RUN apt-get update && apt-get upgrade -y
RUN playwright install chromium
RUN playwright install-deps

EXPOSE 8501

CMD ["streamlit", "run", "--server.enableCORS=false", "stapp.py"]
