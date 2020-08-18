# Quick start
Welcome to MaveDB; a place where all your wildest dreams will come true. This is a short guide on
how to set up your development environment. Windows is not supported due to the Celery package not
supporting Windows but you could potentially use WSL2 to host your developmnent environment and then
develop from within Windows. However, at the time of writing this guide, my PC is apprently 'Not 
yet ready for the Windows 10 2004 update', which contains the WSL2 update. Therefore, if you
would like to proceed with a WSL2 development environment so you can play Steam games between 
running the test suite, good luck.

## Requirements
Docker is great: you can run all sorts of software without cataclysmically destroying all your
system package version dependencies. So, please install the following software:

- Docker
- Docker Compose

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
click the gear icon at the top right and click `Add`. Create a new virtual environment pointing to 
python 3.6 (You can install additional python versions using [pyenv](https://github.com/pyenv/pyenv-installer)).

Done! Now open up a terminal within PyCharm and run `pip install -r requirements/development.txt`.
Your envrionment is now ready to roll. 

### Auto-formatting

I recommend using a file watcher to format your code on save. Follow 
[these instructions](https://black.readthedocs.io/en/stable/editor_integration.html) to get set up.
The only addition is using the argument -l 79 to limit your line length to 79 characters.

## Django setup

If you plan on running the tests (which you should...) then you'll need to point PyCharm to the 
correct settings file. Go to `File > Settings > Language & Frameworks > Django` and point the
settings input box to `settings/development.py`.

## Settings file

This project now uses `.env` files to configure project settings, like database connections, 
allowed hosts, celery configuration etc. There is a template file waiting for you in the `settings`
directory. Create a new file in the same directory called `.settings-development.env` and then cut 
and paste the template into this file. The most important ones are the database and broker connection 
settings. Please choose your favourite database password and username; They can be anything, so let 
your wildest dreams become a reality! However, the database name must be `mavedb`. As for the broker 
and database ports, I've used 5763 and 5433 respectively. You can change these to whatever your like, 
as long as your remain consistent in the next step. The remaining settings can be adjusted to 
whatever you like. Gunicorn settings are not required for development so you may ignore these.

## Docker

Docker expects a few environment variables when running the database and broker services. The file
`host_env.sh` contains a template for you to copy into your shell profile. Do not modify this file 
since it is tracked by git. The settings I've exported in my bash profile for development are:

```shell
export MAVEDB_DB_USER=whatever_you_set_from_last_step
export MAVEDB_DB_PASSWORD=whatever_you_set_from_last_step
export MAVEDB_DB_PORT=whatever_you_set_from_last_step
export MAVEDB_DB_NAME=mavedb
export MAVEDB_BROKER_PORT=whatever_you_set_from_last_step
```

Refresh your shell environment as these are referenced by the docker compose file. Speaking of 
which, to run the development server and test suite, you'll need to start the services with:

```shell script
docker-compose -f docker-compose-dev.yml up database broker
```

Do this everytime you want to start working on the project, but only once per system login.

## Seeding the database

Please run the following commands to in a PyCharm terminal to initialize the database:

```shell script
python manage.py migrate \
  && python manage.py updatesiteinfo \
  && python manage.py createlicences \
  && python manage.py createreferences \
  && python manage.py collectstatic \
  && python manage.py test
```

Developing with a copy of the production database is not a half bad idea, since we can test on
real data. Once you've done your initial database migrations for a fresh project run:

```shell script
docker exec -i \ 
  <your docker-compose database container name> \
  pg_restore -Fc \ 
  -U ${MAVEDB_DB_USER} \
  -d ${MAVEDB_DB_NAME} \
  < "/home/daniel/Desktop/m_test/mavedb_2020_07_28.dump"
```

You can find your docker-compose database container name by typing `docker ps` in the terminal and
looking for your postgres service. It should follow the format `<root folder>_database_1`.

## Conclusion

You're all set up and ready to go! Happy hacking!