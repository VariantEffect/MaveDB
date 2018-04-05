import os
from io import StringIO

from django.core.files.uploadedfile import InMemoryUploadedFile

from dataset.constants import hgvs_column, required_score_column
from variant.factories import generate_hgvs


def make_score_count_files(score_data=None, count_data=None):
    """
    Make mock file objects used by django during a request post with a file
    input from text data.
    """
    hgvs = generate_hgvs()
    if not score_data:
        string_io = StringIO("{},{},se\n{},0.5,0.4\n".format(
            hgvs_column, required_score_column, hgvs
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
        string_io = StringIO("{},count,sig\n{},10,-1\n".format(
            hgvs_column, hgvs
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
        return scores_file, counts_file

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
        return scores_file, counts_file

    return scores_file, None
