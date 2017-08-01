
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