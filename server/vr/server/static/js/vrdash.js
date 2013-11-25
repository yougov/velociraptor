// Depends on vr.js

// DASH //
VR.Dash = {};

VR.Dash.Options = {
    refreshInterval: 60000
};

VR.Dash.init = function(appsContainer, eventsContainer, eventsUrl, procEventsUrl) {

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
        VR.ProcMessages.trigger('updateproc:'+data.id, data);
      });
  });

  // if there are more pages, get those too
  if (data.next) {
    $.getJSON(data.next, VR.Dash.onHostList);
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
