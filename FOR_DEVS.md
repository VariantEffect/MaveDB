# Quick start
Welcome to MaveDB; a place where all your wildest dreams will come true. This is a short guide on
how to set up your development environment. Windows is not supported due to the Celery package not
supporting Windows, but you could potentially use WSL2 to host your development environment and then
develop from within Windows. 

## Requirements
Please install the following software:

- Docker
- Docker Compose
- geckodriver (optional, but required for running webtests)

Consult the official documentation on how to do this. These may require the installation of 
additional system packages on Linux/MacOS.

## PyCharm
This guide assumes you will be using PyCharm. If you are using another IDE/editor, good luck. To 
start off, clone the repository and open it up in PyCharm. PyCharm can also clone repositories for
you if you supply your login credentials. Please make sure you switch to your feature branch or
the **develop** branch, unless you enjoy pushing updates right into production, you monster.

If you're eager to start developing new features, you may notice a red bloodbath of squiggly lines 
and PyCharm having a fit about uninstalled packages; not so fast, you'll need to setup up your 
project interpreter first. Go to `File > Settings > Project: <branch> > Project Interpreter` and 
click the gear icon at the top right, then click `Add`. Create a new virtual environment pointing to 
Python 3.6> You can install additional python versions using 
[pyenv](https://github.com/pyenv/pyenv-installer) or, if you're running Ubuntu, from the 
[deadsnakes PPA](https://launchpad.net/~deadsnakes/+archive/ubuntu/ppa).

Done! Now open up a terminal within PyCharm and run `pip install -r requirements/development.txt`.
Your environment is now ready to roll. 

### Auto-formatting

I recommend using a file watcher to format your code on save. Follow 
[these instructions](https://black.readthedocs.io/en/stable/editor_integration.html) to get set up.
The only addition is using the argument -l 79 to limit your line length to 79 characters.

## Django setup

If you plan on running the tests (which you should...) then you'll need to point PyCharm to the 
correct settings file. Go to `File > Settings > Language & Frameworks > Django` and point the
settings input box to `settings/development.py`.

## Settings file

This project now uses `.env` files to configure project settings like database connections, 
allowed hosts, celery configuration etc. There is a template file waiting for you in the `settings`
directory. Create a new file in the same directory called `.settings-development.env` and then copy 
and paste the template into this file. The most important ones are the database and broker connection 
settings. Please choose your favourite database password and username; they can be anything, so let 
your wildest dreams become a reality! However, the database name must be `mavedb`. As for the broker 
and database ports, I've used 5763 and 5433 respectively. You can change these to whatever your like, 
as long as your remain consistent in the next step. The remaining settings can be adjusted to 
whatever you like, except for `CELERY_PROJECT`. Gunicorn settings are not required for development 
so you may ignore these.

## Docker

To develop with a copy of the production database place you `*.dump` file under `docker/postgres/dumps/`, then in the 
docker-compose file set the `MAVEDB_DUMP_FILE` environment variable to the name of your dump file. Postgres will restore 
this dump file when the image is first created.

Docker expects a few environment variables when running the database and broker services. The file
`host_env.sh` contains a template for you to use with [direnv](https://direnv.net/) or copy into your
profile directly. Do not modify this file since it is tracked by version control. The environment
variables needed by the development environment are:

```shell script
export MAVEDB_DB_USER=whatever_you_set_from_last_step
export MAVEDB_DB_PASSWORD=whatever_you_set_from_last_step
export MAVEDB_DB_PORT=whatever_you_set_from_last_step
export MAVEDB_DB_NAME=mavedb
export MAVEDB_BROKER_PORT=whatever_you_set_from_last_step
```

The remaining entries in this file are for the production database and can be ignored.

Refresh your shell environment as these are referenced by the docker compose file. Speaking of 
which, to run the development server and test suite, you'll need to start the services with:

```shell script
docker-compose -f docker-compose-dev.yml up 
```

## Local development 

You can ignore this section if you are doing remote development within a docker container. This section is for those
who are running the database and broker from Docker but are developing on the host system using a virtual environment.

The following commands will initialize the database and set up the website. You will need to
either add the option `--settings=settings.development` to each `manage.py` command so that
Django uses the right settings file, or add `export DJANGO_SETTINGS_MODULE=settings.development`
to your .envrc (if you're using direnv) or bash profile.

```shell script
python manage.py migrate \
  && python manage.py updatesiteinfo \
  && python manage.py createlicences \
  && python manage.py createreferences \
  && python manage.py collectstatic
```

The following command will run the tests. Note that the Selenium tests may fail unexpectedly
if the test browser is interacted with.

```shell script
python manage.py test --exclude-tags=webtest
```

## Celery
If you want to tes the upload functionality and offline task handling, you'll need to start a Celery process. In a 
separate terminal run:

```shell
celery -A mavedb worker -l debug --concurrency=2
```

You should see output indicating registered tasks similar to:

```shell
[tasks]
  . core.tasks.BaseTask
  . core.tasks.health_check
  . core.tasks.send_mail
  . dataset.tasks.BaseCreateVariantsTask
  . dataset.tasks.BaseDatasetTask
  . dataset.tasks.BaseDeleteTask
  . dataset.tasks.BasePublishTask
  . dataset.tasks.create_variants
  . dataset.tasks.delete_instance
  . dataset.tasks.publish_scoreset
```

## Conclusion

You're all set up and ready to go! Happy hacking!