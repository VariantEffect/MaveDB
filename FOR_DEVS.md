# Quick start

This is a short guide on how to set up your development environment using docker. This guide assumes you will be using
PyCharm. If you are using another IDE/editor you will need to find a way to set up remote debugging and a remote
interpreter. To start off, clone the repository and open it up in PyCharm. PyCharm can also clone repositories for you
if you supply your login credentials/access token. Please make sure you switch to your feature branch, or the
**develop** branch.

# Requirements

Please install the following software:

- Docker
- Docker Compose
- Python 3
- Git

# Pre-commit hooks
Firstly create a virtual environment in root directory of the project (where `manage.py` is):

```shell
python3 -m venv ./venv
```

If you're using ZSH as your shell, in your `~/.zshrc` file  add `virtualenv` to your plugins and insert 
`export VIRTUAL_ENV_DISABLE_PROMPT=` as the last line. This is a magic trick that fixes issues with activating virtual 
environments using ZSH. Activate the virtual environment and install the [pre-commit](https://pre-commit.com/) package:

```shell
source ./venv/bin/activate && pip install pre-commit
```

Now run the `install` command via pre-commit to integrate into the git hook cycle and install the required hooks:

```shell
pre-commit install
```

To make sure it is running correctly, execute `pre-commit run` in your virtual environment. **IMPORTANT: make sure
to activate your virtual environment before committing code.** The hooks will now run on every commit performing checks
and formatting your code using [Black](https://github.com/psf/black). (TODO: Add pylint checks to the hooks config.)

# Database dump
We will restore a copy of the production database into your local development Postgres instance. Copy your database dump
file to `./docker/postgres/dumps`.

# Setting up docker-compose
In the menu bar, go to `Run > Edit Configurations`. In the top left click the '+' button and look for 
`Docker > Docker-compose` in the drop-down menu. In the `Name` input type in `MaveDB Development`. In the `Compose files`
select input the `docker-compose-dev.yml` file. In the `Environment variables` input field click the far right `page` icon 
and paste in the following block:

```text
MAVEDB_DB_USER=mave_admin;
MAVEDB_DB_PASSWORD=abc123;
MAVEDB_DB_NAME=mavedb;
MAVEDB_DUMP_FILE=name_of_your_file_or_keep_this_field_blank.dump;
COMPOSE_PROJECT_NAME=mavedb_dev
```

In the `Services` input box tick all the services using the small '+' button on the far right of the input box. Click
`Apply` then `Ok`.

# Settings file
Copy `settings/.settings-template.env` to `settings/.settings-development.env`. Change the following values:

```dotenv
APP_DB_PASSWORD=abc123
APP_DB_USER=mave_admin
APP_DB_NAME=mavedb

APP_SECRET_KEY="a-super-secret-key"
APP_ORCID_SECRET=
APP_ORCID_KEY=
APP_NCBI_API_KEY=
APP_API_BASE_URL=localhost:8000/api
APP_BASE_URL=localhost:8000/
APP_ALLOWED_HOSTS="localhost 127.0.0.1"
```

Make sure the `APP_DB_*` settings match your `MAVEDB_DB_*` settings from the previous docker-compose set-up step.

# Remote interpreter
Before setting up the remote interpreter via Docker-Compose, we will need to start the development compose service that
we have set up. In the top menu bar, go to `Run > Run > MaveDB Development`. Look at the output in the `Services` tab
at the bottom of the PyCharm window in the task bar. If you don't see it, in the top menu bar go to 
`View > Tool Windows > Services`. If you are running this process for the first time, the images will need to be 
built and this may take a few minutes. 

Before the MaveDB web application service starts, it will wait for the database and broker services to first
successfully start, then it will perform basic checks to see if the Celery service within the `app` container has
initialised correctly. It might look like the container entrypoint is hanging (messages about sleeping), but these checks 
are normal. The entrypoint script will continuously poll the broker and database container until they are ready to 
accept connections before moving on to running migrations and starting the server and celery daemon. If the script 
hangs for more than a few minutes, check that:

- Your connection environment variables and settings are correct
- The broker/database container have not exited due to an error

Once the static files have been collected, the Docker-Compose service is ready. You can check the logs by clicking
the side arrow next to `mavedb_dev` in the `Services` tab we just opened. Then click the arrow next to `app`. Now click
on `mavedb_dev_app_1` and click at the `Log` tab in the window that just appeared to the right. It should say *I am ready!*.

In the top menu bar, click `File > Settings` and search for 'Python Interpreter' in the search box. Click the gear icon
to the far right and then click `Add`. Click the `Docker` menu item, and next to `Image name` select `mavedb/mavedb:dev`.
This will take a few minutes to initialize, but once you're done PyCharm should recognise django imports and imports
from other packages living in the docker image.

## Tests and local server
In your terminal, start a new remote shell session in the `app` container with:

```shell
docker exec -it mavedb_dev_app_1 /bin/bash
```

In this terminal, to run the unit tests:

```shell
python manage.py test --exclude-tag=webtest
```

To start a local development server run:

```shell script
python manage.py runserver 0.0.0.0:8000
```

# Building a new image

## MaveHGVS docs
Place the `mavehgvs` sphinx documentation files into `/docs/mavehgvs/`. The build path in `Makefile` and `make.bat`
must be `../build/docs/mavehgvs/`. Once the application starts, this documentation will be collected in the static file
directory and served at `https://mavedb.org/docs/mavehgvs`.

You can use the `./publish` script to build a new image and push it to the MaveDB [Docker Hub repository](https://hub.docker.com/). 
The script takes the following arguments in the following order `IMAGE_NAME`, `TAG`, `REPOSITORY`', where `IMAGE_NAME` and `REPOSITORY`
are both `mavedb` for now.
