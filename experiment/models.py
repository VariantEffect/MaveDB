
import datetime

from django.conf import settings
from django.db import models
from django.core.exceptions import ValidationError


class ExperimentSet(models.Model):
    """
    This is the class representing a set of related Experiments. Related
    experiments are those that generally had the same data collection
    methodology, same target, target organism etc, but differed in
    the experimental condition and scoring process.

    Parameters
    ----------
    accession : `str`
        This is the only required field, and should be specified at all points
        of instantiation (ExperimentSet, ExperimentSet.objects.create).
    Methods
    -------
    next_accession
        Creates a new accession by creating a digit that is the count of
        current class (active and inactive) plus 1.
    save
        Validates an experiment's fields and saves it to the database if it
        passes all checks. Raises a :py:class:`ValidationError` if a check
        fails.
    """
    # ---------------------------------------------------------------------- #
    #                       Class members/functions
    # ---------------------------------------------------------------------- #
    ACCESSION_DIGITS = 6
    ACCESSION_PREFIX = "EXPS"
    ACCESSION_DEFAULT = "EXPS_DEFAULT"

    @classmethod
    def next_accession(cls):
        """
        Creates a new accession by creating a digit that is the count of
        current class (active and inactive) plus 1.

        Parameters
        ----------
        cls : :py:class:`models.base.ModelBase`
            A class that subclasses django's base model.

        Returns
        -------
        `str`:
            The next accession incremented according to the current
            database entries.
        """
        digit_suffix = cls.objects.count() + 1
        fill_width = cls.ACCESSION_DIGITS - len(str(digit_suffix)) + 1
        accession = cls.ACCESSION_PREFIX + \
            str(digit_suffix).zfill(fill_width)
        return accession

    @classmethod
    def create(cls, **kwargs):
        if not kwargs.get("accession", None):
            kwargs["accession"] = cls.next_accession()

        cls_kwargs = {
            k: v for k, v in kwargs.items()
            if k not in ["save", "owners"]}
        exp_set = cls(**cls_kwargs)
        exp_set.owners = kwargs.get("owners", [])

        if kwargs.get("save", False):
            exp_set.save()
        return exp_set

    # ---------------------------------------------------------------------- #
    #                       Model fields
    # ---------------------------------------------------------------------- #
    accession = models.CharField(
        unique=True, primary_key=True,
        default=ACCESSION_DEFAULT, blank=False, null=False,
        max_length=ACCESSION_DIGITS + len(ACCESSION_PREFIX),
        name="accession", verbose_name="Accession")

    creation_date = models.DateField(
        blank=False, null=False, default=datetime.date.today,
        name="creation_date", verbose_name="Creation date")

    approved = models.BooleanField(
        blank=False, null=False, default=False,
        name="approved", verbose_name="Approved")

    owners = models.ManyToManyField(to=settings.AUTH_USER_MODEL)

    # ---------------------------------------------------------------------- #
    #                       Meta class
    # ---------------------------------------------------------------------- #
    class Meta:
        ordering = ['-creation_date']
        verbose_name = "ExperimentSet"
        verbose_name_plural = "ExperimentSets"

    # ---------------------------------------------------------------------- #
    #                       Data model
    # ---------------------------------------------------------------------- #
    def __str__(self):
        return "ExperimentSet({}, {}, {}, {})".format(
            str(self.accession),
            str(self.owners.all()),
            str(self.creation_date),
            str(self.experiment_set.all()))

    # ---------------------------------------------------------------------- #
    #                       Properties
    # ---------------------------------------------------------------------- #
    @property
    def active_owners(self):
        return self.owners.filter(is_active=True)

    @property
    def inactive_owners(self):
        return self.owners.filter(is_active=False)

    @property
    def all_owners(self):
        return self.owners.all()


