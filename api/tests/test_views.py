import io
import json
import pandas as pd
import numpy as np
from datetime import timedelta

from django.test import TestCase, RequestFactory, mock
from django.contrib.auth import get_user_model
from django.core import exceptions
from django.http import HttpResponse

from rest_framework import exceptions

from accounts.factories import UserFactory

from core.utilities import null_values_list

import dataset.constants as constants
from dataset.utilities import publish_dataset
from dataset.models import scoreset, experimentset
from dataset.factories import (
    ScoreSetFactory,
    ExperimentFactory,
    ExperimentSetFactory,
)

from variant.factories import VariantFactory
from variant.models import Variant

from .. import views


User = get_user_model()


class TestFormatPolicy(TestCase):
    def test_splits_into_lines_of_77_chars_length(self):
        lines = views.format_policy("This, " * 1000, line_wrap_len=77)
        for line in lines:
            self.assertTrue(len(line) <= 77)

    def test_not_specified_if_policy_not_provided(self):
        lines = views.format_policy("", line_wrap_len=77)
        self.assertListEqual(["# Not specified\n"], lines)


class TestAuthenticate(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.user = UserFactory()
        self.client.login(
            username=self.user.username, password=self.user.password
        )

    def test_returns_request_user_if_token_is_none(self):
        request = self.factory.get("/", HTTP_AUTHORIZATION=None)
        request.user = self.user
        user, token = views.authenticate(request)
        self.assertIs(self.user, user)
        self.assertIsNone(token)

    def test_raises_auth_failed_invalid_token_format(self):
        with self.assertRaises(exceptions.AuthenticationFailed):
            request = self.factory.get("/", HTTP_AUTHORIZATION="a")
            views.authenticate(request)

    def test_raises_auth_failed_invalid_token_for_user(self):
        token, exp = self.user.profile.generate_token()
        self.user.profile.generate_token()
        with self.assertRaises(exceptions.AuthenticationFailed):
            request = self.factory.get("/", HTTP_AUTHORIZATION=token)
            views.authenticate(request)

    def test_raises_auth_failed_expired_token(self):
        token, _ = self.user.profile.generate_token()
        profile = self.user.profile
        profile.auth_token_expiry -= timedelta(days=100)
        profile.save()
        with self.assertRaises(exceptions.AuthenticationFailed):
            request = self.factory.get("/", HTTP_AUTHORIZATION=token)
            views.authenticate(request)

    def test_returns_user_and_token_on_success(self):
        token, _ = self.user.profile.generate_token()
        request = self.factory.get("/", HTTP_AUTHORIZATION=token)
        user, ret_token = views.authenticate(request)
        self.assertEqual(token, ret_token)
        self.assertEqual(self.user, user)

    def test_returns_none_none_by_default(self):
        request = self.factory.get("/", HTTP_AUTHORIZATION=None)
        request.user = None
        user, ret_token = views.authenticate(request)
        self.assertIsNone(ret_token)
        self.assertIsNone(user)


class TestCheckPermission(TestCase):
    def test_raises_403_error_private_and_user_is_none(self):
        with self.assertRaises(exceptions.PermissionDenied):
            instance = ScoreSetFactory(private=True)
            views.check_permission(instance, user=None)

    def test_raises_403_private_instance_user_not_a_contributor(self):
        with self.assertRaises(exceptions.PermissionDenied):
            instance = ScoreSetFactory(private=True)
            user = UserFactory()
            views.check_permission(instance, user=user)

    def test_returns_instance_when_private_and_user_is_contributor(self):
        instance = ScoreSetFactory(private=True)
        user = UserFactory()
        instance.add_viewers(user)
        self.assertIs(instance, views.check_permission(instance, user=user))

    def test_returns_instance_when_it_is_public(self):
        instance = ScoreSetFactory(private=False)
        self.assertIs(instance, views.check_permission(instance, user=None))


class TestAuthenticatedViewSet(TestCase):
    def setUp(self):
        self.factory = RequestFactory()

    @mock.patch(
        "api.views.authenticate", side_effect=lambda request: (None, None)
    )
    def test_dispatch_calls_authenticate(self, patch):
        self.client.get("/api/experimentsets/")
        patch.assert_called()


class TestDatasetListViewSet(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.user = UserFactory()
        self.client.login(
            username=self.user.username, password=self.user.password
        )

    @mock.patch(
        "api.views.filter_visible",
        side_effect=lambda instances, user: experimentset.ExperimentSet.objects.none(),
    )
    def test_get_qs_calls_viewable_instances_for_user_with_authed_user(
        self, patch
    ):
        request = self.factory.get(
            "/api/experimentsets/", HTTP_AUTHORIZATION=None
        )
        request.user = self.user
        views.ExperimentSetViewset.as_view({"get": "list"})(request)
        self.assertEqual(self.user, patch.call_args[1]["user"])

    @mock.patch(
        "api.views.check_permission",
        side_effect=lambda instance, user: instance,
    )
    def test_get_object_calls_check_perm_with_instance_and_user(self, patch):
        i = ExperimentSetFactory(private=False)
        request = self.factory.get(
            "/api/experimentsets/{}/".format(i.urn), HTTP_AUTHORIZATION=None
        )
        request.user = self.user
        views.ExperimentSetViewset.as_view({"get": "retrieve"})(
            request, urn=i.urn
        )
        patch.assert_called_with(*(i, self.user))

    @mock.patch("api.views.check_permission")
    def test_get_object_doesnt_call_check_perm_instance_not_found(self, patch):
        request = self.factory.get(
            "/api/experimentsets/{}/".format("aaa"), HTTP_AUTHORIZATION=None
        )
        request.user = self.user
        views.ExperimentSetViewset.as_view({"get": "retrieve"})(
            request, urn="aaa"
        )
        patch.assert_not_called()

    @mock.patch("api.views.check_permission")
    def test_get_object_doesnt_call_check_perm_urn_is_none(self, patch):
        request = self.factory.get(
            "/api/experimentsets/{}/".format("aaa"), HTTP_AUTHORIZATION=None
        )
        request.user = self.user
        views.ExperimentSetViewset.as_view({"get": "retrieve"})(
            request, urn=None
        )
        patch.assert_not_called()


class TestExperimentSetAPIViews(TestCase):
    factory = ExperimentSetFactory
    url = "experimentsets"

    def test_403_private_experimentset(self):
        inst = self.factory(private=True)
        response = self.client.get("/api/{}/{}/".format(self.url, inst.urn))
        self.assertEqual(response.status_code, 403)

    def test_OK_private_experimentset_when_authenticated(self):
        inst = self.factory(private=True)
        user = UserFactory()
        user.profile.generate_token()
        inst.add_viewers(user)
        response = self.client.get(
            "/api/{}/{}/".format(self.url, inst.urn),
            HTTP_AUTHORIZATION=user.profile.auth_token,
        )
        self.assertEqual(response.status_code, 200)

    def test_404_wrong_address(self):
        inst = self.factory()
        response = self.client.get(
            "/api/{}/{}/".format(self.url + "aaa", inst.urn)
        )
        self.assertEqual(response.status_code, 404)

    def test_404_experimentset_not_found(self):
        response = self.client.get("/api/{}/dddd/".format(self.url))
        self.assertEqual(response.status_code, 404)

    def test_list_excludes_private_when_not_authenticated(self):
        instance1 = self.factory(private=True)
        instance2 = self.factory(private=False)
        response = self.client.get("/api/{}/".format(self.url))
        self.assertNotContains(response, instance1.urn)
        self.assertContains(response, instance2.urn)

    def test_list_includes_private_when_authenticated(self):
        instance1 = self.factory(private=True)
        instance2 = self.factory(private=False)
        user = UserFactory()
        user.profile.generate_token()
        instance1.add_viewers(user)
        response = self.client.get(
            "/api/{}/".format(self.url),
            HTTP_AUTHORIZATION=user.profile.auth_token,
        )
        self.assertContains(response, instance1.urn)
        self.assertContains(response, instance2.urn)


class TestExperimentAPIViews(TestCase):
    factory = ExperimentFactory
    url = "experiments"

    def test_403_private_experimentset(self):
        inst = self.factory(private=True)
        response = self.client.get("/api/{}/{}/".format(self.url, inst.urn))
        self.assertEqual(response.status_code, 403)

    def test_OK_private_experimentset_when_authenticated(self):
        inst = self.factory(private=True)
        user = UserFactory()
        user.profile.generate_token()
        inst.add_viewers(user)
        response = self.client.get(
            "/api/{}/{}/".format(self.url, inst.urn),
            HTTP_AUTHORIZATION=user.profile.auth_token,
        )
        self.assertEqual(response.status_code, 200)

    def test_404_wrong_address(self):
        inst = self.factory()
        response = self.client.get(
            "/api/{}/{}/".format(self.url + "aaa", inst.urn)
        )
        self.assertEqual(response.status_code, 404)

    def test_404_experimentset_not_found(self):
        response = self.client.get("/api/{}/dddd/".format(self.url))
        self.assertEqual(response.status_code, 404)

    def test_list_excludes_private_when_not_authenticated(self):
        instance1 = self.factory(private=True)
        instance2 = self.factory(private=False)
        response = self.client.get("/api/{}/".format(self.url))
        self.assertNotContains(response, instance1.urn)
        self.assertContains(response, instance2.urn)

    def test_list_includes_private_when_authenticated(self):
        instance1 = self.factory(private=True)
        instance2 = self.factory(private=False)
        user = UserFactory()
        user.profile.generate_token()
        instance1.add_viewers(user)
        response = self.client.get(
            "/api/{}/".format(self.url),
            HTTP_AUTHORIZATION=user.profile.auth_token,
        )
        self.assertContains(response, instance1.urn)
        self.assertContains(response, instance2.urn)


class TestFormatCSVRows(TestCase):
    def test_dicts_include_urn(self):
        vs = [VariantFactory() for _ in range(5)]
        rows = views.format_csv_rows(
            vs,
            columns=["score", "accession"],
            dtype=constants.variant_score_data,
        )
        for v, row in zip(vs, rows):
            self.assertEqual(v.urn, row["accession"])

    def test_dicts_include_nt_hgvs(self):
        vs = [VariantFactory() for _ in range(5)]
        rows = views.format_csv_rows(
            vs,
            columns=["score", constants.hgvs_nt_column],
            dtype=constants.variant_score_data,
        )
        for v, row in zip(vs, rows):
            self.assertEqual(v.hgvs_nt, row[constants.hgvs_nt_column])

    def test_dicts_include_pro_hgvs(self):
        vs = [VariantFactory() for _ in range(5)]
        rows = views.format_csv_rows(
            vs,
            columns=["score", constants.hgvs_pro_column],
            dtype=constants.variant_score_data,
        )
        for v, row in zip(vs, rows):
            self.assertEqual(v.hgvs_pro, row[constants.hgvs_pro_column])

    def test_dicts_include_data_columns_as_strings(self):
        vs = [
            VariantFactory(
                data={constants.variant_score_data: {"score": 1, "se": 2.12}}
            )
            for _ in range(5)
        ]
        rows = views.format_csv_rows(
            vs, columns=["score", "se"], dtype=constants.variant_score_data
        )
        for v, row in zip(vs, rows):
            self.assertEqual("1", row["score"])
            self.assertEqual("2.12", row["se"])


class TestValidateRequest(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.user = UserFactory()
        self.request = self.factory.get("/")
        self.request.user = self.user
        self.instance = ScoreSetFactory(private=True)

    def test_returns_404_response_when_urn_model_not_found(self):
        response = views.validate_request(self.request, "urn")
        self.assertEqual(response.status_code, 404)

    @mock.patch("api.views.validate_request")
    def test_calls_authenticate(self, patch):
        views.validate_request(self.request, self.instance.urn)
        patch.assert_called()

    @mock.patch("api.views.validate_request")
    def test_calls_check_permission(self, patch):
        views.validate_request(self.request, self.instance.urn)
        patch.assert_called()


class TestFormatResponse(TestCase):
    def setUp(self):
        self.user = UserFactory()
        self.instance = ScoreSetFactory(private=True)
        self.response = HttpResponse(content_type="text/csv")

    def test_adds_comments_to_response(self):
        response = views.format_response(
            self.response, self.instance, dtype="scores"
        )
        content = response.content.decode()
        self.assertIn("# Accession: {}".format(self.instance.urn), content)
        self.assertIn("# Downloaded (UTC):", content)
        self.assertIn(
            "# Licence: {}".format(self.instance.licence.long_name), content
        )
        self.assertIn(
            "# Licence URL: {}".format(self.instance.licence.link), content
        )

    def test_raises_valueerror_unknown_dtype(self):
        with self.assertRaises(ValueError):
            views.format_response(self.response, self.instance, dtype="---")

    @mock.patch("api.views.format_csv_rows")
    def test_calls_format_csv_correct_call_dtype_is_scores(self, patch):
        self.instance.dataset_columns = {
            constants.score_columns: ["score", "se"]
        }
        self.instance.save()
        for i in range(5):
            data = {constants.variant_score_data: {"score": i, "se": 2 * i}}
            VariantFactory(scoreset=self.instance, data=data)

        _ = views.format_response(self.response, self.instance, dtype="scores")

        called_dtype = patch.call_args[1]["dtype"]
        called_columns = patch.call_args[1]["columns"]
        expected_columns = ["accession"] + self.instance.score_columns
        self.assertEqual(called_dtype, constants.variant_score_data)
        self.assertListEqual(called_columns, expected_columns)

    @mock.patch("api.views.format_csv_rows")
    def test_calls_format_csv_correct_call_dtype_is_counts(self, patch):
        self.instance.dataset_columns = {
            constants.count_columns: ["count", "se"]
        }
        self.instance.save()
        for i in range(5):
            data = {constants.variant_count_data: {"count": i, "se": 2 * i}}
            VariantFactory(scoreset=self.instance, data=data)

        _ = views.format_response(self.response, self.instance, dtype="counts")

        called_dtype = patch.call_args[1]["dtype"]
        called_columns = patch.call_args[1]["columns"]
        expected_columns = ["accession"] + self.instance.count_columns
        self.assertEqual(called_dtype, constants.variant_count_data)
        self.assertListEqual(called_columns, expected_columns)

    @mock.patch("api.views.format_csv_rows")
    def test_returns_empty_csv_when_no_additional_columns_present(self, patch):
        _ = views.format_response(self.response, self.instance, dtype="scores")
        patch.assert_not_called()

    def test_double_quotes_column_values_containing_commas(self):
        self.instance.dataset_columns = {
            constants.score_columns: ["hello,world"]
        }

        for i in range(5):
            data = {constants.variant_score_data: {"hello,world": i}}
            VariantFactory(scoreset=self.instance, data=data)

        response = views.format_response(
            self.response, self.instance, dtype="scores"
        )
        content = response.content.decode()
        self.assertIn('"hello,world"', content)

    def test_formats_null_values_as_NA(self):
        for null in null_values_list:
            response = HttpResponse(content_type="text/csv")
            self.instance.variants.all().delete()
            self.assertFalse(self.instance.variants.count())
            self.instance.dataset_columns = {
                constants.score_columns: ["score"]
            }
            variant_count = 5
            for i in range(variant_count):
                data = {constants.variant_score_data: {"score": null}}
                VariantFactory(scoreset=self.instance, data=data)
            response = views.format_response(
                response, self.instance, dtype="scores"
            )

            handle = io.StringIO(response.content.decode())
            comment_line_count = 0
            for line in handle:
                if line.startswith("#"):
                    comment_line_count += 1
                else:
                    break
            handle.seek(0)
            df = pd.read_csv(handle, skiprows=comment_line_count)
            self.assertEqual(df.score.where(np.isnan).size, variant_count)
            handle.close()


class TestScoreSetAPIViews(TestCase):
    factory = ScoreSetFactory
    url = "scoresets"

    def setUp(self):
        Variant.objects.all().delete()
        scoreset.ScoreSet.objects.all().delete()

    def tearDown(self):
        Variant.objects.all().delete()
        scoreset.ScoreSet.objects.all().delete()

    # ---- DRF Views
    def test_403_private_experimentset(self):
        inst = self.factory(private=True)
        response = self.client.get("/api/{}/{}/".format(self.url, inst.urn))
        self.assertEqual(response.status_code, 403)

    def test_OK_private_experimentset_when_authenticated(self):
        inst = self.factory(private=True)
        user = UserFactory()
        user.profile.generate_token()
        inst.add_viewers(user)
        response = self.client.get(
            "/api/{}/{}/".format(self.url, inst.urn),
            HTTP_AUTHORIZATION=user.profile.auth_token,
        )
        self.assertEqual(response.status_code, 200)

    def test_404_wrong_address(self):
        inst = self.factory()
        response = self.client.get(
            "/api/{}/{}/".format(self.url + "aaa", inst.urn)
        )
        self.assertEqual(response.status_code, 404)

    def test_404_experimentset_not_found(self):
        response = self.client.get("/api/{}/dddd/".format(self.url))
        self.assertEqual(response.status_code, 404)

    def test_list_excludes_private_when_not_authenticated(self):
        instance1 = self.factory(private=True)
        instance2 = self.factory(private=False)
        response = self.client.get("/api/{}/".format(self.url))
        self.assertNotContains(response, instance1.urn)
        self.assertContains(response, instance2.urn)

    def test_list_includes_private_when_authenticated(self):
        instance1 = self.factory(private=True)
        instance2 = self.factory(private=False)
        user = UserFactory()
        user.profile.generate_token()
        instance1.add_viewers(user)
        response = self.client.get(
            "/api/{}/".format(self.url),
            HTTP_AUTHORIZATION=user.profile.auth_token,
        )
        self.assertContains(response, instance1.urn)
        self.assertContains(response, instance2.urn)

    # ----- Function based file download views
    def test_403_private_download_scores(self):
        instance = self.factory(private=True)
        response = self.client.get(
            "/api/scoresets/{}/scores/".format(instance.urn)
        )
        self.assertTrue(response.status_code, 403)

    def test_403_private_download_counts(self):
        instance = self.factory(private=True)
        response = self.client.get(
            "/api/scoresets/{}/counts/".format(instance.urn)
        )
        self.assertTrue(response.status_code, 403)

    def test_403_private_download_meta(self):
        instance = self.factory(private=True)
        response = self.client.get(
            "/api/scoresets/{}/metadata/".format(instance.urn)
        )
        self.assertTrue(response.status_code, 403)

    def test_OK_private_download_scores_when_authenticated(self):
        instance = self.factory(private=True)
        user = UserFactory()
        user.profile.generate_token()
        instance.add_viewers(user)
        response = self.client.get(
            "/api/scoresets/{}/scores/".format(instance.urn),
            HTTP_AUTHORIZATION=user.profile.auth_token,
        )
        self.assertTrue(response.status_code, 200)

    def test_OK_private_download_counts_when_authenticated(self):
        instance = self.factory(private=True)
        user = UserFactory()
        user.profile.generate_token()
        instance.add_viewers(user)
        response = self.client.get(
            "/api/scoresets/{}/counts/".format(instance.urn),
            HTTP_AUTHORIZATION=user.profile.auth_token,
        )
        self.assertTrue(response.status_code, 200)

    def test_OK_private_download_meta_when_authenticated(self):
        instance = self.factory(private=True)
        user = UserFactory()
        user.profile.generate_token()
        instance.add_viewers(user)
        response = self.client.get(
            "/api/scoresets/{}/metadata/".format(instance.urn),
            HTTP_AUTHORIZATION=user.profile.auth_token,
        )
        self.assertTrue(response.status_code, 200)

    def test_404_not_found(self):
        response = self.client.get("/api/scoresets/dddd/")
        self.assertEqual(response.status_code, 404)

    @mock.patch("api.views.format_response")
    def test_calls_format_response_with_dtype_scores(self, patch):
        request = RequestFactory().get("/")
        request.user = UserFactory()
        instance = self.factory(private=False)
        instance.add_viewers(request.user)
        views.scoreset_score_data(request, instance.urn)
        self.assertEqual(patch.call_args[1]["dtype"], "scores")

    @mock.patch("api.views.format_response")
    def test_calls_format_response_with_dtype_counts(self, patch):
        request = RequestFactory().get("/")
        request.user = UserFactory()
        instance = self.factory(private=False)
        instance.add_viewers(request.user)
        views.scoreset_count_data(request, instance.urn)
        self.assertEqual(patch.call_args[1]["dtype"], "counts")

    @mock.patch("api.views.format_policy")
    def test_doesnt_call_format_policy_not_policy_present(self, patch):
        request = RequestFactory().get("/")
        request.user = UserFactory()
        instance = self.factory(private=False)
        instance.data_usage_policy = " "
        instance.save()
        instance.add_viewers(request.user)
        views.scoreset_score_data(request, instance.urn)
        patch.assert_not_called()

    @mock.patch("api.views.format_policy")
    def test_calls_format_policy_if_policy_exists(self, patch):
        request = RequestFactory().get("/")
        request.user = UserFactory()
        instance = self.factory(private=False)
        instance.data_usage_policy = "Use freely."
        instance.save()
        instance.add_viewers(request.user)
        views.scoreset_score_data(request, instance.urn)
        patch.assert_called_with(*("Data usage policy: Use freely.",))

    def test_can_download_metadata(self):
        scs = self.factory(private=False)
        scs = publish_dataset(scs)
        scs.refresh_from_db()
        response = json.loads(
            self.client.get(
                "/api/scoresets/{}/metadata/".format(scs.urn)
            ).content.decode()
        )
        self.assertEqual(response, scs.extra_metadata)
