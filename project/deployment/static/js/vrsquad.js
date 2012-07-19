VR.Squad = {};

VR.Squad.init = function() {
    $('#btn-add-host').click(function() {
        $('#add-host-tmpl').goatee().modal();
    });

    _.each($('.hostgrid .hostblock'), function(block) {
        var hostname = $(block).data('hostname');
        // do an ajax request to get the states
        $.getJSON('/api/hosts/' + hostname + '/procs/', function(data, sts, xhr) {
            VR.Squad.renderProcs(block, data);
        });
    });
};

VR.Squad.renderProcs = function(hostblock, hostdata) {
    // add a clean ID for each proc obj
    _.each(hostdata.states, function(el) {
      el.id = el.name.replace(/\./g, "");
    });
    var grid = $(hostblock).children('.procgrid');
    grid.html($('#procgrid-tmpl').goatee(hostdata));
    // bind data to the children
    _.each(hostdata.states, function(el) {
        var procbox = $(hostblock).find('#proc-' + el.id);
        procbox.data(el);
    });
};
