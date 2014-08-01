(function() {

var Swarm = VR.Swarm = {};

Swarm.init = function(swarmId, container) {
  // container should be a jQuery-wrapped node.
  Swarm.container = container;

  var url = VR.Urls.getTasty('swarms', swarmId);
  $.getJSON(url, function(data, sts, xhr) {
      Swarm.swarm = new VR.Models.Swarm(data);
      var compiled_config = Swarm.swarm.get('compiled_config');
      var compiled_env = Swarm.swarm.get('compiled_env');
      $('#compiled_config').text(JSON.stringify(compiled_config, null, '\t'));
      $('#compiled_env').text(JSON.stringify(compiled_env, null, '\t'));
      Swarm.swarm.on('addproc', Swarm.addProcView);
      _.each(data.procs, function(pdata, idx, lst) {
        Swarm.swarm.onProcData(null, pdata);
      });

    }
  );

  // check for pool name hijacking on form submit.
  var form = findForm(container.get(0));
  Swarm.checkPoolName(form);

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

Swarm.checkPoolName = function(form) {
  // intercept the Swarm form's submit event, in order to warn about
  // hijacking a routing pool
  $(form).on('submit', function (e) {
    var currentPool = $('#id_pool').val();
    var poolSearchUrl = VR.Urls.getTasty('swarms') + '?pool=' + currentPool;
    var hijackedPoolOwners = [];

    // synchronous AJAX call to determine if we are about to hijack a pool
    $.ajax({
      type: 'GET',
      url: poolSearchUrl,
      dataType: 'json',
      success: function(data, sts, xhr) {
        if (data.meta.total_count > 0) {
          var currentResourceUri = null;
          if (_.has(Swarm, 'swarm')) {
            currentResourceUri = Swarm.swarm.get('resource_uri');
          }
          _.each(data.objects, function(element, index, list) {
            if (currentResourceUri != element.resource_uri) {
              hijackedPoolOwners.push(element.shortname);
            }
          });
        }
      },
      async: false
    });

    if (hijackedPoolOwners.length) {
      var confirmationMsg = "WARNING!\n\n" +
      "You're about to hijack pool name '" + currentPool + "'. " +
      "It is currently being used by: " + hijackedPoolOwners.join(',') +
      "\n\nIf you are unsure about this, click cancel immediately, " +
      "as unintentionally taking over the pool name of some other Swarm " +
      "may lead to disastrous scenarios.\n\n" +
      "Are you sure you want to proceed?";
      return confirm(confirmationMsg);
    }

    return true;
  });
};

})();
