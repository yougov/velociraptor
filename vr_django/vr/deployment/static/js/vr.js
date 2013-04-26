// Welcome to Velociraptor's Javascript UI code.  Most everything below is
// built out of Backbone models and views.

// This VR object is the only thing that Velociraptor puts in the global
// namespace.  All our other code should be nested under here.
VR = {};
VR.Models = {};
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
  },

  getProcLog: function(hostname, procname) {
      // proc logs are served as SSE streams in /api/streams/
      return '/api/streams/proc_log/' + hostname + '/' + procname + '/';
  },

  getProcLogView: function(hostname, procname) {
      return '/proclog/' + hostname + '/' + procname + '/';
  }
  // XXX: Additional routes for event streams are added to VR.Urls in
  // base.html, where we can pull URLs out of Django by using {% url ... %}.
};

// All proc objects should subscribe to messages from this object, in the form
// "updateproc:<id>" and "destroyproc:<id>" and update themselves when such a
// message comes in.
// This saves having to drill down through collections or the DOM later if data
// comes in on an API or event stream.
VR.ProcMessages = {};
_.extend(VR.ProcMessages, Backbone.Events);


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
      VR.ProcMessages.on('updateproc:' + this.id, this.set, this);
      VR.ProcMessages.on('destroyproc:'+this.id, this.onDestroyMsg, this); 

      _.bindAll(this);
    },

    url: function() {
      return VR.Urls.getProc(this.get('host'), this.get('name'));
    },

    doAction: function(action) {
      var proc = this;
      $.ajax({
        type: 'POST',
        url: proc.url(),
        data: JSON.stringify({'action': action}),
        success: function(data, sts, xhr) {
                  proc.set(data);
                },
        dataType: 'json'
      });    
    },

    stop: function() { this.doAction('stop'); },

    start: function() { this.doAction('start'); },

    restart: function() { this.doAction('restart'); },

    isRunning: function() {return this.get('statename') === 'RUNNING';},

    isStopped: function() {
      var state = this.get('statename');
      return state === 'STOPPED' || state === 'FATAL';
    },

    getLog: function() {
      // return a ProcLog model bound to this Proc model.
      return new VR.Models.ProcLog({proc: this});
    },

    onDestroyMsg: function(data) {
      this.trigger('destroy', this, this.collection);
    }
});


VR.Models.ProcLog = Backbone.Model.extend({
    // Should be initialized with {proc: <proc object>}
    initialize: function(data) {
      this.proc = data.proc;
      this.url = VR.Urls.getProcLog(this.proc.get('host'), this.proc.get('name'));
      this.lines = [];
    },

    connect: function() {
      this.eventsource = new EventSource(this.url);
      this.eventsource.onmessage = $.proxy(this.onmessage, this);
    },

    disconnect: function() {
      this.eventsource.close();
    },

    onmessage: function(msg) {
      this.lines.push(msg.data);
      this.trigger('add', msg.data);
    }
});



