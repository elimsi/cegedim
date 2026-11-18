FROM ghcr.io/dbt-labs/dbt-postgres:1.8.latest

USER root
RUN apt-get update && apt-get install -y python3-pip && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir flask

WORKDIR /usr/app
COPY . /usr/app

ENTRYPOINT []
CMD ["python", "app.py"]
