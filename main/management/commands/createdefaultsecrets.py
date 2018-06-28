import os
import sys
import json
import random
import string

from django.core.management.base import BaseCommand

BASE_DIR = os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))).replace('main/management', '')
SETTINGS_DIR = BASE_DIR + '/settings/'

class Command(BaseCommand):
    def handle(self, *args, **kwargs):
        secrets = {
            "orcid_key": "",
            "orcid_secret": "",
            "secret_key": "".join(
                [random.choice(
                    string.digits + string.ascii_letters + string.punctuation)
                    for _ in range(256)
                ]
            ),
            "database_user": "mave_admin",
            "database_password": "abc123",
            "database_host": "localhost",
            "database_port": "",
            "base_url": "127.0.0.1:8000"
        }
        
        path = os.path.join(SETTINGS_DIR, 'secrets.json')
        if os.path.isfile(path):
            while True:
                overwrite = input(
                    "An existing secrets file exists. "
                    "Would you like to overwrite this file? [y/N]")
                if overwrite == 'y':
                    with open(path, 'w') as fp:
                        json.dump(secrets, fp, sort_keys=True, indent=2)
                        sys.stdout.write("Created secrets file %s\n" % path)
                        return
                elif overwrite == 'N':
                    sys.stdout.write("Fine then.\n")
                    return
                else:
                    sys.stdout.write("Enter y or N.\n")
        else:
            with open(path, 'w') as fp:
                json.dump(secrets, fp, sort_keys=True, indent=2)
                sys.stdout.write("Created secrets file %s\n" % path)
