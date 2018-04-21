from django.test import TestCase, mock
from social_django.compat import reverse
from social_django.models import UserSocialAuth

mock_person = {
    "last-modified-date": {
        "value": 1523885850931
    },
    "name": {
        "created-date": {
            "value": 1501480300784
        },
        "last-modified-date": {
            "value": 1524279424178
        },
        "given-names": {
            "value": "John"
        },
        "family-name": {
            "value": "Smith"
        },
        "credit-name": {
            "value": "Dudebroman"
        },
        "source": None,
        "visibility": "PUBLIC",
        "path": "0000-0002-0001-0003"
    },
    "other-names": {
        "last-modified-date": {
            "value": 1505114342843
        },
        "other-name": [
            {
                "created-date": {
                    "value": 1501480597224
                },
                "last-modified-date": {
                    "value": 1505114342843
                },
                "source": {
                    "source-orcid": {
                        "uri": "http://orcid.org/0000-0002-0001-0003",
                        "path": "0000-0002-0001-0003",
                        "host": "orcid.org"
                    },
                    "source-client-id": None,
                    "source-name": {
                        "value": "Dudebroman"
                    }
                },
                "content": "John C Smith",
                "visibility": "PUBLIC",
                "path": "/0000-0002-0001-0003/other-names/978953",
                "put-code": 978953,
                "display-index": 1
            }
        ],
        "path": "/0000-0002-0001-0003/other-names"
    },
    "biography": None,
    "researcher-urls": {
        "last-modified-date": None,
        "researcher-url": [],
        "path": "/0000-0002-0001-0003/researcher-urls"
    },
    "emails": {
        "last-modified-date": {
            "value": 1523885777896
        },
        "email": [
            {
                "created-date": {
                    "value": 1501480301005
                },
                "last-modified-date": {
                    "value": 1523885777896
                },
                "source": {
                    "source-orcid": {
                        "uri": "http://orcid.org/0000-0002-0001-0003",
                        "path": "0000-0002-0001-0003",
                        "host": "orcid.org"
                    },
                    "source-client-id": None,
                    "source-name": {
                        "value": "Dudebroman"
                    }
                },
                "email": "yproctor@fakemail.com",
                "path": None,
                "visibility": "PUBLIC",
                "verified": True,
                "primary": True,
                "put-code": None
            }
        ],
        "path": "/0000-0002-0001-0003/email"
    },
    "addresses": {
        "last-modified-date": {
            "value": 1501480583422
        },
        "address": [
            {
                "created-date": {
                    "value": 1501480583422
                },
                "last-modified-date": {
                    "value": 1501480583422
                },
                "source": {
                    "source-orcid": {
                        "uri": "http://orcid.org/0000-0002-0001-0003",
                        "path": "0000-0002-0001-0003",
                        "host": "orcid.org"
                    },
                    "source-client-id": None,
                    "source-name": {
                        "value": "Dudebroman"
                    }
                },
                "country": {
                    "value": "AU"
                },
                "visibility": "PUBLIC",
                "path": "/0000-0002-0001-0003/address/753757",
                "put-code": 753757,
                "display-index": 1
            }
        ],
        "path": "/0000-0002-0001-0003/address"
    },
    "keywords": {
        "last-modified-date": {
            "value": 1523885850931
        },
        "keyword": [
            {
                "created-date": {
                    "value": 1501480564153
                },
                "last-modified-date": {
                    "value": 1523885850931
                },
                "source": {
                    "source-orcid": {
                        "uri": "http://orcid.org/0000-0002-0001-0003",
                        "path": "0000-0002-0001-0003",
                        "host": "orcid.org"
                    },
                    "source-client-id": None,
                    "source-name": {
                        "value": "Dudebroman"
                    }
                },
                "content": "Bioinformatics",
                "visibility": "PUBLIC",
                "path": "/0000-0002-0001-0003/keywords/754348",
                "put-code": 754348,
                "display-index": 4
            }
        ],
        "path": "/0000-0002-0001-0003/keywords"
    },
    "external-identifiers": {
        "last-modified-date": None,
        "external-identifier": [],
        "path": "/0000-0002-0001-0003/external-identifiers"
    },
    "path": "/0000-0002-0001-0003/person"
}


class TestOrcidLogin(TestCase):
    def setUp(self):
        session = self.client.session
        session['orcid_state'] = '1'
        session.save()

    @mock.patch('social_core.backends.base.BaseAuth.request')
    def test_complete(self, mock_request):
        url = reverse('social:complete', kwargs={'backend': 'orcid'})
        url += '?code=2&state=1'
        mock_request.return_value.json.return_value = {
            'access_token': '123',
            'orcid': '0000-0002-0001-0003',
            'person': mock_person,
        }
        with mock.patch('django.contrib.sessions.backends.base.SessionBase'
                        '.set_expiry', side_effect=[OverflowError, None]):
            response = self.client.get(url)
            self.assertEqual(response.status_code, 302)
            self.assertEqual(response.url, '/accounts/profile/')
            self.assertEqual(UserSocialAuth.objects.count(), 1)

            social = UserSocialAuth.objects.first()
            print(social.extra_data)
            user = social.user
            self.assertEqual(user.profile.get_display_name(), 'Dudebroman')
