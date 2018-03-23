import os
from io import StringIO

from django.core.files.uploadedfile import InMemoryUploadedFile


def make_score_count_files(score_data=None, count_data=None):
    """
    Make mock file objects used by django during a request post with a file
    input from text data.
    """
    if not score_data:
        string_io = StringIO("hgvs,score,se\nc.54A>G,0.5,0.4\n")
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

    if count_data:
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
