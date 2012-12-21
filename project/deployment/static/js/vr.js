// Welcome to Velociraptor's Javascript UI code.  Most everything below is
// built out of Backbone models and views.

// This VR object is the only thing that Velociraptor puts in the global
// namespace.  All our other code should be nested under here.
VR = {};
VR.Views = {};

// VR.Urls contains data and functions for getting urls to the Velociraptor
// API.  There are three main parts to Velociraptor's API:
//
// 1 - The RESTful API over the Django models.  This uses the Tastypie API
// framework, which provides for very consistent URLs.  To get a URL to a
// Tastypie-provided resource, call VR.Urls.getTasty.
//
// 2 - The quasi-RESTful API for procs.  I say 'quasi' because I don't really
// know how to express 'restart' restfully, and also because some state changes
// (like proc deletion) are actually offloaded to Celery workers and handled
// asyncronously.  So your DELETE will return instantly but the resource will
// still exist until the worker has finished.
//
// 3 - Server-Sent-Event streams.  These let the Velociraptor web processes
// push messages out to the browser when something happens in the system.

VR.Urls = {

  // All Tastypie-provided resources are within this path.
  root: '/api/v1/',

  getTasty: function (resource, name) {
      // A helper for generating urls to talk to the VR Tastypie API.  This
      // seems the least verbose way of doing this.
      //
      // 'resource' is a name of a Tastypie-provided resource.  You'll most
      // often be passing 'apps', 'hosts', 'squads', or 'swarms' as the
      // resource.  The full list of available resources can be seen at the api
      // root url.
      //
      // 'name' is the key by which instances of that resource are identified.
      // For hosts, it's the hostname.  For many resources, it's the integer ID
      // used in the Django DB.  Click around the JSON API to see which you
      // need to provide in a given circumstance.

      if (name) {
          // we were asked for a particular instance of a resource.  Build
          // the whole URL.
          return this.root + resource + '/' + name + '/';
      } else {
          // no instance name passed in, so assume they're asking for the
          // list URL.
          return this.root + resource + '/';
      }
  },
  getProc: function (hostname, procname) {
      // unlike the tastypie resources, the procs API is normal Django views
      // nested inside the Tastypie API, so they have a different url
      // pattern.
      return VR.Urls.getTasty('hosts', hostname) + 'procs/' + procname + '/';
  }
  // XXX: Additional routes for event streams are added to VR.Urls in
  // base.html, where we can pull URLs out of Django by using {% url ... %}.
};

// All proc objects should subscribe to messages from this object, in the form
// "change:<proc id>", and update themselves when such a message comes in.
// This saves having to drill down through collections or the DOM later if data
// comes in on an API or event stream.
VR.Messages = {};
_.extend(VR.Messages, Backbone.Events);

// All Backbone models should be stored on VR.Models.
VR.Models = {};

// Base model for all models that talk to the Tastypie API. This includes
// hosts, squads, swarms, etc. (but not procs and events)
VR.Models.Tasty = Backbone.Model.extend({
    url: function() {
      return this.attributes.resource_uri;
    }
});

VR.Models.Proc = Backbone.Model.extend({
    initialize: function() {
      this.on('change', this.updateUrl);
      VR.Messages.on('change:' + this.id, this.set, this);
      VR.Messages.on('remove:' + this.id, this.onRemoveMsg, this);
    },
    url: function() {
      return VR.Urls.getProc(this.get('host'), this.get('name'));
    },
    onRemoveMsg: function(a, b, c) {
      console.log('onRemoveMsg', a, b, c);
    }
});

// TODO: Make ProcList subscribe to removal events somehow.
VR.Models.ProcList = Backbone.Collection.extend({
    model: VR.Models.Proc,

    getOrCreate: function(data) {
      // if proc with id is in collection, return it.
      var proc = _.find(this.models, function(proc) {
          return proc.id == data.id;
        });
      if (proc) {
        proc.set(data);
        return proc;
      }
      // else create, add, and return.
      proc = new VR.Models.Proc(data);
      this.add(proc);
      return proc;
    },

    cull: function(host, cutoff) {
      // given a cutoff timestamp string, look at .time on each proc in the
      // collection.  If it's older than the cutoff, then kill it.

      // build a separate list of procs to remove because otherwise, we're
      // modifying the same list that we're iterating over, which throws things
      // off.
      var stale = _.filter(this.models, function(proc) {
          return proc.get('host') === host && proc.get('now') < cutoff;
      });
      _.each(stale, function(proc) {this.remove(proc);}, this);
    }
});

