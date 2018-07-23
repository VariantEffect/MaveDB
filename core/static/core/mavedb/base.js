// Forward declare jQuery"s `$` symbol
"use strict";
jQuery, $;

// Buttons ----------------------------------------------------------------- //
// ORCID button in base.html
function openORCID() {
  var baseUrl = window.location.origin;
  var loginPath = baseUrl + "/login/";
  window.location.assign(loginPath);
  return false;
}

function goToUrl(url) {
  var baseUrl = window.location.origin;
  var path = baseUrl + url;
  window.location.assign(path);
  return false;
}

function cancelSubmission() {
  var baseUrl = window.location.origin;
  var profileUrl = baseUrl + "/profile/";
  window.location.assign(profileUrl);
  return false;
}

function confirmDelete(urn) {
  var yes = confirm(
    "Deleting an entry is final and cannot be undone. Are you sure" +
    "you would like to continue? Note that before deleting an Experiment Set or " +
    "Experiment, you must first delete all child entries."
  );
  if (yes) {
    return document.getElementById(urn + "-delete").submit();
  }
}

function confirmPublish(urn) {
  var yes = confirm(
    "WARNING! Proceeding will freeze your upload and limit which fields " +
    "can be edited. If this score set is part of a private experiment, " +
    "this experiment will also be published and frozen. " +
    "Please make sure you have read the documentation before proceeding." +
    " This action cannot be undone. Would you like to proceed?"
  );
  if (yes) {
    return document.getElementById(urn + "-publish").submit();
  }
}

// Check management form submission
// ----------------------------------------------------------------------- //
// `user` is a global defined in base.html using Django"s templating system.
function askConfirmation() {
  return confirm(
    "This assignment will remove you as an administartor. If you " +
    "continue, you will no longer be able to access this page. " +
    "Are you sure?"
  );
}

function validateAdminSubmit(e) {
  var aSelected = $("#admin-form > div > select option:selected");
  var aSelectedPks = aSelected.map(function() {
    return parseInt(this.value);
  });

  var willRemoveSelfAsAdmin = aSelectedPks.index(user) < 0;
  if(willRemoveSelfAsAdmin && !ignore) {
    var submit = askConfirmation();
    if(submit) {
      return $("#admin-form").submit();
    }
    return false;
  }
  return $("#admin-form").submit();
}

function validateEditorSubmit(e) {
  var eSelected = $("#editor-form > div > select option:selected");
  var eSelectedPks = eSelected.map(function() {
    return parseInt(this.value);
  });

  var willRemoveSelfAsAdmin = eSelectedPks.index(user) >= 0;
  if(willRemoveSelfAsAdmin && !ignore) {
    var submit = askConfirmation();
    if(submit) {
      return $("#editor-form").submit();
    }
    return false;
  }
  return $("#editor-form").submit();
}

function validateViewerSubmit(e) {
  var vSelected = $("#viewer-form > div > select option:selected");
  var vSelectedPks = vSelected.map(function() {
    return parseInt(this.value);
  });

  var willRemoveSelfAsAdmin = vSelectedPks.index(user) >= 0;
  if(willRemoveSelfAsAdmin && !ignore) {
    var submit = askConfirmation();
    if(submit) {
      return $("#viewer-form").submit();
    }
    return false;
  }
  return $("#viewer-form").submit();
}


// Dynaimic form selection
// ------------------------------------------------------------------------ //
// Re-add any external_accession, keywords or target organism
// back to failed form submission
function repopulateSelect(selectId, listId) {
  var selectItems = listId;
  var i,j = 0;


  if (selectItems !== undefined) {
    if (typeof listId === "string") {
      selectItems = $(listId).text();
      selectItems = selectItems.trim().split(",");
    }

    for(i=0; i<selectItems.length; i++) {
      var optionExists = false;
      var select = document.getElementById(selectId.replace("#", ''));
      if (select === null) {
        return
      }
      var options = select.getElementsByTagName("option");

      for (j=0; j<options.length; j++) {
        if (selectItems[i] === options[j].value) {
          options[j].selected = true;
          optionExists = true;
          break;
        }
      }

      if (!optionExists && selectItems[i]) {
        $(selectId).append($("<option/>", {
          value: selectItems[i],
          text: selectItems[i],
          selected: true
        }));
      }
    }
  }
}


// AJAX Calls -------------------------------------------------------------- //
// ------------------------------------------------------------------------- //
$("#preview-abstract").click(function (e) {
  // First get whatever is in the form and send an ajax request
  // to convert it to markdown.
  var abstract = $("#id_abstract_text").val();
  $.ajax({
    url: window.location.pathname,
    type: "GET",
    data: { "abstractText": abstract, "markdown": true},
    dataType: "json",
    success: function (data) {
      abstract = data.abstractText;
      $("#abstract-markdown-modal .modal-body")
        .text("")
        .append(abstract);
    },
    error : function(xhr, errmsg, err) {
      console.log(xhr.status + ": " + xhr.responseText);
    }
  });
  return true;
});


$("#preview-method").click(function (e) {
  // First get whatever is in the form and send an ajax request
  // to convert it to markdown.
  var method = $("#id_method_text").val();
  $.ajax({
    url: window.location.pathname,
    type: "GET",
    data: { "methodText": method, "markdown": true },
    dataType: "json",
    success: function (data) {
      method = data.methodText;
      $("#method-markdown-modal .modal-body")
        .text("")
        .append(method);
    },
    error : function(xhr,errmsg,err) {
      console.log(xhr.status + ": " + xhr.responseText);
    }
  });
  return true;
});


