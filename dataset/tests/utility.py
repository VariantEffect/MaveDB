import os
import json
from io import StringIO

from django.core.files.uploadedfile import InMemoryUploadedFile

from variant.factories import generate_hgvs

from .. import constants


def make_files(score_data=None, count_data=None, meta_data=None):
    """
    Make mock file objects used by django during a request post with a file
    input from text data.
    """
    hgvs_nt = generate_hgvs(prefix='c')
    hgvs_pro = generate_hgvs(prefix='p')
    
    if not score_data:
        string_io = StringIO("{},{},{},se\n{},{},0.5,0.4\n".format(
            constants.hgvs_nt_column, constants.hgvs_pro_column,
            constants.required_score_column, hgvs_nt, hgvs_pro,
        ))
    else:
        string_io = StringIO(score_data)
    size = string_io.seek(0, os.SEEK_END)
    string_io.seek(0)
    scores_file = InMemoryUploadedFile(
        file=string_io,
        name="scores.csv",
        field_name=None,
        content_type='text/csv',
        size=size,
        charset="utf-8"
    )

    if isinstance(count_data, bool) and count_data:
        string_io = StringIO("{},{},count,sig\n{},{},10,-1\n".format(
            constants.hgvs_nt_column, constants.hgvs_pro_column,
            hgvs_nt, hgvs_pro,
        ))
        size = string_io.seek(0, os.SEEK_END)
        string_io.seek(0)
        counts_file = InMemoryUploadedFile(
            file=string_io,
            name="counts.csv",
            field_name=None,
            content_type='text/csv',
            size=size,
            charset="utf-8"
        )
    elif count_data:
        counts_io = StringIO(count_data)
        size = counts_io.seek(0, os.SEEK_END)
        counts_io.seek(0)
        counts_file = InMemoryUploadedFile(
            file=counts_io,
            name="counts.csv",
            field_name=None,
            content_type='text/csv',
            size=size,
            charset="utf-8"
        )
    else:
        counts_file = None

    if isinstance(meta_data, dict):
        meta_data = json.dumps(meta_data)

    if isinstance(meta_data, bool) and meta_data:
        dict_ = {
            "inner": {"foo": 2, "bar": 1},
            "hello": ["world"]
        }
        string_io = StringIO(json.dumps(dict_))
        size = string_io.seek(0, os.SEEK_END)
        string_io.seek(0)
        meta_file = InMemoryUploadedFile(
            file=string_io,
            name="meta.json",
            field_name=None,
            content_type='json',
            size=size,
            charset="utf-8"
        )
    elif meta_data:
        string_io = StringIO(meta_data)
        size = string_io.seek(0, os.SEEK_END)
        string_io.seek(0)
        meta_file = InMemoryUploadedFile(
            file=string_io,
            name="meta.json",
            field_name=None,
            content_type='json',
            size=size,
            charset="utf-8"
        )
    else:
        meta_file = None

    return scores_file, counts_file, meta_file
