import datetime

from django.db import IntegrityError
from django.db import models
from django.test import TransactionTestCase
from django.contrib.auth import get_user_model

from metadata.models import (
    Keyword, SraIdentifier, PubmedIdentifier, DoiIdentifier
)

from ..models import DatasetModel, ExperimentSet


User = get_user_model()


class DatasetModelDriver(DatasetModel):
    """Test driver for the abstract class :class:`DatasetModel`."""
    def create_urn(self):
        return '{}-{}'.format(self.URN_PREFIX, self.pk)


class TestDatasetModel(TransactionTestCase):
    reset_sequences = True

    def test_save_updates_last_edit_date(self):
        self.fail()

    def test_set_created_by_sets_updates_created_by(self):
        self.fail()

    def test_set_last_edit_by_propagates_to_parents(self):
        self.fail()

    def test_publish_sets_private_to_false(self):
        self.fail()

    def test_typeerror_add_non_keyword_instance(self):
        self.fail()

    def test_typeerror_add_non_external_identifier_instance(self):
        self.fail()

    def test_clear_m2m_clears_m2m_relationships(self):
        self.fail()

    def test_approve_sets_approved_to_true(self):
        self.fail()
