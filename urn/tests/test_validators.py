from django.test import TestCase
from django.core.exceptions import ValidationError

from ..validators import (
    validate_mavedb_urn,
    validate_mavedb_urn_experiment,
    validate_mavedb_urn_experimentset,
    validate_mavedb_urn_scoreset,
    validate_mavedb_urn_variant
)

from variant.factories import VariantFactory


class TestURNValidators(TestCase):
    """
    Tests all the URN validators using an instance of
    :class:`variant.models.Variant` as the driver.
    """
    def test_validationerror_malformed_experimentset_urn(self):
        variant = VariantFactory()
        with self.assertRaises(ValidationError):
            validate_mavedb_urn_experimentset(variant.urn)
        # Should pass
        validate_mavedb_urn_experimentset(
            variant.scoreset.experiment.experimentset.urn)

    def test_validationerror_malformed_experiment_urn(self):
        variant = VariantFactory()
        with self.assertRaises(ValidationError):
            validate_mavedb_urn_experiment(variant.urn)
        # Should pass
        validate_mavedb_urn_experiment(variant.scoreset.experiment.urn)

    def test_wrapped_experiment_urn_does_not_raise_error(self):
        variant = VariantFactory()
        validate_mavedb_urn_experiment(variant.scoreset.experiment.urn + 'a')

    def test_validationerror_malformed_scoreset_urn(self):
        variant = VariantFactory()
        with self.assertRaises(ValidationError):
            validate_mavedb_urn_scoreset(variant.urn)
        # Should pass
        validate_mavedb_urn_scoreset(variant.scoreset.urn)

    def test_validationerror_malformed_variant_urn(self):
        variant = VariantFactory()
        with self.assertRaises(ValidationError):
            validate_mavedb_urn_variant(variant.urn + 'extra')
        # Should pass
        validate_mavedb_urn_variant(variant.urn)

    def test_validationerror_malformed_any_urn(self):
        with self.assertRaises(ValidationError):
            validate_mavedb_urn("urn:mavedb:0001")

        variant = VariantFactory()
        instances = [
            variant,
            variant.scoreset,
            variant.scoreset.experiment,
            variant.scoreset.experiment.experimentset
        ]
        for i in instances:
            # Test should pass
            validate_mavedb_urn(i.urn)
