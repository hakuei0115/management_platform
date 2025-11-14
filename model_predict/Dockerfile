FROM python:3.9-slim

WORKDIR /app

COPY app.py ./
COPY NG項_最終維修建議對照.csv ./
COPY requirements.txt ./
COPY model ./model
COPY logs ./logs

RUN pip install --no-cache-dir -r requirements.txt

EXPOSE 5000

CMD ["python", "app.py"]
