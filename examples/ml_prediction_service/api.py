"""Minimal example API using dike for microbatching.

Dependencies: fastapi, uvicorn
Run with: python api.py

Simple load test with github.com/codesenberg/bombardier:

    bombardier -c 25 -r 300 -d 10s -l 'localhost:8000/predict?number=5'
"""

import asyncio
import concurrent
import random
from typing import List

import numpy as np
from fastapi import FastAPI, Response

import dike

app = FastAPI()


def predict(numbers: List[float]):
    """Dummy machine learning operation."""
    arr = np.array(numbers)
    for _ in range(10000):
        arr = np.sqrt(arr + random.random() * 2)
    return list(arr)


@dike.limit_jobs(limit=20)
@dike.batch(target_batch_size=10, max_waiting_time=0.1)
async def predict_in_pool(numbers: List[float]):
    """Wrapper function for the predictions to allow batching."""
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(app.state.pool, predict, numbers)


@app.on_event("startup")
async def on_startup():  # noqa: D103
    app.state.pool = concurrent.futures.ProcessPoolExecutor(max_workers=2)


@app.get("/predict")
async def get_predict(number: float, response: Response):
    """API endpoint for machine learning inference."""
    try:
        x = await predict_in_pool([number])
        return {"result": x}
    except dike.TooManyCalls:
        response.status_code = 503
        return {
            "status": 503,
            "title": "Service unavailable",
            "detail": "Too many concurrent requests",
        }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, port=8000, workers=1)
