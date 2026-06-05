FROM python:3.13-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p db && touch db/clan_prod.sqlite3 && chmod 777 db

EXPOSE 10000

CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:10000"]
