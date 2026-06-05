FROM python:3.13-slim

WORKDIR /app

ENV DJANGO_SETTINGS_MODULE=config.settings.production
ENV PYTHONUNBUFFERED=1
ENV SECRET_KEY=flyio-temp-key-for-migrations

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p db && chmod 777 db
RUN python manage.py migrate --noinput

EXPOSE 10000

CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:10000"]
