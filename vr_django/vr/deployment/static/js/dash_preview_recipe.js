//// Fire in the hole! ////
$(document).ready(function(){
    $('#id_recipe_id').after(" <a id=\"preview_recipe\" href=\"#\">Preview</a>");
    $('#preview_recipe').click(function() {
        var selected = $("#id_recipe_id option:selected").val();
        $.get('/preview_recipe/' + selected + '/', function(data) {
            if ($('#config-preview').length) {
                $('#config-preview').html('<h3>Config Preview</h3><pre>' + data + '</pre></div>');
            } else {
            $('.row-fluid').after('<div id="config-preview"><h3>Config Preview</h3><pre>' + data + '</pre></div>');
            }
        });
        return false;
    });
});
