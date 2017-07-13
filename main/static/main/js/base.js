$(document).ready(function() {
    // Setup - add a text input to each footer cell
    $('#table_id .filters th').each(function() {
        var title = $('#example thead th').eq($(this).index()).text();
        $(this).html([
            '<input type="text"',
            'class="textinput textInput form-control"',
            'placeholder="..." />'].join(' '));
    } );
    
    // DataTable
    var table = $('#table_id').DataTable({
        "order": [],
        "pageLength": 25,
        "lengthMenu": [[25, 50, 100, -1], [25, 50, 100, "All"]],
        "dom": "<'row'<'col-xs-1'l>>" + "<'row'<'col-xs-4'i><'col-xs-8'p>>"
    });
   
    // Apply the search
    table.columns().eq(0).each(function(colIdx) {
        $('input', $('.filters th')[colIdx]).on('keyup change', function () {
            table.column(colIdx).search(this.value).draw();
        } );
    } );

    $('#min').keyup( function() { table.draw(); } );
    $('#table_id_filter').hide();
});