// JS file for the squad detail page.  Requires that vr.js, backbone.js, and
// goatee.js are already in the page.

(function() {

var Squad = VR.Squad = {};

Squad.init = function(squadname, container) {
  // container should be a jQuery-wrapped node.
  Squad.container = container;

  Squad.hosts = new VR.Models.HostList();

  var url = VR.Urls.getTasty('squads', squadname);
  $.getJSON(url, function(data, sts, xhr) {
      _.each(data.hosts, function(hostdata, idx, list) {
          var host = new VR.Models.Host(hostdata);
          var hostview = new VR.Views.Host(host);
          Squad.hosts.add(host);
          Squad.container.append(hostview.el);
      });
    }
  );

  // subscribe to events
  var procEvents = new EventSource(VR.Urls.procEvents);
  procEvents.onmessage = $.proxy(function(e) {
    var parsed = JSON.parse(e.data);
    // only respond to proc events for procs that are on hosts in this squad.
    var host = _.find(Squad.hosts.models, function(thisHost) {
      return thisHost.get('name') === parsed.host;
    });
    if (host) {
      if (parsed.event == 'PROCESS_GROUP_REMOVED') {
        host.procs.removeByData(parsed);
      } else {
        host.procs.getOrCreate(parsed);
      }
    }
  }, this);
};

})();
