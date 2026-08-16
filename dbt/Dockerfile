FROM ghcr.io/dbt-labs/dbt-postgres:1.8.latest

USER root
RUN apt-get update && apt-get install -y python3-pip && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir flask
USER dbt_user

WORKDIR /usr/app
COPY . /usr/app

EXPOSE 8080
CMD ["python", "app.py"]
