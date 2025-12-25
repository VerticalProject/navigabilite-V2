FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /code

RUN apt-get update         && apt-get install -y --no-install-recommends build-essential libpq-dev         && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /code/
RUN pip install --no-cache-dir -r requirements.txt

COPY . /code/

# Create a non-root user for better security
RUN useradd -ms /bin/bash appuser
USER appuser

EXPOSE 8000
CMD ["bash", "-lc", "python manage.py migrate && python manage.py runserver 0.0.0.0:8000"]
