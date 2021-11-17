import json
import os
from pathlib import Path
import zipfile

from django.db import transaction
from django.contrib.auth import get_user_model

from .constants import BASE_RESULTS_DIR
from .utilities import format_variant_get_response
from celery.utils.log import get_task_logger
from core.tasks import BaseTask
from mavedb import celery_app
from variant.models import Variant

User = get_user_model()
logger = get_task_logger("api.tasks")

@celery_app.task(ignore_result=False, base=BaseTask)
def format_variant_large_get_response(results_uuid, variant_urn, offset, limit):
    '''
    For large responses, asynchronously call format_variant_get_response()
    and save the output to a file for the user to access/download later.
    '''
    results_dir = BASE_RESULTS_DIR
    Path(results_dir).mkdir(parents=True, exist_ok=True)

    results_identifier = results_uuid
    results_json_filepath = f'{results_dir}/{results_identifier}.json'
    results = format_variant_get_response(variant_urn, offset, limit)
    with open(results_json_filepath, 'w') as f:
        json.dump(results, f)

    # If we need more files like metadata or something, we can add them here.
    files_to_zip = []
    files_to_zip.append(results_json_filepath)

    zip_filename = f'{BASE_RESULTS_DIR}/{results_identifier}.zip'
    zip_file = zipfile.ZipFile(zip_filename, 'w')

    for filepath in files_to_zip:
        fdir, fname = os.path.split(filepath)
        zip_file.write(filepath, fname)
    zip_file.close()
