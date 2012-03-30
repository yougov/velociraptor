$(document).ready(function() {
// for each host on the page, make an API request to get the status of all
// the apps on that host
    var proc_tmpl = $('#host-procs-tmpl');
    $('.dash-host').each(function() {
        var el = $(this);
        var host = el.data('hostname');
        var url = '/api/host/' + host + '/procs/';
        $.getJSON(url, function(data, txtStatus, xhr) {
            el.append(proc_tmpl.goatee(data));

        });
    });

    // make a request to /api/tasks.  If there are any listed, put them at the
    // top of the page
    $.getJSON('/api/task/active/', function(data, txtStatus, xhr) {
            console.log(data);
        if (data.tasks.length) {
            var tasks_tmpl = $('#tasks-tmpl');
            $('#dash-main').prepend(tasks_tmpl.goatee(data));
        }
    });
});
