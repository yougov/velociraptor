// JS file for the squad detail page.  Requires that vr.js, backbone.js, and
// goatee.js are already in the page.

(function() {

var Squad = VR.Squad = {};

Squad.init = function(squadname, container) {
  // container should be a jQuery-wrapped node.
  this.container = container;

  this.hosts = new VR.Models.HostList();

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
};

})();
