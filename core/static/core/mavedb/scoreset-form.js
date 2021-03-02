/**
 * Toggle experiment input and clear data if turned off.
 *
 * @param element {HTMLSelectElement}
 */
function maybe_toggle_experiment_input (element) {
  if (element == null) return;

  let experiment_select = $('#id_experiment');
  if ($(element).val().length > 0) {
    $(experiment_select).prop('disabled', true);
    $(experiment_select).val('');
  } else {
    $(experiment_select).prop('disabled', false);
  }
}

/**
 * A row parsed from a scores file. These are the named fields that the server expects, although other user defined
 * fields may exist.
 *
 * @typedef {{hgvs_nt: String?, hgvs_splice: String?, hgvs_pro: String?, score: Number?}} ScoreRow
 */

/**
 * A row parsed from a counts file. These are the named fields that the server expects, although other user defined
 * fields may exist.
 *
 * @typedef {{hgvs_nt: String?, hgvs_splice: String?, hgvs_pro: String?, count: Number?}} CountRow
 */

/**
 * Displays a warning message to the user if it looks like an SGE dataset is being uploaded recommending that a
 * sequence identifier is provided.
 *
 * @param {{data: Array<Array<String, Number>>}} results
 */
function warn_sge_missing_metadata (results) {
  if (
    (has_splice_variants(results.data) || has_genomic_variants(results.data)) &&
    metadata_is_empty()
  ) {
    display_warnings();
  }
}

/**
 * Checks if any hgvs_splice transcript variants (n. or c. prefix) have been defined.
 *
 * @param data {Array<Array<String, Number>>}
 *
 * @returns {boolean}
 */
function has_splice_variants (data) {
  let splice_column_index = data[0].indexOf('hgvs_splice');
  if (splice_column_index < 0) return false;

  let splice_variants = new Set();
  data.slice(1).forEach(function (row) {
    if (row[splice_column_index] != null) {
      splice_variants.add(row[splice_column_index]);
    }
  });

  // Check if any tx variants are supplied. If not, return since we don't need to then do a
  // further check for metadata presence.
  let has_splice_variants = Array.from(splice_variants).
    some(function (variant) {
      return variant.toString().startsWith('n.') ||
        variant.toString().startsWith('c.');
    });

  if (splice_variants.size === 0 || !has_splice_variants) {
    console.log('There are no splice variants.');
    return false;
  }
  return true;
}

/**
 * Checks if any hgvs_nt genomic (g. prefix) variants have been defined.
 *
 * @param data {Array<Array<String, Number>>}
 *
 * @returns {boolean}
 */
function has_genomic_variants (data) {
  let nt_column_index = data[0].indexOf('hgvs_nt');
  if (nt_column_index < 0) return false;

  let nt_variants = new Set();
  data.slice(1).forEach(function (row) {
    if (row[nt_column_index] != null) {
      nt_variants.add(row[nt_column_index]);
    }
  });

  // Check if any g. variants are supplied. If not, return since we don't need to then do a
  // further check for metadata presence.
  let has_g_variants = Array.from(nt_variants).some(function (variant) {
    return variant.toString().startsWith('g.');
  });

  if (nt_variants.size === 0 || !has_g_variants) {
    console.log('There are no genomic variants.');
    return false;
  }
  return true;
}

/**
 * Checks if any of the identifiers fields have been set.
 *
 * @returns {boolean}
 */
function metadata_is_empty () {
  let refseq = $('#id_refseq-offset-identifier').val();
  let uniprot = $('#id_uniprot-offset-identifier').val();
  let ensembl = $('#id_ensembl-offset-identifier').val();

  let refseq_blank = (refseq === '') || (refseq == null);
  let uniprot_blank = (uniprot === '') || (uniprot == null);
  let ensembl_blank = (ensembl === '') || (ensembl == null);

  return refseq_blank && uniprot_blank && ensembl_blank;
}

/**
 * Displays a warning to the user in a fancy yellow box.
 */
function display_warnings () {
  $('#sge-warning').show().text(
    'It looks like you are trying to upload an SGE dataset. We strongly encourage you to ' +
    'provide the relevant sequence metadata.',
  );
}

/**
 * Uses the PapaParse.js package to parse a scores/counts csv file into an object with an attribute called 'data'.
 * This fields points to an array of arrays where the first row are the file column names and the following arrays
 * are the parsed columns for each row.
 *
 * @param inputId
 *
 * @return {{data: Array<Array<String, Number>>}}
 */
function parse_file (inputId) {
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
  });
}

/**
 * Sets up the dynamic form handlers and other bits of interactivity.
 *
 * @param newForm {boolean} If true, will initialize all the form handlers.
 * @param privateDateset {boolean} if true, will initialize the auto-fill aspects when altering target.
 */
