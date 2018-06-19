from django.test import TestCase
from django.core.exceptions import ValidationError

from ..hgvs.protein import (
    validate_substitution,
    validate_deletion,
    validate_delins,
    validate_insertion,
    validate_frame_shift,
    single_variant_re,
    multi_variant_re,
)


class TestVariantRegexPatterns(TestCase):
    def test_single_var_re_matches_each_variant_type(self):
        self.assertIsNotNone(single_variant_re.fullmatch('p.Trp24Cys^Gly'))
        self.assertIsNotNone(single_variant_re.fullmatch('p.(Trp24Cys)'))
        self.assertIsNotNone(single_variant_re.fullmatch('p.Lys23_Val25del'))
        self.assertIsNotNone(single_variant_re.fullmatch('p.(Lys23_Val25del)'))
        self.assertIsNotNone(single_variant_re.fullmatch('p.His4_Gln5insAla'))
        self.assertIsNotNone(single_variant_re.fullmatch('p.(His4_Gln5insAla)'))
        self.assertIsNotNone(single_variant_re.fullmatch('p.Cys28delinsVal'))
        self.assertIsNotNone(single_variant_re.fullmatch('p.(Cys28delinsVal)'))
        self.assertIsNotNone(single_variant_re.fullmatch('p.Cys28fs'))
        self.assertIsNotNone(single_variant_re.fullmatch('p.(Cys28fs)'))
        
    def test_multi_var_re_matches_multi_variants(self):
        self.assertIsNotNone(
            multi_variant_re.fullmatch(
                'p.[Trp24Cys;Lys23_Val25del;His4_Gln5insAla;'
                'Cys28fs;Cys28delinsVal]'
            ))
        # Non-multi should be none
        self.assertIsNone(multi_variant_re.fullmatch('p.[Trp24Cys;]'))
        self.assertIsNone(multi_variant_re.fullmatch('p.[(Trp24Cys)]'))
        self.assertIsNone(multi_variant_re.fullmatch('p.[Trp24Cys,]'))
        self.assertIsNone(multi_variant_re.fullmatch('p.[Trp24Cys]'))


