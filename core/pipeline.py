"""
Custom pipeline step for loading extra data within the ORCID pipeline.

See Also
--------
`Custom pipelines <https://github.com/python-social-auth/social-docs/blob/master/docs/pipeline.rst>`_
"""
from social_core.pipeline.social_auth import load_extra_data


def mave_load_extra_data(backend, details, response, uid, user,
                         *args, **kwargs):
    load_extra_data(backend, details, response, uid, user, *args, **kwargs)
    social = (
        kwargs.get('social') or
        backend.strategy.storage.user.get_social_auth(backend.name, uid)
    )
    if social:
        credit_name = response.get('person', {}).get('name', {}).get(
            'credit-name', {}).get('value', None)
        social.set_extra_data({'credit-name': credit_name})
