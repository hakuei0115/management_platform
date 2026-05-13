FROM python:3.9-slim

WORKDIR /app

ENV MERGE_GUI_PORT=8501 \
    TRAIN_OUTPUT_DIR=/app/outputs \
    MODEL_PREDICT_DATA_DIR=/shared/model_predict/data \
    MODEL_PREDICT_MODEL_DIR=/shared/model_predict/model

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
RUN mkdir -p /app/outputs /shared/model_predict/data /shared/model_predict/model

EXPOSE 8501

CMD ["python", "merge_gui.py"]
