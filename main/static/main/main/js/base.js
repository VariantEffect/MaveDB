// Forward declare jQuery"s `$` symbol
"use strict";
jQuery, $;

// ORCID button in base.html
function openORCID() {
    var baseUrl = window.location.origin;
    var loginPath = baseUrl + "/accounts/login/";
    window.location.assign(loginPath);
    return false;
}

$("document").ready(function() {
    // Initialise select2
    $(".select2").select2();
    $(".select2-token-select").select2({
        tags: true,
        tokenSeparators: [","]
    });

    var currentUrl = window.location.toString();
    if (currentUrl.endsWith("#counts")) {
        $("#counts-tab").click();
    }
    if (currentUrl.endsWith("#scores")) {
        $("#scores-tab").click();
    }

    // Re-add any external_accession, keywords or target organism
    // back to failed form submission
    repopulateSelect("#id_keywords", "#keywords-to-add");
    repopulateSelect("#id_sra_ids", "#sra-identifiers-to-add");
    repopulateSelect("#id_doi_ids", "#doi-identifiers-to-add");
    repopulateSelect("#id_pmid_ids", "#pubmed-identifiers-to-add");
    repopulateSelect("#id_target_organism", "#target-organisms-to-add");
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

// Re-add any external_accession, keywords or target organism
// back to failed form submission
function repopulateSelect(selectId, listId) {
    var ls = $(listId).text();
    if (ls !== undefined) {
        ls = ls.trim().split(",");
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
// `userPk` is a global defined in base.html using Django"s templating system.

function askConfirmation() {
    var saidYes = confirm(
        "This assignment will remove you as an administartor. If you " +
        "continue, you will no longer be able to access this page. " +
        "Are you sure?"
    );
    return saidYes;
}

function validateAdminSubmit(e) {
    var aSelected = $("#admin-form > div > select option:selected");
    var aSelectedPks = aSelected.map(function() {
        return parseInt(this.value);
    });

    var willRemoveSelfAsAdmin = aSelectedPks.index(userPk) < 0;
    if(willRemoveSelfAsAdmin) {
        var submit = askConfirmation();
        if(submit) {
            return $("#admin-form").submit();
        }
        return false;
    }
    return $("#admin-form").submit();
  }

function validateContribSubmit(e) {
    var cSelected = $("#contrib-form > div > select option:selected");
    var cSelectedPks = cSelected.map(function() {
        return parseInt(this.value);
    });

    var willRemoveSelfAsAdmin = cSelectedPks.index(userPk) >= 0;
    if(willRemoveSelfAsAdmin) {
        var submit = askConfirmation();
        if(submit) {
            return $("#contrib-form").submit();
        }
        return false;
    }
    return $("#contrib-form").submit();
}

function validateViewerSubmit(e) {
    var vSelected = $("#viewer-form > div > select option:selected");
    var vSelectedPks = vSelected.map(function() {
        return parseInt(this.value);
    });

    var willRemoveSelfAsAdmin = vSelectedPks.index(userPk) >= 0;
    if(willRemoveSelfAsAdmin) {
        var submit = askConfirmation();
        if(submit) {
            return $("#viewer-form").submit();
        }
        return false;
    }
    return $("#viewer-form").submit();
}

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
                var targetName = data.targetName;
                var wildTypeSequence = data.wildTypeSequence;
                var referenceGenome = data.referenceGenome;
                var isPrimary = data.isPrimary;
                var intervalStart = data.intervalStart;
                var intervalEnd = data.intervalEnd;
                var chromosome = data.chromosome;
                var strand = data.strand;

                console.log(targetName);
                console.log(wildTypeSequence);
                console.log(referenceGenome);
                console.log(isPrimary);
                console.log(intervalStart);
                console.log(intervalEnd);
                console.log(chromosome);
                console.log(strand);

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