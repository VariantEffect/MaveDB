
from main.models import Keyword
from django.test import TransactionTestCase


class TestKeyword(TransactionTestCase):
    """
    This suite of tests the correctness of the Keyword class.
    """

    def test_can_create_and_save_keyword(self):
        kw = Keyword.objects.create(
            name="DNA repair"
        )
        self.assertEqual(Keyword.objects.count(), 1)

    def test_associate_keyword_with_experiment(self):
        from experiment.models import Experiment
        exp = Experiment.objects.create(
            wt_sequence="ATCG", target="brca1"
        )
        kw = Keyword.objects.create(
            name="DNA repair",
            experiment=exp
        )
        self.assertEqual(exp.keyword_set.count(), 1)

    def test_associate_keyword_with_scoreset(self):
        from experiment.models import Experiment
        from scoreset.models import ScoreSet
        exp = Experiment.objects.create(
            wt_sequence="ATCG", target="brca1"
        )
        scs = ScoreSet.objects.create(
            experiment=exp
        )
        kw = Keyword.objects.create(
            name="DNA repair",
            experiment=None,
            scoreset=scs
        )
        self.assertEqual(exp.keyword_set.count(), 0)
        self.assertEqual(scs.keyword_set.count(), 1)
