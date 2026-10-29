/** @namespace $.SickShift.Root */
/** @namespace $.SickShift.Host */
/** @namespace $.SickShift.Port */
/** @namespace $.SickShift.UseHttps */
/** @namespace $.SickShift.PID */
/** @namespace data.msg */

var sgRoot = $.SickShift.Root,
	browserUrl = window.location.protocol + '//' + window.location.host + sgRoot,
	baseUrl = 'http' + ($.SickShift.UseHttps ? 's' : '') + '://' + $.SickShift.Host + ':'
		+ (('' == sgRoot) ? $.SickShift.Port : location.port) + sgRoot,
	isAliveUrl = sgRoot + '/home/is-alive/',
	timeoutId;
$.SickShift.numRestartWaits = 0;

function is_alive() {
	timeoutId = 0;

	//noinspection JSUnusedLocalSymbols
	$.ajax({
		'url': isAliveUrl,
		'type': 'GET',
		'dataType': 'jsonp',
		'success': function(data) {
			var resp = data.msg.toString();
			if ('nope' == resp) {
				// if initialising then just wait and try again

				$('#shut_down_message').find('.spinner,.hide-yes').removeClass();
				$('#restart_message').removeClass();
				setTimeout(is_alive, 100);

			} else if (/undefined/i.test($.SickShift.PID) || $.SickShift.PID == resp) {
				// if this is before we've even shut down then just try again later

				setTimeout(is_alive, 100);

			} else {
				// if we're ready to go then redirect to new url

				$('#restart_message').find('.spinner,.hide-yes').removeClass();
				$('#refresh_message').removeClass();
				window.location = baseUrl + '/home/';
			}
		},
		'error': function(XMLHttpRequest, textStatus, errorThrown) {
			setTimeout(is_alive, 100);
		}
	});
}

$(document).ready(function() {

	is_alive();

	//noinspection JSUnusedLocalSymbols
	$('#shut_down_message').ajaxError(function(e, jqxhr, settings, exception) {
		$.SickShift.numRestartWaits += 1;

		$('#shut_down_message').find('.spinner,.hide-yes').removeClass();

		var restart$ = $('#restart_message');
		restart$.removeClass();

		isAliveUrl = baseUrl + '/home/is-alive/';

		// If using https and the port or protocol changed, then wait 5 seconds before redirect because ajax calls will
		// fail with untrusted certs or when a http ajax request is made from https with a mixed content error.
		if ($.SickShift.UseHttps || 'https:' == window.location.protocol) {
			if (browserUrl != baseUrl) {

				timeoutId = 1;
				setTimeout(function() {
					$('#restart_message').find('.spinner,.hide-yes').removeClass();
					$('#refresh_message').removeClass();
				}, 3000);
				setTimeout(function() {
					window.location = baseUrl + '/home/'
				}, 5000);
			}
		}

		// if it is taking forever just give up
		if (90 < $.SickShift.numRestartWaits) {

			restart$.find('.spinner,.yes,.hide-no').removeClass();
			$('#restart_fail_message').removeClass();
			return;
		}

		if (0 == timeoutId) {

			timeoutId = setTimeout(is_alive, 100);
		}
	});

});
