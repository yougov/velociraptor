var dash = {};
dash.init = function() {

    dash.proc_tmpl = $('#host-procs-tmpl');
    dash.container = $('#dash-procs');
    $.getJSON('/api/host/', dash.onHostData);

    $.getJSON('/api/task/active/', dash.onActiveTaskData);

    dash.container.isotope({
        itemSelector: '.host-status',
        layoutMode: 'masonry',
        animationOptions: {duration: 10}
      });

    $('.procfilter').click(dash.onFilterClick);

    // use $().delegate to set up handlers for elements that don't exist yet.
    dash.container.delegate('.host-status .label', 'click', dash.onHostClick);
    dash.container.delegate('.host-actions .btn', 'click', dash.onHostActionClick);
};

// EVENT HANDLERS
dash.onHostData = function(data, txtStatus, xhr) {
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
              el.destroyable = dash.procIsOurs(el.name); 
              el.shortname = el.name.split('-')[0].split('_')[0];
          });
          dash.container.isotope('insert', dash.proc_tmpl.goatee(data));
      });
  });
};

dash.onActiveTaskData = function(data, txtStatus, xhr) {
  // put active tasks at the top of the page
  if (data.tasks.length) {
      var tasks_tmpl = $('#tasks-tmpl');
      $('#dash-tasks').append(tasks_tmpl.goatee(data));
  }
};

dash.onFilterClick = function() {
  var selector = $(this).attr('data-filter');
  $(this).button('toggle');
  // hide the host dropdown
  $('.hostlist, .applist').removeClass('open');
  dash.container.isotope({ filter: selector });
  return false;
};

dash.onHostClick = function() {
  // add a class to make big
  $(this).parent().toggleClass('host-expanded');
  dash.reflow();
};

dash.onHostActionClick = function() {
  console.log(this);
};

// UTILITY FUNCTIONS
dash.isNumber = function(n) {
  return !isNaN(parseFloat(n)) && isFinite(n);
};

dash.procIsOurs = function(proc) {
  // if we can use a "-" to split a procname into 5 parts, and the last one
  // is a port number, then guess that this is a proc that the dashboard
  // can control.
  var parts = proc.split('-');
  return parts.length === 5 && dash.isNumber(parts[4]);
};

dash.reflow = function() { dash.container.isotope('reLayout');};

$(document).ready(function() {
    dash.init();
});
