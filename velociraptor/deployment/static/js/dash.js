$(document).ready(function() {
// for each host on the page, make an API request to get the status of all
// the apps on that host
    var proc_tmpl = $('#host-procs-tmpl');
    var container = $('#dash-procs');
    $.getJSON('/api/host/', function(data, txtStatus, xhr) {
        _.each(data.hosts, function(el, idx, lst) {
            // for each host in the list, make a request for the procs and draw
            // a box for each.
            $.getJSON('/api/host/' + el + '/procs/', function(data, txtStatus, xhr) {
                _.each(data.states, function(el, idx, lst) {
                    el.host = data.host;
                    // strip dots from the host so it can be used as a
                    // classname
                    el.hostclass = data.host.replace(/\./g, "");
                    el.appclass = el.name.split('-')[0];
                    el.shortname = el.name.split('-')[0].split('_')[0];
                });
                container.isotope('insert', proc_tmpl.goatee(data));
            });
        });

      });

    // put active tasks at the top of the page
    $.getJSON('/api/task/active/', function(data, txtStatus, xhr) {
        if (data.tasks.length) {
            var tasks_tmpl = $('#tasks-tmpl');
            $('#dash-tasks').append(tasks_tmpl.goatee(data));
        }
    });

    container.isotope({
        itemSelector: '.host-status',
        layoutMode: 'masonry',
        animationOptions: {duration: 10}
      });

      $('.procfilter').click(function() {
        var selector = $(this).attr('data-filter');
        $(this).button('toggle');
        // hide the host dropdown
        $('.hostlist, .applist').removeClass('open');
        container.isotope({ filter: selector });
        return false;
      });

    $('#dash-procs').delegate('.host-status .label', 'click', function() {
        // add a class to make big
        $(this).parent().toggleClass('host-expanded');
        // reflow the isotope
        container.isotope('reLayout');
      });
});
