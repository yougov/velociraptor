// Stick 3rd party and oddball bits of javascript here.

// Ensure that AJAX posts to this domain include the CSRF token stored in the
// cookies. See https://docs.djangoproject.com/en/dev/ref/contrib/csrf/#ajax
var pendingAjaxRequests = [];

jQuery(document).ajaxSend(function(event, xhr, settings) {
    // build up a queue of pending ajax requests
    // that we can work with
    pendingAjaxRequests.push(settings);

    function getCookie(name) {
        var cookieValue = null;
        if (document.cookie && document.cookie != '') {
            var cookies = document.cookie.split(';');
            for (var i = 0; i < cookies.length; i++) {
                var cookie = jQuery.trim(cookies[i]);
                // Does this cookie string begin with the name we want?
                if (cookie.substring(0, name.length + 1) == (name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    }
    function sameOrigin(url) {
        // url could be relative or scheme relative or absolute
        var host = document.location.host; // host + port
        var protocol = document.location.protocol;
        var sr_origin = '//' + host;
        var origin = protocol + sr_origin;
        // Allow absolute or scheme relative URLs to same origin
        return (url == origin || url.slice(0, origin.length + 1) == origin + '/') ||
            (url == sr_origin || url.slice(0, sr_origin.length + 1) == sr_origin + '/') ||
            // or any other URL that isn't scheme relative or absolute i.e relative.
            !(/^(\/\/|http:|https:).*/.test(url));
    }
    function safeMethod(method) {
        return (/^(GET|HEAD|OPTIONS|TRACE)$/.test(method));
    }

    if (!safeMethod(settings.type) && sameOrigin(settings.url)) {
        xhr.setRequestHeader("X-CSRFToken", getCookie('csrftoken'));
    }
});

jQuery(document).ajaxComplete(function(event, xhr, settings) {
    // update our pending requets array
    pendingAjaxRequests = pendingAjaxRequests.filter(function(object) {
        return object.url !== settings.url;
    });
});


/*
  http://stevenlevithan.com/assets/misc/date.format.js
 * Date Format 1.2.3
 * (c) 2007-2009 Steven Levithan <stevenlevithan.com>
 * MIT license
 *
 * Includes enhancements by Scott Trenda <scott.trenda.net>
 * and Kris Kowal <cixar.com/~kris.kowal/>
 *
 * Accepts a date, a mask, or a date and a mask.
 * Returns a formatted version of the given date.
 * The date defaults to the current date/time.
 * The mask defaults to dateFormat.masks.default.
 */

var dateFormat = function () {
	var	token = /d{1,4}|m{1,4}|yy(?:yy)?|([HhMsTt])\1?|[LloSZ]|"[^"]*"|'[^']*'/g,
		timezone = /\b(?:[PMCEA][SDP]T|(?:Pacific|Mountain|Central|Eastern|Atlantic) (?:Standard|Daylight|Prevailing) Time|(?:GMT|UTC)(?:[-+]\d{4})?)\b/g,
		timezoneClip = /[^-+\dA-Z]/g,
		pad = function (val, len) {
			val = String(val);
			len = len || 2;
			while (val.length < len) val = "0" + val;
			return val;
		};

	// Regexes and supporting functions are cached through closure
	return function (date, mask, utc) {
		var dF = dateFormat;

		// You can't provide utc if you skip other args (use the "UTC:" mask prefix)
		if (arguments.length == 1 && Object.prototype.toString.call(date) == "[object String]" && !/\d/.test(date)) {
			mask = date;
			date = undefined;
		}

		// Passing date through Date applies Date.parse, if necessary
		date = date ? new Date(date) : new Date;
		if (isNaN(date)) throw SyntaxError("invalid date");

		mask = String(dF.masks[mask] || mask || dF.masks["default"]);

		// Allow setting the utc argument via the mask
		if (mask.slice(0, 4) == "UTC:") {
			mask = mask.slice(4);
			utc = true;
		}

		var	_ = utc ? "getUTC" : "get",
			d = date[_ + "Date"](),
			D = date[_ + "Day"](),
			m = date[_ + "Month"](),
			y = date[_ + "FullYear"](),
			H = date[_ + "Hours"](),
			M = date[_ + "Minutes"](),
			s = date[_ + "Seconds"](),
			L = date[_ + "Milliseconds"](),
			o = utc ? 0 : date.getTimezoneOffset(),
			flags = {
				d:    d,
				dd:   pad(d),
				ddd:  dF.i18n.dayNames[D],
				dddd: dF.i18n.dayNames[D + 7],
				m:    m + 1,
				mm:   pad(m + 1),
				mmm:  dF.i18n.monthNames[m],
				mmmm: dF.i18n.monthNames[m + 12],
				yy:   String(y).slice(2),
				yyyy: y,
				h:    H % 12 || 12,
				hh:   pad(H % 12 || 12),
				H:    H,
				HH:   pad(H),
				M:    M,
				MM:   pad(M),
				s:    s,
				ss:   pad(s),
				l:    pad(L, 3),
				L:    pad(L > 99 ? Math.round(L / 10) : L),
				t:    H < 12 ? "a"  : "p",
				tt:   H < 12 ? "am" : "pm",
				T:    H < 12 ? "A"  : "P",
				TT:   H < 12 ? "AM" : "PM",
				Z:    utc ? "UTC" : (String(date).match(timezone) || [""]).pop().replace(timezoneClip, ""),
				o:    (o > 0 ? "-" : "+") + pad(Math.floor(Math.abs(o) / 60) * 100 + Math.abs(o) % 60, 4),
				S:    ["th", "st", "nd", "rd"][d % 10 > 3 ? 0 : (d % 100 - d % 10 != 10) * d % 10]
			};

		return mask.replace(token, function ($0) {
			return $0 in flags ? flags[$0] : $0.slice(1, $0.length - 1);
		});
	};
}();

// Some common format strings
dateFormat.masks = {
	"default":      "ddd mmm dd yyyy HH:MM:ss",
	shortDate:      "m/d/yy",
	mediumDate:     "mmm d, yyyy",
	longDate:       "mmmm d, yyyy",
	fullDate:       "dddd, mmmm d, yyyy",
	shortTime:      "h:MM TT",
	mediumTime:     "h:MM:ss TT",
	longTime:       "h:MM:ss TT Z",
	isoDate:        "yyyy-mm-dd",
	isoTime:        "HH:MM:ss",
	isoDateTime:    "yyyy-mm-dd'T'HH:MM:ss",
	isoUtcDateTime: "UTC:yyyy-mm-dd'T'HH:MM:ss'Z'"
};

// Internationalization strings
dateFormat.i18n = {
	dayNames: [
		"Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat",
		"Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"
	],
	monthNames: [
		"Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
		"January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"
	]
};

// For convenience...
Date.prototype.format = function (mask, utc) {
	return dateFormat(this, mask, utc);
};

// A little hackishness to set up the swarm dropdown in the nav.
$(function() {

    $(document).on('hidden.bs.modal', function(ev) {
        $(ev.target).remove();
        $('.modal-backdrop').remove();
    });

    var ESCAPE = 27, UP = 38, DOWN = 40, ENTER = 13;

    // filter-as-you-type on swarm dropdown in nav.
    var checker = setInterval(function(){
        if(pendingAjaxRequests.length == 0){
            clearInterval(checker);
            // re-enable the swarm dropdown menu item
            $('#swarm-dropdown').removeClass('disabled').css({'cursor': 'pointer'});
        }
    }, 500);

    var swarmInput = $('#swarm-filter');
    var hideByStart = function(els, txt) {
      // take a jquery selector of elements.  Hide all the ones that don't
      // start with "start", and show all the rest.
      els.each(function(idx, el) {
            el = $(el);
            try {
              if (el.attr('rel').indexOf(txt.toLowerCase()) > -1) {
                  el.show();
              } else {
                  el.hide();
              }
            } catch(e) {}
        });

      return els.filter(':visible');
    };

    // listen for keyboard up/down and highlight results.
    swarmInput.on('keyup', function(ev) {
        if (ev.keyCode === ESCAPE) {
            $(this).parent('.dropdown-menu').hide();
            return;
        } 
        var txt = $(this).val();
        var visible, selectedLi;

        if (ev.keyCode === DOWN) {
            visible = hideByStart($('#swarmlist li'), txt);
            selectedLi = visible.filter('[class*="active"]');

            if (selectedLi.length) {
              selectedLi.next('li').addClass('active');
              selectedLi.removeClass('active');
            } else {
                visible.filter(':first').addClass('active');
            }
        }
        else if (ev.keyCode === UP) {
            visible = hideByStart($('#swarmlist li'), txt);
            selectedLi = visible.filter('[class*="active"]');

            if (selectedLi.length) {
                selectedLi.prev('li').addClass('active');
                selectedLi.removeClass('active');
            }
        }
        else if (ev.keyCode === ENTER) {
            visible = hideByStart($('#swarmlist li'), txt);
            selectedLi = visible.filter('[class*="active"]');

            if (selectedLi.length) {
                window.location.href = selectedLi.find('a').attr('href');
            }
        }
        else if (txt.length > 2 && ev.keyCode !== 91) {
            $('#swarmlist').html('<li><a>Searching...</a></li>');
            // only search if we've entered text
            delay(function(){
                var resource = 'swarms';

                // make api request for filtered swarms
                $.getJSON('/swarmsearch/?query=' + txt, function(data, status, xhr) {
                    $('#swarmlist').empty();
                    if("success" === status && data.length > 0) {
                        var listItem;
                        for(var i = 0; i < data.length; i++) {
                            listItem = ''+
                            '<li rel="' + data[i].shortname.toLowerCase() + '">'+
                                '<a href="/swarm/' + data[i].id + '/">' + data[i].shortname + '</a>'+
                            '</li>';
                            $('#swarmlist').append(listItem);
                        }
                    } else {
                        $('#swarmlist').append('<li style="padding: 3px 20px;">No results</li>');
                    }
                });
            }, 800);
        } else {
            // reset the drop-down
            delay(function(){
                $('#swarmlist').empty();
                $('#swarmlist').append('<li rel="new_swarm"><a href="{% url new_swarm %}">New</a></li>');
            }, 500);
        }
    });  

    // replace bootstrap dropdown behavior with our own, since we customized it
    // with a type filter.
    $('#swarm-dropdown').on('click', function(ev) {
        if($(this).hasClass('disabled')) {
            return;
        }
        var menu = $(this).next('.dropdown-menu');
        if (menu.is(':visible')) {
            menu.hide();
        } else {
            menu.show();
            var inp = menu.find('input');
            inp.focus();
            $('body').on('click', function() {
                if (!inp.is(':focus')) {
                    menu.hide();
                } 
            });
        }
    });

    // function to delay callback by specified 'ms'
    var delay = (function(){
        var timer = 0;
        return function(callback, ms){
            clearTimeout (timer);
            timer = setTimeout(callback, ms);
        };
    })();

    // watch filter input and make delayed requests
    $('.filterBy').on('keyup', function(e) {
        delay(function(){
            var resource = $(e.currentTarget).data('resource');
            $.getJSON(VR.Urls.root + resource + '/?'+ e.currentTarget.name + '=' + e.currentTarget.value, function(data, status, xhr) {
                if("success" === status) {
                    var results = data.objects;
                    $('.ingredients-list').empty();
                    _.each(results, function(el) {
                        $('.ingredients-list').append('<li><a href="/ingredient/' + el.id + '/">' + el.name + '</a></li>');
                    });
                    if(results.length < 50)
                        $('ul.pager').hide();
                    else
                        $('ul.pager').show();
                }
            });
        }, 500);
    });

    // Update dropdown in navigation
    $.getJSON(VR.Urls.getTasty('dashboard'), function(data, stat, xhr) {
        _.each(data.objects, function(dashboard) {
          $('#dashboard-submenu').append('<li><a href="/dashboard/'+dashboard.slug+'/">'+dashboard.name+'</a></li>');
        });

        $('#dashboard-submenu').append('<li class="divider"></li><li><a href="javascript:;" class="dashboard-new">New</a></li>');

        $('.dashboard-new').click(function() {
          var template = VR.Templates.DashModal,
              modal = template.goatee(),
              apps;

          var counter = 0;
          $(modal).modal('show').on('shown.bs.modal', function(ev) {
            counter++;
            $('#dashboard-name').on('change', function() {
              var name = $(this).val();
                  name = name.replace(/\ /g, '-').toLowerCase();

              $('#dashboard-slug').val(name);
            });
            
            if(counter===1) {
              $.getJSON(VR.Urls.getTasty('apps'), function(data) {
                apps = data.objects;

                _.each(apps, function(app) {
                  if($('#'+app.name+'-option').length === 0)
                    $('#dashboard-apps').append('<option id="'+app.name+'-option" data-id="'+app.id+'" value="'+app.id+'|'+app.name+'">'+app.name+'</option>');
                });

                SelectFilter.init('dashboard-apps', "Apps", 0, "/static/");
              });
            }
          });

          $(modal).find('.btn-success').on('click', function(ev) {
            var form = $(modal).find('form'),
                name = form.find('#dashboard-name').val(),
                slug = form.find('#dashboard-slug').val();

            var payload = {
              name: name,
              slug: slug,
              apps: []
            };

            $('#dashboard-apps_to option').each(function(i, option) {
              var app = $(option).val().split('|');
              payload.apps.push({'id': app[0], 'name': app[1]});
            });

            $.ajax({
              url: VR.Urls.getTasty('dashboard'),
              data: JSON.stringify(payload),
              dataType: 'json',
              type: 'POST',
              headers: {
                'Content-type': 'application/json'
              },
              processData: false,
              success: function(data, status) {
                if("success" === status) window.location = '/dashboard/' + slug;
              }
            });
          });
        });
    });

});
