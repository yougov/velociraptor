
(function() {

var Swarm = VR.Swarm = {};

Swarm.init = function(swarmId, container) {
  // container should be a jQuery-wrapped node.
  Swarm.container = container;

  var vContainer, hContainer, url = VR.Urls.getTasty('swarms', swarmId);
  $.getJSON(url, function(data, sts, xhr) {
      Swarm.swarm = new VR.Models.Swarm(data);
      Swarm.swarm.on('addproc', Swarm.addProcView);
      _.each(data.procs, function(pdata, idx, lst) {
        var versionId = 'version_'+pdata.version.replace(/\./g,'_');
        var hostId = versionId+'_host_'+pdata.host.replace(/\./g,'_');
        vContainer = '<table class="table table-striped table-bordered" id="'+versionId+'"><thead><tr><th colspan="2">Version: '+pdata.version+'</th></tr></table>';

        if($('#'+versionId).length == 0)
          Swarm.container.append(vContainer);

        hContainer = '<tr id="'+hostId+'"><td style="text-align: right;vertical-align: middle"><span>'+pdata.host+'</span></td><td></td></tr>';

        if($('#'+hostId).length == 0)
          $('#'+versionId).append(hContainer);

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
  var hostname = proc.get('host');
  var version = proc.get('version');

  var versionId = 'version_'+version.replace(/\./g,'_');
  var hostId = versionId+'_host_'+hostname.replace(/\./g,'_');

  $('#'+hostId+' td:last-child').append(view.el);
};

Swarm.checkPoolName = function(form) {
  // intercept the Swarm form's submit event, in order to warn about
  // hijacking a routing pool
  $(form).on('submit', function (e) {
    var currentPool = $('#id_pool').val();
    var currentBalancer = $('#id_balancer').val();
    var poolSearchUrl = VR.Urls.getTasty('swarms') + '?pool=' + currentPool;
    var hijackedPoolOwners = [];

    // normalize the value of the current balancer
    if (currentBalancer == '') {
      currentBalancer = 'default';
    }

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
            if (currentResourceUri != element.resource_uri
                && currentBalancer == element.balancer) {
              hijackedPoolOwners.push({
                name: element.shortname
                      + ' (balancer=' + element.balancer + ')'
              });
            }
          });
        }
      },
      async: false
    });

    if (hijackedPoolOwners.length) {
      // show the pool hijacking warning dialog
      var warningModal = new VR.Views.SwarmWarningModal({
          current_pool: currentPool,
          swarms: hijackedPoolOwners
        },
        function () {
          // this callback is fired when the 'Proceed' button gets clicked
          form.submit();
        }
      );
      warningModal.show();

      // prevent the normal form submit. The 'proceed' callback above takes
      // care of the form's submission.
      return false;
    }

    return true;
  });
};

})();
