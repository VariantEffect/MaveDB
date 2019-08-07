from django.test import TestCase

from accounts.factories import UserFactory

from metadata.factories import (
    SraIdentifierFactory,
    KeywordFactory,
    PubmedIdentifierFactory,
    DoiIdentifierFactory,
)

from ..factories import ExperimentSetFactory
from ..forms.base import DatasetModelForm


class TestDataSetModelForm(TestCase):
    """
    Tests that the base model form can correctly handle m2m relationship
    validation and textual field validation. Uses :class:`ExperimentSet`
    as the driver.
    """

    def setUp(self):
        self.user = UserFactory()
        self.data = {"short_description": "experimentset", "title": "title"}

    def test_will_create_new_keywords(self):
        self.data.update(**{"keywords": ["protein"]})
        obj = ExperimentSetFactory()
        form = DatasetModelForm(data=self.data, user=self.user, instance=obj)
        obj = form.save(commit=True)
        self.assertEqual(obj.keywords.first().text, "protein")

    def test_will_create_new_identifiers(self):
        fs = [
            (SraIdentifierFactory, "sra_ids"),
            (PubmedIdentifierFactory, "pubmed_ids"),
            (DoiIdentifierFactory, "doi_ids"),
        ]
        for factory, attr in fs:
            m2m = factory()
            self.data.update(**{attr: [m2m.identifier]})
            m2m.delete()  # delete instance from db so it's new

            obj = ExperimentSetFactory()
            form = DatasetModelForm(
                data=self.data, user=self.user, instance=obj
            )
            obj = form.save(commit=True)
            self.assertEqual(
                getattr(obj, attr).first().identifier, self.data[attr][0]
            )

    def test_will_associate_existing_keywords(self):
        kw = KeywordFactory()
        self.data.update(**{"keywords": [kw.text]})
        obj = ExperimentSetFactory()
        form = DatasetModelForm(data=self.data, user=self.user, instance=obj)

        before_count = KeywordFactory._meta.model.objects.count()
        obj = form.save(commit=True)
        after_count = KeywordFactory._meta.model.objects.count()

        self.assertEqual(before_count, after_count)
        self.assertEqual(obj.keywords.first().text, kw.text)

    def test_will_associate_existing_identifiers(self):
        fs = [
            (SraIdentifierFactory, "sra_ids"),
            (PubmedIdentifierFactory, "pubmed_ids"),
            (DoiIdentifierFactory, "doi_ids"),
        ]
        for factory, attr in fs:
            m2m = factory()
            self.data.update(**{attr: [m2m.identifier]})
            obj = ExperimentSetFactory()
            form = DatasetModelForm(
                data=self.data, user=self.user, instance=obj
            )

            before_count = factory._meta.model.objects.count()
            obj = form.save(commit=True)
            after_count = factory._meta.model.objects.count()

            self.assertEqual(before_count, after_count)
            self.assertEqual(
                getattr(obj, attr).first().identifier, self.data[attr][0]
            )

    def test_will_clear_existing_keywords(self):
        kw = KeywordFactory()
        self.data.update(**{"keywords": [kw.text]})
        obj = ExperimentSetFactory()
        obj.keywords.add(KeywordFactory())
        form = DatasetModelForm(data=self.data, user=self.user, instance=obj)

        before_count = KeywordFactory._meta.model.objects.count()
        obj = form.save(commit=True)
        after_count = KeywordFactory._meta.model.objects.count()

        self.assertEqual(before_count, after_count)
        self.assertEqual(obj.keywords.first().text, kw.text)

    def test_will_clear_existing_identifiers(self):
        fs = [
            (SraIdentifierFactory, "sra_ids"),
            (PubmedIdentifierFactory, "pubmed_ids"),
            (DoiIdentifierFactory, "doi_ids"),
        ]
        for factory, attr in fs:
            self.data.update(**{attr: []})
            obj = ExperimentSetFactory()
            self.assertEqual(getattr(obj, attr).count(), 1)
            form = DatasetModelForm(
                data=self.data, user=self.user, instance=obj
            )

            before_count = factory._meta.model.objects.count()
            obj = form.save(commit=True)
            after_count = factory._meta.model.objects.count()

            self.assertEqual(before_count, after_count)
            self.assertEqual(getattr(obj, attr).count(), 0)

    def test_m2m_instances_for_field_returns_new_instances(self):
        fs = [
            (SraIdentifierFactory, "sra_ids"),
            (PubmedIdentifierFactory, "pubmed_ids"),
            (DoiIdentifierFactory, "doi_ids"),
        ]
        for factory, attr in fs:
            new = factory()
            self.data.update(**{attr: [new.identifier]})
            new.delete()  # delete instance from db so it's new

            obj = ExperimentSetFactory()
            form = DatasetModelForm(
                data=self.data, user=self.user, instance=obj
            )
            self.assertTrue(form.is_valid())
            self.assertEqual(
                form.m2m_instances_for_field(attr, True)[0].identifier,
                self.data[attr][0],
            )

    def test_m2m_instances_for_field_returns_existing_instances(self):
        fs = [
            (SraIdentifierFactory, "sra_ids"),
            (PubmedIdentifierFactory, "pubmed_ids"),
            (DoiIdentifierFactory, "doi_ids"),
        ]
        for factory, attr in fs:
            new = factory()
            self.data.update(**{attr: [new.identifier]})
            obj = ExperimentSetFactory()
            form = DatasetModelForm(
                data=self.data, user=self.user, instance=obj
            )
            self.assertTrue(form.is_valid())
            self.assertEqual(form.m2m_instances_for_field(attr)[0], new)

    def test_save_updates_modified_by(self):
        obj = ExperimentSetFactory()
        form = DatasetModelForm(self.data, user=self.user, instance=obj)
        form.save(commit=True)
        self.assertEqual(obj.modified_by, self.user)

    def test_will_not_override_created_by(self):
        obj = ExperimentSetFactory()
        obj.created_by = self.user
        obj.save()
        form = DatasetModelForm(self.data, user=UserFactory(), instance=obj)
        form.save(commit=True)
        self.assertEqual(obj.created_by, self.user)

    def test_save_updates_created_by(self):
        obj = ExperimentSetFactory()
        form = DatasetModelForm(self.data, user=self.user, instance=obj)
        form.save(commit=True)
        self.assertEqual(obj.created_by, self.user)
