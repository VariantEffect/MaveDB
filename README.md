# 0. About
MaveDB web application

# 1. Pre-requistite Requirements
Setting up a server will require some configuration. Instructions on how to
spin up a server using CentOS 6 and Apache can be found 
[here](./CentOS6.md). If you are only running a local development server,
then you can skip this setup and start below.

 MaveDB was developed with to target python 3.4, but should be compatible with
 any python 3 install. Python 2 is not supported. Running MaveDB requires 
 the following software:
 - [Python 3](https://www.python.org/downloads/)
 - [Mercurial](https://www.mercurial-scm.org/) (required to install the [metapub](http://bitbucket.org/afrubin/metapub) python package)
 - [PostgreSQL 9.6](https://www.postgresql.org/about/) (installation will be operating system dependent)
 - [Pandoc 1.9](https://pandoc.org/releases.html#pandoc-1.19.2.4-10-sep-2017) (required by pypandoc)
 - [Erlang](http://www.rabbitmq.com/which-erlang.html) (required by RabbitMQ)
 - [RabbitMQ](http://www.rabbitmq.com/download.html) (**Note**: RabbitMQ no longer supports Windows)
 
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
with password `abc123`. The default port for PostgreSQL is 5432. Using the `psql`
command line interface, this can be achieved using the following code:

```postgresplsql
CREATE DATABASE mavedb;
CREATE USER mave_admin WITH PASSWORD 'abc123';
ALTER ROLE mave_admin SET client_encoding to 'utf8';
ALTER ROLE mave_admin SET default_transaction_isolation TO 'read committed';
GRANT ALL PRIVILEGES ON DATABASE mavedb TO mave_admin;
```

Once the database has been configured, you will need to start the PostgreSQL server
before running the MaveDB local/live server.


# 2. Python Base Requirements 
The packages below are the base packages required to run local and live
versions of MaveDB:
- django==1.11.5
- django-braces>=1.12.0
- django-extensions>=2.0.6
- django-guardian>=1.4.9
- django-reversion>=2.0.9
- django-widget-tweaks>=1.4.2
- djangorestframework>=3.8.2
- djangorestframework-filters>=0.10.2
- social-auth-app-django>=1.2.0
- factory-boy>=2.9.2
- numpy>=1.12.1
- celery>=3.1
- psycopg2>=2.7.1
- pypandoc>=1.4
- selenium>=3.4.3
- Faker>=0.7.18
- gunicorn
- whitenoise
- dj-database-url
- git+https://github.com/afrubin/idutils.git@bio
- hg+http://bitbucket.org/afrubin/metapub@html_citation

# 3. Additional Requirements
Running a live server will require some additional packages:
- mod_wsgi

# 4. Management commands
Before starting the server you will need to run the following commands:

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

This will either update an existing instance or create one. The data for
all the above commands is located in the `data` subdirectory.


# 5. Django-reversion
[Django-reversion](https://django-reversion.readthedocs.io/en/stable/) has been 
integrated with the site. This is a well maintained model versioning application 
that keeps a history of each instance in the database for models that have been 
registered. There are two key commands to run when deploying:

python manage.py migrate
python manage.py createinitialrevisions

To delete recorded history for a particular model:

```bash
python manage.py deleterevisions <appname.modelname> --keep=[int] --days=[int]
```

This will keep anything from last *n* `days` or `keep` at least *n* history 
items.

# 6. Starting RabbitMQ
You will need to start the RabbitMQ service if you plan to use spawn a worker
pool for concurrency. Once `rabbitmq-server` is added to your path, you
can start the server (CentoOS 6/Debian based command):

```bash
service rabbitmq-server start
```

# 7. Starting Celery
To start a worker pool, you may use the provided shell script:

```bash
bash start_celery.sh settings.local
``` 

Alternatively, if you are in a production environment and you like to use 
the default settings configuration in `mavedb/settings.py`, do not supply an argument.