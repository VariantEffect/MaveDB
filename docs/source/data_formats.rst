Data table formats
============================

MaveDB accepts and provides data tables in CSV format.
Each row of the data table describes a single variant, and variants are described using `MAVE-HGVS`_ format.
All other columns are expected to be floating point values.

For both score and count data tables, there are three variant columns:

* ``hgvs_nt`` describes variants with respect to the nucleotide target sequence
* ``hgvs_tx`` describes variants with respect to a transcript model
* ``hgvs_pro`` describes variants with respect to the amino acid target sequence

``hgvs_nt`` and ``hgvs_pro`` variants are required to be described in relation to the score set target sequence,
rather than to an external reference sequence.

If ``hgvs_nt`` is present, it will be used as the primary key for distinguishing variants and must be unique.
Otherwise, ``hgvs_pro`` will be used as the primary key.

.. note::
   Datasets with only ``hgvs_pro`` variants can specify nucleotide target sequences.
   In this case, the target sequence will be translated using the
   `standard amino acid translation table
   <https://www.ncbi.nlm.nih.gov/Taxonomy/Utils/wprintgc.cgi?chapter=cgencodes#SG1>`_ for validation.

The ``hgvs_tx`` variants are not validated against a transcript model or target sequence.
This is a convenience feature for datasets that contain splice variants; most datasets will not use ``hgvs_tx``.
Datasets that use ``hgvs_tx`` must also have ``hgvs_nt``, which is used as the primary key,
and the ``hgvs_nt`` variants must use the ``'g.'`` prefix.

Example data table excerpts
##################################
TODO: add an example data table excerpt for scores, counts using csv-table


TODO: description of variants with respect to target sequence

TODO: description of required columns and recommended columns

TODO: description of information in header of downloaded files
