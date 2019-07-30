"""
Custom pipeline step for loading extra data within the ORCID pipeline.

See Also
--------
`Custom pipelines <https://github.com/python-social-auth/social-docs/blob/master/docs/pipeline.rst>`_
"""
import logging
from social_core.pipeline.social_auth import load_extra_data

logger = logging.getLogger("django")


def mave_load_extra_data(
    backend, details, response, uid, user, *args, **kwargs
):
    load_extra_data(backend, details, response, uid, user, *args, **kwargs)
    social = kwargs.get(
        "social"
    ) or backend.strategy.storage.user.get_social_auth(backend.name, uid)
    if social:
        if "person" in response:
            person = response.get("person", {})
            if person:
                name = person.get("name", {})
            else:
                social.set_extra_data({"credit-name": ""})
                return

            if name:
                credit_name = name.get("credit-name", {})
            else:
                social.set_extra_data({"credit-name": ""})
                return

            if credit_name:
                credit_name_value = credit_name.get("value", "")
            else:
                social.set_extra_data({"credit-name": ""})
                return

            if credit_name_value:
                social.set_extra_data({"credit-name": credit_name_value})
            else:
                social.set_extra_data({"credit-name": ""})
                return
        else:
            social.set_extra_data({"credit-name": ""})
            return
