
//// Fire in the hole! ////
$(document).ready(function(){
    $('#id_tag').after(" <a id=\"get_latest_tag\" href=\"#\">Show gathered tags</a> <p>(Note that this may not be the latest tags, they are gathered async.)</p> <ul id=\"tag_list\"></ul>");
    $('#get_latest_tag').click(function() {
        var selected = $("#id_recipe_id option:selected").val();
        $.get('/get_latest_tag/' + selected + '/', function(data) {
            var items = [];
            $.each(data, function(key, val) {
                items.push('<li class="select_tag">' + val + '</li>');
            });
            $("#tag_list").html(items.join(''));
        });
        return false;
    });
});
