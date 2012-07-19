// Set up our namespacing. //
//
VR = {};

// Util //
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
