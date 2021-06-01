from django.contrib.messages.storage.fallback import FallbackStorage
from django.test import TestCase

from celery.contrib.testing.worker import start_worker
from mavedb import celery_app


class TestMessageMixin:
    """
    Tests will fail on views that user messages. Use this mixin to prevent
    these tests failing. Assumes the caller has a `django.test.RequestFactory`
    attribute `self.factory`.
    """

    def create_request(self, method="get", **kwargs):
        request = getattr(self.factory, method)(**kwargs)
        setattr(request, "session", "session")
        messages = FallbackStorage(request)
        setattr(request, "_messages", messages)
        return request


class CeleryTestCase(TestCase):
    allow_database_queries = True

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # Start up celery worker
        celery_app.loader.import_module("celery.contrib.testing.tasks")
        cls.celery_worker = start_worker(celery_app, perform_ping_check=False)
        cls.celery_worker.__enter__()

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()

        # Close worker
        cls.celery_worker.__exit__(None, None, None)
