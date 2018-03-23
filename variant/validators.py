import re

#: Matches a single amino acid substitution in HGVS_ format.
RE_PROTEIN = re.compile(
    "(?P<match>p\.(?P<pre>[A-Z][a-z][a-z])(?P<pos>-?\d+)"
    "(?P<post>[A-Z][a-z][a-z]))")
#: Matches a single nucleotide substitution (coding or noncoding)
#: in HGVS_ format.
RE_NUCLEOTIDE = re.compile(
    "(?P<match>[nc]\.(?P<pos>-?\d+)(?P<pre>[ACGT])>(?P<post>[ACGT]))")
#: Matches a single coding nucleotide substitution in HGVS_ format.
RE_CODING = re.compile(
    "(?P<match>c\.(?P<pos>-?\d+)(?P<pre>[ACGT])>(?P<post>[ACGT]) "
    "\(p\.(?:=|[A-Z][a-z][a-z]-?\d+[A-Z][a-z][a-z])\))")
#: Matches a single noncoding nucleotide substitution in HGVS_ format.
RE_NONCODING = re.compile(
    "(?P<match>n\.(?P<pos>-?\d+)(?P<pre>[ACGT])>(?P<post>[ACGT]))")


def validate_hgvs_string(value):
    return
    # variants = [v.strip() for v in string.strip().split(',')]
    #
    # protein_matches = all([RE_PROTEIN.match(v) for v in variants])
    # nucleotide_matches = all([re_nucleotide.match(v) for v in variants])
    # coding_matches = all([re_coding.match(v) for v in variants])
    # noncoding_matches = all([re_noncoding.match(v) for v in variants])
    # wt_or_sy = all([v in ["_wt", "_sy"] for v in variants])
    #
    # if not (protein_matches or nucleotide_matches or
    #         coding_matches or noncoding_matches or wt_or_sy):
    #     raise ValidationError(
    #         ugettext("Variant '%(variant)s' is not a valid HGVS string."),
    #         params={'variant': string}
    #     )