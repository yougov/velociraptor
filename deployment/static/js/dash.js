$(document).ready(function() {
// for each host on the page, make an API request to get the status of all
// the apps on that host
    var tmpl = $('#host-procs-tmpl');
    $('.dash-host').each(function() {
        var el = $(this);
        var host = el.data('hostname');
        var url = '/api/status/' + host;
        $.getJSON(url, function(data, txtStatus, xhr) {
            el.append(tmpl.goatee(data));

        });
    });

});
