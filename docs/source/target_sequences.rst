Target sequence information
===========================================

All variants in a MaveDB :ref:`score set<Score sets>` are described relative to a target sequence.
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
   When entering target information for a new score set, users will have the option to use an existing target.
   Typically users will only want to use an existing target that they created themselves,
   as even targets with the same name may specify a different part of the gene or alternative sequence.

Targets can also be linked to accession numbers in other databases, including `UniProt <https://www.uniprot.org/>`_,
`RefSeq <https://www.ncbi.nlm.nih.gov/refseq/>`_, and `Ensembl <https://www.ensembl.org/>`_.
If the target sequence provided to MaveDB starts partway through the linked sequence
(such as an assay targeting a single functional domain), the target should have an "offset" term.
The offset is the integer value that should be added to the MaveDB coordinates
(which are relative to the target sequence) in order to match the coordinates in the linked sequence.

For example, the target sequence for `urn:mavedb:00000002-a-1 <https://mavedb.org/scoreset/urn:mavedb:00000002-a-1/>`_
is a codon optimized version of the WW domain of YAP1.
This corresponds to UniProt identifier `P46937 <https://www.uniprot.org/uniprot/P46937>`_ with offset 169,
meaning that position 1 in the MaveDB score set is position 170 in the UniProt sequence.
