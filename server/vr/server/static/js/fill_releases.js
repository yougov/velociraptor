/**
 * Created by yougov on 10/9/14.
 */

$('#id_app').on('change', function() {
    var selectedApp = $('#id_app').val();
    var releaseSearchUrl = VR.Urls.getTasty('releases') + '?build__app__id=' + selectedApp + '&limit=20';
    $('#id_release_id').empty();
    $.ajax({
  type: 'GET',
  url: releaseSearchUrl,
  dataType: 'json',
  success: function(data, sts, xhr) {
    if (data.meta.total_count > 0) {
      _.each(data.objects, function(release) {
          console.log(release);
          $('#id_release_id').append('<option value="' + release.id + '">' + release.compiled_name + '</option>');
      });
    }
  },
  async: false
});
});



