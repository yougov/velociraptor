(function() {

var Swarm = VR.Swarm = {};

Swarm.init = function(swarmId, container) {
  // container should be a jQuery-wrapped node.
  Swarm.container = container;

  var url = VR.Urls.getTasty('swarms', swarmId);
  $.getJSON(url, function(data, sts, xhr) {
      
      Swarm.swarm = new VR.Models.Swarm(data);
      Swarm.swarm.procs.on('add', Swarm.addProcView);

      _.each(data.procs, function(pdata, idx, lst) {
        Swarm.swarm.procs.getOrCreate(pdata);
      });
    }
  );

  // bind proc event stream to handler
  var procEvents = new EventSource(VR.Urls.procEvents);
  procEvents.onmessage = $.proxy(function(e) {
    var parsed = JSON.parse(e.data);
    // only respond to proc events for procs that are part of this swarm.
    if (Swarm.swarm.procIsMine(parsed.name)) {
      if (parsed.event == 'PROCESS_GROUP_REMOVED') {
        Swarm.removeProc(parsed);
      } else {
        Swarm.swarm.procs.getOrCreate(parsed);
      }
    }
  }, this);
};

Swarm.addProcView = function(proc) {
  var view = new VR.Views.Proc(proc);
  Swarm.container.append(view.el);
};

Swarm.removeProc = function(data) {
  var proc = _.find(VR.Swarm.swarm.procs.models, function(p) {
    return p.id === data.id;
  });
  if (proc) {
    Swarm.swarm.procs.remove(proc);
  };
};
})();
