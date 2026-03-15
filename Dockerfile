FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

COPY pyproject.toml README.md LICENSE requirements.txt requirements-app.txt ./
COPY src ./src
COPY data ./data
COPY demo ./demo
COPY examples ./examples

RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir .[app]

EXPOSE 8501

ENTRYPOINT ["mhc-atlas"]
CMD ["app", "--demo", "small_project", "--host", "0.0.0.0", "--port", "8501"]
