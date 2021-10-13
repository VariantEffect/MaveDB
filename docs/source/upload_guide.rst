Depositing your data into MaveDB
=======================================

Creating a complete entry in MaveDB requires several pieces of data and metadata.
This document includes a high-level description of MaveDB's organizational model,
descriptions of the data and metadata included in MaveDB,
and checklist of what is required to deposit a study.

Record types
###################################

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

Experiment sets
-----------------------------------

Experiment sets do not have their own data or metadata and are used to group related experiments,
such as when different functional assays are performed on the same target and described in the same publication
(`example experiment set <https://www.mavedb.org/experimentset/urn:mavedb:00000003/>`_).

In general, an experiment set should contain data for a single target.
It is not necessary to include all data from a single publication or research project under one experiment set.

Experiment sets are automatically created when the first associated experiment is saved.

Experiments
-----------------------------------

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
-----------------------------------

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
+++++++++++++++++++++++++++++++++++
Meta-analysis score sets have all the same attributes as a regular score set,
but they are linked to existing score sets rather than an existing experiment
(`example meta-analysis score set <https://www.mavedb.org/scoreset/urn:mavedb:00000055-0-1/>`_).

Metadata formatting
###################################

Experiment and score set records contain several different types of required and optional metadata,
either free text or accession numbers for other databases.
These elements are described in this section.

Free text metadata
-----------------------------------

Experiments and score sets both have descriptive free text fields.
These are the title, short description, abstract, and methods.

The title and short description are plain text.
The abstract and methods support `Markdown <https://daringfireball.net/projects/markdown/>`_
formatting with embedded equations using `MathML <https://www.w3.org/Math/>`_,
converted using `Pandoc <https://pandoc.org/>`_.

The title is displayed at the top of the record page, and should be quite brief.

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
* Structure of biological or technical replicates (if applicable)

For a score set the methods section should include:

* Sequence read filtering approach
* Description of the statistical model for converting counts to scores, including normalization
* Description of additional data columns included in the score or count tables, including column naming conventions
* Details of how replicates were combined (if applicable)

For a meta-analysis score set the methods section should include:

* Description of the statistical model for converting the linked scores or counts into the scores presented
* Description of additional data columns included in the score or count tables, including column naming conventions

Score sets can also include an optional free-text data usage policy intended for unpublished data.
For example, data producers may wish to assert their right to publish the results of certain analyses first.

Publication details
-----------------------------------

Publications can be included by entering their `PubMed ID <https://pubmed.ncbi.nlm.nih.gov/>`_ and they will appear
as formatted references.
Publications included in an experiment will also be displayed on their associated score set pages.

Preprints or publications that are not indexed by PubMed can be included via the DOI field.
Improved support for preprints (including displaying them as formatted references) is planned for a future release.

Raw data accessions
-----------------------------------

Experimenters are encouraged to deposit their raw sequence data in a public repository and link it to the relevant
experiment record(s).

MaveDB currently supports accession numbers for:

* `ArrayExpress <https://www.ebi.ac.uk/arrayexpress/>`_
* `BioProject <https://www.ncbi.nlm.nih.gov/bioproject/>`_
* `Gene Expression Omnibus <https://www.ncbi.nlm.nih.gov/geo/>`_
* `Sequence Read Archive <https://www.ncbi.nlm.nih.gov/sra>`_

Raw data that is stored elsewhere can be included via the DOI field.

Keywords
-----------------------------------

Experiments and score sets can be tagged with optional, user-specified keywords.
In a future release, the keyword vocabulary will become restricted and keyword selection will be mandatory.
This will improve the ability for data modellers to select appropriate MAVE datasets for their studies,
and also facilitate more sophisticated tracking of the kind of data being generated by researchers.

Data formatting
###################################

Score sets require detailed information about the target sequence, including the sequence,
as well as a CSV-formatted file containing the variant scores
(and optionally a second CSV-formatted file containing the variant counts).
These elements are described in this section.

Target information
-----------------------------------

All variants in a score set are described relative to a target sequence.
This target sequence should be the sequence that was mutagenized to create the variant library.

For datasets that target a single functional domain, only that part of the gene should be included as the target.
If multiple discontinuous functional domains were included in a single experiment,
the target sequence should be given with the intervening sequence so that coordinates can be mapped back to a
full-length reference.

While some target sequences match those that appear in sequence databases, others have important differences.
Examples include codon optimized sequences or non-reference backgrounds.
Other sequences may not appear in any database, such as synthetic or designed proteins.

When uploading a dataset to MaveDB, it is required that the uploader provide the target sequence.
If the target is protein coding and variants are only described by their protein changes,
the target sequence can be an amino acid sequence.
If variants describing nucleotide changes are present, the target sequence must be a DNA sequence.

.. note::
   When entering target information for a new score set, you will have the option to use an existing target.
   Before using an existing target, make sure that the sequence is the same as for your dataset!
   Typically you will only want to use an existing target that you created yourself.

Targets can also be linked to accession numbers in other databases, including `UniProt <https://www.uniprot.org/>`_,
`RefSeq <https://www.ncbi.nlm.nih.gov/refseq/>`_, and `Ensembl <https://www.ensembl.org/>`_.
If the target sequence provided to MaveDB starts partway through the linked sequence
(such as an assay targeting a single functional domain), uploaders can provide an "offset" term.
The offset is the integer value that should be added to the MaveDB coordinates
(which are relative to the target sequence) in order to match the coordinates in the linked sequence.

For example, the target sequence for `urn:mavedb:00000002-a-1 <https://mavedb.org/scoreset/urn:mavedb:00000002-a-1/>`_
is a codon optimized version of the WW domain of YAP1.
This corresponds to UniProt identifier `P46937 <https://www.uniprot.org/uniprot/P46937>`_ with offset 169,
meaning that position 1 in the MaveDB score set is position 170 in the UniProt sequence.

Score and count tables
-----------------------------------

TODO: include link to data licensing page

TODO: describe columns for score set data.

TODO: describe the format requirements, including linking to MAVE-HGVS

TODO: describe required columns (hgvs_* and score)

Optional structured metadata
-----------------------------------

Score sets also support the inclusion of optional `JSON <https://www.json.org/>`_-formatted metadata.
This can be used to describe features like genomic coordinates for a target sequence or score cutoff ranges that the
uploader would like to be more easily machine-readable than if this information was included in free text.

If optional metadata is included, the uploader should describe it in the score set methods.

Required information checklist
###################################

TODO: many of these items should have links

For each experiment and score set:

* `Free text metadata`_
    * Title
    * Short description (1-3 brief sentences)
    * Abstract
    * Methods
* Keywords
* ORCID iDs for other people you want to add as :ref:`contributors<Contributor roles>`.
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
