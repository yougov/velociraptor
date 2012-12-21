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

  // bind host change event stream to handler
  var procEvents = new EventSource(procEventsUrl || VR.Urls.procEvents);
  procEvents.onmessage = $.proxy(function(e) {
      var parsed = JSON.parse(e.data);
      if (parsed.event == 'PROCESS_GROUP_REMOVED') {
         VR.Messages.trigger('remove:'+parsed.id);
         VR.Dash.removeProc(parsed.id);
      } else {
        VR.Dash.updateProcData(parsed);
      }
      }, this
  );

  // bind proc change event stream to handler 
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
        _.each(el.procs, VR.Dash.updateProcData);
    });
   setTimeout(VR.Dash.getHostData, VR.Dash.Options.refreshInterval);
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

VR.Dash.updateProcData = function(data) {
    app = VR.Dash.Apps.getOrCreate(data.app_name);
    VR.Dash.Apps.add(app);

    var swarmname = [data.recipe_name, data.proc_name].join('-');
    var s = app.swarms.getOrCreate(swarmname);
    var p = s.procs.getOrCreate(data);
};

