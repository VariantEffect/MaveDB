#!/usr/bin/env python

"""
This module contains helper functions relating to pandoc ReSt/Md output
"""

import pypandoc

PANDOC_DEFAULT_ARGS = [
    '--mathml',
    '--smart',
    '--standalone',
    '--biblatex',
    '--html-q-tags'
]


def convert_md_to_html(source, extra_args=PANDOC_DEFAULT_ARGS, **kwargs):
    """
    Convert a string that is written in markdown to a html format. Ignores
    keyword arguments "format" and "to".
    """
    kwargs = {k: v for k, v in kwargs.items() if k not in ["format", "to"]}
    return pypandoc.convert_text(
        source, to='html', format="md", extra_args=extra_args, **kwargs
    )


def convert_rest_to_html(source, extra_args=PANDOC_DEFAULT_ARGS, **kwargs):
    """
    Convert a string that is written in rest to a html format. Ignores
    keyword arguments "format" and "to".
    """
    kwargs = {k: v for k, v in kwargs.items() if k not in ["format", "to"]}
    return pypandoc.convert_text(
        source, to='html', format="rest", extra_args=extra_args, **kwargs
    )
