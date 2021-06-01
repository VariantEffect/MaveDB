from typing import Dict, Optional
import json

from django.test import TestCase, RequestFactory, mock
from django.contrib.auth import get_user_model

from accounts.factories import UserFactory

from dataset import factories
from dataset import utilities

from .. import views


User = get_user_model()


class TestSearchView(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.path = "/search/"
        self.exp1 = factories.ExperimentWithScoresetFactory()
        self.exp2 = factories.ExperimentWithScoresetFactory()
        self.exp3 = factories.ExperimentWithScoresetFactory()
        self.scs1 = self.exp1.scoresets.first()
        self.scs2 = self.exp2.scoresets.first()
        self.scs3 = self.exp3.scoresets.first()

        self.scs1 = utilities.publish_dataset(self.scs1)
        self.scs2 = utilities.publish_dataset(self.scs2)
        self.scs3 = utilities.publish_dataset(self.scs3)

        self.exp1.refresh_from_db()
        self.exp2.refresh_from_db()
        self.exp3.refresh_from_db()

    @staticmethod
    def mock_data(options: Optional[Dict] = None) -> Dict:
        data = {
            "draw": 1,
            "start": 0,
            "length": 10,
            "order[0][column]": "0",
            "order[0][dir]": "asc",
            "search[value]": "",
        }
        data.update(options or {})
        return data

    def test_search_returns_public_scoresets_when_not_logged_in(self):
        request = self.factory.post(
            self.path,
            data=self.mock_data(),
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )
        request.user = UserFactory()
        response = views.search_view(request)
        self.assertEqual(response.status_code, 200)

        data = json.loads(response.content)
        self.assertEqual(
            [record["urn"] for record in data.get("data")],
            [self.scs1.urn, self.scs2.urn, self.scs3.urn],
        )
        self.assertEqual(
            [record["parent_urn"] for record in data.get("data")],
            [self.exp1.urn, self.exp2.urn, self.exp3.urn],
        )

    def test_private_entries_for_user_have_private_in_name(self):
        user = UserFactory()
        self.exp1.private = True
        self.exp1.add_administrators(user)

        self.scs1.add_administrators(user)
        self.scs1.private = True

        self.exp1.save()
        self.scs1.save()

        request = self.factory.post(
            self.path,
            data=self.mock_data(),
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )
        request.user = user

        response = views.search_view(request)
        self.assertEqual(response.status_code, 200)

        data = json.loads(response.content)
        self.assertEqual(
            [record["urn_display"] for record in data.get("data")],
            [f"{self.scs1.urn} [Private]", self.scs2.urn, self.scs3.urn],
        )
        self.assertEqual(
            [record["parent_urn_display"] for record in data.get("data")],
            [f"{self.exp1.urn} [Private]", self.exp2.urn, self.exp3.urn],
        )

    def test_uses_search_panes_options(self):
        data = self.mock_data(
            {"searchPanes[target]": self.scs1.get_target().name}
        )
        request = self.factory.post(
            self.path,
            data=data,
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )
        request.user = None

        response = views.search_view(request)
        self.assertEqual(response.status_code, 200)

        data = json.loads(response.content)
        self.assertEqual(
            [record["urn"] for record in data.get("data")],
            [self.scs1.urn],
        )

    def test_uses_datatables_search_options(self):
        data = self.mock_data({"search[value]": self.scs1.urn})
        request = self.factory.post(
            self.path,
            data=data,
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )
        request.user = None

        response = views.search_view(request)
        self.assertEqual(response.status_code, 200)

        data = json.loads(response.content)
        self.assertEqual(
            [record["urn"] for record in data.get("data")],
            [self.scs1.urn],
        )

    def test_pagination(self):
        data = self.mock_data({"start": 1, "length": 1})
        request = self.factory.post(
            self.path,
            data=data,
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )
        request.user = None

        response = views.search_view(request)
        self.assertEqual(response.status_code, 200)

        data = json.loads(response.content)
        self.assertEqual(
            [record["urn"] for record in data.get("data")],
            [self.scs2.urn],
        )

    def test_ordering(self):
        data = self.mock_data(
            {
                "order[0][column]": "0",
                "order[0][dir]": "desc",
            }
        )
        request = self.factory.post(
            self.path,
            data=data,
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )
        request.user = None

        response = views.search_view(request)
        self.assertEqual(response.status_code, 200)

        data = json.loads(response.content)
        self.assertEqual(
            [record["urn"] for record in data.get("data")],
            [self.scs3.urn, self.scs2.urn, self.scs1.urn],
        )

    def test_formats_search_panes_options(self):
        request = self.factory.post(
            self.path,
            data=self.mock_data(),
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )
        request.user = None

        response = views.search_view(request)
        self.assertEqual(response.status_code, 200)

        data = json.loads(response.content)
        search_panes_data = data.get("searchPanes")["options"]

        for scoreset in [self.scs1, self.scs2, self.scs3]:
            self.assertTrue(
                scoreset.get_target().name
                in [r["value"] for r in search_panes_data["target"]]
            )
            self.assertTrue(
                scoreset.get_target().category
                in [r["value"] for r in search_panes_data["type"]]
            )
            self.assertTrue(
                scoreset.get_target()
                .get_primary_reference_map()
                .format_reference_genome_organism_html()
                in [r["value"] for r in search_panes_data["organism"]]
            )
