// Forward declare jQuery's `$` symbol
jQuery, $;

// ORCID button in base.html
function openORCID() {
    var currentUrl = "accounts/login/";
    window.location.assign(currentUrl);
    return false;
}


$('document').ready(function() {
    // Initialise select2
    $('.select2').select2();
    $(".select2-token-select").select2({
        tags: true,
        tokenSeparators: [',']
    });

    currentUrl = window.location.toString();
    if (currentUrl.endsWith("#counts")) {
        $("#counts-tab").click();
    }
    if (currentUrl.endsWith("#scores")) {
        $("#scores-tab").click();
    }

    // Re-add any external_accession, keywords or target organism
    // back to failed form submission
    repopulateSelect("#id_keywords", "#keywords-to-add");
    repopulateSelect("#id_external_accessions", "#accession-to-add");
    repopulateSelect("#id_target_organism", "#organisms-to-add");
});

// Ajax for markdown field preview
$("#preview-abstract").click(function (e) {
    // First get whatever is in the form and send an ajax request
    // to convert it to markdown.
    var abstract = $("#id_abstract").val();
    $.ajax({
        url: "/scoreset/new/",
        type: "GET",
        data: { "abstract": abstract },
        dataType: "json",
        success: function (data) {
            abstract = data.abstract;
            $("#abstract-markdown-modal .modal-body").text("");
            $("#abstract-markdown-modal .modal-body").append(abstract);
        },
        error : function(xhr,errmsg,err) {
            console.log(xhr.status + ": " + xhr.responseText);
        }
    });
    return true;
});
$("#preview-method").click(function (e) {
    // First get whatever is in the form and send an ajax request
    // to convert it to markdown.
    var method = $("#id_method_desc").val();
    $.ajax({
        url: "/scoreset/new/",
        type: "GET",
        data: { "method_desc": method },
        dataType: "json",
        success: function (data) {
            method = data.method_desc;
            $("#method-markdown-modal .modal-body").text("");
            $("#method-markdown-modal .modal-body").append(method);
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
    ls = $(listId).text();
    if (ls !== undefined) {
        ls = ls.trim().split(',');
        $.each(ls, function (index, value) {
            if (value !== "") {
                $(selectId).append($('<option/>', {
                    value: value,
                    text: value,
                    selected: true
                }));
            }
        });
    }
}


// Pagination submission
// dataType: 'scores', 'counts' or 'search'
// selectObj: select object
function paginationSubmit(dataType, clickedLink) {
    var scoresSelect = $("#scores-per-page-select")[0];
    var countsSelect = $("#counts-per-page-select")[0];
    var searchSelect = $("#per-page-select")[0];

    var scoresPageLink = $(".scores-active")[0];
    var countsPageLink = $(".counts-active")[0];
    var searchPageLink = $(".search-active")[0];

    var scoresPageNum;
    var countsPageNum;
    var searchPageNum;
    if (scoresPageLink !== undefined) {
        scoresPageNum = parseInt(scoresPageLink.innerHTML);
    }
    if (countsPageLink !== undefined) {
        countsPageNum = parseInt(countsPageLink.innerHTML);
    }
    if (searchPageLink !== undefined) {
        searchPageNum = parseInt(searchPageLink.innerHTML);
    }

    if (clickedLink !== undefined) {
        var nextPageNum;
        var previousPageNum;
        if (clickedLink.childNodes[1] !== undefined) {
            nextPageNum = parseInt(clickedLink.childNodes[1].innerHTML);
            previousPageNum = parseInt(clickedLink.childNodes[1].innerHTML);
        }

        if (dataType === "scores") {
            scoresPageNum = parseInt(clickedLink.innerHTML);
            if (nextPageNum !== undefined) {
                scoresPageNum = nextPageNum;
            }
            else if (previousPageNum !== undefined) {
                scoresPageNum = previousPageNum;
            }
        }
        else if (dataType === "counts") {
            countsPageNum = parseInt(clickedLink.innerHTML);
            if (nextPageNum !== undefined) {
                countsPageNum = nextPageNum;
            }
            else if (previousPageNum !== undefined) {
                countsPageNum = previousPageNum;
            }
        }
        else if (dataType === "search") {
            searchPageNum = parseInt(clickedLink.innerHTML);
            if (nextPageNum !== undefined) {
                searchPageNum = nextPageNum;
            }
            else if (previousPageNum !== undefined) {
                searchPageNum = previousPageNum;
            }
        }
    }

    var scoresPerPage;
    var countsPerPage;
    var searchPerPage;
    if (scoresSelect !== undefined) {
        scoresPerPage = parseInt(
            scoresSelect.options[scoresSelect.selectedIndex].value
        );
    }
    if (countsSelect !== undefined) {
        countsPerPage = parseInt(
            countsSelect.options[countsSelect.selectedIndex].value
        );
    }
    if (searchSelect !== undefined) {
        searchPerPage = parseInt(
            searchSelect.options[searchSelect.selectedIndex].value
        );
    }

    var base = window.location.toString().split("#")[0].split("?")[0];
    var url = base;
    if (dataType !== "search") {
        if (scoresPerPage !== undefined) {
            url += "?scores-per-page=" + scoresPerPage;
        }
        if (countsPerPage !== undefined) {
            url += "&counts-per-page=" + countsPerPage;
        }
        if (scoresPageNum !== undefined) {
            url += "&scores-page=" + scoresPageNum;
        }
        if (countsPageNum !== undefined) {
            url += "&counts-page=" + countsPageNum;
        }
        url += "#" + dataType;
    }
    else {
        if (searchPerPage !== undefined) {
            url += "?per-page=" + searchPerPage;
        }
        if (searchPageNum !== undefined) {
            url += "&page=" + searchPageNum;
        }
    }

    window.location.assign(url);
    return false;
}


// Check Publish is ok with user
$("#publish").click(function (event) {
    var saidYes = confirm(
        'WARNING! Proceeding will freeze your upload and limit which fields can be edited. ' +
        
        'If this score set is part of a private experiment, this experiment ' +
        'will also be published and frozen. ' + 
        
        'Please make sure you have read the documentation before proceeding. ' +
        'This action cannot be undone. Would you like to proceed?'
    );
    return saidYes;
});


// Check management form submission
// ----------------------------------------------------------------------- //
// `userPk` is a global defined in base.html using Django's templating system.

function askConfirmation() {
    var saidYes = confirm(
        'This assignment will remove you as an administartor. If you ' +
        'continue, you will no longer be able to access this page. ' +
        'Are you sure?'
    );
    return saidYes;
}

function validate_admin_submit(e) {
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

function validate_contrib_submit(e) {
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

function validate_viewer_submit(e) {
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

// Formsets
// ----------------------------------------------------------------------- //
function reset_index(prefix) {
    formset_tag = prefix + '-form-set';
    form_idx_tag = formset_tag +
                    " > #id_" +
                    prefix.replace('#', '') +
                    "-TOTAL_FORMS";

    var form_idx = parseInt($(form_idx_tag).val());
    element = prefix + "-formset-" + form_idx;
    if ($(element).length === 0 && form_idx > 0) {
        $(form_idx_tag).val(1);
    }
}

function add_formset(prefix) {
    formset_tag = prefix + '-form-set';
    form_idx_tag = formset_tag +
                    " > #id_" +
                    prefix.replace('#', '') +
                    "-TOTAL_FORMS";
    template_form_tag = prefix + "-empty-form";
    empty_set_tag = prefix + '-empty-set';

    var form_idx = parseInt($(form_idx_tag).val());
    if (form_idx < 0) {
        form_idx = 0;
    }

    var item = $(template_form_tag).html().replace(/__prefix__/g, form_idx);
    new_idx = form_idx === 0 ? form_idx : form_idx + 1;
    item =
        '<div id="' + prefix.replace("#", '') +
            '-formset-' + (form_idx + 1) + '">' +
        item +
        '<hr></div>';

    $(empty_set_tag).hide();
    $(formset_tag).append(item);
    $(form_idx_tag).val(form_idx + 1);
}

function remove_formset(prefix) {
    formset_tag = prefix + '-form-set';
    form_idx_tag = formset_tag +
                    " > #id_" +
                    prefix.replace('#', '') +
                    "-TOTAL_FORMS";
    template_form_tag = prefix + "-empty-form";
    empty_set_tag = prefix + '-empty-set';

    var form_idx = parseInt($(form_idx_tag).val());
    element = prefix + "-formset-" + form_idx;

    possible_elemet = prefix + "-formset-" + 1;
    if (form_idx === 0 && $(possible_elemet).length > 0) {
        $(possible_elemet).remove();
        $(empty_set_tag).show();
        $(form_idx_tag).val(0);
    }
    else {
        $(element).remove();
        if (form_idx - 1 <= 0) {
            $(empty_set_tag).show();
            $(form_idx_tag).val(0);
        }
        else {
            $(form_idx_tag).val(form_idx - 1);
        }
    }
}

$('#add_reference_mapping').click(function () {
    reset_index("#reference_mapping");
    add_formset("#reference_mapping");
});
$('#remove_reference_mapping').click(function () {
    reset_index("#reference_mapping");
    remove_formset("#reference_mapping");
});
