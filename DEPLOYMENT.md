This guide will walk through deploying a dockerized version of MaveDB. Please clone the latest tag from the 
[MaveDB](https://github.com/VariantEffect/mavedb/tags) github repository. This guide assumes that the website will be 
served on ports 80/443.


## Requirements
- Docker
- Docker-compose
- direnv


## Environment variables
A template file called `template.envrc` exists in the root directory. For deployment of a production version:

```shell
export MAVEDB_DB_USER=mave_admin
export MAVEDB_DB_PASSWORD="<a secure password>"
export MAVEDB_DB_PORT="<host port to allow PostgreSQL connection on>"
export MAVEDB_DB_NAME=mavedb
export MAVEDB_BROKER_PORT="<host port to allow RabbitMQ connection on>"

# Production only settings
export MAVEDB_RELEASE_TAG=latest

# Database restore
export MAVEDB_DUMP_FILE="mavedb_2020_07_28.dump"

# Nginx SSL certs
export MAVEDB_SSL_CERTS_DIR=docker/nginx/ssl
```

### Nginx
If you have SSL certificates available for MaveDB, name them `mavedb.cert` and `mavedb.key`. Place these in any directory 
(default is `docker/nginx/ssl/`) and set the environment variable `MAVEDB_SSL_CERTS_DIR` in your `.envrc`. A template 
conf file has been placed under `docker/nginx/nginx.conf`. Copy this file into the root directory and customise as 
needed, such as specifying additional SSL options. It has been pre-configured to proxy pass incoming requests to the 
nginx container to the Django application running via the `app` container. This file will be mounted into the nginx 
container upon starting up.

### Postgres
You can restore a previous database dump file when creating the Postgres container for the first time (or the first time
that docker-compose up is called.). If you do have one, copy it to `docker/postgres/dumps/`, then set the `MAVEDB_DUMP_FILE`
environment variable in your `.envrc` file to this file name (just the file name, not path). If you want to perform another 
restore, you will have to delete the container, image and database volume.

### Conclusion
Copy this file to a new file called `.envrc` which will be sourced by `direnv` on entering the directory to start the
docker-compose service. Manually source it if you are not using `direnv`.


## MaveHGVS docs
Place the `mavehgvs` sphinx documentation files into `/docs/mavehgvs/`. The build path in `Makefile` and `make.bat`
must be `../build/docs/mavehgvs/`. Once the application starts, this documentation will be collected in the static file
directory and served at `https://mavedb.org/docs/mavehgvs`.


## Settings file
The settings file is loaded by the docker-compose service into the application container. The database and broker 
connection information must match those set above.

```dotenv
# Database settings for postgres
APP_DB_PASSWORD="<your secure password from above>"
APP_DB_USER=mave_admin
APP_DB_NAME=mavedb
APP_DB_HOST=database
APP_DB_PORT=5432 # Internal port database container listens on, NOT the host port.

# Rabbit MQ connection information
APP_BROKER_HOST=broker
APP_BROKER_PORT=5672 # Internal port broker container listens on, NOT the host port.

# Django settings
APP_SECRET_KEY="<a randomly generated secure secret key>"
APP_ORCID_SECRET="<ORCID secret key from your ORCID developer account>"
APP_ORCID_KEY="<ORCID app key from your ORCID developer account>"
APP_NCBI_API_KEY="<NCBI api key from your NCBI account, leave blank if you don't have one>"
APP_API_BASE_URL="https://mavedb.org/api"
APP_BASE_URL="https://mavedb.org"
APP_ALLOWED_HOSTS="localhost 127.0.0.1" # Allowed hosts in addition to www.mavedb.org and mavedb.org

# Celery settings
CELERY_CONCURRENCY=4
CELERY_LOG_LEVEL=INFO
CELERY_NODES=worker1
CELERY_PROJECT=mavedb

# Gunicorn settings - ignored in development
GUNICORN_FORWARDED_ALLOW_IPS=
GUNICORN_WORKERS=2
GUNICORN_THREADS=4
GUNICORN_BIND_HOST=0.0.0.0
GUNICORN_BIND_PORT=8000
```


## Docker-compose
After the above steps are complete, you should be ready to deploy the production system. At the command line invoke:

```shell
docker-compose -f docker-compose-prod.yml up -d
```

Before the MaveDB web application service starts, it will wait for the database and broker services to first 
successfully start, then it will perform basic checks to see if the Celery service within the `app` container has 
initialised correctly. It might look like the container entrypoint is hanging, but these checks are normal. The entrypoint
script will continuously poll the broker and database container until they are ready to accept connections before moving 
on to running migrations and starting the server and celery daemon. If the script hangs for more than a few minutes, 
check that:

- Your connection environment variables and settings are correct
- The broker/database container have not exited due to an error


## Tests
Once the service is running, execute a bash shell session into the `app` container:

```shell
docker exec -it <container name> /bin/bash
```

Then run the test suite using the following shell command:

```shell
python manage.py test --exclude-tag=webtest
```


## Troubleshooting
If the web application has not started after a few minutes check the docker-compose logs in the `app` container. If you 
see messages regarding the database or broker not being ready then check the logs in those containers. If you see a 
message about the Celery service not being ready, there might have been an error during Celery's initialization. You can
see the logs of a container using:

```shell
docker-compose logs <name-of-service>
```