VR.Models.Host = VR.Models.Tasty.extend({
  initialize: function(data) {
    this.procs = new VR.Models.ProcList();

    // if there are procs in the data, put them in the collection.
    _.each(data.procs, function(el, idx, list) {
      var p = new VR.Models.Proc(el);
      this.procs.add(p);
    }, this);
  }
});

VR.Models.HostList = Backbone.Collection.extend({
  model: VR.Models.Host
});


VR.Models.Swarm = VR.Models.Tasty.extend({
    initialize: function() {
      this.procs = new VR.Models.ProcList();
    }
});

VR.Models.SwarmList = Backbone.Collection.extend({
    model: VR.Models.Swarm,

    comparator: function(swarm) {
      return swarm.id;
    },
    getOrCreate: function(id) {
      // if swarm with id is in collection, return it.
      var swarm = _.find(this.models, function(swarm) {
          return swarm.id == id;
        });
      if (swarm) {
        return swarm;
      }
      // else create, add, and return.
      swarm = new VR.Models.Swarm({id: id});
      this.add(swarm);
      return swarm;
    },
    cull: function(host, cutoff) {
      // call cull on each proclist on each swarm in the collection.
      _.each(this.models, function(swarm) {
          swarm.procs.cull(host, cutoff);
        }, this);
      // if there are any swarms wth no procs, remove them.
      var empty_swarms = _.filter(this.models, function(swarm) {
          return swarm.procs.models.length === 0;
        }, this);
      _.each(empty_swarms, function(swarm) {this.remove(swarm);}, this);
    }
});

VR.Models.App = VR.Models.Tasty.extend({
    initialize: function() {
      this.swarms = new VR.Models.SwarmList();
    }
});

VR.Models.AppList = Backbone.Collection.extend({
    model: VR.Models.App,

    comparator: function(app) {
      return app.id;
    },

    getOrCreate: function(id) {
      // if app with id is in collection, return it.
      var app = _.find(this.models, function(app) {
          return app.id == id;
        });
      if (app) {
        return app;
      }
      // else create, add, and return.
      app = new VR.Models.App({id: id, "class": "appbox"});
      this.add(app);
      return app;
    },
    cull: function(host, cutoff) {
      // call cull on each swarmlist on each swarm in the collection.
      _.each(this.models, function(app) {
          app.swarms.cull(host, cutoff);
        }, this);
      // if there are any apps wth no swarms, remove them.
      var empty_apps = _.filter(this.models, function(app) {
          return app.swarms.models.length === 0;
        }, this);
      _.each(empty_apps, function(app) {this.remove(app);}, this);
    }
});

VR.Views.Apps = Backbone.View.extend({
  initialize: function(appList, container) {
    this.apps = appList;
    this.container = container;
    this.apps.on('add', this.onAdd, this);
    _.each(this.apps.models, function(el, idx, list) {
        this.onAdd(el);
    }, this);
  },

  onAdd: function(app) {
    // draw the new app on the page
    var v = new VR.Views.App(app);
    v.render();
    var inserted = false;
    // loop until we see one later than us, alphabetically, and insert
    // there.
    _.each(this.container.find('.approw'), function(row) {
        var title = $(row).find('.apptitle').text();
        if (!inserted && title > app.id) {
            $(row).before(v.el);
            inserted = true;
        } 
    });

    // If still not inserted, just append to container
    if (!inserted) {
        this.container.append(v.el);
    }
  }
});

// VIEWS

