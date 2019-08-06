if [ "$1" != "" ]; then
    settings="--settings=$1"
else
    settings="--settings=settings.production"
fi

if [ "$2" != "" ]; then
    requirements="$2"
else
    requirements="production.txt"
fi

echo "Using settings $settings"
echo "Using requirements $requirements"


pip install -r requirements/$requirements \
  && python manage.py migrate $settings \
  && python manage.py createlicences $settings \
  && python manage.py createreferences $settings \
  && python manage.py collectstatic $settings \
  && python manage.py test accounts api core dataset genome main metadata search urn variant $settings