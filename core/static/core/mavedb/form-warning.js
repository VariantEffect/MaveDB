$(document).ready(function () {
  $("#id_score_data").change(function () {
    parse_file('#id_score_data');
  });
  
  $("#id_count_data").change(function () {
    parse_file('#id_count_data');
  });
  
  function warn_sge_missing_metadata(results, file) {
    let tx_column_index = results.data[0].indexOf('hgvs_tx');
    if (tx_column_index < 0) return;
    
    let tx_variants = new Set()
    results.data.slice(1,).forEach(function (row) {
      if (row[tx_column_index] != null) {
        tx_variants.add(row[tx_column_index]);
      }
    });
    
    // Check if any tx variants are supplied. If not, return since we don't need to then do a
    // further check for metadata presence.
    if (
      tx_variants.size === 0 ||
      tx_variants.size === 1 && ['c', 'n'].indexOf(Array.from(tx_variants)[0][0]) < 0
    ) {
      console.log('This is not the SGE dataset you are looking for, move along.');
      return;
    }
    
    let refseq = $("#id_refseq-offset-identifier").val();
    let uniprot = $("#id_uniprot-offset-identifier").val();
    let ensembl = $("#id_ensembl-offset-identifier").val();
    
    let refseq_blank = (refseq === "") || (refseq == null)
    let uniprot_blank = (uniprot === "") || (uniprot == null)
    let ensembl_blank = (ensembl === "") || (ensembl == null)
    
    if (refseq_blank && uniprot_blank && ensembl_blank) {
      console.log(refseq, uniprot, ensembl);
      display_warnings();
    }
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