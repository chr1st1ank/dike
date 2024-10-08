# Build:
#   docker build -t prediction-example .
# Run:
#   docker run -it --rm -p 8000:8000 prediction-example
# Test:
#   curl 'localhost:8000/predict?number=10'
#
# Simple load test with https://github.com/hatoo/oha:
#   oha -c 25 -q 300 -n 2000  'http://localhost:8000/predict?number=5'

FROM python:3.13-slim

RUN pip install --no-cache-dir dike numpy fastapi uvicorn
COPY api.py /app/api.py

USER 1000
EXPOSE 8000
WORKDIR /app

CMD ["uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8000"]
