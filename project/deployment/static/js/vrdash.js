// Depends on vr.js
//
// TODO: Handle HTTP 500 responses to ajax calls.  They should contain JSON.

// DASH //
VR.Dash = {};


Proc = Backbone.Model.extend({
    initialize: function() {
      this.on('change', this.updateUrl);
    },
    url: function() {
      var host = this.get('host');
      var name = this.get('name');
      return '/api/hosts/' + host + '/procs/' + name + '/';
    }
});


ProcList = Backbone.Collection.extend({
    model: Proc,

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
      proc = new Proc(data);
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
          return proc.get('host') === host && proc.get('time') < cutoff;
      });
      _.each(stale, function(proc) {this.remove(proc);}, this);
    }
});

Swarm = Backbone.Model.extend({
    initialize: function() {
      this.procs = new ProcList();
    }
});


SwarmList = Backbone.Collection.extend({
    model: Swarm,

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
      swarm = new Swarm({id: id});
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


App = Backbone.Model.extend({
    initialize: function() {
      this.swarms = new SwarmList();
    }
});


AppList = Backbone.Collection.extend({
    model: App,

    initialize: function(container) {
      this.on('add', function(app) {
        // TODO: this should be a view
        // draw the new app on the page
        var v = new AppView(app);
        v.render();
        var inserted = false;
        // loop until we see one later than us, alphabetically, and insert
        // there.
        _.each(container.find('.approw'), function(row) {
            var title = $(row).find('.apptitle').text();
            if (!inserted && title > app.id) {
                $(row).before(v.el);
                inserted = true;
            } 
        });

        // If still not inserted, just append to container
        if (!inserted) {
            container.append(v.el);
        }
      });
    },

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
      app = new App({id: id, "class": "appbox"});
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


ProcView = Backbone.View.extend({
    template: '#proc-tmpl',
    el: '<div class="procwrap"></div>',
    modalTemplate: '#proc-details-tmpl',
    initialize: function(proc) {
      this.proc = proc;
      this.template = $(this.template);
      this.proc.on('change', this.render, this);
      this.proc.on('destroy', this.onRemove, this);
      this.proc.on('remove', this.onRemove, this);
    },
    render: function() {
      this.$el.html(this.template.goatee(this.proc.toJSON()));
    },

    events: {
      'click': 'onClick'
    },

    onClick: function(ev) {
      if (!this.modal) {
        this.modal = new ProcModalView(this.proc);   
      }

      this.modal.show();
    },

    onRemove: function() {
      this.$el.remove();
    }
});


ProcModalView = Backbone.View.extend({
    template: '#proc-details-tmpl',
    initialize: function(proc) {
      this.proc = proc;
      this.template = $(this.template);
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
      $.post(this.proc.url(), {'action': action}, function(data, stat, xhr) {
          VR.Dash.updateProcData(data);
        });
    },
    onDestroyBtn: function(ev) {
      this.proc.destroy();
    },
    onProcDestroy: function() {
      this.$el.modal('hide');
      this.$el.remove();
    },
    show: function() {
      this.render();
      this.$el.modal('show');
    }
});


SwarmView = Backbone.View.extend({
    template: '#swarm-tmpl',
    el: '<div class="swarmbox"></div>',
    initialize: function(swarm) {
      this.swarm = swarm;
      this.template = $(this.template);
      // when a new proc is added, make sure it gets rendered in here
      this.swarm.procs.on('add', this.procAdded, this);
      this.swarm.on('remove', this.onRemove, this);
    },

    procAdded: function(proc) {
      var pv = new ProcView(proc);
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


AppView = Backbone.View.extend({
    template: '#app-tmpl',
    el: '<tr class="approw"></tr>',
    initialize: function(app) {
      this.app = app;
      this.template = $(this.template);
      this.app.swarms.on('add', this.swarmAdded, this);
      this.app.on('remove', this.onRemove, this);
    },

    swarmAdded: function(swarm) {
      var sv = new SwarmView(swarm);
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

VR.Dash.getHostList = function() {
  $.getJSON('/api/hosts/', VR.Dash.onHostList);
};

VR.Dash.onHostList = function(data, stat, xhr) {
   _.each(data.hosts, function(el) {
     $.getJSON('/api/hosts/' + el + '/procs/', VR.Dash.onHostData);
   });

   setTimeout(VR.Dash.getHostList, 5000);
};


VR.Dash.onHostData = function(data, stat, xhr) {
  _.each(data.procs, VR.Dash.updateProcData);

  // cull any old procs
  VR.Dash.Apps.cull(data.host, data.time);
};

VR.Dash.updateProcData = function(data) {
    app = VR.Dash.Apps.getOrCreate(data.app);
    VR.Dash.Apps.add(app);

    var swarmname = [data.recipe, data.proc].join('-');
    var s = app.swarms.getOrCreate(swarmname);
    var p = s.procs.getOrCreate(data);
};

VREvent = Backbone.Model.extend({});

VREvents = Backbone.Collection.extend({
    model: VREvent,
    maxlength: 100,

    initialize: function() {
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

VREventView = Backbone.View.extend({
    initialize: function(model, template) {
        this.model = model;
        this.model.on('destroy', this.onDestroy, this);
        this.template = template;
        this.render();
    },

    render: function() {
        this.$el.html(this.template.goatee(this.model.attributes));
    },

    onDestroy: function() {
        this.$el.remove();
    }
});

VREventsView = Backbone.View.extend({
    initialize: function(collection, template, container) {
        this.collection = collection;
        // template should be the template to use for individual items.  It
        // should be a goatee template already wrapped in a jquery obj.
        this.template = template;

        // container should also be already wrapped in a jquery
        this.container = container;

        this.collection.on('remove', this.onRemove, this);

        this.collection.on('add', this.onAdd, this);
    },

    onAdd: function(model) {
        // create model view and bind it to the model
        var mv = new VREventView(model, this.template);
        this.container.prepend(mv.$el);
    },

    onRemove: function(model) {
        model.trigger('destroy');
    }
});

VR.Dash.Events = {
  init: function(stream_url, tmpl_id, container_id, maxlength) {
    // bind stream to handler
    this.stream = new EventSource(stream_url);
    this.stream.onmessage = $.proxy(this.onTaskEvent, this);

    this.collection = new VREvents();
    this.listview = new VREventsView(this.collection, 
        $('#' + tmpl_id), 
        $('#' + container_id)
    );
  },

  onTaskEvent: function(e) {
    var data = JSON.parse(e.data);
    data.time = new Date(data.time);
    data.prettytime = data.time.format("mm/dd HH:MM:ss");
    data.id = e.lastEventId;
    data.classtags = data.tags.join(' ');
    var evmodel = new VREvent(data);
    this.collection.add(evmodel);
  }
};

