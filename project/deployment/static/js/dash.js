// Set up our namespacing. //
window.Dash = {
    Models: {},
    Collections: {},
    Views: {},
    Routers: {},
    Utilities: {},
    init: function(){
        this.mainElement = $('#dash-procs');
        Dash.Procs.initialize();
        Dash.Tasks.initialize();
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
        // if we can use a "-" to split a procname into 5 parts (old version) or 6
        // parts (new version), and the last one
        // is a port number, then guess that this is a proc that the dashboard
        // can control.
        var parts = proc.split('-');
        var len = parts.length;
        return (len === 5 || len === 6) && this.isNumber(parts[len-1]);       
    },

    reflow: function(host){
        Dash.mainElement.isotope('reLayout');
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

/////////////////// Dash Models  /////////////////// 

// DASH Procs Methods //
// It's not a model in the Backbone sense, but a structure that holds all
// methods related to what we've defined as a "proc". 

Dash.Procs = {
    // formerly dash.onHostData
    initialize: function(){

        $.getJSON('api/hosts/', Dash.Procs.loadHostViews);

        Dash.mainElement.isotope({
            itemSelector: '.host-status',
            layoutMode: 'masonry',
            animationOptions: {duration: 10}
        });

        // Load up Click Events for this Object
        Dash.mainElement.delegate('.host-status .label', 'click', Dash.Procs.onProcClick);
        Dash.mainElement.delegate('.host-actions .btn', 'click', Dash.Procs.onProcActionClick);
        $('body').delegate('.action-dialog .btn', 'click', Dash.Procs.onActionModalClick); 
        $('.procfilter').click(Dash.Procs.onFilterClick);
        $('.expandcollapse button').click(Dash.Procs.onExpandCollapseClick);

    },

    loadHostViews: function(data, txtStatus, xhr){
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
              var hostView = new Dash.Views.Host({collection: data});
              hostView.render();
            });
        });
    },

    onProcClick: function(){
        $(this).parent().toggleClass('host-expanded');
        Dash.Utilities.reflow();      
    },

    onProcActionClick: function() {
        var data = $(this).parents('.host-status').data();
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
            $('.host-status').addClass('host-expanded');
        } else if (action === 'collapse') {
            $('.host-status').removeClass('host-expanded');
        }
        Dash.Utilities.reflow();
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
        Dash.Utilities.reflow();
    }
};// end Dash.Procs


// DASH Tasks Methods //
Dash.Tasks = {
    mainElement: $('#dash-tasks'),
    taskDataQueue: '',

    initialize: function(){
        var that = this;
        
        // run immediately on init
        this.loadTaskData();
        // then setInterval to re-check every 4 seconds.
        setInterval(function(){
            that.loadTaskData();
        }, 4000);

    },

    loadTaskData: function(){
    // Since we're only chaining 2 requests, its not so bad, but we should consider:
    // http://spin.atomicobject.com/2011/08/24/chaining-jquery-ajax-calls/
    // if we need to expand it.
        var that = this;

        $.getJSON('/api/task/active/', function(data){
            var lastTask = (data.tasks.length -1);
            // check this ajax call with previous, if any.
            if (that.taskDataQueue == '' && data.tasks.length){
                // this is the first call if taskDataQueue is empty. Load up container.
                var taskView = new Dash.Views.Task();
                taskView.renderContainer();

                // update dataQueue with the most recent id. That should be all we need.
                that.taskDataQueue = data.tasks[lastTask].id;

                that.getActiveTaskInfo(data.tasks);

            } else if (data.tasks.length){
                // update with new id once we know the array has changed.
                that.taskDataQueue = data.tasks[lastTask].id;
                that.getActiveTaskInfo(data.tasks);
            } 
            // Clean house if there's no more tasks.
            if (data.tasks.length == 0 && that.taskDataQueue != '') {
                var taskView = new Dash.Views.Task();
                taskView.unRenderContainer();
            }
        });

    },

    getActiveTaskInfo: function(task){
        for(t=0; t < task.length; t++){
            var taskName = task[t].desc;

            $.getJSON('/api/task/'+ task[t].id, function(data){
                var taskData = {
                    name: taskName,
                    data: data
                }

                //make sure we haven't already loaded a block for this id:
                if($('.tasks-list').find('.'+data.id).length < 1){
                    var taskView = new Dash.Views.Task();
                    taskView.render(taskData);
                }
            });
        }

    }

};// end Dash.Tasks


/////////////////// Dash Views /////////////////// 
// http://documentcloud.github.com/backbone/#View

// The Host View //
// This is the block that represents each of our host blocks that get rendered. //
Dash.Views.Host = Backbone.View.extend({
    el: '.host-status',
    template: '#host-procs-tmpl',

    render: function(){
        var element = $(this.template).goatee(this.collection);
        Dash.mainElement.isotope('insert', element);
    }

}); // end Dash.Views.Host

// The Task View //
Dash.Views.Task = Backbone.View.extend({
    parentEl: '.tasks-list',
    template: '#tasks-partial',

    render: function(data){
        var element = $(this.template).goatee(data);
        $(this.parentEl).isotope('insert', element);
    },

    renderContainer: function(){
    // Since the guts around the tasks are also dynamically added, we'll make them a 
    // part of the Task view, but not rendered in a loop like the actual tasks.
    // If I could figure out how goatee uses template partials, this could be
    // written with that. >.>

        // a lil' bit of bootstrap fanciness...
        $('.proc-column').addClass('span8');
        $('.tasks-column').addClass('span4');
        Dash.Utilities.reflow();
    
        // the actual rendering:
        $('#dash-tasks').html($('#tasks-tmpl').html()).show();
        $('.tasks-list').isotope({
            itemSelector: '.task-status',
            layoutMode: 'masonry',
            animationOptions: {duration: 10}
        });
    },

    unRenderContainer: function(){
        // a lil' bit of bootstrap fanciness...
        $('.proc-column').removeClass('span8');
        $('.tasks-column').removeClass('span4');
        Dash.Utilities.reflow();

        $('#dash-tasks').html('');
    }

});