class Experiment(models.Model):
    """
    This is the class representing an Experiment. The experiment object
    houses all information relating to a particular experiment up to the
    scoring of its associated variants.

    Parameters
    ----------
    accession : `str`
        This is the only required field, and should be specified at all points
        of instantiation (Experiment, Experiment.objects.create).

    Methods
    -------
    next_accession
        Creates a new accession by creating a digit that is the count of
        current class (active and inactive) plus 1.
    save
        Validates an experiment's fields and saves it to the database if it
        passes all checks. Raises a :py:class:`ValidationError` if a check
        fails.
    """
    # ---------------------------------------------------------------------- #
    #                       Class members/functions
    # ---------------------------------------------------------------------- #
    ACCESSION_DIGITS = 6
    ACCESSION_PREFIX = "EXP"
    ACCESSION_DEFAULT = "EXP_DEFAULT"

    @classmethod
    def next_accession(cls):
        """
        Creates a new accession by creating a digit that is the count of
        current class (active and inactive) plus 1.

        Parameters
        ----------
        cls : :py:class:`models.base.ModelBase`
            A class that subclasses django's base model.

        Returns
        -------
        `str`:
            The next accession incremented according to the current
            database entries.
        """
        digit_suffix = cls.objects.count() + 1
        fill_width = cls.ACCESSION_DIGITS - len(str(digit_suffix)) + 1
        accession = cls.ACCESSION_PREFIX + \
            str(digit_suffix).zfill(fill_width)
        return accession

    @classmethod
    def create(cls, **kwargs):
        owners = kwargs.get("owners", [])
        save = kwargs.get("save", False)

        if not kwargs.get("accession", None):
            kwargs["accession"] = cls.next_accession()
        if not kwargs.get("experiment_set", None):
            exp_set = ExperimentSet.create(owners=owners)
            kwargs["experiment_set"] = exp_set

        cls_kwargs = {
            k: v for k, v in kwargs.items()
            if k not in ["save", "owners"]}
        exp = cls(**cls_kwargs)
        exp.owners = owners
        if save:
            exp.save()
        return exp

    # ---------------------------------------------------------------------- #
    #                       Model fields
    # ---------------------------------------------------------------------- #
    accession = models.CharField(
        unique=True, primary_key=True,
        default=ACCESSION_DEFAULT, blank=False, null=False,
        max_length=ACCESSION_DIGITS + len(ACCESSION_PREFIX),
        name="accession", verbose_name="Accession")

    creation_date = models.DateField(
        blank=False, null=False, default=datetime.date.today,
        name="creation_date", verbose_name="Creation date")

    approved = models.BooleanField(
        blank=False, null=False, default=False,
        name="approved", verbose_name="Approved")

    owners = models.ManyToManyField(to=settings.AUTH_USER_MODEL)

    experiment_set = models.ForeignKey(
        to=ExperimentSet, on_delete=models.PROTECT, null=True,
        default=None
    )

    # ---------------------------------------------------------------------- #
    #                       Meta class
    # ---------------------------------------------------------------------- #
    class Meta:
        ordering = ['-creation_date']
        verbose_name = "Experiment"
        verbose_name_plural = "Experiments"

    # ---------------------------------------------------------------------- #
    #                       Data model
    # ---------------------------------------------------------------------- #
    def __str__(self):
        return "Experiment({}, {}, {})".format(
            str(self.accession),
            str(self.owners.all()),
            str(self.creation_date))

    # ---------------------------------------------------------------------- #
    #                       Properties
    # ---------------------------------------------------------------------- #
    @property
    def active_owners(self):
        return self.owners.filter(is_active=True)
 
    @property
    def inactive_owners(self):
        return self.owners.filter(is_active=False)

    @property
    def all_owners(self):
        return self.owners.all()

    # ---------------------------------------------------------------------- #
    #                       Methods
    # ---------------------------------------------------------------------- #
    def assign_to_default_experiment_set(self):
        """
        If the current instance is not already assigned to an experiment set,
        then create and assign a new empty experiment set for this instance.
        """
        if self.experiment_set is None:
            exp_set = ExperimentSet(accession=ExperimentSet.next_accession())
            exp_set.save()
            exp_set.owners = list(self.all_owners)
            exp_set.save()
            self.experiment_set = exp_set
            self.save()
            return True
        return False
