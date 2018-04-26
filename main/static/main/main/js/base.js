// Forward declare jQuery"s `$` symbol
"use strict";
jQuery, $;


$("form#data").submit(function(e) {
  e.preventDefault();
  var formData = new FormData(this);
  console.log(formData);
});


// ORCID button in base.html
function openORCID() {
  var baseUrl = window.location.origin;
  var loginPath = baseUrl + "/accounts/login/";
  window.location.assign(loginPath);
  return false;
}

function cancelSubmission() {
  var baseUrl = window.location.origin;
  var profileUrl = baseUrl + "/profile/";
  window.location.assign(profileUrl);
  return false;
}

$("document").ready(function() {
  // Initialise select2
  $(".select2").select2();
  $(".select2-token-select").select2({
    tags: true,
    tokenSeparators: [","],
  });

  // Re-add any external_accession, keywords or target organism
  // back to failed form submission
  repopulateSelect("#id_keywords", "#keywords-to-add");
  repopulateSelect("#id_sra_ids", "#sra-identifiers-to-add");
  repopulateSelect("#id_doi_ids", "#doi-identifiers-to-add");
  repopulateSelect("#id_pubmed_ids", "#pubmed-identifiers-to-add");
  repopulateSelect("#id_uniprot_id", "#uniprot-identifier-to-add");
  repopulateSelect("#id_ensembl_id", "#ensembl-identifier-to-add");
  repopulateSelect("#id_refseq_id", "#refseq-identifier-to-add");
});


// Ajax for markdown field preview
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

// Check Publish is ok with user
$("#publish").click(function (event) {
  var saidYes = confirm(
    "WARNING! Proceeding will freeze your upload and limit which fields " +
    "can be edited. If this score set is part of a private experiment, " +
    "this experiment will also be published and frozen. " +
    "Please make sure you have read the documentation before proceeding." +
    " This action cannot be undone. Would you like to proceed?"
  );
  return saidYes;
});


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
  var ls = listId;
  if (ls !== undefined) {
    if (typeof listId === "string") {
      ls = $(listId).text();
      ls = ls.trim().split(",");
    }
    $.each(ls, function (index, value) {
      if (value !== "") {
        $(selectId).append($("<option/>", {
          value: value,
          text: value,
          selected: true
        }));
      }
    });
  }
}

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
        console.log(data);
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
        console.log(xhr.status + ": " + errmsg);
      }
    })
  }
});


$("#id_target").on("change", function() {
  // First get whatever is in the form and send an ajax request
  // to convert it to markdown.
  var id = this.value;
  if (parseInt(id)) {
    $.ajax({
      url: window.location.pathname,
      type: "GET",
      data: {"targetId": id},
      dataType: "json",
      success: function (data) {
        console.log(data);
        var targetName = data.name;
        var wildTypeSequence = data.wt_sequence.sequence;
        var referenceGenome = data.referenceGenome;
        var isPrimary = data.isPrimary;
        var intervalStart = data.intervalStart;
        var intervalEnd = data.intervalEnd;
        var chromosome = data.chromosome;
        var strand = data.strand;

        if (targetName) {
          $("#id_name").val(targetName);
        } else {
          $("#id_name").val("");
        }
        if (wildTypeSequence) {
          $("#id_wt_sequence").val(wildTypeSequence);
        } else {
          $("#id_wt_sequence").val("");
        }
        if (referenceGenome) {
          $("#id_genome").val(referenceGenome);
        } else {
          $("#id_genome").val("");
        }
        if (isPrimary) {
          $("#id_is_primary").prop('checked', isPrimary);
        } else {
          $("#id_is_primary").prop('checked', false);
        }
        if (intervalStart) {
          $("#id_start").val(intervalStart);
        } else {
          $("#id_start").val("");
        }
        if (intervalEnd) {
          $("#id_end").val(intervalEnd);
        } else {
          $("#id_end").val("");
        }
        if (chromosome) {
          $("#id_chromosome").val(chromosome);
        } else {
          $("#id_chromosome").val("");
        }
        if (strand) {
          $("#id_strand").val(strand);
        } else {
          $("#id_strand").val('F');
        }
      },
      error: function (xhr, errmsg, err) {
        console.log(xhr.status + ": " + xhr.responseText);
      }
    });
    return true;
  }
  return false;
});


function ensureAtLeastOne() {
  var num = parseInt(document.getElementById("id_form-TOTAL_FORMS").value);
  if (num <= 0 ) {
    return $("#add-interval").trigger("click");
  }
  return false;
}

$("#add-interval").click(function(e) {
  e.preventDefault();
  $(".add-interval-link").click();
});


function sortTable(id, n) {
  var table, rows, switching, i, x, y, shouldSwitch, dir, switchcount = 0;
  var x_val, y_val = 0;
  table = document.getElementById(id);
  switching = true;
  // Set the sorting direction to ascending:
  dir = "asc";
  /* Make a loop that will continue until
  no switching has been done: */
  while (switching) {
    // Start by saying: no switching is done:
    switching = false;
    rows = table.getElementsByTagName("TR");
    /* Loop through all table rows (except the
    first, which contains table headers): */
    for (i = 1; i < (rows.length - 1); i++) {
      // Start by saying there should be no switching:
      shouldSwitch = false;
      /* Get the two elements you want to compare,
      one from current row and one from the next: */
      x = rows[i].getElementsByTagName("TD")[n];
      y = rows[i + 1].getElementsByTagName("TD")[n];
      /* Check if the two rows should switch place,
      based on the direction, asc or desc: */
      x_val = parseFloat(x.innerHTML.toLowerCase());
      y_val = parseFloat(y.innerHTML.toLowerCase());
      if (isNaN(x_val) || isNaN(y_val)) {
        x_val = x.innerHTML.toLowerCase();
        y_val = y.innerHTML.toLowerCase();
      }
      if (dir === "asc") {
        if (x_val > y_val) {
          // If so, mark as a switch and break the loop:
          shouldSwitch= true;
          break;
        }
      } else if (dir === "desc") {
        if (x_val < y_val) {
          // If so, mark as a switch and break the loop:
          shouldSwitch= true;
          break;
        }
      }
    }
    if (shouldSwitch) {
      /* If a switch has been marked, make the switch
      and mark that a switch has been done: */
      rows[i].parentNode.insertBefore(rows[i + 1], rows[i]);
      switching = true;
      // Each time a switch is done, increase this count by 1:
      switchcount ++;
    } else {
      /* If no switching has been done AND the direction is "asc",
      set the direction to "desc" and run the while loop again. */
      if (switchcount === 0 && dir === "asc") {
        dir = "desc";
        switching = true;
      }
    }
  }
}

function showOptions() {
  $( ".fade-option" ).toggle("fade");
}