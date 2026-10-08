FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

RUN useradd --create-home --uid 1000 app
WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

# Settings refuse to load without a key; this one exists only for this build step.
RUN DJANGO_SECRET_KEY=build-only python manage.py collectstatic --noinput

USER app
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/saude/', timeout=3)"

CMD ["sh", "-c", "python manage.py migrate --noinput && exec gunicorn esteira.wsgi:application --bind 0.0.0.0:8000 --workers ${WEB_CONCURRENCY:-2} --access-logfile -"]
