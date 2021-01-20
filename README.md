# About
MaveDB is a biological database for Multiplex Assays of Variant Effect (MAVE)
datasets. The primary installation of MaveDB is located at
https://www.mavedb.org. For more information about MaveDB or to cite MaveDB
please refer to the
[MaveDB paper in *Genome Biology*](https://doi.org/10.1186/s13059-019-1845-6).

# Installation
## Required software
Setting up a server will require some configuration. Detailed instructions on
setting up MaveDB using CentOS 6 on an Amazon Web Services EC2 instance can be
found in the [MaveDB documentation](./CentOS6.md). If you are running a local
development server, then you can skip this setup and start below.

 MaveDB was developed using Python 3.4.3, but should be compatible with
 any later Python 3 version. Python 2 is not supported. Running MaveDB requires
 the following software:
 - [Python 3](https://www.python.org/downloads/)
 - [Mercurial](https://www.mercurial-scm.org/) (required to install the
 [metapub](http://bitbucket.org/afrubin/metapub) python package)
 - [PostgreSQL 9.6](https://www.postgresql.org/about/) (installation will be
 operating system dependent)
 - [Pandoc 1.9](https://pandoc.org/releases.html#pandoc-1.19.2.4-10-sep-2017)
 (required by pypandoc)
 - [Erlang](http://www.rabbitmq.com/which-erlang.html) (required by RabbitMQ)
 - [RabbitMQ](http://www.rabbitmq.com/download.html)
 (**Note**: RabbitMQ no longer supports Windows)

 User authentication with OAuth and ORCID iD requires additional setup and may
 not be suitable for a local development server. See the
 [ORCID API documentation](https://members.orcid.org/api/oauth) for a
 description of OAuth and detailed instructions.

## Required Python packages
The packages required to run local and live versions of MaveDB are listed in the `requirements/base.txt` file in the repository.

Requirements files including additional packages for local, production and staging environments are provided. These files include the base requirements file, so the appropriate file can be installed using `pip install -r requirements/<environment>.txt`.

## PostgreSQL setup
 By default the local server will use the following PostgreSQL settings:

```json
    {
        "ENGINE": "django.db.backends.postgresql_psycopg2",
        "NAME": "mavedb",
        "USER": "mave_admin",
        "PASSWORD": "abc123",
        "HOST": "localhost",
        "PORT": ""
    }
```

Once PostgreSQL is installed. You will need to create a new user `mave_admin`
with password `abc123`. The default port for PostgreSQL is 5432. Using the
`psql` command line interface, this can be achieved using the following code:

```postgresplsql
CREATE DATABASE mavedb;
CREATE USER mave_admin WITH PASSWORD 'abc123';
ALTER ROLE mave_admin SET client_encoding to 'utf8';
ALTER ROLE mave_admin SET default_transaction_isolation TO 'read committed';
GRANT ALL PRIVILEGES ON DATABASE mavedb TO mave_admin;
```

Once the database has been configured, you will need to start the PostgreSQL
server before running the MaveDB local/live server. See the [PostgreSQL
documentation](https://www.postgresql.org/docs/9.6/static/server-start.html)
for details.

## To restore a database:
To pg_restore a pg_dump, nothing can be connected to the database. that means
that if you use docker-compose, this will be a huge headache because the `app`
service will connect to the database automatically.  
A way around this is to comment out parts of the docker-compose file so only
the database comes up, copy in the dump file, bring up the container's command
line, delete the existing database, and then pg_restore the dump file.  
EXAMPLE
```bash
# After you've commented out the 'app' and 'broker' sections from the
# docker-compose file you're using:
docker-compose -f $YOUR_DOCKER_COMPOSE_FILE up -d
docker cp $PATH_TO_PG_DUMP $DB_CONTAINER_NAME:/pg_dump.file
docker exec -it $DB_CONTAINER_NAME /bin/bash

# Now from inside the container:
dropdb -U $POSTGRES_USER mavedb
createdb -U $POSTGRES_USER mavedb
pg_restore -U $POSTGRES_USER -d mavedb /pg_dump.file

# Then exit the container! You're done!
```

## Asynchronous task management
You will need to start the RabbitMQ service if you plan to use a worker
pool for concurrency. Once `rabbitmq-server` is added to your path, you
can start the server using the following command on CentOS and Debian systems:

```bash
service rabbitmq-server start
```

To start a worker pool, you may use the provided shell script:

```bash
bash start_celery.sh settings.local
```

Alternatively, if you are in a production environment and would like to use
the default configuration in `mavedb/settings.py`, do not supply an argument.

# Management commands
Before starting the server you will need to run the following utility commands:

```bash
python managy.py migrate
python manage.py createsuperuser
python manage.py createreferences
python manage.py createlicences
python manage.py collectstatic
```

Additional utility commands have been created that can serialize reference
genomes in the database and serialize the current `SiteInformation`
singleton to JSON:

```bash
python manage.py savereferences
python manage.py savesiteinfo
```

To update or create the `SiteInformation` singleton from a JSON file, use the
command:

```bash
python manage.py updatesiteinfo
```

This will update the existing instance or create a new one if necessary. The
data files loaded by the above commands are located in the `data` subdirectory.


## Django-reversion
[Django-reversion](https://django-reversion.readthedocs.io/en/stable/) has been
integrated with the site. This is a well maintained model versioning application
that keeps a history of each instance in the database for models that have been
registered. There are two key commands to run when deploying:

```python manage.py migrate
python manage.py createinitialrevisions
```

To delete the recorded history for a particular model:

```bash
python manage.py deleterevisions <appname.modelname> --keep=[int] --days=[int]
```

This will keep anything from last *n* `days` or `keep` at least *n* history
items.
