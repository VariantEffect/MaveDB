FROM python:3.6 AS base

# Argument list for dockerfile script.
ARG DJANGO_REQUIREMENTS=production
RUN echo "Requirements: ${DJANGO_REQUIREMENTS}.txt"

ENV PYTHONUNBUFFERED 1
ENV DJANGO_REQUIREMENTS ${DJANGO_REQUIREMENTS}

###############################################################################
# Base configuration stage
###############################################################################
FROM base as builder

ENV APP_USER=mavedb

# Update the default application repository sources list and install
# required dependencies
RUN useradd -m ${APP_USER}
RUN apt-get update && apt-get -y upgrade
RUN apt-get install -y build-essential
RUN apt-get install -y git wget curl pandoc

# Local directory with project source
ENV HOST_SRC=.
# Directory in container where web app will live
ENV SRV_DIR=/srv
# Directory for local binaries
ENV LOCAL_BIN=/usr/local/bin/

# Directory in container for Django source files in web app directory
ENV APP_SOURCE=${SRV_DIR}/app
RUN mkdir -p ${APP_SOURCE}

# Directory in container for database mount for backup/restore etc
ENV DATABASE_BACKUP=${HOME}/database
RUN mkdir -p ${DATABASE_BACKUP}

# Directory in container for application and celery logs
ENV APP_LOGS=${APP_SOURCE}/logs
RUN mkdir -p ${APP_SOURCE}

# Directory in container for Django media files
ENV APP_MEDIA=${APP_LOGS}/media
RUN mkdir -p ${APP_MEDIA}

# Directory in container for Django static files
ENV APP_STATIC=${APP_SOURCE}/static
RUN mkdir -p ${APP_STATIC}

# Set up celery logging locations
ENV CELERY_LOG_DIR /var/log/celery
ENV CELERY_PID_DIR /var/run/celery
RUN mkdir -p ${CELERY_LOG_DIR}
RUN mkdir -p ${CELERY_PID_DIR}

# Create application subdirectories
WORKDIR ${APP_SOURCE}
RUN mkdir -p media static logs
RUN mkdir ${HOME}/database

COPY ${HOST_SRC}/requirements/base.txt .
COPY ${HOST_SRC}/requirements/${DJANGO_REQUIREMENTS}.txt .
RUN pip3 install --no-cache-dir wheel
RUN pip3 install --no-cache-dir -r ${DJANGO_REQUIREMENTS}.txt

###############################################################################
# App configuration stage
###############################################################################
FROM builder as app

WORKDIR ${APP_SOURCE}

COPY ${HOST_SRC} .

# Build the Sphinx documentation
WORKDIR ${APP_SOURCE}/docs
RUN make html

#WORKDIR ${APP_SOURCE}/docs/mavehgvs
#RUN make html; exit 0

WORKDIR ${APP_SOURCE}

RUN chown -R ${APP_USER}:${APP_USER} ${APP_SOURCE}
RUN chown -R ${APP_USER}:${APP_USER} ${APP_MEDIA}
RUN chown -R ${APP_USER}:${APP_USER} ${APP_STATIC}
RUN chown -R ${APP_USER}:${APP_USER} ${APP_LOGS}

# Create log directories for worker and pid logs
RUN mkdir -p /var/log/celery/
RUN mkdir -p /var/run/celery/
RUN chown -R ${APP_USER}:${APP_USER} /var/log/celery/
RUN chown -R ${APP_USER}:${APP_USER} /var/run/celery/

# Copy entrypoint script into the image
COPY ${HOST_SRC}/docker-entrypoint.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

# Port to expose for external comms
EXPOSE 8000

# Run entrypoint script in maveric source root
USER ${APP_USER}
WORKDIR ${APP_SOURCE}

ENTRYPOINT ["docker-entrypoint.sh"]
