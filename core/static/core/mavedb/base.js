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
  return false;
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
  return false;
}

// Check management form submission
// ----------------------------------------------------------------------- //
// `user` is a global defined in base.html using Django"s templating system.
function askConfirmation() {
  return confirm(
    "This assignment will remove you as an administrator. If you " +
    "continue, you will no longer be able to access this page. " +
    "Are you sure?"
  );
}

// Dynaimic form selection
// ------------------------------------------------------------------------ //


function init_select2() {
  $(".select2").select2({});
  $(".select2-token-select").select2({
    tags: true,
    tokenSeparators: [","]
  });
}
