# About
Prototype for the MaveDB web application

# Requirements
- django-guardian (pip install django-guardian)
- pypandoc (pip install pypandoc, but may require installation of pandoc depending on the wheel available, and whether it includes pandoc)
- psycopg2 (pip install psycopg2, also requires python-devel installed through
apt-get/yum etc)

### For Unit/Functional testing
- selenium (pip install selenium)
- factory-boy (pip install factory-boy)

You may need to install [geckodriver](https://github.com/mozilla/geckodriver/releases) for running the functional test suite.

# Static Files
Run python manage.py collectstatic to collect static files.
