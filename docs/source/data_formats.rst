Data table formats
============================

MaveDB accepts and provides data tables in CSV format.
Each row of the data table describes a single variant, and variants are described using `MAVE-HGVS`_ format.
All other columns are expected to be floating point values.

Variant columns
############################

For both score and count data tables, there are three variant columns:

* ``hgvs_nt`` describes variants with respect to the nucleotide :ref:`target sequence<Target sequence information>`
* ``hgvs_tx`` describes variants with respect to a transcript model
* ``hgvs_pro`` describes variants with respect to the amino acid :ref:`target sequence<Target sequence information>`

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

Score table columns
############################

All score tables must have a column named ``score`` that describes the score of that variant in the assay.
Score tables may have any number of additional numeric columns.

Suggested numeric columns include a standard deviation or variance,
or some other measure of uncertainty for the score such as a 95% confidence interval
(represented as two columns, e.g. ``ci_lower`` and ``ci_upper``).

Score sets that describe experiments with multiple replicates often include the score and standard deviation for each
replicate as additional columns.

For datasets with categorical data,
we recommend encoding the categories as integers and describing the mapping between integers and categories in the
:ref:`free text methods<Free text metadata>`.
Support for additional data columns with string data will be added in a future version to support this use case.

Score table examples
----------------------------------

Here is a short excerpt from the score table for
`urn:mavedb:00000003-a-1 <https://mavedb.org/scoreset/urn:mavedb:00000003-a-1/>`_.

That this dataset uses ``hgvs_nt`` as the primary variant key.
It has several additional data columns with the scores and error estimates for multiple biological replicates.

Note that some variants do not have a score.
This is permitted (and encouraged) as long as there is some data provided for that variant,
such as a score in an individual replicate or some counts.

.. csv-table:: Example Score Data
   :header: hgvs_nt,hgvs_splice,hgvs_pro,score,SE,epsilon,SE_PlusE2NewRep3,score_PlusE2NewRep3,SE_PlusE2NewRep4,score_PlusE2NewRep4,SE_PlusE2NewRep5,score_PlusE2NewRep5,SE_PlusE2Rep3,score_PlusE2Rep3,SE_PlusE2Rep4,score_PlusE2Rep4,SE_PlusE2Rep5,score_PlusE2Rep5

   c.38T>C,NA,p.Val13Ala,-0.128,0.115,0.000,0.148,0.283,0.162,-0.456,0.075,-0.186,0.167,-0.165,0.289,-0.073,0.388,-0.184
   c.186A>T,NA,p.Leu62Phe,-4.132,0.396,0.000,0.289,-3.752,0.433,-4.166,0.549,-3.456,0.341,-3.166,0.499,-6.079,0.204,-4.309
   c.164A>T,NA,p.Lys55Ile,-0.655,0.112,0.000,0.100,-0.592,0.121,-0.929,0.086,-0.254,0.143,-0.695,0.039,-0.950,0.080,-0.514
   c.[439C>A;441G>A;842C>A],NA,p.[Gln147Lys;Ser281Ter],NA,NA,NA,0.668,-1.612,NA,NA,NA,NA,NA,NA,NA,NA,0.464,-1.273
   c.22_23delinsCC],NA,p.Glu8Pro,-0.375,0.280,0.000,0.158,-1.421,0.240,-0.265,0.200,-0.796,0.192,-0.022,0.311,-0.232,0.091,0.476
   c.598G>A,NA,p.Asp200Asn,0.271,0.170,0.000,0.103,-0.337,0.094,0.830,0.092,0.408,0.163,0.051,0.243,0.278,0.172,0.382
   c.285C>G,NA,p.Asp95Glu,NA,NA,NA,0.401,-3.993,0.150,-3.380,NA,NA,0.452,-3.221,0.228,-1.973,0.277,-1.774
   c.[64G>C;142C>T],NA,p.Glu22Gln,NA,NA,NA,NA,NA,NA,NA,NA,NA,NA,NA,NA,NA,NA,NA
   c.869T>G,NA,p.Leu290Ter,-1.231,0.245,0.000,0.117,-0.456,0.285,-0.792,0.424,-0.993,0.084,-1.909,0.143,-1.325,0.093,-1.735
   c.200T>G,NA,p.Ile67Arg,NA,NA,NA,0.255,-3.600,0.152,-3.399,NA,NA,0.171,-4.097,0.361,-3.764,NA,NA
   c.[1G>T;97_99delinsGGG],NA,p.[Asp1Tyr;Pro33Gly],NA,NA,NA,0.159,-0.177,0.445,-0.583,0.500,-0.323,0.537,-0.470,NA,NA,0.284,0.188
   c.476G>T,NA,p.Gly159Val,-1.192,0.100,0.000,0.141,-1.050,0.079,-1.557,0.030,-0.969,0.114,-1.030,0.126,-1.264,0.168,-1.303

Count table columns
##################################

Count data are optional for MaveDB score sets, but are recommended.

There are no required columns for count data,
but uploaders should decide on an intuitive naming convention for the column names and describe it in the
:ref:`free text methods<Free text metadata>`.
