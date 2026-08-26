FROM python:3.14-slim

# Install Flutter dependencies
RUN apt-get update && apt-get install -y \
    curl git unzip xz-utils zip \
    && rm -rf /var/lib/apt/lists/*

# Install Flutter SDK
RUN git clone https://github.com/flutter/flutter.git -b stable /opt/flutter
ENV PATH="/opt/flutter/bin:$PATH"

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

COPY . .

# Build Flutter only if not already built locally
RUN if [ ! -f "web/build/web/index.html" ]; then \
        echo "Flutter build not found, building ..." && \
        cd web && flutter pub get && flutter build web --release --base-href /sales-admin/ ; \
    else \
        echo "Flutter build found, skipping ..." ; \
    fi

RUN chmod +x scripts/entrypoint.sh

ENV POSTGRES_DB=django
ENV POSTGRES_USER=django
ENV POSTGRES_PASSWORD=placeholder
ENV POSTGRES_HOST=localhost
ENV POSTGRES_PORT=5432

RUN python manage.py collectstatic --noinput

EXPOSE 8000

ENTRYPOINT ["scripts/entrypoint.sh"]