$("#id_experiment").on("change", function() {
  var id = this.value;
  var replaces_selector = "#id_replaces";
  var options = $(replaces_selector).children();
  if (parseInt(id)) {
    $.ajax({
      url: window.location.pathname,
      type: "GET",
      data: {"experiment": id},
      dataType: "json",

      success: function (data) {
        // console.log(data);
        $.each(options, function (index, option) {
          if (option.value !== "") {
            $(option).remove();
          } else {
            $(option).select();
          }
        });

        $.each(data.scoresets, function (index, tuple) {
          if (tuple[0] !== "" && tuple[1] !== "") {
            $(replaces_selector).append($("<option/>", {
              value: tuple[0],
              text: tuple[1]
            }));
          }
        });
      },
      error: function (xhr, errmsg, err) {
        console.log(xhr.status + ": " + xhr + errmsg + err);
      }
    })
  }
});


$("#id_target").on("change", function() {
  // First get whatever is in the form and send an ajax request
  // to convert it to markdown.
  if (window.location.href.includes('search')) {
    return false;
  }
  
  var id = this.value;
  var emptySelect = '---------';

  var uniprotSelect = document.getElementById(
    'select2-id_uniprot-offset-identifier-container');
  var uniprotOffsetElem = document.getElementById(
    "id_uniprot-offset-offset");

  var refseqSelect = document.getElementById(
    'select2-id_refseq-offset-identifier-container');
  var refseqOffsetElem = document.getElementById(
    "id_refseq-offset-offset");

  var ensemblSelect = document.getElementById(
    'select2-id_ensembl-offset-identifier-container');
  var ensemblOffsetElem = document.getElementById(
    "id_ensembl-offset-offset");

  var nameElem = document.getElementById('id_name');
  var seqElem = document.getElementById('id_wt_sequence');
  var genomeElem = document.getElementById('id_genome');

  if (parseInt(id)) {
    $.ajax({
      url: window.location.pathname,
      type: "GET",
      data: {"targetId": id},
      dataType: "json",
      success: function (data) {
        // console.log(data);
        var i = 0;
        var options = document.getElementsByTagName('OPTION');
        var targetName = data.name;
        var wildTypeSequence = data.wt_sequence.sequence;
        var referenceGenome = data.genome;
        
        var uniprot_id, refseq_id, ensembl_id = null;
        var uniprot_offset, refseq_offset, ensembl_offset = null;
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
        
        if (uniprot_id) {
          for(i=0; i<options.length; i++) {
            if (options[i].value === uniprot_id) {
              options[i].selected = true;
              uniprotSelect.innerHTML = uniprot_id;
              uniprotSelect.title = uniprot_id;
              uniprotOffsetElem.value = uniprot_offset;
            }
          }
        } else {
          uniprotSelect.innerHTML = emptySelect;
          uniprotSelect.title = emptySelect;
          uniprotOffsetElem.value = 0;
        }

        if (refseq_id) {
          for(i=0; i<options.length; i++) {
            if (options[i].value === refseq_id) {
              options[i].selected = true;
              refseqSelect.innerHTML = refseq_id;
              refseqSelect.title = refseq_id;
              refseqOffsetElem.value = refseq_offset;
            }
          }
        } else {
          refseqSelect.innerHTML = emptySelect;
          refseqSelect.title = emptySelect;
          refseqOffsetElem.value = 0;
        }

        if (ensembl_id) {
          for(i=0; i<options.length; i++) {
            if (options[i].value === ensembl_id) {
              options[i].selected = true;
              ensemblSelect.innerHTML = ensembl_id;
              ensemblSelect.title = ensembl_id;
              ensemblOffsetElem.value = ensembl_offset;
            }
          }
        } else {
          ensemblSelect.innerHTML = emptySelect;
          ensemblSelect.title = emptySelect;
          ensemblOffsetElem.value = 0;
        }

        if (targetName) {
          nameElem.value = targetName;
        } else {
          nameElem.value = "";
        }
        if (wildTypeSequence) {
          seqElem.value = wildTypeSequence
        } else {
          seqElem.value = ""
        }
        if (referenceGenome) {
          genomeElem.value = referenceGenome;
        } else {
          genomeElem.value = "";
        }
       },
      error: function (xhr, errmsg, err) {
        console.log(xhr.status + ": " + xhr + errmsg + err);
      }
    });
    return true;
  } else {
    nameElem.value = "";
    seqElem.value = "";
    genomeElem.value = "";

    ensemblSelect.innerHTML = emptySelect;
    ensemblSelect.title = emptySelect;
    ensemblOffsetElem.value = 0;

    refseqSelect.innerHTML = emptySelect;
    refseqSelect.title = emptySelect;
    refseqOffsetElem.value = 0;

    uniprotSelect.innerHTML = emptySelect;
    uniprotSelect.title = emptySelect;
    uniprotOffsetElem.value = 0;
  }
  return false;
});


function init_select2(params) {
  $(".select2").select2();
  $(".select2-token-select").select2({
    tags: true,
    tokenSeparators: [","]
  });
}
