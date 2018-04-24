"""
Custom pipeline step for loading extra data within the ORCID pipeline.

See Also
--------
`Custom pipelines <https://github.com/python-social-auth/social-docs/blob/master/docs/pipeline.rst>`_
"""
import logging
from social_core.pipeline.social_auth import load_extra_data

logger = logging.getLogger("django")


def mave_load_extra_data(backend, details, response, uid, user,
                         *args, **kwargs):
    load_extra_data(backend, details, response, uid, user, *args, **kwargs)
    social = (
        kwargs.get('social') or
        backend.strategy.storage.user.get_social_auth(backend.name, uid)
    )
    if social:
        try:
            credit_name = response.get('person', {}).get('name', {}).get(
                'credit-name', {}).get('value', "")
            social.set_extra_data({'credit-name': credit_name})
        except Exception as e:
            logging.warning(
                "Encountered the following exception when "
                "attempting to retrieve an ORCID credit-name: "
                "\n{}\nSetting credit-name to an empty string.".format(
                    str(e)
                )
            )
            social.set_extra_data({'credit-name': ""})
