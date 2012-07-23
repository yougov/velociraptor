VR.Squad = {};

VR.Squad.init = function() {
    $('#btn-add-host').click(function() {
        $('#add-host-tmpl').goatee().modal();
    });

    _.each($('.hostgrid .hostblock'), function(block) {
        var hostname = $(block).data('hostname');
        // do an ajax request to get the procs 
        $.getJSON('/api/hosts/' + hostname + '/procs/', function(data, sts, xhr) {
            VR.Squad.renderProcs(block, data);
        });
    });
};

VR.Squad.renderProcs = function(hostblock, hostdata) {
    var grid = $(hostblock).children('.procgrid');
    grid.html($('#procgrid-tmpl').goatee(hostdata));
    // bind data to the children
    _.each(hostdata.procs, function(el) {
        var procbox = $(hostblock).find('#proc-' + el.jsname);
        procbox.data(el);
    });
};
