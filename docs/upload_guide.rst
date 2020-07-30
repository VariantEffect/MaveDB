Depositing your data into MaveDB
=======================================

Understanding experiments and score sets
-------------------------------------------

MaveDB datasets are organized as experiment sets, experiments, and score sets.

**Experiment sets** do not have their own metadata and are used to group related
experiments, such as when different functional assays are performed on the
same target and typically described in the same publication
(`example <https://www.mavedb.org/experimentset/urn:mavedb:00000003/>`_).
New experiment sets are automatically created when their first experiment is
saved.

**Experiments** are records that describe the data generated from performing a MAVE
on a target. The descriptions and other metadata in an experiment describe the
experimental procedure, including library construction, assay design, and
sequencing strategy. Links to the raw data in an external resource such as the
`Sequence Read Archive <https://www.ncbi.nlm.nih.gov/sra>`_ can be provided.
Importantly, experiments do not have scores directly. Instead, each experiment
can have one or more linked score sets.

**Score sets** are records that describe the process of calculating scores from raw
data (sequencing data) and contain the variant scores and (optionally) counts.

Metadata score sets
###################################

Metadata score sets are a new feature in MaveDB version 1.8.0. While a normal score
set is based on data from a single experiment, a metadata score set is instead based
on multiple existing score sets. These score sets can be from one or more experiments
or experiment sets.

Like a regular score set, a metadata score set reports scores for a single target.
The primary use case for metadata score sets is combining the results from two different
MAVEs on the same target (example TBA - *NUDT15*? *VKOR*?). This allows the uploader to
combine multiple score sets across existing experiments or experiment sets.

Another use case for metadata score sets reporting scores that have been substantially
altered by imputation or score recalibration. In this case, the metadata score set
would be based on a single existing score set and be part of that experiment.

Required information checklist
--------------------------------------

Descriptive information
###################################


Additional metadata fields
###################################


Score set targets
###################################

.. note::
    When entering target information for a new score set, you will have the
    option to use an existing target. Before using an existing target, make
    sure that the full-length nucleotide sequence is the same as for your
    dataset! Typically you will only want to use an existing target that you
    created yourself.

Suggestions for writing the abstract and methods
--------------------------------------------------------

Preparing scores and counts using :code:`mavedbconvert`
--------------------------------------------------------

Starting the upload process
--------------------------------------------------------

Temporary accession numbers
###################################


Adding multiple score sets
###################################

