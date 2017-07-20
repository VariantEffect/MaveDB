
import datetime
from django.db import models
from django.core.validators import MinValueValidator


class News(models.Model):
    text = models.TextField(blank=False, default="")
    date = models.DateField(blank=False, default=datetime.date.today)

    class Meta:
        ordering = ['-date']
        verbose_name_plural = "News items"
        verbose_name = "News item"

    def __str__(self):
        return '[{}]: {}'.format(str(self.date), self.text)

    def save(self, *args, **kwargs):
        if self.text is None:
            raise ValueError("A null message is not allowed.")
        elif not self.text.strip():
            raise ValueError("A blank message is not allowed.")

        if self.date is None:
            raise ValueError("A null date is not allowed.")
        try:
            datetime.datetime.strptime(str(self.date), '%Y-%m-%d')
        except ValueError:
            raise ValueError("Incorrect data format, should be YYYY-MM-DD")
        else:
            super().save(*args, **kwargs)

    @property
    def message(self):
        return str(self)

    @staticmethod
    def recent_news():
        return News.objects.all()[0: 10]


class SiteInformation(models.Model):
    about = models.TextField(default="", blank=False)
    citation = models.TextField(default="", blank=False)
    # TODO: Create these fields:
    # usage_guide
    # documentation
    # help
    # terms
    # privacy

    class Meta:
        verbose_name_plural = "Site Information"
        verbose_name = "Site Information"

    def can_save(self):
        existing = SiteInformation.objects.all()
        if len(existing) < 1:
            return True
        else:
            return existing[0].pk == self.pk

    def save(self, *args, **kwargs):
        if self.about is None:
            raise ValueError("A null about is not allowed.")
        elif not self.about.strip():
            raise ValueError("A blank about is not allowed.")
        if self.citation is None:
            raise ValueError("A null citation is not allowed.")
        elif not self.citation.strip():
            raise ValueError("A blank citation is not allowed.")

        if not self.can_save():
            raise ValueError("This is a singleton table. Cannot add entry.")
        else:
            super().save(*args, **kwargs)


# -------------------------------------------------------------------------- #
#
#                           DEBUG/TESTING GROUNDS
#
# -------------------------------------------------------------------------- #
class Experiment(models.Model):
    accession = models.CharField(
        default="", blank=False, max_length=128, verbose_name="Accession")

    target = models.CharField(
        default="", blank=False, max_length=128,
        verbose_name="Target")
    authors = models.TextField(
        default="", blank=False, verbose_name="Author(s)")
    wt_sequence = models.TextField(
        default="", blank=False, verbose_name='Wild type sequence')
    date = models.DateField(
        default=datetime.date.today, blank=False,
        verbose_name="Publication date")

    target_organism = models.TextField(
        blank=True, default="", verbose_name="Target organism")
    abstract = models.TextField(
        default="", blank=True, verbose_name="Abstract")
    short_description = models.TextField(
        default="", blank=True, verbose_name="Short description")
    method_description = models.TextField(
        default="", blank=True, verbose_name="Method description")
    keywords = models.TextField(
        default="", blank=True, verbose_name="Keywords")
    alt_target_accessions = models.TextField(
        default="", blank=True, verbose_name="Accessions")

    placeholder_text = {
        'accession': 'EXP0001HSA',
        'target': 'BRCA1',
        'authors': 'Author 1, Author 2, ...',
        'wt_sequence': 'ATCG or atcg',
        'target_organism': 'Homo Sapiens',
        'keywords': 'Kinase, DNA repair, ...',
        'alt_target_accessions': 'UniProt, RefSeq'
    }

    def __str__(self):
        return "Experiment(\n\t" + \
            str(self.accession) + '\n\t' + \
            str(self.target) + '\n\t' + \
            str(self.wt_sequence) + '\n\t' + \
            str(self.date)

    @property
    def author_count(self):
        return len(self.authors.split(','))

    @property
    def formatted_authors(self):
        if self.author_count > 1:
            last = self.authors.split(',')[0].split(' ')[1]
            return "{} et al.".format(last)
        else:
            first = self.authors.split(',')[0].split(' ')[0]
            last = self.authors.split(',')[0].split(' ')[1]
            return '{}, {}'.format(last, first)

    @property
    def short_date(self):
        year = self.date.year
        month = self.date.month
        day = self.date.day
        return '{}/{}/{}'.format(year, month, day)

    @property
    def score_sets(self):
        return self.scoreset_set.all()


