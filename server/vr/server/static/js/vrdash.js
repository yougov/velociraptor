// Depends on vr.js

// DASH //
VR.Dash = {};

VR.Dash.Options = {
    refreshInterval: 60000,
    apps: []
};

VR.Dash.init = function(appsContainer, eventsContainer, eventsUrl, procEventsUrl, dashboardId) {

  if(dashboardId) {
    $.getJSON(VR.Urls.getTasty('dashboard', dashboardId), function(data, stat, xhr) {
      _.each(data.apps, function(app) {
        VR.Dash.Options.apps.push({'name': app.name});
      })
    });
  }

  // Update dropdown in navigation
  $.getJSON(VR.Urls.getTasty('dashboard'), function(data, stat, xhr) {
    _.each(data.objects, function(dashboard) {
      $('#dashboard-submenu').append('<li><a href="/dashboard/'+dashboard.slug+'/">'+dashboard.name+'</a></li>');
    });

    $('#dashboard-submenu').append('<li class="divider"></li><li><a href="javascript:;" class="dashboard-new">New</a></li>');

    $('.dashboard-new').click(function() {
      var template = VR.Templates.DashModal,
          modal = template.goatee(),
          apps;
      $(modal).modal('show').queue(function() {
        $.getJSON(VR.Urls.getTasty('apps'), function(data) {
          apps = data.objects;
        });
      });

      $(modal).on('shown.bs.modal', function(ev) {
        _.each(apps, function(app) {
          if($('#'+app.name+'-option').length === 0)
            $('#dashboard-apps').append('<option id="'+app.name+'-option" data-id="'+app.id+'" value="'+app.id+'|'+app.name+'">'+app.name+'</option>');
        });

        $('#dashboard-name').on('change', function() {
          var name = $(this).val();
              name = name.replace(' ', '-').toLowerCase();

          $('#dashboard-slug').val(name);
        });
      });

      $(modal).find('.btn-success').on('click', function(ev) {
        var form = $(modal).find('form'),
            name = form.find('#dashboard-name').val(),
            slug = form.find('#dashboard-slug').val(),
            apps = form.find('#dashboard-apps').val();

        var payload = {
          name: name,
          slug: slug,
          apps: []
        };

        _.each(apps, function(app) {
          app = app.split('|');
          payload.apps.push({'id': app[0], 'name': app[1]});
        });

        $.ajax({
          url: VR.Urls.getTasty('dashboard'),
          data: JSON.stringify(payload),
          dataType: 'json',
          type: 'POST',
          headers: {
            'Content-type': 'application/json'
          },
          processData: false,
          success: function(data, status) {
            if("success" === status) window.location.reload();
          }
        });
      });
    });
  });

  // Create a new applist, bound to our container
  VR.Dash.Apps = new VR.Models.AppList();
  var view = new VR.Views.Apps(VR.Dash.Apps, appsContainer);
  VR.Dash.getHostData();

  // bind deployment event stream to handler
  VR.Events.init(
    eventsContainer,
    eventsUrl || VR.Urls.events
  );

  // bind proc event stream to handler
  var procEvents = new EventSource(procEventsUrl || VR.Urls.procEvents);
  procEvents.onmessage = $.proxy(function(e) {
      var parsed = JSON.parse(e.data);
      if (parsed.event == 'PROCESS_GROUP_REMOVED') {
        VR.ProcMessages.trigger('destroyproc:'+parsed.id, parsed);
      } else {
        VR.ProcMessages.trigger('updateproc:'+parsed.id, parsed);
      }
  }, this);

  // bind proc change event stream to handler
};

VR.Dash.removeProc = function(procdata) {
  // called when a removal event comes in on the pubsub.  Drill down into the
  // App>Swarm>Proc structure to find the proc and remove it.  On the way out,
  // remove any empty swarms or apps.
  var swarmName = procdata.config_name+'-'+procdata.proc_name;

  var app = VR.Dash.Apps.find(function(a, idx, list) {return a.get('name') === procdata.app_name;});
  if (!app) {return;}

  var swarm = app.swarms.find(function(s, idx, list) {return s.get('name') === swarmName;});
  if (!swarm) {return;}
  swarm.procs.removeByData(procdata);

  // If the swarm now has no procs, remove from dashboard
  if (swarm.procs.length === 0) {
    app.swarms.remove(swarm);
  }

  // if the app now has no swarms, remove from dashboard
  if (app.swarms.length === 0) {
    VR.Dash.Apps.remove(app);
  }
};

VR.Dash.onHostChange = function(e) {
  // when we get a host change event from the SSE stream, parse its JSON and
  // call our normal 'on host data' function.
  var hostdata = JSON.parse(e.data);
  VR.Dash.onHostData(hostdata);
};

VR.Dash.getHostData = function() {
  $.getJSON(VR.Urls.getTasty('hosts'), VR.Dash.onHostList);
};

VR.Dash.onHostList = function(data, stat, xhr) {
  _.each(data.objects, function(el) {
      _.each(el.procs, function(data) {
        if(VR.Dash.Options.apps.length > 0) {
          _.each(VR.Dash.Options.apps, function(app) {
            if(data.app_name === app.name) {
              VR.ProcMessages.trigger('updateproc:'+data.id, data);
            }
          });
        }
        else {
          VR.ProcMessages.trigger('updateproc:'+data.id, data);
        }
      });
  });

  // if there are more pages, get those too
  if (data.meta.next) {
    $.getJSON(data.meta.next, VR.Dash.onHostList);
  } else {
    // poll the API again after a minute to refresh the host list, just in case
    // it somehow didn't stay in sync from the pubsub.
    setTimeout(VR.Dash.getHostData, VR.Dash.Options.refreshInterval);
  }
};

VR.Dash.onHostData = function(data, stat, xhr) {
  // This function serves double duty.  When requesting data on an individual
  // host, this can be used as the AJAX callback.  When requesting data for all
  // hosts, you can loop over all of them and pass the data into this function
  // in order to get all its procs rendered.
  _.each(data.procs, VR.Dash.updateProcData);

  // cull any old procs
  VR.Dash.Apps.cull(data.host, data.time);
};

VR.Dash.getActiveHostData = function() {
  $.getJSON(VR.Urls.active_hosts, VR.Dash.onActiveHostData);
};

VR.Dash.onActiveHostData = function(data, stat, xhr) {
  _.each(data.hosts, function(el, idx, list) {
    VR.Dash.onHostData(el);
  });
};
