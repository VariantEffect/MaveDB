# About
Prototype for the MaveDB web application

# Requirements
- django-guardian (pip install django-guardian)
- pypandoc (pip install pypandoc, requires pandoc 1.19.x to be installed)
- psycopg2 (pip install psycopg2, may require python-devel)

### For Unit/Functional testing
- selenium (pip install selenium)
- factory-boy (pip install factory-boy)
- numpy (pip install numpy)

You may need to install [geckodriver](https://github.com/mozilla/geckodriver/releases) for running the functional test suite.

# Static Files
Run python manage.py collectstatic to collect static files.
