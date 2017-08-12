jQuery, $;

// Container variable for common tags on the base tamplate
function basePageTags() {
    "use strict";
    var tags = {
        header: ".header",
        logoCol: ".logo",
        logoImage: ".logo-img",
        navbarCol: ".navbar",
        navbarList: ".navbar-list",
        navbarItem: ".navbar-item",
        navbarSearchCol: ".navbar-search",
        navbarSearchForm: ".navbar-search > form",
        navbarSearchInput: ".navbar-search > form > input",
        bodyBlock: ".body-block",
        footer: ".footer",
        footerbar: ".footerbar",
        footerbarList: ".footerbar-list",
        footerbarItem: ".footerbar-item"
    };
    return tags;
}


$('document').ready(function() {
    $(basePageTags().navbarSearchInput).focus(function (ev) {
        $(this).attr(
            'placeholder',
            "Kinase, DNA repair, regression, 'exact string', ..."
        );
    });
    $(basePageTags().navbarSearchInput).blur(function (ev) {
        $(this).attr("placeholder", "Search...");
    });

    $(".select-menu").change(function (ev) {
        $(".hidden-submit").attr("type", "submit");
        $(".hidden-submit").trigger("click");
        $(".hidden-submit").attr("type", "hidden");
    });
});


function reset_index(prefix) {
    formset_tag = prefix + '-form-set';
    form_idx_tag = formset_tag + " > #id_" + prefix.replace('#', '') + "-TOTAL_FORMS";

    var form_idx = parseInt($(form_idx_tag).val());
    element = prefix + "-formset-" + form_idx;
    if ($(element).length === 0 && form_idx > 0) {
        $(form_idx_tag).val(1);
    }
}


function add_formset(prefix) {
    formset_tag = prefix + '-form-set';
    form_idx_tag = formset_tag + " > #id_" + prefix.replace('#', '') + "-TOTAL_FORMS";
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
    form_idx_tag = formset_tag + " > #id_" + prefix.replace('#', '') + "-TOTAL_FORMS";
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

$('#add_keyword').click(function () {
    reset_index("#keyword");
    add_formset("#keyword");
});

$('#remove_keyword').click(function () {
    reset_index("#keyword");
    remove_formset("#keyword");
});

$('#add_ref_mapping').click(function () {
    reset_index("#ref_mapping");
    add_formset("#ref_mapping");
});
$('#remove_ref_mapping').click(function () {
    reset_index("#ref_mapping");
    remove_formset("#ref_mapping");
});

$('#add_external_accession').click(function () {
    reset_index("#external_accession");
    add_formset("#external_accession");
});
$('#remove_external_accession').click(function () {
    reset_index("#external_accession");
    remove_formset("#external_accession");
});