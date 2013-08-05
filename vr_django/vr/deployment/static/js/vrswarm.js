(function() {

var Swarm = VR.Swarm = {};

Swarm.init = function(swarmId, container) {
  // container should be a jQuery-wrapped node.
  Swarm.container = container;

  var url = VR.Urls.getTasty('swarms', swarmId);
  $.getJSON(url, function(data, sts, xhr) {
      Swarm.swarm = new VR.Models.Swarm(data);
      var compiled_config = Swarm.swarm.get('compiled_config');
      $('#compiled_config').text(JSON.stringify(compiled_config, null, '\t'));
      Swarm.swarm.on('addproc', Swarm.addProcView);
      _.each(data.procs, function(pdata, idx, lst) {
        Swarm.swarm.onProcData(null, pdata);
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
        VR.ProcMessages.trigger('destroyproc:'+parsed.id, parsed);
      } else {
        Swarm.swarm.onProcData(e, parsed);
        VR.ProcMessages.trigger('updateproc:'+parsed.id, parsed);
      }
    }
  }, this);
};

Swarm.addProcView = function(proc) {
  var view = new VR.Views.Proc(proc);
  Swarm.container.append(view.el);
};

})();
