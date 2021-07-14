# Build:
#   docker build -t prediction-example .
# Run:
#   docker run -it --rm -p 8000:8000 prediction-example
# Test:
#   curl 'localhost:8000/predict?number=10'
# Load test with github.com/codesenberg/bombardier:
#   bombardier -c 25 -r 300 -d 10s -l 'localhost:8000/predict?number=5'

FROM tiangolo/uvicorn-gunicorn-fastapi:python3.8

RUN pip install dike numpy
COPY api.py /app/api.py

EXPOSE 8000
CMD ["uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8000"]
