# Image mẫu để CI quét Trivy + ký Cosign. Chạy non-root để khớp policy D1.
FROM python:3.12-slim

RUN pip install --no-cache-dir flask==3.0.3 \
    && useradd -u 10001 -m appuser
COPY app.py /app/app.py
WORKDIR /app
USER 10001
EXPOSE 8080
CMD ["python", "app.py"]
