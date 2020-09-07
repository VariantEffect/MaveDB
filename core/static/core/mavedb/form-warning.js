$(document).ready(function () {
  $("#id_score_data").change(function () {
    parse_file('#id_score_data');
  });
  
  $("#id_count_data").change(function () {
    parse_file('#id_count_data');
  });
  
  function warn_sge_missing_metadata(results, file) {
    if (
      (has_tx_variants(results.data) || has_genomic_variants(results.data)) &&
      metadata_is_empty()
    ) {
      display_warnings();
    }
  }
  
  function has_tx_variants(data) {
    let tx_column_index = data[0].indexOf('hgvs_tx');
    if (tx_column_index < 0) return;
    
    let tx_variants = new Set()
    data.slice(1).forEach(function (row) {
      if (row[tx_column_index] != null) {
        tx_variants.add(row[tx_column_index]);
      }
    });
    
    // Check if any tx variants are supplied. If not, return since we don't need to then do a
    // further check for metadata presence.
    let has_tx_variants = Array.from(tx_variants).some(function (variant) {
      return variant.toString().startsWith('n.') || variant.toString().startsWith('c.')
    })
    
    if (tx_variants.size === 0 || !has_tx_variants) {
      console.log('There are no transcript variants.');
      return false;
    }
    return true;
  }
  
  function has_genomic_variants(data) {
    let nt_column_index = data[0].indexOf('hgvs_nt');
    if (nt_column_index < 0) return;
    
    let nt_variants = new Set()
    data.slice(1).forEach(function (row) {
      if (row[nt_column_index] != null) {
        nt_variants.add(row[nt_column_index]);
      }
    });
    
    // Check if any g. variants are supplied. If not, return since we don't need to then do a
    // further check for metadata presence.
    let has_g_variants = Array.from(nt_variants).some(function (variant) {
      return variant.toString().startsWith('g.')
    })
    
    if (nt_variants.size === 0 || !has_g_variants) {
      console.log('There are no genomic variants.');
      return false;
    }
    return true;
  }
  
  function metadata_is_empty() {
    let refseq = $("#id_refseq-offset-identifier").val();
    let uniprot = $("#id_uniprot-offset-identifier").val();
    let ensembl = $("#id_ensembl-offset-identifier").val();
    
    let refseq_blank = (refseq === "") || (refseq == null)
    let uniprot_blank = (uniprot === "") || (uniprot == null)
    let ensembl_blank = (ensembl === "") || (ensembl == null)
    
    return refseq_blank && uniprot_blank && ensembl_blank
  }
  
  function display_warnings() {
    $("#sge-warning")
      .removeAttr('hidden')
      .text(
        'It looks like you are trying to upload an SGE dataset. We strongly encourage you to ' +
        'provide the relevant sequence metadata.'
      )
  }
  
  function parse_file(inputId) {
    $(inputId).parse({
      config: {
        complete: warn_sge_missing_metadata,
        comments: '#',
        skipEmptyLines: true,
      },
      error: function (err, file, inputElem, reason) {
        console.log(err);
        console.log(reason);
        console.log(file);
      },
    })
  }
});