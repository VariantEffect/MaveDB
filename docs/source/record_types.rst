Record types
============================

MaveDB has three kinds of records: experiment set, experiment, and score set.
These records are organized hierarchically.
Each experiment set can contain multiple experiments and each experiment can contain multiple score sets.
MaveDB also supports meta-analysis score sets, which are based on one or more existing score sets.
Each of these record types are described in more detail below.

.. figure:: images/brca1_mavedb_cartoon.svg
   :name: experiment-set-cartoon
   :alt: cartoon schematic of an experiment set with multiple experiments and score sets in MaveDB
   :align: left

   Schematic of an experiment set.

   This cartoon shows the experiment set for
   `urn:mavedb:00000003 <https://www.mavedb.org/experimentset/urn:mavedb:00000003/>`_,
   which describes two distinct assays performed on a single *BRCA1* variant library,
   each with two associated score sets.
   This nested structure is typical of a MaveDB record describing a complex study with multiple elements.
   Note that each assay (symbolized by the yeast and bacteriophage and their associated sequencing instruments)
   is described in its own experiment record,
   and that each experiment has its own score set records that describe the analysis and results
   (symbolized by the computer and data table).

Experiment sets
###################################

Experiment sets do not have their own data or metadata and are used to group related experiments,
such as when different functional assays are performed on the same target and described in the same publication
(`example experiment set <https://www.mavedb.org/experimentset/urn:mavedb:00000003/>`_).

In general, an experiment set should contain data for a single target.
It is not necessary to include all data from a single publication or research project under one experiment set.

Experiment sets are automatically created when the first associated experiment is saved.

Experiments
###################################

Experiments describe the data generated from performing a MAVE on a target.
This includes all steps of the experimental procedure up to and including high-throughput sequencing.
Library construction, assay design, and sequencing strategy are all described in the experiment
(`example experiment <https://www.mavedb.org/experiment/urn:mavedb:00000003-a/>`_).

.. seealso::
   Data analysis steps including read filtering, read counting, and score calculation are described in a
   :ref:`score set<Score sets>`.

Publications that perform more than one functional assay should be represented as multiple experiments organized under
a single experiment set, and each functional assay should be described in its own experiment record.
This still applies to experimental designs where the differences between assays were relatively minor,
such as varying the temperature or the concentration of a small molecule.

To assign a new experiment to an existing experiment set, use the dropdown at the top of the experiment form.

Replicate assays should not be reported as separate experiments,
instead the number and nature of the replicates should be clearly stated in the experiment's methods section.

Score sets
###################################

Score sets are records that describe the scores generated from the raw data described in their associated experiment.
This includes all steps following the high-throughput sequencing step, including read filtering, read counting, and
score calculations (`example score set <https://www.mavedb.org/scoreset/urn:mavedb:00000003-a-1/>`_).

Multiple score sets should be used when distinct methods were used to calculate scores for raw data described by the
experiment.
The most common use case for multiple score sets is when scores are calculated at nucleotide resolution and amino
acid resolution for deep mutational scanning data.

To assign a new score set to an existing experiment, use the dropdown at the top of the score set form.

When uploading results based on imputation or complex normalization,
it's recommended to upload a more raw form of the scores (e.g. enrichment ratios) as a normal score set,
and then use :ref:`meta-analysis score sets<Meta-analysis score sets>` to describe the imputed or normalized results.

Meta-analysis score sets
-----------------------------------

Meta-analysis score sets have all the same attributes as a regular score set,
but they are linked to existing score sets rather than an existing experiment
(`example meta-analysis score set <https://www.mavedb.org/scoreset/urn:mavedb:00000055-0-1/>`_).
