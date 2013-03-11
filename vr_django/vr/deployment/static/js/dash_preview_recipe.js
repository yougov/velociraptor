//// Fire in the hole! ////
$(document).ready(function(){
    var updatePreview = function() {
      console.log('updatePreview');
        var selected = $("#id_recipe_id option:selected").val();
        if (selected) {
          console.log('selected', selected);
          $.get('/preview_recipe/' + selected + '/', function(data) {
              if ($('#config-preview').length) {
                  $('#config-preview').html('<h3>Config Preview</h3><pre>' + data + '</pre></div>');
              } else {
                $('.row-fluid').after('<div id="config-preview"><h3>Config Preview</h3><pre>' + data + '</pre></div>');
              }
          });
      } else {
        console.log('nope');
      }
    };

  // update on selecting new recipe
  $('#id_recipe_id').change(function() {
      updatePreview();
  });

  // update now (on dom ready) too
  updatePreview();
});
