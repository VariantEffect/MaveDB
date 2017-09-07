# About
Prototype for the MaveDB web application

# Requirements
- django-guardian (pip install django-guardian)
- django-reversion (pip install django-reversion)
- pypandoc (pip install pypandoc, requires pandoc 1.19.x to be installed)
- psycopg2 (pip install psycopg2, may require python-devel)

### For Unit/Functional testing
- selenium (pip install selenium)
- factory-boy (pip install factory-boy)
- numpy (pip install numpy)

You may need to install [geckodriver](https://github.com/mozilla/geckodriver/releases) for running the functional test suite.

# Static Files
Run python manage.py collectstatic to collect static files.

# Django-reversion
[Django-reversion](https://django-reversion.readthedocs.io/en/stable/) has been integrated with the site. This is a well maintained model versioning application that keeps a history of each instance in the database for models that have been registered. There are two key commands to run when deploying:

python manage.py migrate
python manage.py createinitialrevisions

To delete recorded history for a particular model:

python manage.py deleterevisions <appname.modelname> --keep=<int> --days=<int>

This will keep anything from last X days and at least X history items.
