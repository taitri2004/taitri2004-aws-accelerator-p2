import os
import random
import socket
import time

from flask import Flask, jsonify, request
from prometheus_flask_exporter import PrometheusMetrics

app = Flask(__name__)
PrometheusMetrics(app)

ERROR_RATE = float(os.getenv("ERROR_RATE", "0"))
VERSION = os.getenv("VERSION", "v1")
POD = socket.gethostname()
STARTED = time.time()
visits = {"count": 0}


@app.get("/")
def index():
    if random.random() < ERROR_RATE:
        return jsonify(error="injected", version=VERSION), 500
    return jsonify(ok=True, version=VERSION)


@app.get("/healthz")
def healthz():
    return "ok", 200


@app.get("/api/info")
def info():
    return jsonify(
        version=VERSION,
        pod=POD,
        uptime_s=int(time.time() - STARTED),
        error_rate=ERROR_RATE,
    )


@app.get("/api/ping")
def ping():
    if random.random() < ERROR_RATE:
        return jsonify(ok=False, version=VERSION, pod=POD), 500
    return jsonify(ok=True, version=VERSION, pod=POD)


@app.get("/api/visits")
def get_visits():
    return jsonify(count=visits["count"], pod=POD)


@app.post("/api/visits")
def add_visit():
    visits["count"] += 1
    return jsonify(count=visits["count"], pod=POD)


@app.post("/api/echo")
def echo():
    data = request.get_json(silent=True) or {}
    text = str(data.get("text", ""))[:200]
    return jsonify(
        original=text,
        upper=text.upper(),
        reversed=text[::-1],
        length=len(text),
        pod=POD,
        version=VERSION,
    )
