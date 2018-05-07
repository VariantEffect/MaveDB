// Forward declare jQuery"s `$` symbol
"use strict";
jQuery, $;


$("form#data").submit(function(e) {
  e.preventDefault();
  var formData = new FormData(this);
});


// ORCID button in base.html
function openORCID() {
  var baseUrl = window.location.origin;
  var loginPath = baseUrl + "/accounts/login/";
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
  repopulateSelect("#id_uniprot-offset-identifier", "#uniprot-identifier-to-add");
  repopulateSelect("#id_ensembl-offset-identifier", "#ensembl-identifier-to-add");
  repopulateSelect("#id_refseq-offset-identifier", "#refseq-identifier-to-add");
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
  var selectItems = listId;
  var i,j = 0;

  if (selectItems !== undefined) {
    if (typeof listId === "string") {
      selectItems = $(listId).text();
      selectItems = selectItems.trim().split(",");
    }

    for(i=0; i<selectItems.length; i++) {
      var optionExists = false;
      var options = document.getElementsByTagName("option");

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


function getNewDataSelectId(formGroupClass) {
  var parent = document.getElementsByClassName(formGroupClass)[0];
  var children = parent.getElementsByClassName(
    "select2-selection__rendered")[0].children;
  var nums = [];
  for(var i =0; i < children.length; i++) {
    var num = children[i].getAttribute('data-select2-id');
    if (!isNaN(parseInt(num))) {
      nums.push(parseInt(num));
    }
  }
  var num = nums.sort()[nums.length - 1] + 1;
  if (isNaN(num)) {
    return -1;
  } else {
    return num
  }
}


$("#id_experiment").on("change", function() {
  var id = this.value;
  var replaces_selector = "#id_replaces";
  var options = $(replaces_selector).children();
  console.log("here")
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
        
        // // <li class="select2-selection__choice" title="process" data-select2-id="67">
        // /* <span class="select2-selection__choice__remove" role="presentation">×</span>process</li> */
        //
        //
        // var options = document.getElementById('id_keywords').children;
        // console.log(options);
        // var keywords = data.keywords;
        // var i, j = 0;
        // for (i = 0; i < options.length; i++) {
        //   for (j=0; j<keywords.length; j++)
        //     if (options[i].value === keywords[j]) {
        //       console.log(options[i]);
        //       options[i].selected = true;
        //
        //       let li = document.createElement("li")
        //       li.title = options[i].value;
        //       li.setAttribute('data-select-id', parseString(getNewDataSelectId('keywords-group')))
        //
        //     }
        // }
        
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
        console.log(data);
        var i = 0;
        var options = document.getElementsByTagName('OPTION');
        var targetName = data.name;
        var wildTypeSequence = data.wt_sequence.sequence;
        var referenceGenome = data.genome;
        
        var uniprot_id = data.uniprot.identifier;
        var uniprot_offset = data.uniprot.offset;
        
        var refseq_id = data.refseq.identifier;
        var refseq_offset = data.refseq.offset;

        var ensembl_id = data.ensembl.identifier;
        var ensembl_offset = data.ensembl.offset;
        
         
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


function sortTable(id, n, isHyperlinked) {
  var table, rows, switching, i, elem, x, y, shouldSwitch, dir, switchcount = 0;
  var x_val, y_val = 0;
  if (!isHyperlinked) {
    isHyperlinked = false;
  }
  console.log(isHyperlinked);

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

      // Some rows will have hyperlinked values. Parse these out into strings
      if (isHyperlinked) {
        x_val = "";
        y_val = "";
        var x_vals = x.getElementsByTagName('A');
        var y_vals = y.getElementsByTagName('A');
        for (elem = 0; elem < x_vals.length; elem++) {
          x_val += x_vals[elem].innerHTML;
        }
        for (elem = 0; elem < y_vals.length; elem++) {
          y_val += y_vals[elem].innerHTML;
        }
      } else {
        // Otherwise attempt parsing into a float. If that fails,
        // treat the inner HTML as a string
        x_val = parseFloat(x.innerHTML.toLowerCase());
        y_val = parseFloat(y.innerHTML.toLowerCase());
        if (isNaN(x_val) || isNaN(y_val)) {
          x_val = x.innerHTML.toLowerCase();
          y_val = y.innerHTML.toLowerCase();
        }
      }

      /* Check if the two rows should switch place,
      based on the direction, asc or desc: */
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