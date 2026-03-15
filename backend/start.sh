#!/bin/bash
set -e

echo "Starting Celery worker..."
celery -A app.celery_app.celery worker --loglevel=info &

echo "Starting Flask API..."
python run.py