VR.Views.Proc = Backbone.View.extend({
    el: '<div class="procview"></div>',
    initialize: function(proc, template, modalTemplate) {
      this.proc = proc;

      // If you don't pass templates, we'll use the ones on VR.Templates.
      this.template = template || VR.Templates.Proc;
      this.modalTemplate = modalTemplate || VR.Templates.ProcModal;

      this.proc.on('change', this.render, this);
      this.proc.on('destroy', this.onRemove, this);
      this.proc.on('remove', this.onRemove, this);
      this.render();
    },
    render: function() {
      this.$el.html(this.template.goatee(this.proc.toJSON()));
    },

    events: {
      'click': 'onClick'
    },

    onClick: function(ev) {
      if (!this.modal) {
        this.modal = new VR.Views.ProcModal(this.proc);   
      }

      this.modal.show();
    },

    onRemove: function() {
      this.$el.remove();
    }
});


VR.Views.ProcModal = Backbone.View.extend({
    initialize: function(proc, template) {
      this.proc = proc;
      this.template = template || VR.Templates.ProcModal;
      this.proc.on('change', this.render, this);
      this.proc.on('destroy', this.onProcDestroy, this);
      this.proc.on('remove', this.onProcDestroy, this);
    },
    render: function() {
      this.$el.html(this.template.goatee(this.proc.toJSON()));
    },
    events: {
      'click .proc-start': 'onStartBtn',
      'click .proc-stop': 'onStopBtn',
      'click .proc-restart': 'onRestartBtn',
      'click .proc-destroy': 'onDestroyBtn'
    },
    show: function() {
      this.render();
      this.$el.modal('show');
    },
    onStartBtn: function(ev) {
      this.doAction('start');
    },
    onStopBtn: function(ev) {
      this.doAction('stop');
    },
    onRestartBtn: function(ev) {
      this.doAction('restart');
    },
    doAction: function(action) {
      var proc = this.proc;
      $.post(proc.url(), {'action': action}, function(data, stat, xhr) {
          proc.set(data);
        });
    },
    onDestroyBtn: function(ev) {
      this.proc.destroy();
    },
    onProcDestroy: function() {
      this.$el.modal('hide');
      this.$el.remove();
    }
});


VR.Views.Host = Backbone.View.extend({
    el: '<div class="hostview"></div>',
    initialize: function(host, template) {
      this.host = host;
      this.template = template || VR.Templates.Host;
      // when a new proc is added, make sure it gets rendered in here
      this.host.procs.on('add', this.renderProc, this);
      this.host.on('remove', this.onRemove, this);

      this.render();
    },

    renderProc: function(proc) {
      var pv = new VR.Views.Proc(proc, VR.Templates.Proc);
      this.grid.append(pv.el);
    },

    render: function() {
      this.$el.html(this.template.goatee(this.host.attributes));
      this.grid = this.$el.find('.procgrid');
      this.host.procs.each(this.renderProc, this);
    },

    onRemove: function() {
      this.$el.remove();
    }
});

VR.Views.Swarm = Backbone.View.extend({
    el: '<div class="swarmbox"></div>',
    initialize: function(swarm, template) {
      this.swarm = swarm;
      this.template = template || VR.Templates.Swarm;
      // when a new proc is added, make sure it gets rendered in here
      this.swarm.procs.on('add', this.procAdded, this);
      this.swarm.on('remove', this.onRemove, this);
    },

    procAdded: function(proc) {
      var pv = new VR.Views.Proc(proc);
      pv.render();
      this.$el.find('.procgrid').append(pv.el);
    },

    render: function() {
      this.$el.html(this.template.goatee(this.swarm.toJSON()));
    },

    onRemove: function() {
      this.$el.remove();
    }
});


VR.Views.App = Backbone.View.extend({
    el: '<tr class="approw"></tr>',
    initialize: function(app, template) {
      this.app = app;
      this.template = template || VR.Templates.App;
      this.app.swarms.on('add', this.swarmAdded, this);
      this.app.on('remove', this.onRemove, this);
    },

    swarmAdded: function(swarm) {
      var sv = new VR.Views.Swarm(swarm);
      sv.render();
      this.$el.find('.proccell').append(sv.el);
    },

    events: {
      'click .apptitle': 'toggleBigness'
    },

    toggleBigness: function() {
        this.$el.toggleClass('biggened');
    },

    render: function() {
      this.$el.html(this.template.goatee(this.app.toJSON()));
    },

    onRemove: function() {
      this.$el.remove();
    }
});