class ScoreSet(models.Model):
    HEADER = 'hgvs,score,SE'
    experiment = models.ForeignKey(
        'Experiment', on_delete=models.CASCADE)

    accession = models.CharField(
        default="", blank=False, max_length=128, verbose_name="Accession")
    authors = models.TextField(
        default="", blank=False, verbose_name="Author(s)")
    dataset = models.TextField(
        default=HEADER, blank=False, verbose_name="Dataset")

    abstract = models.TextField(
        default="", blank=True, verbose_name="Abstract")
    theory = models.TextField(
        default="", blank=True, verbose_name="Method theory")
    keywords = models.TextField(
        default="", blank=True, verbose_name="Keywords")
    name = models.TextField(
        default="", blank=True, verbose_name="Score set name")


    def __str__(self):
        return "ScoreSet({}, {})".format(self.accession, self.experiment.pk)

    def data_header(self):
        return [x.strip() for x in
                self.dataset.split('\n')[0].strip().split(',')]

    def data_rows(self):
        for row in self.dataset.split('\n')[1:]:
            if row:
                yield [x.strip() for x in row.strip().split(',')]


# -------------------------------------------------------------------------- #
#                        DATABASE POPULATION
# -------------------------------------------------------------------------- #
def make_random_scoreset():
    import random as rand
    import names
    from faker import Faker

    fake = Faker()
    possible_experiments = [e for e in Experiment.objects.all()]
    experiment = rand.choice(possible_experiments)
    abstract = '. '.join(
        [fake.text() for _ in range(rand.randint(1, 15))])
    theory = '. '.join(
        [fake.text() for _ in range(rand.randint(1, 15))])

    score_set_count = experiment.scoreset_set.count()
    exp_accession = experiment.accession
    accession = exp_accession.replace(
        "EXP", "SCS") + '.{}'.format(score_set_count + 1)
    authors = ', '.join(
        [names.get_full_name() for _ in range(0, rand.randint(1, 4))])
    keywords = ['Regression', 'Log ratios', "Weighted", 'Ordinary']
    name = rand.choice(keywords)
    dataset=ScoreSet.HEADER + '\n'

    for i in range(1, 256):
        dataset += 'hgvs_str,{},{}\n'.format(*[rand.random() for i in range(2)])


    return ScoreSet.objects.create(
        accession=accession,
        abstract=abstract,
        theory=theory,
        experiment=experiment,
        authors=authors,
        keywords=', '.join(rand.choice(keywords) for _ in range(0, 3)),
        name=name,
        dataset=dataset
    )


def make_random_experiment():
    import names
    import random as rand
    from faker import Faker
    fake = Faker()

    references = {
        "BVN": "Bovine",
        "ECO": "Escherichia coli",
        "HSA": "Homo sapiens",
        "MUS": "Mus musculus",
        "YST": "Saccharomyces cerevisiae"
    }
    targets = [
        "A2M", "ABL1", "APEX1", "APOC3", "APOE", "BDNF", "BLM", "BRCA1",
        "BRCA2", "BSCL2", "CDC42", "CDK1", "CDK7", "CEBPA", "CEBPB", "DBN1",
        "DDIT3", "DGAT1", "DLL3", "E2F1", "EGF", "EGFR", "EGR1", "ELN",
        "EMD", "UCHL1", "UCP1", "UCP2", "UCP3", "VCP", "VEGFA",
        "WRN", "XPA", "XRCC5", "XRCC6"
    ]
    keywords = [
        'Kinase', 'Disease', 'Metastasis', 'Energy Production',
        'DNA Repair', 'Response to Cellular Damage', 'Cell Structure',
        'Methylase'
    ]
    alts = [
        'P11142', 'Q9H446', 'Q9UJM8',
        'NG_055433.1', 'NR_148450.1', 'NR_148445.1',
        'NP_001340125.1', 'NP_001340126.1', 'NP_001340004.1'
    ]

    num = rand.randint(0, 1000)
    org_code = rand.choice(list(references.keys()))
    accession = 'EXP' + '0'*(4-len(str(num))) + str(num) + org_code
    target = rand.choice(targets)
    authors = ', '.join(
        [names.get_full_name() for _ in range(0, rand.randint(1, 4))])
    target_org = references[org_code]
    size = rand.randint(1, 5)
    keywords = [rand.choice(keywords) for _ in range(size)]
    keywords = ', '.join(keywords)
    date = datetime.date.today() - \
        datetime.timedelta(days=rand.randint(0, 500))

    exp = Experiment.objects.create(
        accession=accession,

        target=target,
        authors=authors,
        date=date,
        wt_sequence=''.join(rand.choice('ATCG') for _ in range(256, 512)),

        short_description='. '.join(
            [fake.text() for _ in range(rand.randint(1, 4))]),
        abstract='. '.join(
            [fake.text() for _ in range(rand.randint(8, 16))]),
        target_organism=target_org,
        alt_target_accessions=', '.join(rand.choice(alts) for _ in range(0, 3)),
        keywords=keywords,
        method_description='. '.join(
            [fake.text() for _ in range(rand.randint(1, 4))])
    )
    return exp
