
//// Fire in the hole! ////
$(document).ready(function(){
    $('#id_recipe_id').after(" <a id=\"preview_recipe\" href=\"#\">Preview</a>");
    $('#preview_recipe').click(function() {
        var selected = $("#id_recipe_id option:selected").val();
        $.get('/preview_recipe/' + selected + '/', function(data) {
            alert(data);
        });
        return false;
    });


});