function initializeScoresetForm ({ newForm = true, privateDateset = true }) {
  init_select2();

  $('#dl-count-data-errors').click(function () {
    window.open('?errors_for=count_data', '_blank');
    return false;
  });
  $('#dl-score-data-errors').click(function () {
    window.open('?errors_for=score_data', '_blank');
    return false;
  });

  $('.clearable-file-input').click(function () {
    const input = $(this).parent().find('input')[0];
    if (!input) return;

    $(input).val('');
    if (input.id === 'id_score_data' || input.id === 'id_count_data') {
      const warning = $('#sge-warning');
      if (warning) warning.hide();
    }
  });

  // Only new datasets will have experiment/metadata fields available
  if (newForm) {
    // ---------- Disable/enable experiment selection and meta-analysis selection
    // Run once on page load
    let select_element = $('#id_meta_analysis_for');
    maybe_toggle_experiment_input(select_element);

    $(select_element).on('change', function () {
      maybe_toggle_experiment_input(select_element);
    });

    // ----------------------- Set replaces options when selecting experiments
    $('#id_experiment').on('change', function () {
      let id = this.value;
      let replaces_selector = '#id_replaces';
      let options = $(replaces_selector).children();

      $(replaces_selector).
        find('option').
        remove().
        end().
        append('<option value="">---------</option>').
        val('').
        trigger('change');

      if (parseInt(id)) {
        $.ajax({
          url: window.location.pathname,
          type: 'GET',
          data: { 'experiment': id },
          dataType: 'json',

          success: function (data) {
            // console.log(data);
            $.each(options, function (index, option) {
              if (option.value !== '') {
                $(option).remove();
              } else {
                $(option).select();
              }
            });

            $.each(data.scoresets, function (index, tuple) {
              if (tuple[0] !== '' && tuple[1] !== '') {
                $(replaces_selector).append($('<option/>', {
                  value: tuple[0],
                  text: tuple[1] + ' | ' + tuple[2],
                }));
              }
            });
          },
          error: function (xhr, errmsg, err) {
            console.log(xhr.status + ': ' + xhr + errmsg + err);
          },
        });
      }
    });
  }

  // Functionality only available in new/edit forms where not public
  if (newForm || privateDateset) {
    // -------------- Show warning when SGE dataset detected
    $('#id_score_data').change(function () {
      $('#sge-warning').hide();
      parse_file('#id_score_data');
    });

    $('#id_count_data').change(function () {
      $('#sge-warning').hide();
      parse_file('#id_count_data');
    });

    // ------------ Pre-fetch target information
    $('#id_target').on('change', function () {
      // First get whatever is in the form and send an ajax request
      // to convert it to markdown.
      if (window.location.href.includes('search')) {
        return false;
      }

      let id = this.value;
      let uniprotSelect = $('#id_uniprot-identifier');
      let uniprotOffsetElem = $('#id_uniprot-offset');

      let refseqSelect = $('#id_refseq-identifier');
      let refseqOffsetElem = $('#id_refseq-offset');

      let ensemblSelect = $('#id_ensembl-identifier');
      let ensemblOffsetElem = $('#id_ensembl-offset');

      let nameElem = document.getElementById('id_name');
      let categoryElem = document.getElementById('id_category');
      let seqElem = document.getElementById('id_sequence_text');
      let seqTypeSelect = $('#id_sequence_type');
      let genomeSelect = $('#id_genome');

      if (parseInt(id)) {
        $.ajax({
          url: window.location.pathname,
          type: 'GET',
          data: { 'targetId': id },
          dataType: 'json',
          success: function (data) {
            console.log(data);
            let targetName = data.name;
            let wildTypeSequence = data.reference_sequence.sequence;
            let wildTypeSequenceType = data.reference_sequence.sequence_type;

            let category = data.type;
            let referenceGenome = data.genome;

            let uniprot_id, refseq_id, ensembl_id = null;
            let uniprot_offset, refseq_offset, ensembl_offset = null;
            if (data.uniprot != null) {
              uniprot_id = data.uniprot.identifier;
              uniprot_offset = data.uniprot.offset;
            }
            if (data.refseq != null) {
              refseq_id = data.refseq.identifier;
              refseq_offset = data.refseq.offset;
            }
            if (data.ensembl != null) {
              ensembl_id = data.ensembl.identifier;
              ensembl_offset = data.ensembl.offset;
            }

            // Change Uniprot
            if (uniprot_id) {
              $(uniprotSelect).val(uniprot_id).trigger('change');
              $(uniprotOffsetElem).val(uniprot_offset);
            } else {
              $(uniprotSelect).val('').trigger('change');
              $(uniprotOffsetElem).val(0);
            }

            // Change RefSeq
            if (refseq_id) {
              $(refseqSelect).val(refseq_id).trigger('change');
              $(refseqOffsetElem).val(refseq_offset);
            } else {
              $(refseqSelect).val('').trigger('change');
              $(refseqOffsetElem).val(0);
            }

            // Change Ensembl
            if (ensembl_id) {
              $(ensemblSelect).val(ensembl_id).trigger('change');
              $(ensemblOffsetElem).val(ensembl_offset);
            } else {
              $(ensemblSelect).val('').trigger('change');
              $(ensemblOffsetElem).val(0);
            }

            nameElem.value = targetName ? targetName : '';
            categoryElem.value = category ? category : '';
            seqElem.value = wildTypeSequence ? wildTypeSequence : '';
            $(seqTypeSelect).
              val(wildTypeSequenceType ? wildTypeSequenceType : '').
              trigger('change');
            $(genomeSelect).
              val(referenceGenome ? referenceGenome : '').
              trigger('change');
          },
          error: function (xhr, errmsg, err) {
            console.log(xhr.status + ': ' + xhr + errmsg + err);
          },
        });
        return true;
      } else {
        nameElem.value = '';
        categoryElem.value = '';

        seqElem.value = '';
        $(seqTypeSelect).val('').trigger('change');

        $(genomeSelect).val('').trigger('change');

        $(uniprotSelect).val('').trigger('change');
        $(uniprotOffsetElem).val(0);

        $(ensemblSelect).val('').trigger('change');
        $(ensemblOffsetElem).val(0);

        $(refseqSelect).val('').trigger('change');
        $(refseqOffsetElem).val(0);
      }
      return false;
    });
  }
}
