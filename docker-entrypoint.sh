#!/bin/bash
set -e

echo "Spinning up image with release tag '${APP_VERSION}'"
###############################################################################
# Function definitions
###############################################################################
function database_ready() {
python3 << END
import os
import sys
import psycopg2

host = os.getenv("APP_DB_HOST")
port = os.getenv("APP_DB_PORT")
user = os.getenv("APP_DB_USER")
password = os.getenv("APP_DB_PASSWORD")
dbname = os.getenv("APP_DB_NAME")

try:
    psycopg2.connect(
        host=host,
        port=port,
        user=user,
        password=password,
        dbname=dbname,
    )
except psycopg2.OperationalError as e:
    sys.stderr.write(str(e))
    raise e

sys.stdout.write("Connection successful\n")
END
}


function broker_ready() {
python3 << END
import os
import sys
import socket

from kombu import Connection

host = os.getenv("APP_BROKER_HOST")
port = os.getenv("APP_BROKER_PORT")
broker_url = "amqp://{}:{}//".format(host, port)

try:
    conn = Connection(broker_url)
    conn.ensure_connection(max_retries=3)
except socket.error:
    msg = "Failed to connect to RabbitMQ instance at {}".format(broker_url)
    sys.stderr.write(msg)
    raise RuntimeError(msg)
END
}

function celery_has_initialized() {
python3 << END
import os
import sys
import time
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "mavedb.settings")
django.setup(set_prefix=False)

# Check tasks have registered
from mavedb import celery_app

attempt = 0
while attempt < 3:
  attempt += 1

  try:
    inspection = celery_app.control.inspect().registered_tasks()
    if inspection is None:
      sys.stdout.write("No response. Sleeping\n")
      time.sleep(5)
    else:
      tasks = list(inspection.items())[0][1]
      assert len(tasks) == 10, "Expected 10 tasks. {} tasks were registered.".format(len(tasks))
  except Exception as e:
    raise e

if inspection is None:
  raise RuntimeError("Could not inspect registered tasks")

# Test tasks can be run
from core.tasks import health_check

result = health_check.delay(1, 2).get()
assert result == 3, "Expected 3 as the result but '{}' was returned".format(result)

sys.stdout.write("Celery has correctly initialized!\n")
END
}

###############################################################################
# Health checks
###############################################################################
sleep 10

echo "Checking database"
until database_ready; do
  >&2 echo "Database is unavailable - sleeping"
  sleep 1
done
>&2 echo "Database is ready"

echo "Checking broker"
until broker_ready; do
  >&2 echo "Broker is unavailable - sleeping"
  sleep 1
done
>&2 echo "Broker is ready"

echo "Starting Celery worker."
find "${CELERY_PID_DIR}" -name '*.pid' -delete
celery multi start "${CELERY_NODES}" \
  -A "${CELERY_PROJECT}" \
  --concurrency="${CELERY_CONCURRENCY}" \
  --loglevel="${CELERY_LOG_LEVEL}" \
  --pidfile="${CELERY_PID_DIR}/%n.pid" \
  --logfile="${CELERY_LOG_DIR}/%n%I.log"

echo "Checking Celery"
until celery_has_initialized; do
  >&2 echo "Could not check registered Celery tasks - sleeping"
  sleep 1
done
>&2 echo "Celery is ready"

###############################################################################
# Web project init
###############################################################################
echo "Running management commands."
python3 manage.py migrate
python3 manage.py updatesiteinfo
python3 manage.py createlicences
python3 manage.py createreferences
python3 manage.py collectstatic --noinput --clear

if [ "$ENVIRONMENT" = "production" ]; then
  gunicorn mavedb.wsgi:application \
    --bind 0.0.0.0:8000 \
    --workers="${GUNICORN_WORKERS}" \
    --threads="${GUNICORN_THREADS}" \
    --worker-class=gthread
else
  python3 manage.py runserver 0.0.0.0:8000
fi
