var dash = {};
dash.init = function() {

    dash.proc_tmpl = $('#host-procs-tmpl');
    dash.container = $('#dash-procs');
    $.getJSON('/api/hosts/', dash.onHostData);
    // TODO: put urls in a single place, and provide a url builder function to
    // plug in the parts that vary.

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
    $('body').delegate('.action-dialog .btn', 'click', dash.onActionModalClick); 
};

dash.cleanName = function(host) {
  return host.replace(/\./g, "");
};

dash.createID = function(host, proc) {
  return host.replace(/\./g, "") + proc.replace(/\./g, "");
};

// EVENT HANDLERS
dash.onHostData = function(data, txtStatus, xhr) {
  _.each(data.hosts, function(el, idx, lst) {
      // for each host in the list, make a request for the procs and draw
      // a box for each.
      $.getJSON('/api/hosts/' + el + '/procs/', function(data, txtStatus, xhr) {
          _.each(data.states, function(el, idx, lst) {
              el.host = data.host;
              // strip dots from the host so it can be used as a
              // classname
              el.hostclass = dash.cleanName(data.host);
              el.appclass = el.name.split('-')[0];
              el.destroyable = dash.procIsOurs(el.name); 
              el.shortname = el.name.split('-')[0].split('_')[0];
              // each proc gets a unique id of host + procname, with illegal
              // chars stripped out.
              el.procid = dash.createID(el.host, el.name);
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
  $(this).parent().toggleClass('host-expanded');
  dash.reflow();
};

dash.onHostActionClick = function() {
  var data = $(this).parents('.host-status').data();
  // action buttons will have their action stored in the 'rel attribute.
  data.action = $(this).attr('rel');
  if (data.action === 'destroy') {
    // show a confirmation dialog before doing proc deletions
    popup = $('#proc-modal-tmpl').goatee(data);
    popup.data(data);
    $(popup).modal();
  } else {
    // do stops and starts automatically
    dash.doHostAction(data.host, data.proc, data.action);
  }
};

dash.doHostAction = function(host, proc, action, method, callback) {
    if (method === undefined) {
        method = 'POST';
    }
    if (callback === undefined) {
        callback = dash.onActionResponse;
    }

    var url = '/api/hosts/' + host + '/procs/' + proc + '/';
    data = {host:host,proc:proc,action:action};
    $.ajax(url, {
        data: data,
        dataType: 'json',
        type: method,
        success: callback 
    });
};

dash.destroyProc = function(host, proc) {
    return dash.doHostAction(host, proc, 'destroy', 'DELETE', dash.onProcDestroy);
};

dash.onProcDestroy = function(data, txtStatus, xhr) {
    // callback for deleting a proc from the DOM when server lets us know it's
    // been destroyed.
    $('#' + dash.createID(data.host, data.name)).remove();
    dash.reflow();
};

dash.onActionModalClick = function() {
  // this handler is bound using $().delegate on init.
    var btn = $(this).attr('rel');
    var modal = $(this).parents('.modal');
    if (btn === 'confirm') {
        // get the data, and make an ajax request with it.
        var data = modal.data();
        if (data.action === 'destroy') {
            dash.destroyProc(data.host, data.proc);
        } else {
            dash.doHostAction(data.host, data.proc, data.action);
        }
    } 
    // no matter what button we got, hide and destroy the modal.
    modal.modal('hide');
    modal.remove();
};

dash.clearStatus = function(proc) {
    _.each(['RUNNING', 'STOPPED', 'FATAL', 'BACKOFF', 'STARTING'], function(el, idx, lst) {
        proc.removeClass('status-' + el);
    });
};

dash.onActionResponse = function(data, txtStatus, xhr) {
  // find the proc
  // update its class so it changes colors
  var proc = $('#' + dash.createID(data.host, data.name));
  dash.clearStatus(proc);
  proc.addClass('status-' + data.statename);
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
