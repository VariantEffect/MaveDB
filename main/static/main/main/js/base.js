// Forward declare jQuery's `$` symbol
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

    // Initialise select2
    $('.select2').select2();
    $(".select2-token-select").select2({
        tags: true,
        tokenSeparators: [',']
    });
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
