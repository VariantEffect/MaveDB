"""
Custom pipeline step for loading extra data within the ORCID pipeline.

See Also
--------
`Custom pipelines <https://github.com/python-social-auth/social-docs/blob/master/docs/pipeline.rst>`_
"""

def load_extra_data(backend, details, response, uid, user, *args, **kwargs):
    social = kwargs.get('social') or \
             backend.strategy.storage.user.get_social_auth(backend.name, uid)
    if social:
        extra_data = backend.extra_data(user, uid, response, details,
                                        *args, **kwargs)
        social.set_extra_data(extra_data)
        social.set_extra_data({'credit-name': 'credit_name'})
