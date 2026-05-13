FROM python:3.9-slim

WORKDIR /app

COPY app.py ./
COPY requirements.txt ./
COPY data ./data
COPY model ./model

RUN pip install --no-cache-dir -r requirements.txt
RUN mkdir -p data model logs

EXPOSE 5001

CMD ["python", "app.py"]
