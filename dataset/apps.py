from django.contrib.auth.management import create_permissions
from django.apps import apps


class DatasetConfig(apps.AppConfig):
    name = 'dataset'


create_permissions(apps.get_app_config('dataset'))
