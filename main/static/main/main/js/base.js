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

function getCookie(name) {
    // Get the CSRF token for this submission
    var cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        var cookies = document.cookie.split(';');
        for (var i = 0; i < cookies.length; i++) {
            var cookie = jQuery.trim(cookies[i]);
            // Does this cookie string begin with the name we want?
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

$("#select-add-btn").click(function(ev) {
    ev.preventDefault();
    var values = $("#select-left").val();

    for (var i = 0; i < values.length; i++) {
        var value = values[i];
        var node = $("#select-left option[value=OPT]".replace("OPT", value));

        // Remove item from left box
        node.remove();

        // Add item to right box
        $("#select-right")
            .append(
                $("<option></option>")
                    .attr("value", value)
                    .text(node.text())
            );
    }
});

$("#select-remove-btn").click(function(ev) {
    ev.preventDefault();
    var values = $("#select-right").val();

    for (var i = 0; i < values.length; i++) {
        var value = values[i];
        var node = $("#select-right option[value=OPT]".replace("OPT", value));

        // Remove item from left box
        node.remove();

        // Add item to left box
        $("#select-left")
            .append(
                $("<option></option>")
                    .attr("value", value)
                    .text(node.text())
            );
    }
});


$("#select-save").click(function(ev){
    ev.preventDefault();
    var csrftoken = getCookie('csrftoken');
    var options = $('#select-right option');
    var usernames = [];
    for (var i=0; i < options.length; i++) {
        option = options[i];
        usernames.push(option.value);
    }

    $.ajax({
        type: "POST",
        url: window.location,
        dataType: 'json',
        data: {
            usernames: usernames,
            csrfmiddlewaretoken: csrftoken,
            type: "administrators"
        },
        success: function(data) {
            var left = data["left"];
            var right = data["right"];
            var error = data["error"];
            var success_msg = data["success"];

            if(error !== "" && error !== undefined) {
                var parentNode = $("#admin-errors");
                var error_div = $('<div class="alert error">' + error + '</div>');
                parentNode.prepend(error_div).show();
                error_div.delay(2000);
                error_div.fadeOut(500);
                parentNode.delay(2000);
                parentNode.slideUp(1000);
            }
            else{
                var parentNode = $("#admin-success");
                var success_div = $('<div class="alert success">' + success_msg + '</div>');
                parentNode.prepend(success_div).show();
                setTimeout(function() {
                    window.location = window.location.href;
                }, 250);
            }
        },
        error: function(error) {
            var msg = error.status + ": " + error.statusText;
            alert("There was an error processing this request:\n\n" + error.responseText);
        }
    });
    return false;
});


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

$('#add_reference_mapping').click(function () {
    reset_index("#reference_mapping");
    add_formset("#reference_mapping");
});
$('#remove_reference_mapping').click(function () {
    reset_index("#reference_mapping");
    remove_formset("#reference_mapping");
});

$('#add_external_accession').click(function () {
    reset_index("#external_accession");
    add_formset("#external_accession");
});
$('#remove_external_accession').click(function () {
    reset_index("#external_accession");
    remove_formset("#external_accession");
});