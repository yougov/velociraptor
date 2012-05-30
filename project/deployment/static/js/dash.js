// Set up our namespacing. //
window.Dash = {
    init: function(){
        this.mainElement = $('#dash-procs');
        Dash.Procs.init();
        Dash.Tasks.init();
    }
};

//// Fire in the hole! ////
$(document).ready(function(){
    Dash.init();
});


///////////////////  Dash Utilities  ///////////////////
// Generic-use things that didn't seem to fit in a specific model. 

Dash.Utilities = {
    isNumber: function(n){
       return !isNaN(parseFloat(n)) && isFinite(n);   
    },

    procIsOurs: function(proc){
        // if we can use a "-" to split a procname into 6 parts, and the last
        // one is a port number, then guess that this is a proc that the
        // dashboard can control.
        var parts = proc.split('-');
        var len = parts.length;
        return len === 6 && this.isNumber(parts[len-1]);       
    },

    cleanName: function(host){
        return host.replace(/\./g, "");
    },

    createID: function(host, proc){
        return host.replace(/\./g, "") + proc.replace(/\./g, "");
    },

    clearStatus: function(proc) {
        _.each(['RUNNING', 'STOPPED', 'FATAL', 'BACKOFF', 'STARTING'], function(el, idx, lst) {
            proc.removeClass('status-' + el);
        });
    }
}; // end Utilities

// DASH Procs Methods //

Dash.Procs = {
    // formerly dash.onHostData
    init: function(){

        $.getJSON('api/hosts/', Dash.Procs.getHostProcs);

        Dash.mainElement.isotope({
            itemSelector: '.proc-status',
            layoutMode: 'masonry',
            animationOptions: {duration: 10}
        });

        // Load up Click Events for this Object
        Dash.mainElement.delegate('.proc-status .label', 'click', Dash.Procs.onProcClick);
        Dash.mainElement.delegate('.proc-actions .btn', 'click', Dash.Procs.onProcActionClick);
        $('body').delegate('.action-dialog .btn', 'click', Dash.Procs.onActionModalClick); 
        $('.procfilter').click(Dash.Procs.onFilterClick);
        $('.expandcollapse button').click(Dash.Procs.onExpandCollapseClick);

    },

    getHostProcs: function(data, txtStatus, xhr){
        // note - scope is inside getJSON call! 
        _.each(data.hosts, function(el, idx, lst) {
            // for each host in the list, make a request for the procs and draw
            // a box for each.
            $.getJSON('/api/hosts/' + el + '/procs/', function(data, txtStatus, xhr) {
              _.each(data.states, function(el, idx, lst) {
                  el.host = data.host;
                  // strip dots from the host so it can be used as a
                  // classname
                  el.hostclass = Dash.Utilities.cleanName(data.host);
                  el.appclass = el.name.split('-')[0];
                  el.destroyable = Dash.Utilities.procIsOurs(el.name); 
                  el.shortname = el.name.split('-')[0].split('_')[0];
                  // each proc gets a unique id of host + procname, with illegal
                  // chars stripped out.
                  el.procid = Dash.Utilities.createID(el.host, el.name);
              });

              // Load up our host object based on the View we made.
              // 'collection' is a Backbone.View data storage object already set for us.
              var element = $('#host-procs-tmpl').goatee(data);
              Dash.mainElement.isotope('insert', element);
            });
        });
    },

    onProcClick: function(){
        $(this).parent().toggleClass('host-expanded');
        Dash.Procs.reflow();      
    },

    onProcActionClick: function() {
        var data = $(this).parents('.proc-status').data();
        // action buttons will have their action stored in the 'rel attribute.
        data.action = $(this).attr('rel');
        if (data.action === 'destroy') {
            // show a confirmation dialog before doing proc deletions
            popup = $('#proc-modal-tmpl').goatee(data);
            popup.data(data);
            $(popup).modal();
        } else {
            // do stops and starts automatically
            Dash.Procs.doProcAction(data.host, data.proc, data.action);
        }
    },

    onActionResponse: function(data, txtStatus, xhr) {
        // find the proc
        // update its class so it changes colors
        var proc = $('#' + Dash.Utilities.createID(data.host, data.name));
        Dash.Utilities.clearStatus(proc);
        proc.addClass('status-' + data.statename);
    },

    onExpandCollapseClick: function() {
        var action = $(this).attr('rel');
        if (action === 'expand') {
            $('.proc-status').addClass('host-expanded');
        } else if (action === 'collapse') {
            $('.proc-status').removeClass('host-expanded');
        }
        Dash.Procs.reflow();
    },

    onFilterClick: function() {
      var selector = $(this).attr('data-filter');
      $(this).button('toggle');
      // hide the host dropdown
      $('.hostlist, .applist').removeClass('open');
      Dash.mainElement.isotope({ filter: selector });
      return false;
    },

    onActionModalClick: function() {
      // this handler is bound using $().delegate on init.
        var btn = $(this).attr('rel');
        var modal = $(this).parents('.modal');
        if (btn === 'confirm') {
            // get the data, and make an ajax request with it.
            var data = modal.data();
            if (data.action === 'destroy') {
                Dash.Procs.destroyProc(data.host, data.proc);
            } else {
                Dash.Procs.doProcAction(data.host, data.proc, data.action);
            }
        } 
        // no matter what button we got, hide and destroy the modal.
        modal.modal('hide');
        modal.remove();
    },

    doProcAction: function(host, proc, action, method, callback) {
        if (method === undefined) {
            method = 'POST';
        }
        if (callback === undefined) {
            callback = Dash.Procs.onActionResponse;
        }
        

        var url = '/api/hosts/' + host + '/procs/' + proc + '/';
        data = {host:host,proc:proc,action:action};
        $.ajax(url, {
            data: data,
            dataType: 'json',
            type: method,
            success: callback 
        });
    },

    destroyProc: function(host, proc) {
        return Dash.Procs.doProcAction(host, proc, 'destroy', 'DELETE', Dash.Procs.onProcDestroy);
    },

    onProcDestroy: function(data, txtStatus, xhr) {
        // callback for deleting a proc from the DOM when server lets us know it's
        // been destroyed.
        $('#' + Dash.Utilities.createID(data.host, data.name)).remove();
        Dash.Procs.reflow();
    },

    reflow: function(host){
        Dash.mainElement.isotope('reLayout');
    }

};// end Dash.Procs


// DASH Tasks Methods //
Dash.Tasks = {
    mainElement: $('#dash-tasks'),
    taskDataQueue: '',

    init: function(){
        var that = this;
        
        // run immediately on init
        this.loadTaskData();
        // then setInterval to re-check every 4 seconds.
        setInterval(function(){
            that.loadTaskData();
        }, 4000);

    },

    loadTaskData: function(){
        var that = this;

        $.getJSON('/api/task/active/', function(data){
            if (data.tasks.length) {
                $('.proc-column').addClass('span8');
                $('.tasks-column').addClass('span4');
                Dash.Procs.reflow();
                $('#dash-tasks').html($('#tasks-tmpl').goatee(data));
            } else {
                // unRender container
                $('.proc-column').removeClass('span8');
                $('.tasks-column').removeClass('span4');
                Dash.Procs.reflow();
                $('#dash-tasks').html('');
            }
        });
    }
};// end Dash.Tasks