class TestEventValidators(TestCase):
    def test_valid_substitutions_pass(self):
        validate_substitution('Trp24Cys')
        validate_substitution('Cys188=')
        validate_substitution('Trp24*')
        validate_substitution('Trp24Ter')
        validate_substitution('Trp24Ter^Ala^G')
        validate_substitution('Trp24?')
        validate_substitution('Trp24=/Cys')
        validate_substitution('p.Trp24=/Cys')
        validate_substitution('p.(Trp24=/Cys)')
        validate_substitution('0')
        validate_substitution('?')
        validate_substitution('p.=')
    
    def test_validation_error_ref_same_as_new(self):
        with self.assertRaises(ValidationError):
            validate_substitution('Val5Val')
    
    def test_error_invalid_substitutions(self):
        with self.assertRaises(ValidationError):
            validate_substitution("")
        with self.assertRaises(ValidationError):
            validate_substitution("a>g")
        with self.assertRaises(ValidationError):
            validate_substitution('*a>g')
        with self.assertRaises(ValidationError):
            validate_substitution('1a>a')
        with self.assertRaises(ValidationError):
            validate_substitution('12a=g')
        with self.assertRaises(ValidationError):
            validate_substitution('12a>E')
        with self.assertRaises(ValidationError):
            validate_substitution('12a<E')
        with self.assertRaises(ValidationError):
            validate_substitution('12-1>a')
        with self.assertRaises(ValidationError):
            validate_substitution('+12a>g')
    
    def test_valid_deletions_pass(self):
        validate_deletion('Val7del')
        validate_deletion('Lys23_Val25del')
        validate_deletion('Trp4del')
        validate_deletion('Gly2_Met46del')
        validate_deletion('Val7=/del')
        validate_deletion('p.Val7=/del')
        validate_deletion('p.(Val7=/del)')
    
    def test_error_invalid_deletions(self):
        with self.assertRaises(ValidationError):
            validate_deletion('19delR')
        with self.assertRaises(ValidationError):
            validate_deletion('')
        with self.assertRaises(ValidationError):
            validate_deletion('dela')
        with self.assertRaises(ValidationError):
            validate_deletion('4071+1_4072-1_5154+1_5155-1del')
        with self.assertRaises(ValidationError):
            validate_deletion('(?_-1)_(+1_?)del')
        with self.assertRaises(ValidationError):
            validate_deletion('1704+1delaaa')
        with self.assertRaises(ValidationError):
            validate_deletion('19_21del(5)')
        with self.assertRaises(ValidationError):
            validate_deletion('19_21deluuu')
    
    def test_valid_insertions_pass(self):
        validate_insertion('His4_Gln5insAla')
        validate_insertion('His4_Gln5insAla^Gly^Ser')
        validate_insertion('Lys2_Gly3insGlnSerLys')
        validate_insertion('Met3_His4insGlyTer')
        validate_insertion('Arg78_Gly79ins23')
        validate_insertion('Ser332_Ser333ins(1)')
        validate_insertion('Val582_Asn583ins(5)')
        validate_insertion('Val582_Asn583insX')
        validate_insertion('Val582_Asn583insXXXXX')
        validate_insertion('p.Val582_Asn583ins(5)')
        validate_insertion('p.(Val582_Asn583ins(5))')

    
    def test_error_invalid_insertions(self):
        with self.assertRaises(ValidationError):
            validate_insertion('Val582insXXXXX')
        with self.assertRaises(ValidationError):
            validate_insertion('')
        with self.assertRaises(ValidationError):
            validate_insertion('ins')
        with self.assertRaises(ValidationError):
            validate_insertion('(Val582_Asn583)insXXXXX')
        with self.assertRaises(ValidationError):
            validate_insertion('Val582_Asn583ins')
        with self.assertRaises(ValidationError):
            validate_insertion('Val582+1_Asn583insXXXXX')
    
    def test_valid_delins_passes(self):
        validate_delins('Cys28delinsTrpVal')
        validate_delins('C28_L29delinsT')
        validate_delins('C28_L29delins*')
        validate_delins('Cys28delinsTrpVal')
        validate_delins('Glu125_Ala132delinsGlyLeuHisArgPheIleValLeu')
        validate_delins('C28_L29delinsT^G^L')
        validate_delins('p.C28_L29delinsT^G^L')
        validate_delins('p.(C28_L29delinsT^G^L)')

    def test_error_invalid_delins(self):
        with self.assertRaises(ValidationError):
            validate_delins('Cys28delinsZ')
        with self.assertRaises(ValidationError):
            validate_delins('')
        with self.assertRaises(ValidationError):
            validate_delins('(Cys28_Cys)delinsTrpVal')
        with self.assertRaises(ValidationError):
            validate_delins('C28_L29delinsTG^G^L')
        with self.assertRaises(ValidationError):
            validate_delins('Cys28+5delinsZ')
        with self.assertRaises(ValidationError):
            validate_delins('*?_45+1delinsg')
    
    def test_valid_frameshift_passes(self):
        validate_frame_shift('Arg97ProfsTer23')
        validate_frame_shift('Glu5ValfsTer5')
        validate_frame_shift('Ile327Argfs*?')
        validate_frame_shift('Ile327fs')
        validate_frame_shift('Gln151Thrfs*9')
        validate_frame_shift('p.Ile327fs')
        validate_frame_shift('p.(Ile327fs)')

    def test_error_invalid_frameshift(self):
        with self.assertRaises(ValidationError):
            validate_frame_shift('Arg97ProfsTer23Pro')
        with self.assertRaises(ValidationError):
            validate_frame_shift('')
        with self.assertRaises(ValidationError):
            validate_frame_shift('fsTer')
        with self.assertRaises(ValidationError):
            validate_frame_shift('Glu5_Val7fsTer5')
        with self.assertRaises(ValidationError):
            validate_frame_shift('Ile327Argfs*?Ter')
        with self.assertRaises(ValidationError):
            validate_frame_shift('Ile327fs(4)')
        with self.assertRaises(ValidationError):
            validate_frame_shift('*?_45+1delinsc')

