Depositing your data into MaveDB
=======================================

Understanding experiments and score sets
-------------------------------------------

MaveDB datasets are organized into experiment sets, experiments, and score sets.

Experiment sets
###################################

Experiment sets do not have their own metadata and are used to group related
experiments, such as when different functional assays are performed on the
same target and typically described in the same publication
(`example <https://www.mavedb.org/experimentset/urn:mavedb:00000003/>`_).
New experiment sets are automatically created when their first experiment is
saved.

Experiments
###################################

Experiments are records that describe the data generated from performing a MAVE
on a target. The descriptions and other metadata in an experiment describe the
experimental procedure, including library construction, assay design, and
sequencing strategy. Links to the raw data in an external resource such as the
`Sequence Read Archive <https://www.ncbi.nlm.nih.gov/sra>`_ can be provided.
Importantly, experiments do not have scores directly. Instead, each experiment
can have one or more linked score sets.

Score sets
###################################

Score sets are records that describe the process of calculating scores from raw
data (sequencing data) and contain the variant scores and (optionally) counts.
Importantly, score sets contain the target information that describes the sequence
used in the experiment.

Meta-analysis score sets
###################################

Meta-analysis score sets are a new feature in MaveDB version 1.8.0. While a normal score
set is based on data from a single experiment, a meta-analysis score set is instead based
on multiple existing score sets. These score sets can be from one or more experiments
or experiment sets.

Like a regular score set, a meta-analysis score set reports scores for a single target.
The primary use case for meta-analysis score sets is combining the results from two different
MAVEs on the same target (example TBA - *NUDT15*? *VKOR*?). This allows the uploader to
combine multiple score sets across existing experiments or experiment sets.

Another use case for meta-analysis score sets reporting scores that have been substantially
altered by imputation or score recalibration. In this case, the meta-analysis score set
would be based on a single existing score set and be part of that experiment.

Required information checklist
--------------------------------------

## TODO: many of these items should have links

For each experiment and score set:

* Short description (1-3 brief sentences)
* Title
* Abstract
* Methods
* Keywords
* ORCID iDs for other people you want to add as contributors
* PubMed IDs for the study reference(s) or DOIs for references not listed in PubMed (such as on bioRxiv)

For each experiment you will also want:

* SRA accessions or DOIs for raw sequence data (if available)

For each score set you will also want:

* Target information
    * Nucleotide sequence for the target region
    * Type (coding, non-coding)
    * Organism the sequence is derived from (if applicable)
    * Sequence reference genome and assembly version (if applicable)
    * UniProt ID (if applicable)
    * RefSeq ID (if applicable)
    * Ensembl ID (if applicable)
* DOIs for additional data specific to the score set (and not the experiment)
* Variant score table
* Variant count table (if available)
* Choice of data license
* Data usage policy text (if needed)

Descriptive information
###################################

Each experiment and score set in MaveDB should have a short description, title, abstract,
and methods section. The title and short descriptions are required for submission, and
the abstract and methods are strongly recommended.

The short description will be displayed in the search table and should summarize the
experimental design at a high level.

The title is typically an abbreviated version of the short description, and is displayed
at the top of the experiment or score set page.

The abstract should describe the motivation and approach for the dataset at a high level.
Some MaveDB abstracts include a summary of the results of the related publications but
many do not. The entry describes the MAVE data rather than a full study so the submitter
should use their judgement when deciding what details to include. When a dataset is first
uploaded, the experiment and score set typically have the same abstract.

The methods section should describe the approach in a condensed form, suitable for a
specialist audience of MAVE researchers. Because

For an experiment the methods section should include:

* Variant and library construction methods
* Description of the functional assay, including model and selection type
* Sequencing strategy

For a score set the methods section should include:

* High-level description of the statistical model for converting counts to scores
* Read filtering used
* Normalization used, including any cutoffs applied
* Description of any additional data columns included in the score or count table, including column naming conventions

Additional metadata fields
###################################

* Publications by PMID
* bioRxiv by DOI as external identifier (improvements TBA)
* JSON-format "bonus metadata" (score set only)
* User-specified keywords
* SRA, etc. raw data accessions (experiment only)
* Data usage policy (score set only)
* ???

Score set targets
###################################

.. note::
    When entering target information for a new score set, you will have the
    option to use an existing target. Before using an existing target, make
    sure that the full-length nucleotide sequence is the same as for your
    dataset! Typically you will only want to use an existing target that you
    created yourself.

Data license
###################################

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