VR.Models.ProcList = Backbone.Collection.extend({
    model: VR.Models.Proc,

    getOrCreate: function(data) {
      // if proc with id is in collection, update and return it.
      var proc = _.find(this.models, function(proc) {
          return proc.id === data.id;
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
    },

    stopAll: function() {
      this.each(function(proc) {
        proc.stop();
      });
    },

    startAll: function() {
      this.each(function(proc) {
        proc.start();
      });
    },

    restartAll: function() {
      this.each(function(proc) {
        proc.restart();
      });
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

    this.procs.on('add', this.onAddProc, this);
    this.procs.on('remove', this.onRemoveProc, this);
  },

  onProcData: function(ev, data) {
    // backbone will instsantiate a new Proc and handle deduplication in the collection for us, 
    // if procs have a consistent 'id' attribute, which they do.
    this.procs.add(data);
  },

  onAddProc: function(proc) {
    this.trigger('addproc', proc);
  },

  onRemoveProc: function(proc) {
    this.trigger('removeproc', proc);
    // if there are no more procs, then remove self
    if (this.procs.length === 0 && this.collection) {
      this.collection.remove(this);
    }
  }
});


VR.Models.HostList = Backbone.Collection.extend({
  model: VR.Models.Host,
  onProcData: function(ev, data) {
    // see if we already have a host for this proc.  If not, make one.  Pass the proc down to that host.
    var hostId = [data.app_name, data.recipe_name, data.host].join('-');

    var host = this.get(hostId);
    if (!host) {
      host = new VR.Models.Host({ id: hostId, name: data.host });
      this.add(host);
    }
    host.onProcData(ev, data);
  }
});


VR.Models.Swarm = VR.Models.Tasty.extend({
    initialize: function() {
      this.hosts = new VR.Models.HostList();
      this.hosts.on('all', this.onHostsEvent, this);
    },

    procIsMine: function(fullProcName) {
      // Given a full proc name like
      // Velociraptor-1.2.3-local-a4dfd8fa-web-5001, return True if its app,
      // recipe, and proc name (e.g. 'web') match this swarm.
      var split = fullProcName.split('-');
      return split[0] === this.get('app_name') &&
             split[2] === this.get('recipe_name') &&
             split[4] === this.get('proc_name');
    },

    fetchByProcData: function(procData) {
      // since swarms are instantiated as a side effect of getting proc data,
      // we need to take that proc data and build up a Tastypie query to fetch
      // full swarm data from the API.

      var url = VR.Urls.root 
          +'swarms/?'
          +'recipe__app__name='+procData.app_name
          +'&recipe__name='+procData.recipe_name
          +'&proc_name='+procData.proc_name
          +'&squad__hosts__name='+procData.host;
      // query the URL, and update swarm's attributes from data in first (and
      // only) result.
      var swarm = this;
      $.getJSON(url, function(data, sts, xhr) {
        if (data.objects && data.objects.length) {
          swarm.set(data.objects[0]);
        };
      });
    },

    onProcData: function(ev, data) {
      // called when proc data comes down from above 
      this.hosts.onProcData(ev, data);
    },

    onHostsEvent: function(event, model, collection, options) {
      // all events on our hosts list should be bubbled up to be events on 
      // the swarm itself.
      this.trigger.apply(this, arguments);

      // if all my hosts are gone, I should go too.
      if (event === 'remove' && this.hosts.length === 0 && this.collection) {
        this.collection.remove(this);
      }
    },

    getProcs: function() {
      // loop over all hosts in this.hosts and build up an array with all their procs.
      // return that.
      var procsArrayArray = _.map(this.hosts.models, function(host){return host.procs.models;});
      return _.flatten(procsArrayArray);
    },

    // convenience methods since we'll so often work with procs at the swarm level.
    // FIXME: Provide a server-side view that will restart all procs in a swarm with a
    // single API call, instead of doing all this looping.
    stopAll: function() {
      this.hosts.each(function(host) {
        host.procs.stopAll();
      });
    },

    startAll: function() {
      this.hosts.each(function(host) {
        host.procs.startAll();
      });
    },

    restartAll: function() {
      this.hosts.each(function(host) {
        host.procs.restartAll();
      });
    }
});


VR.Models.SwarmList = Backbone.Collection.extend({
    model: VR.Models.Swarm,

    comparator: function(swarm) {
      return swarm.get('name');
    },

    getByProcData: function(procData) {
      var swarmname = [procData.recipe_name, procData.proc_name].join('-');
      // if swarm with id is in collection, return it.
      var swarm = this.find(function(swarm) {
          return swarm.get('name') === swarmname;
        });
      if (swarm) {
        return swarm;
      }
      // else create, add, and return.
      swarm = new VR.Models.Swarm({
          name: swarmname
        });

      swarm.fetchByProcData(procData);
      swarm.on('addproc', this.onAddProc, this);
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
    },

    onProcData: function(ev, data) {
      // when we hear from above that new proc data has come in, send that down
      // the tree.
      var swarm = this.getByProcData(data);
      swarm.onProcData(ev, data);
    }
});


VR.Models.App = VR.Models.Tasty.extend({
    initialize: function() {
      this.swarms = new VR.Models.SwarmList();
      this.swarms.on('all', this.onSwarmsEvent, this);
    },

    onProcData: function(ev, data) {
      this.swarms.onProcData(ev, data);
    },

    onAddProc: function(proc) {
      this.trigger('addproc', proc);
    },

    onSwarmsEvent: function(event, model, collection, options) {
      this.trigger.apply(this, arguments);
      if (event === 'removeproc') {
        console.log(this.swarms);
      }
    }
});


VR.Models.AppList = Backbone.Collection.extend({
    model: VR.Models.App,
    
    initialize: function() {
      this.on('change', this.updateUrl);
      VR.ProcMessages.on('all', this.onProcData, this);
    },

    comparator: function(app) {
      return app.id;
    },

    getOrCreate: function(name) {
      // if app with id is in collection, return it.
      var app = _.find(this.models, function(app) {
          return app.get('name') === name;
        });
      if (app) {
        return app;
      }
      // else create, add, and return.
      app = new VR.Models.App({
        name: name, 
        "class": "appbox",
        resource_uri: VR.Urls.getTasty('apps', name)
      });
      app.fetch();
      this.add(app);

      return app;
    },

    onProcData: function(ev, data) {
      // handle updates differently from removals.
      var parsed = ev.split(":");
      if (parsed[0] === 'updateproc') {
        var app = this.getOrCreate(data.app_name);
        app.onProcData(ev, data);
      } else if (parsed[0] === 'destroyproc') {
        // TODO: here's where we should handle drilling down to remove
        // destroyed procs, empty swarms, and empty apps, rather than from the
        // outside in vrdash.js.
      }
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
        if (!inserted && title > app.get('name')) {
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
      this.proc.on('remove', this.onProcRemove, this);
      this.proc.on('destroy', this.onProcRemove, this);
      this.render();
    },
    render: function() {
      this.$el.html(this.template.goatee(this.proc.toJSON()));
    },

    events: {
      'click': 'onClick'
    },

    onProcRemove: function(proc) {
      this.remove();
    },

    onClick: function(ev) {
      if (!this.modal) {
        this.modal = new VR.Views.ProcModal(this.proc);   
      }

      this.modal.show();
    }
});


VR.Views.ProcModal = Backbone.View.extend({
    el: '<div class="modalwrap" tabindex="-1"></div>',
    initialize: function(proc) {
      this.proc = proc;
      this.fresh = true;
      this.proc.on('change', this.render, this);
      this.proc.on('destroy', this.onProcDestroy, this);
      this.proc.on('remove', this.onProcDestroy, this);
      this.$el.on('shown', $.proxy(this.onShown, this));
      this.$el.on('hidden', $.proxy(this.onHidden, this));
    },

    render: function() {
      // this render function is careful not to do a whole repaint, because
      // that would mean that you'd lose your selection if you're trying to
      // copy/paste from the streaming log section.  That'd be annoying!

      var data = this.proc.toJSON();
      data.logs_uri = VR.Urls.getProcLog(data.host, data.name);
      data.logs_view_uri = VR.Urls.getProcLogView(data.host, data.name);

      if (this.fresh) {
        // only do a whole render the first time.  After that just update the
        // bits that have changed.
        this.$el.html(VR.Templates.ProcModal.goatee(data));
        this.fresh = false;
      }
      
      // insert/update details table.
      var detailsRows = VR.Templates.ProcModalRows.goatee(data);
      this.$el.find('.proc-details-table').html(detailsRows);

      // insert/update buttons
      var detailsButtons = VR.Templates.ProcModalButtons.goatee(data);
      this.$el.find('.modal-footer').html(detailsButtons);
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
      this.trigger('show');
    },

    onShown: function() {
      // show streaming logs
      this.log = this.proc.getLog();
      var logContainer = this.$el.find('.proc-log');
      logContainer.html('');
      this.logview = new VR.Views.ProcLog(this.log, logContainer);
      this.log.connect();
    },

    onHidden: function() {
      // stop the log stream.
      this.log.disconnect();
    },

    onStartBtn: function(ev) {
      this.proc.start();
    },

    onStopBtn: function(ev) {
      this.proc.stop();
    },

    onRestartBtn: function(ev) {
      this.proc.restart();
    },

    onDestroyBtn: function(ev) {
      this.proc.destroy({wait: true, sync: true});
    },

    onProcDestroy: function() {
      this.$el.modal('hide');
      this.$el.remove();
    }
});


VR.Views.ProcLog = Backbone.View.extend({
    initialize: function(proclog, container, scrollContainer) {
      this.log = proclog;
      this.container = container;

      // optionally allow passing in a different element to be scrolled.
      this.scrollContainer = scrollContainer || container;

      this.log.on('add', this.onmessage, this);
      this.render();
    },

    render: function() {
      this.container.append(this.el);
    },

    onmessage: function(line) {
      var node = $('<div />');
      node.text(line);
      this.$el.append(node);
      // set scroll to bottom of div.
      var height = this.scrollContainer[0].scrollHeight;
      this.scrollContainer.scrollTop(height);
    },

    clear: function() {
      // stop listening for model changes
      this.log.off('add', this.onmessage, this);
      // clean out lines
      this.lines = [];
    }
}); 


VR.Views.Host = Backbone.View.extend({
    el: '<tr class="hostview"></tr>',
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


VR.Views.ProcList = Backbone.View.extend({
    el: '<div class="procboxes"></div>',
    initialize: function(owner) {
      // owner is an object that may fire the 'addproc' event, which could be
      // an app, swarm, or host.
      this.owner = owner;
      // whenever the owner adds a proc, add a view to ourself.
      this.owner.on('addproc', this.addProcView, this);
    },

    addProcView: function(proc) {
      // create a procview.
      var pv = new VR.Views.Proc(proc);
      // insert it in my container
      this.$el.append(pv.el);
    }
});


VR.Views.Swarm = Backbone.View.extend({
    el: '<tr class="swarmbox"></tr>',
    initialize: function(swarm, template) {
      this.swarm = swarm;
      this.template = template || VR.Templates.Swarm;
      // what a new host gets added, make sure we render a hostview for it
      this.swarm.hosts.on('add', this.hostAdded, this);

      // when a new proc is added, make sure it gets rendered in here
      this.swarm.hosts.on('addproc', this.procAdded, this);
      this.swarm.on('remove', this.onRemove, this);

      this.procsEl = this.$el.find('.procgrid');
    },
    events: {
      'click .swarmtitle': 'onClick',
      'click th .expandtree': 'toggleExpanded'
    },
    onClick: function(ev) {
      if (!this.modal) {
        this.modal = new VR.Views.SwarmModal(this.swarm);   
      }

      this.modal.show();
    },
    toggleExpanded: function() {
      this.$el.toggleClass('biggened');
      this.$el.find('i').toggleClass('icon-caret-right').toggleClass('icon-caret-down');
    },
    hostAdded: function(host) {
      var hv = new VR.Views.Host(host);
      this.$el.find('.hosttable').append(hv.el);
    },
    procAdded: function(proc) {
      var pv = new VR.Views.Proc(proc);
      pv.render();
      this.$el.children('.procgrid').append(pv.el);
    },
    render: function() {
      this.$el.html(this.template.goatee(this.swarm.toJSON()));
    },
    onRemove: function() {
      this.$el.remove();
    }
});

VR.Views.SwarmModal = Backbone.View.extend({
    el: '<div class="modalwrap" tabindex="-1"></div>',
    initialize: function(swarm, template) {
      this.swarm = swarm;
      this.current_state = '';
      this.template = template || VR.Templates.SwarmModal;

      // FIXME: if a new proc is added to the swarm/host while the modal is open
      // will we see it?  I think we need to listen for 'addproc' on the swarm to
      // catch that.
      this.listenTo(this.swarm, 'remove', this.remove);
      this.listenTo(this.swarm, 'all', this.onSwarmEvent, this);

      this.swarm.hosts.each(function(host) {
          this.listenTo(host.procs, 'all', this.updateState, this);
      }, this);
    },
    events: {
      'click .swarm-start': 'onStartBtn',
      'click .swarm-stop': 'onStopBtn',
      'click .swarm-restart': 'onRestartBtn'
    },

    render: function() {
      this.$el.html(this.template.goatee(this.swarm.toJSON()));

      var procs = this.swarm.getProcs();
      _.each(procs, function(proc) {
          this.procAdded(proc);
      }, this);
    },

    show: function() {
      this.render();
      this.$el.modal('show');

      this.updateState();
    },

    procAdded: function(proc) {
      var pv = new VR.Views.Proc(proc);
      // unbind the model click events inside the swarm modal.
      pv.undelegateEvents();

      pv.render();
      this.$el.find('.procboxes').append(pv.el);
      this.updateState();
    },

    updateState: function() {

      // if there are any stopped/fatal procs, add the class to show the start
      // button.
      var procs = this.swarm.getProcs();
      if (_.some(procs, function(proc) {return proc.isStopped();})) {
        this.$el.find('.modal').addClass('somestopped');
      } else {
        this.$el.find('.modal').removeClass('somestopped');
      }

      // if there are any running procs, add the class to show the stop button
      if (_.some(procs, function(proc) {return proc.isRunning();})) {
        this.$el.find('.modal').addClass('somerunning');
      } else {
        this.$el.find('.modal').removeClass('somerunning');
      }
    },

    onRemove: function() {
      this.$el.remove();
    },
    onStartBtn: function(ev) {
      this.swarm.startAll();
    },
    onStopBtn: function(ev) {
      this.swarm.stopAll();
    },
    onRestartBtn: function(ev) {
      this.swarm.restartAll();
    },
    onSwarmEvent: function(event, model, collection, options) {
      console.log(arguments);
    },
    onProcEvent: function(event, model, collection, options) {
      console.log(arguments);
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
      this.$el.find('.swarmtable').append(sv.el);
    },

    events: {
      'click .titlecell .expandtree': 'toggleExpanded',
      'click .apptitle': 'appModal'
    },

    toggleExpanded: function() {
      this.$el.toggleClass('biggened');
      // only toggle this arrow, not the ones deeper inside
      this.$el.find('.titlecell > .expandtree > i').toggleClass('icon-caret-right').toggleClass('icon-caret-down');
    },

    appModal: function() {
      if (!this.modal) {
        this.modal = new VR.Views.AppModal(this.app);   
      }

      this.modal.show();
    },

    render: function() {
      this.$el.html(this.template.goatee(this.app.toJSON()));
      var plv = new VR.Views.ProcList(this.app);
      this.$el.find('td').append(plv.el);
    },

    onRemove: function() {
      this.$el.remove();
    }
});

VR.Views.AppModal = Backbone.View.extend({
    el: '<div class="modalwrap" tabindex="-1"></div>',
    initialize: function(app, template) {
      this.app = app;
      this.template = template || VR.Templates.AppModal;
    },

    render: function() {
      this.$el.html(this.template.goatee(this.app.toJSON()));
    },

    show: function() {
      this.render();
      this.$el.modal('show');
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
