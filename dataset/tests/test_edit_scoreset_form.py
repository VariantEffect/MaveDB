from django.test import TestCase, RequestFactory

from accounts.factories import UserFactory
from accounts.permissions import assign_user_as_instance_admin
from main.models import Licence
from variant.factories import VariantFactory

import dataset.constants as constants

from ..factories import ExperimentFactory, ScoreSetFactory
from ..forms.scoreset import ScoreSetEditForm

from .utility import make_score_count_files


class TestScoreSetEditForm(TestCase):
    """
    Tests functionality of the fields specific to the ScoreSetForm.
    """
    def setUp(self):
        self.user = UserFactory()
        self.factory = RequestFactory()

    def make_post_data(self, score_data=None, count_data=None,
                       make_exp=True):
        """
        Makes sample test input for instantiating the form to simulate
        POST data from a view. By default creates an experiment and
        assigns the class user as the administrator.

        Parameters
        ----------
        score_data : str or None
            The score file content in string format

        count_data : str, boolean or None
            The score file content in string format

        make_exp : bool
            If True, makes an experiment, otherwise leaves this as None
        """
        experiment = None
        if make_exp:
            experiment = ExperimentFactory()
            assign_user_as_instance_admin(self.user, experiment)
        data = {
            'short_description': 'experiment',
            'title': 'title',
            "experiment": experiment.pk if experiment else None,
        }
        s_file, c_file = make_score_count_files(score_data, count_data)
        files = {constants.variant_score_data: s_file}
        if c_file is not None:
            files[constants.variant_count_data] = c_file
        return data, files

    def test_empty_data_submission_is_invalid(self):
        obj = ScoreSetFactory()
        form = ScoreSetEditForm(data={}, user=self.user, instance=obj)
        self.assertFalse(form.is_valid())

    def test_cannot_save_popped_field(self):
        exp = ExperimentFactory()
        replaced = ScoreSetFactory(experiment=exp)
        obj = ScoreSetFactory(replaces=replaced)
        for i in range(5):
            VariantFactory(scoreset=obj)

        old_experiment = obj.experiment
        old_licence = obj.licence
        old_replaces = obj.previous_version
        old_variants = obj.children

        data, files = self.make_post_data()
        data['licence'] = Licence.get_cc0()
        data['replaces'] = ScoreSetFactory(experiment=exp).pk
        form = ScoreSetEditForm(
            data=data, files=files, user=self.user, instance=obj
        )
        instance = form.save(commit=True)
        self.assertTrue(form.is_valid())
        self.assertEqual(instance.children.count(), old_variants.count())
        self.assertEqual(instance.experiment, old_experiment)
        self.assertEqual(instance.previous_version, old_replaces)
        self.assertEqual(instance.licence, old_licence)
