$(document).ready(function() {
    // Run once on page load
    let select_element = $("#id_meta_analysis_for")
    maybe_toggle_experiment_input(select_element)

    $(select_element).on('change', function() {
       maybe_toggle_experiment_input(select_element);
    });

    function maybe_toggle_experiment_input(element) {
        let experiment_select = $("#id_experiment")
        if ($(element).val().length > 0) {
            $(experiment_select).prop('disabled', true);
            $(experiment_select).val('');
        } else {
            $(experiment_select).prop('disabled', false);
        }
    }
})