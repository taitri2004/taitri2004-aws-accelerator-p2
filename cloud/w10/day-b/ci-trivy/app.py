import os

from flask import Flask, jsonify

app = Flask(__name__)


@app.get("/")
def index():
    # Đọc secret qua file (do ESO + volume mount cấp), không hardcode.
    secret_path = "/etc/secret/db-password"
    has_secret = os.path.exists(secret_path)
    return jsonify(app="w10-app", version=os.getenv("VERSION", "1"), secret_mounted=has_secret)


@app.get("/healthz")
def healthz():
    return jsonify(status="ok")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
