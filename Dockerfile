FROM python:3.14-slim

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

COPY . .

RUN chmod +x scripts/entrypoint.sh

ENV POSTGRES_DB=django
ENV POSTGRES_USER=django
ENV POSTGRES_PASSWORD=placeholder
ENV POSTGRES_HOST=localhost
ENV POSTGRES_PORT=5432

RUN python manage.py collectstatic --noinput

EXPOSE 8000

ENTRYPOINT ["scripts/entrypoint.sh"]
