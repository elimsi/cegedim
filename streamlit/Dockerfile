FROM python:3.11-slim

WORKDIR /app

RUN pip install --no-cache-dir streamlit pandas plotly sqlalchemy psycopg2-binary requests streamlit-autorefresh

COPY . /app

EXPOSE 8501

CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
