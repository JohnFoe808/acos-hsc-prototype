FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app
COPY pyproject.toml README.md ./
COPY acos ./acos
COPY static ./static
RUN pip install --no-cache-dir .
RUN mkdir -p /app/data/workspace

EXPOSE 8000
CMD ["uvicorn", "acos.main:app", "--host", "0.0.0.0", "--port", "8000"]
