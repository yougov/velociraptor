// Set up our namespacing. //
window.Dash = {
    Models: {},
    Collections: {},
    Views: {},
    Routers: {},
    Utilities: {},
    init: function(){
        this.mainElement = $('#dash-procs');
        new Dash.Models.Hosts;
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
    },

    doHostAction: function(host, proc, action, method, callback) {
        if (method === undefined) {
            method = 'POST';
        }
        if (callback === undefined) {
            callback = this.onActionResponse;
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

    onActionResponse: function(data, txtStatus, xhr) {
        // find the proc
        // update its class so it changes colors
        var proc = $('#' + Dash.Utilities.createID(data.host, data.name));
        Dash.Utilities.clearStatus(proc);
        proc.addClass('status-' + data.statename);
    }

}; // end Utilities

/////////////////// Dash Models  /////////////////// 

// DASH Hosts Methods //
// It's not a model in the traditional sense, but a structure that holds all methods related
// to what we've defined as a "host". 

Dash.Models.Hosts = Backbone.Model.extend({

    // formerly dash.onHostData
    initialize: function(){

        $.getJSON('api/hosts/', this.loadHostViews);

        Dash.mainElement.isotope({
            itemSelector: '.host-status',
            layoutMode: 'masonry',
            animationOptions: {duration: 10}
        });

        // Load up Click Events for this Object
        // Because of how we're using isotope, the traditional Backbone
        // events binding is not available to us.
        this.clickEvents();

    },

    loadHostViews: function(data, txtStatus, xhr){
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

    clickEvents: function(){
        Dash.mainElement.delegate('.host-status .label', 'click', this.onHostClick);
        Dash.mainElement.delegate('.host-actions .btn', 'click', this.onHostActionClick);
        $('.procfilter').click(this.onFilterClick);
        $('.expandcollapse button').click(this.onExpandCollapseClick);
    },

    onHostClick: function(){
        $(this).parent().toggleClass('host-expanded');
        Dash.Utilities.reflow();      
    },

    onHostActionClick: function() {
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
            Dash.Utilities.doHostAction(data.host, data.proc, data.action);
        }
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
    }


});// end Dash.Models.Hosts


// DASH Tasks Methods //
Dash.Models.Tasks = Backbone.Models.extend({

    initialize: function(){

    },

    clickEvents: function(){

    }

});// end Dash.Models.Tasks


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
    parentEl: '#dash-tasks',
    template: '#tasks-tmpl',

    render: function(){
        $(this.parentEl).append($(this.template).goatee(this.collection));
    }
});

