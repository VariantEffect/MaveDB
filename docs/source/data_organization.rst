Data organization
============================

MaveDB has three kinds of records: experiment set, experiment, and score set.
These records are organized hierarchically.
Each experiment set can contain multiple experiments and each experiment can contain multiple score sets.
MaveDB also supports meta-analysis score sets, which are based on one or more existing score sets.
Each of these record types are described in more detail below.

.. graphviz::
   :caption: MaveDB record organization.

   digraph foo {
      "bar" -> "baz";
   }

TODO: Figure (with caption) showing hierarchy of records in .svg format

Each assay condition should be reported as its own experiment with its own score sets.
Multiple experiments should be organized under a single experiment set include when multiple assays were performed on a
single target, particularly when presented as part of a single publication.
This still applies to experimental designs where the differences between assays were relatively minor,
such as varying the temperature or the concentration of a small molecule.

In general, an experiment set should contain data for a single target.
It is not necessary to include all data from a single publication or research project under one experiment set.

Replicate assays should not be reported as separate experiments,
instead the number and nature of replicates should be clearly stated in the experiment's methods section.
The approach used to combine replicates when calculating variant scores should be clearly stated in the score set's
methods section.

Multiple score sets should be used when distinct methods were used to calculate scores for raw data described by the
experiment.
The most common use case for multiple score sets is when scores are calculated at nucleotide resolution and amino
acid resolution for deep mutational scanning data.

When uploading results based on imputation or complex normalization,
it's recommended to upload a more raw form of the scores (e.g. enrichment ratios) as a score set,
and then use meta-analysis score sets to describe the imputed or normalized results.

Experiment sets
############################

Experiment sets do not have their own data or metadata and are used to group related experiments,
such as when different functional assays are performed on the same target and described in the same publication
(`example experiment set <https://www.mavedb.org/experimentset/urn:mavedb:00000003/>`_).

Experiment sets are automatically created when the first associated experiment is saved.

Experiments
###################################

Experiments describe the data generated from performing a MAVE on a target.
This includes all steps of the experimental procedure up to and including high-throughput sequencing.
Library construction, assay design, and sequencing strategy are all described in the experiment
(`example experiment <https://www.mavedb.org/experiment/urn:mavedb:00000003-a/>`_).

.. note::
   Data analysis steps including read filtering, read counting, and score calculation are described in a
   :ref:`score set<Score sets>`.

Publications that perform more than one functional assay should be represented as multiple experiments organized under
a single experiment set, and each functional assay should be described in its own experiment record.
Biological or technical replicates should be described in the same experiment.

Experiments have several fields for descriptive, free-text metadata, as well as additional structured metadata fields.
Each experiment and score set in MaveDB should have a title, short description, abstract, and methods.
The title and short description are required, and the abstract and methods are strongly recommended.

The title is displayed at the top of the experiment page, and should be quite brief.

The short description is displayed in the search results table and should summarize the entry at a high level in one
or two sentences.

The abstract should describe the motivation and approach for the dataset.
Some MaveDB abstracts include a summary of the results of the related publications but many do not.
The entry describes the MAVE data rather than a full study so the submitter should use their judgement when deciding
what details are most relevant.
It is common that experiments and score sets share the same abstract text if they are from the same study.

The methods section should describe the approach in a condensed form,
suitable for a specialist audience of MAVE researchers.
For an experiment the methods section should include:

* Variant library construction methods
* Description of the functional assay, including model system and selection type
* Sequencing strategy and sequencing technology

Experiments can be tagged with optional, user-specified keywords.
In a future release, the keyword vocabulary will become restricted and keyword selection will be mandatory.
This will improve the ability for data modellers to select appropriate MAVE datasets for their studies,
and also facilitate more sophisticated tracking of the kind of data being generated by the field.

Publications can be included by entering their `PubMed ID <https://pubmed.ncbi.nlm.nih.gov/>`_
and they will appear as formatted references.
Publications included in an experiment will also be displayed on their associated score set pages.

Preprints or publications that are not indexed by PubMed can be included via the DOI field.
Improved support for preprints (including displaying them as formatted references) is planned for a future release.

Accession numbers for raw sequencing data in an external resource can be provided as part of the experiment metadata.
MaveDB currently supports accession numbers for:

* `ArrayExpress <https://www.ebi.ac.uk/arrayexpress/>`_
* `BioProject <https://www.ncbi.nlm.nih.gov/bioproject/>`_
* `Gene Expression Omnibus <https://www.ncbi.nlm.nih.gov/geo/>`_
* `Sequence Read Archive <https://www.ncbi.nlm.nih.gov/sra>`_

Raw data that is stored elsewhere can be included via the DOI field.
To request support for additional accession formats, please use the `MaveDB issue tracker`_.

Note that experiments do not have variant scores themselves.
Instead, each experiment has one or more linked score sets.

Score sets
###################################

Score sets are records that describe the scores generated from the raw data described in their associated experiment.
This includes all steps following the high-throughput sequencing step, including read filtering, read counting, and
score calculations (`example score set <https://www.mavedb.org/scoreset/urn:mavedb:00000003-a-1/>`_).

Like experiments, score sets have several fields for descriptive, free-text metadata,
as well as additional structured metadata fields.
Each experiment and score set in MaveDB should have a title, short description, abstract, and methods.
The title and short description are required, and the abstract and methods are strongly recommended.

The title is displayed at the top of the score set page, and should be quite brief.

The short description is displayed in the search results table and should summarize the entry at a high level.

The abstract should describe the motivation and approach for the dataset.
Some MaveDB abstracts include a summary of the results of the related publications but many do not.
The entry describes the MAVE data rather than a full study so the submitter should use their judgement when deciding
what details are most relevant.
It is common that experiments and score sets share the same abstract text if they are from the same study.

The methods section should describe the approach in a condensed form, suitable for a specialist audience of MAVE
researchers.
For a score set the methods section should include:

* Sequence read filtering approach
* Description of the statistical model for converting counts to scores, including normalization
* Description of additional data columns included in the score or count tables, including column naming conventions
* Details of how replicates were combined (if applicable)

Score sets can be tagged with optional, user-specified keywords.
In a future release, the keyword vocabulary will become restricted and keyword selection will be mandatory.
This will improve the ability for data modellers to select appropriate MAVE datasets for their studies,
and also facilitate more sophisticated tracking of the kind of data being generated by the field.

Publications can be included by entering their `PubMed ID <https://pubmed.ncbi.nlm.nih.gov/>`_ and they will appear
as formatted references.
Publications included in an experiment will also be displayed on their associated score set pages.

Preprints or publications that are not indexed by PubMed can be included via the DOI field.
Improved support for preprints (including displaying them as formatted references) is planned for a future release.

Score set data are covered by a license specified by the uploader,
and can also include an optional free-text data usage policy intended for unpublished data.
For more information and a description of each licensing option, see :ref:`data licensing<Data licensing>`.

Meta-analysis score sets
-----------------------------------
Meta-analysis score sets have all the same attributes as a regular score set,
but they are linked to existing score sets rather than an existing experiment.

The methods should describe the process that was used to convert the linked scores or counts into the scores presented
in the meta-analysis score set record.

Score set targets
-----------------------------------

TODO: add information about the target, including offset terms and sequence.

Score set data table format
--------------------------------------

TODO: describe columns for score set data.
TODO: describe the format requirements, including linking to MAVE-HGVS
TODO: describe required columns (hgvs_* and score)
TODO: describe JSON-format "bonus metadata"
