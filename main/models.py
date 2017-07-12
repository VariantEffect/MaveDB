
import datetime
from django.db import models
from django.core.validators import MinValueValidator
from markdownx.models import MarkdownxField
from markdownx.utils import markdownify


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
    date = models.DateField(blank=False, default=datetime.date.today)
    accession = models.CharField(default="", blank=False, max_length=1024)
    target = models.CharField(default="", blank=False, max_length=1024)
    author = models.CharField(default="", blank=False, max_length=1024)
    reference = models.CharField(default="", blank=False, max_length=1024)
    alt_reference = models.CharField(default="", blank=False, max_length=1024)
    scoring_method = models.CharField(default="", blank=False, max_length=1024)
    keywords = models.CharField(default="", blank=False, max_length=1024)
    read_depth = models.IntegerField(
        default=1, blank=False, validators=[MinValueValidator(1)])
    base_coverage = models.PositiveIntegerField(
        default=1, blank=False, validators=[MinValueValidator(1)])
    num_variants = models.PositiveIntegerField(
        default=1, blank=False, validators=[MinValueValidator(1)])

    def __str__(self):
        return "Experiment(\n\t" + \
            str(self.accession) + '\n\t' + \
            str(self.target) + '\n\t' + \
            str(self.date) + '\n\t' + \
            str(self.author) + '\n\t' + \
            str(self.reference) + '\n\t' + \
            str(self.alt_reference) + '\n\t' + \
            str(self.scoring_method) + '\n\t' + \
            str(self.keywords) + '\n\t' + \
            str(self.read_depth) + '\n\t' + \
            str(self.base_coverage) + '\n\t' + \
            str(self.num_variants)


def make_random_experiment():
    import names
    import random as rand

    references = {
        "BOVIN": "Bovine", "CHICK": "Chicken",
        "ECOLI": "Escherichia coli", "HORSE": "Horse",
        "HUMAN": "Homo sapiens", "MAIZE": "Maize (Zea mays)",
        "MOUSE": "Mouse", "PEA": "Garden pea (Pisum sativum)",
        "PIG": "Pig", "RABIT": "Rabbit",
        "RAT": "Rat", "SHEEP": "Sheep",
        "SOYBN": "Soybean (Glycine max)",
        "TOBAC": "Common tobacco (Nicotina tabacum)",
        "WHEAT": "Wheat (Triticum aestivum)",
        "YEAST": "Baker’s yeast (Saccharomyces cerevisiae)"
    }
    targets = [
        "A2M", "ABL1", "APEX1", "APOC3", "APOE", "BDNF", "BLM", "BRCA1",
        "BRCA2", "BSCL2", "CDC42", "CDK1", "CDK7", "CEBPA", "CEBPB", "DBN1",
        "DDIT3", "DGAT1", "DLL3", "E2F1", "EGF", "EGFR", "EGR1", "ELN",
        "EMD", "UCHL1", "UCP1", "UCP2", "UCP3", "VCP", "VEGFA",
        "WRN", "XPA", "XRCC5", "XRCC6"
    ]

    methods = ['WLS Regression', 'OLS Regression', 'Log Ratios']
    keywords = [
        'Kinase', 'Disease', 'Metastasis', 'Energy Production',
        'DNA Repair', 'Response to Cellular Damage', 'Cell Structure',
        'Methylase'
    ]

    num = rand.randint(0, 1000)
    org_code = rand.choice(list(references.keys()))

    accession = 'EXP' + '0'*(4-len(str(num))) + str(num) + org_code
    target = rand.choice(targets)
    author = ', '.join(
        [names.get_full_name() for _ in range(0, rand.randint(1, 4))])
    primary_ref = references[org_code]
    secondary_ref = references[rand.choice(list(references.keys()))]
    method = rand.choice(methods)
    read_depth = rand.randint(10, 50)
    base_coverage = rand.randint(10, 100)
    num_variants = rand.randint(50, 1000)
    keywords = ', '.join(
        [rand.choice(keywords) for _ in range(0, rand.randint(1, 4))])
    date = datetime.date.today() - \
        datetime.timedelta(days=rand.randint(0, 500))

    exp = Experiment.objects.create(
        accession=accession,
        target=target,
        author=author,
        reference=primary_ref,
        alt_reference=secondary_ref,
        scoring_method=method,
        read_depth=read_depth,
        base_coverage=base_coverage,
        num_variants=num_variants,
        keywords=keywords,
        date=date
    )
    return exp