// Events
// For displaying stuff that's going on all over the system.

// Since they're just for display, the Event model itself has just data.  No
// behavior.
VR.Models.Event = Backbone.Model.extend({});

VR.Models.Events = Backbone.Collection.extend({
    model: VR.Models.Event,

    initialize: function(maxlength) {
        // By default, show only 100 messages.  We don't want the message pane
        // to grow forever on the dashboard, or in memory.
        this.maxlength = maxlength || 100;
        this.on('add', this.trim, this);
    },

    trim: function() {
        // ensure that there are only this.maxlength items in the collection.
        // The rest should be discarded.
        while (this.models.length > this.maxlength) {
            var model = this.at(0);
            this.remove(model);
        }
    }
});

// This view renders the clickable summary with the icon in the right hand pane
// of the dashboard.
VR.Views.Event = Backbone.View.extend({
    initialize: function(model, template, modalTemplate) {
        this.model = model;
        this.model.on('destroy', this.onDestroy, this);
        this.template = template || VR.Templates.Event;
        this.modalTemplate = modalTemplate || VR.Templates.EventDetail;
        this.render();
    },

    render: function() {
        this.$el.html(this.template.goatee(this.model.attributes));
    },

    onDestroy: function() {
        this.$el.remove();
    },

    events: {
      'click': 'onClick'
    },

    onClick: function(ev) {
      // When you click an Event, you should see an EventDetail modal.  These
      // are created on the fly when first requested.
      if (!this.modal) {
        this.modal = new VR.Views.EventDetail(this.model, this.modalTemplate);   
      }

      this.modal.show();
    }
});

// The modal that provides additional details about the event.
VR.Views.EventDetail = Backbone.View.extend({
    initialize: function(model, template) {
      this.model = model;
      this.template = template || VR.Templates.EventDetail;
      this.model.on('change', this.render, this);
      this.model.on('remove', this.onRemove, this);
    },
    render: function() {
      this.$el.html(this.template.goatee(this.model.attributes));
    },
    show: function() {
      this.render();
      this.$el.modal('show');
    },
    onRemove: function() {
      this.$el.remove();
    }
});

// The view for the pane that shows individual events inside.
VR.Views.Events = Backbone.View.extend({
    initialize: function(collection, container, template, modalTemplate) {
        this.collection = collection;
        this.collection.on('remove', this.onRemove, this);
        this.collection.on('add', this.onAdd, this);

        // container should also be already wrapped in a jquery
        this.container = container;

        this.template = template || VR.Templates.Event;
        this.modalTemplate = modalTemplate || VR.Templates.EventModal;
    },

    onAdd: function(model) {
        // create model view and bind it to the model
        var mv = new VR.Views.Event(model, this.template, this.modalTemplate);
        this.container.prepend(mv.$el);
    },

    onRemove: function(model) {
        model.trigger('destroy');
    }
});

// Initialization of the Events system happens by calling VR.Events.init
VR.Events = {
  init: function(container, streamUrl) {
    // bind stream to handler
    this.stream = new EventSource(streamUrl);
    this.stream.onmessage = $.proxy(this.onEvent, this);

    this.collection = new VR.Models.Events();
    this.listview = new VR.Views.Events(
        this.collection, 
        container 
    );
  },

  onEvent: function(e) {
    var data = JSON.parse(e.data);
    // Messages may be hidden. 
    if (!_.contains(data.tags, 'hidden')) {
      data.time = new Date(data.time);
      data.prettytime = data.time.format("mm/dd HH:MM:ss");
      data.id = e.lastEventId;
      data.classtags = data.tags.join(' ');
      var evmodel = new VR.Models.Event(data);
      this.collection.add(evmodel);
    }
  }
};


// Util
// Generic-use things that didn't seem to fit in a specific model.

VR.Util = {
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
