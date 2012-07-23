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
        // draw the new app on the page
        var v = new AppView(app);
        v.render();
        container.append(v.el);
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
      this.proc.on('destroy', this.onProcDestroy, this);
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
    onProcDestroy: function() {
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
    },
    render: function() {
      this.$el.html(this.template.goatee(this.proc.toJSON()));
    },
    events: {
      'click .proc-start': 'onStartBtn',
      'click .proc-stop': 'onStopBtn',
      'click .proc-destroy': 'onDestroyBtn'
    },
    onStartBtn: function(ev) {
      this.doAction('start');
    },
    onStopBtn: function(ev) {
      this.doAction('stop');
    },
    doAction: function(action) {
      $.post(this.proc.url(), {'action': action}, function(data, stat, xhr) {
          VR.Dash.updateProcData(data);
        });
    },
    onDestroyBtn: function(ev) {
      console.log('destroy btn');
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
    },

    procAdded: function(proc) {
      var pv = new ProcView(proc);
      pv.render();
      this.$el.find('.procgrid').append(pv.el);
    },

    render: function() {
      this.$el.html(this.template.goatee(this.swarm.toJSON()));
    }
});


AppView = Backbone.View.extend({
    template: '#app-tmpl',
    el: '<tr></tr>',
    initialize: function(app) {
      this.app = app;
      this.template = $(this.template);
      this.app.swarms.on('add', this.swarmAdded, this);
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
    }
});


VR.Dash.onHostList = function(data, stat, xhr) {
   _.each(data.hosts, function(el) {
     $.getJSON('/api/hosts/' + el + '/procs/', VR.Dash.onHostData);
   });
};


VR.Dash.onHostData = function(data, stat, xhr) {
  _.each(data.procs, VR.Dash.updateProcData);
};

VR.Dash.updateProcData = function(data) {
    app = VR.Dash.Apps.getOrCreate(data.app);
    VR.Dash.Apps.add(app);

    var swarmname = [data.proc, data.recipe].join('-');
    var s = app.swarms.getOrCreate(swarmname);
    var p = s.procs.getOrCreate(data);
};

// DASH Tasks Methods //
VR.Dash.Tasks = {
    taskDataQueue: '',

    init: function(){
        VR.Dash.Tasks.tmpl = $('#task-tmpl');
        VR.Dash.Tasks.el = $('#tasks-list');

        VR.Dash.Tasks.el.delegate('.task-wrapper', 'click', VR.Dash.Tasks.onTaskClick);

        VR.Dash.Tasks.getTaskData();
        // then setInterval to re-check every 4 seconds.
        setInterval(function(){
            VR.Dash.Tasks.getTaskData();
        }, 4000);

    },

    getTaskData: function(){
        var that = this;

        $.getJSON('/api/task/', function(data){
            // the data comes back with the most recent first, but it's
            // actually simpler to do most recent last and always use
            // $().prepend.  So reverse it.
            data.tasks.reverse();
            _.each(data.tasks, VR.Dash.Tasks.doItem);

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
            task = VR.Dash.Tasks.tmpl.goatee(taskdata);
            VR.Dash.Tasks.el.prepend(task);
        } else {
            // update existing one.
            if (!_.isEqual(task.data('taskdata'), taskdata)) {
                var newtask = VR.Dash.Tasks.tmpl.goatee(taskdata);
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
};// end VR.Dash.Tasks
