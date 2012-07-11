// Set up our namespacing. //
window.Dash = {
    init: function(){
        Dash.Procs.init();
        Dash.Tasks.init();
    }
};

function IsNumeric(input)
{
    return (input - 0) == input && input.length > 0;
}

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
        Dash.Procs.el = $('#dash-procs');

        $.getJSON('api/hosts/', Dash.Procs.getHostProcs);

        Dash.Procs.el.isotope({
            itemSelector: '.proc-status',
            layoutMode: 'masonry',
            animationOptions: {duration: 10}
        });

        // Load up Click Events for this Object
        Dash.Procs.el.delegate('.proc-status .label', 'click', Dash.Procs.onProcClick);
        Dash.Procs.el.delegate('.proc-actions .btn', 'click', Dash.Procs.onProcActionClick);
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
                  var splitresult = el.name.split('-');
                  el.hostclass = Dash.Utilities.cleanName(data.host);
                  el.appclass = splitresult[0];
                  el.destroyable = Dash.Utilities.procIsOurs(el.name);
                  el.shortname = splitresult[0];
                  if(splitresult.length > 4) {
                    if(IsNumeric(el.name.split('-')[5])){
                      el.port = el.name.split('-')[5];
                    }else{
                      el.port = false;
                    }
                  }else{
                    el.port = false;
                  }
                  // each proc gets a unique id of host + procname, with illegal
                  // chars stripped out.
                  el.procid = Dash.Utilities.createID(el.host, el.name);
              });

              var element = $('#host-procs-tmpl').goatee(data);
              Dash.Procs.el.isotope('insert', element);
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
            var popup = $('#proc-modal-tmpl').goatee(data);
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
      Dash.Procs.el.isotope({ filter: selector });
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
        Dash.Procs.el.isotope('reLayout');
    }

};// end Dash.Procs


// DASH Tasks Methods //
Dash.Tasks = {
    taskDataQueue: '',

    init: function(){
        Dash.Tasks.tmpl = $('#task-tmpl');
        Dash.Tasks.el = $('#tasks-list');

        Dash.Tasks.el.delegate('.task-wrapper', 'click', Dash.Tasks.onTaskClick);

        Dash.Tasks.getTaskData();
        // then setInterval to re-check every 4 seconds.
        setInterval(function(){
            Dash.Tasks.getTaskData();
        }, 4000);

    },

    getTaskData: function(){
        var that = this;

        $.getJSON('/api/task/', function(data){
            // the data comes back with the most recent first, but it's
            // actually simpler to do most recent last and always use
            // $().prepend.  So reverse it.
            data.tasks.reverse();
            _.each(data.tasks, Dash.Tasks.doItem);

            // Now remove any tasks that are in the DOM but not in the data.
            var ids = _.map(data.tasks, function(task) {return 'task-' + task.task_id;});
            _.each($('.task-wrapper'), function(el, idx, lst) {
                el = $(el);
                if (!_.include(ids, el.attr('id'))) {
                    el.remove();
                }
            });
        });
    },

    // doItem should be called for each task returned from the API, each time.
    // It will check whether the item already exists in the list, and only add
    // it if necessary.
    doItem: function(taskdata, idx, lst) {
        if (_.isNull(taskdata.name)) {
            taskdata.shortname = taskdata.task_id;
        } else {
            taskdata.shortname = taskdata.name.split('.').pop();
        }

        // Set a nicer date for humans.  Assumes all browsers we care about can
        // accept an iso datetime on Date init.
        var date = new Date(taskdata.tstamp);
        taskdata.prettydate = date.toString();

        var task = $('#task-' + taskdata.task_id);
        if (task.length === 0) {
            // add new one
            task = Dash.Tasks.tmpl.goatee(taskdata);
            Dash.Tasks.el.prepend(task);
        } else {
            // update existing one.
            if (!_.isEqual(task.data('taskdata'), taskdata)) {
                var newtask = Dash.Tasks.tmpl.goatee(taskdata);
                // update existing item with contents of new one.
                task.html(newtask.html());
            }
        }

        // remember taskdata for comparing later.  Also for rendering details
        // in a modal.
        task.data('taskdata', taskdata);
    },

    onTaskClick: function(ev) {
        var popup = $('#task-modal-tmpl').goatee($(this).data('taskdata'));
        $(popup).modal();
    }
};// end Dash.Tasks
