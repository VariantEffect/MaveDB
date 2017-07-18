# About
Prototype for the MaveDB web application

# Requirements
Running the site requires the following django apps:
- django-markup (pip install django-markup)
- django-markdownx (pip install django-markdownx)
- django-bootstrap3 (pip install django-bootstrap3)
- django-bootstrap-themes (pip install django-bootstrap-themes)
- django-crispy-forms (pip install django-crispy-forms)
- selenium (pip install selenium)

# Static Files
Run python manage.py collectstatic to collect static files.

# Database
Currently set as the the django default (SQLite3). This can be changed in mavedb/settings.py.

You may need to install [geckodriver](https://github.com/mozilla/geckodriver/releases) for running the functional test suite.
