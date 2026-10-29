/** @namespace $.SickShift.Root */
/** @namespace $.SickShift.glideFancyBoxOpen */
/** @namespace config.TVShowList */
/** @namespace config.useIMDbInfo */
/** @namespace $.SickShift.config.useFuzzy */
/** @namespace $.SickShift.config.dateFormat */
/** @namespace $.SickShift.config.timeFormat */
/** @namespace $.SickShift.config.fuzzyTrimZero */
/** @namespace $.SickShift.config.glideStartAt */
/** @namespace $.SickShift.config.glideSlideTime */
$(document).ready(function() {

	// handle the show selection dropbox
	var select$ = $('#pickShow'), populateItem;
	select$.change(function() {
		var val = $(this).val();
		if (0 !== val)
			window.location.href = $.SickShift.Root + '/home/view-show?tvid_prodid=' + val;
	});
	populateItem = function(data) {
		if (!data.element || !$(data.element).hasClass('ended')) {
			return data.text;
		}
		return $('<span class="ended"><span class="label" title="">ended</span> <i>' + data.text + '</i></span>');
	}
	// https://github.com/bevacqua/fuzzysearch
	function fuzzysearch(needle, haystack) {
		var hlen = haystack.length;
		var nlen = needle.length;
		if (nlen > hlen) {
			return false;
		}
		if (nlen === hlen) {
			return needle === haystack;
		}
		outer: for (var i = 0, j = 0; i < nlen; i++) {
			var nch = needle.charCodeAt(i);
			while (j < hlen) {
				if (haystack.charCodeAt(j++) === nch) {
					continue outer;
				}
			}
			return false;
		}
		return true;
	}

	const white_space_regex = /\W/gui;
	function sel_matcher(params, data) {

		// If there are no search terms, return all of the data
		if ($.trim(params.term) === '') {
			return data;
		}

		// Do not display the item if there is no 'text' property
		if (typeof data.text === 'undefined') {
			return null;
		}

		// `params.term` should be the term that is used for searching
		var param_term = params.term.toLowerCase().trim().replace(white_space_regex, '');

		if ('undefined' !== typeof data.children) {
			// `data.children` contains options to match against
			var filteredChildren = [];
			$.each(data.children, function (idx, child) {
				// `child.text` is the text that is displayed for the data object
				var param_data = child.text.toLowerCase().trim().replace(white_space_regex, '');

				if (fuzzysearch(param_term, param_data)) {
					filteredChildren.push(child);
				}
			});

			// If any of the group's children match,
			// then set the matched children on the group and return the group object
			if (filteredChildren.length) {
				let modifiedData = $.extend({}, data, true);
				modifiedData.children = filteredChildren;

				// You can return modified objects from here
				// This includes matching the `children` how you want in nested data sets
				return modifiedData;
			}
		}

		// `data.text` is the text that is displayed for the data object
		var param_data = data.text.toLowerCase().trim().replace(white_space_regex, '');
		if (fuzzysearch(param_term, param_data)) {
			// You can return modified objects from here
			// This includes matching the `children` how you want in nested data sets
			return $.extend({}, data, true);
		}

		// Return `null` if the term should not be displayed
		return null;
	}

	select$.select2({templateResult: populateItem, templateSelection:populateItem, matcher: sel_matcher});

	$('#prevShow, #nextShow').on('click', function() {
		var select$ = $('#pickShow'),
			index = $.inArray(select$.find('option:selected').val(), config.TVShowList);
		//noinspection JSUnresolvedVariable
		select$.find('option[value="' + config.TVShowList[('nextShow' === $(this).attr('id')
			? (index < config.TVShowList.length - 1 ? index + 1 : 0)
			: (0 < index ? index - 1 : config.TVShowList.length - 1))] + '"]').prop('selected', !0);
		select$.change();
		return !1;
	});

	$('#seasonJump').change(function() {
		var id = $(this).val();
		if (id && 'jump' !== id) {
			$('html,body').animate({scrollTop: $(id).offset().top}, 'slow');
			location.hash = id;
		}
		$(this).val('jump');
	});

	var slideGap = 5,
	slideCount = $('.cast').length;

	if (0 < slideCount) {

		function slideTime(){
			return 0 < $.SickShift.config.glideSlideTime && !$.SickShift.glideFancyBoxOpen
				? $.SickShift.config.glideSlideTime : !1;
		}

		$.calcSlideCount = function(initSet){
			var maxCount = Math.floor($('.glide__track').width() / (170 + slideGap)),
				perView = maxCount < slideCount ? maxCount : slideCount;
			if (initSet)
				return {perView: perView, isNotEnd: maxCount < slideCount};

			if (maxCount < slideCount) {
				$.glide.update({perView: perView, autoplay: slideTime()});
				if (slideTime()){
					$.glide.play();
				}
			} else {
				$.glide.pause();
				$.glide.update({perView: perView, autoplay: !1});
				$.glide.go('=0');
			}
		}

		var initGlideVars = $.calcSlideCount(!0),
			startAt = $('.cast[data-rid="' + $.SickShift.config.glideStartAt + '"]').index();
		$.glide = new Glide('.cast-holder', {
			type: 'carousel',
			gap: slideGap,
			startAt: -1 === startAt ? 0 : startAt,
			peek: 0,
			perSwipe: '|',
			perView: initGlideVars.perView,
			autoplay: initGlideVars.isNotEnd && slideTime()
		});

		$.glide.on('resize', function(){
			$.calcSlideCount(!1);
			$('#display-show .cast-bg').each(function (i, oImage){
				scaleImage(oImage);
			});
		});

		$.glide.on('run.after', function(){
			saveGlide();
		});

		function initFancybox(){
			try {
				setupFancyBox();
			} catch {
				var fancy = $.SickShift.Root + '/js/fancybox/jquery.fancybox.min';
				$.getScript(fancy + '.js', function() {
					$('head').append('<link rel="stylesheet" href="' + fancy + '.css">');
					setupFancyBox();
				});
			}
		}

		function setupFancyBox(){
			if (!!$('a[rel="glide"]').length){
				$().fancybox(jQuery.extend({
					selector: 'li:not(.glide__slide--clone) a[rel="glide"]',
					slideShow: {
						speed: Math.abs($.SickShift.config.glideSlideTime)
					},
					afterShow: function(instance, slide){
						$.SickShift.glideFancyBoxOpen = !0;
						$.glide.go('=' + slide.index);
					},
					// adhere to standard convention of prefixing args with _ to denote these exist but are unused here
					beforeShow: function(_instance, _slide){
						if (!$.SickShift.glideFancyBoxOpen && 0 < $.SickShift.config.glideSlideTime){
							$.glide.pause();
							$.glide.update({autoplay: !1});
						}
					},
					afterClose: function(_instance, _slide){
						if (!!$.SickShift.glideFancyBoxOpen){
							$.SickShift.glideFancyBoxOpen = !1;
							if (0 < $.SickShift.config.glideSlideTime){
								$.calcSlideCount(!1);
							}
						}
					},
				}, $.sgFancyBoxOptions));
			}
		}

		$.glide.on('build.after', function(){
			initFancybox();
			$('.cast.glide__slide').removeClass('last');
			$('.cast.glide__slide:not(.glide__slide--clone):last').addClass('last');
			$('.cast.body .cast-bg, #pin-glide, .glide-arrows, .cast.body .links').fadeIn('slow', 'linear');
			$('#about-hide').addClass('hide');
			$('#about-show').removeClass('hide');
			$('.glide__slide--clone').click(function(){
				$('li[data-rid="' + $(this).data('rid') + '"]:not(.glide__slide--clone) a[rel="glide"]')[0].click();
				return !1;
			});
			$('#display-show .cast-bg').each(function (i, oImage){
				scaleImage(oImage);
			});
		});

		window.onload = function(){
			$.glide.mount();
		};

		function saveGlide(saveTime){
			if (!$.SickShift.glideFancyBoxOpen){
				var params = {};
				if (!slideTime()){
					params = {
						tvid_prodid: $('#tvid-prodid').val(),
						start_at: $('.cast.glide__slide--active').data('rid')
					};
				}
				if (saveTime){
					params.slidetime = $.SickShift.config.glideSlideTime;
				}
				if (!$.isEmptyObject(params)){
					$.get($.SickShift.Root + '/home/set-display-show-glide', params);
				}
			}
		}

		var ivTimes = [10000, 6000, 3000];
		function pinState(el$){
			var ivTime = slideTime();

			el$.removeClass('one two three four');
			if (!ivTime) {
				el$.addClass('one');
			} else if (ivTimes[0] === ivTime) {
				el$.addClass('two');
			} else if (ivTimes[1] === ivTime) {
				el$.addClass('three');
			} else {
				el$.addClass('four');
			}
		}

		var pinGlide$ = $('#pin-glide');
		pinState(pinGlide$);
		pinGlide$.on('click', function (){
			var ivTime = slideTime();

			if (!ivTime) { // unpause as was paused when clicked
				$.SickShift.config.glideSlideTime *= -1;
			} else if (ivTimes[0] === ivTime) {
				$.SickShift.config.glideSlideTime = ivTimes[1];
			} else if (ivTimes[1] === ivTime) {
				$.SickShift.config.glideSlideTime = ivTimes[2];
			} else {
				$.SickShift.config.glideSlideTime = -1 * ivTimes[0];
			}
			pinState($(this));
			$.calcSlideCount(!1);
			saveGlide(!0);
		});
	}

	$('.details-plot').collapser({
		mode: 'lines',
		truncate: 10,
		showText: '<i class="sgicon-arrowdown"></i>more',
		hideText: '<i class="sgicon-arrowup"></i>less',
		showClass: 'show-class'
	});

	if (config.useIMDbInfo){
		$.fn.generateStars = function() {
			return this.each(function(i,e){$(e).html($('<span/>').width($(e).text()*12));});
		};
		$('.imdbstars').generateStars();
	}

	$('#changeStatus').on('click', function() {
		var epArr = [];

		$('.epCheck').each(function() {
			this.checked && epArr.push($(this).attr('id'))
		});
		if (epArr.length)
			window.location.href = $.SickShift.Root + '/home/set-show-status?tvid_prodid=' + $('#tvid-prodid').val() +
				'&eps=' + epArr.join('|') + '&status=' + $('#statusSelect').val();
	});

	// show/hide different types of rows when the checkboxes are changed
	var el = $('#checkboxControls').find('input');
	el.change(function() {
		$(this).showHideRows($(this).attr('id'));
	});

	// initially show/hide all the rows according to the checkboxes
	el.each(function() {
		var status = this.checked;
		$('tr.' + $(this).attr('id')).each(function() {
			status && $(this).show() || $(this).hide();
		});
	});

	$.fn.showHideRows = function(whichClass) {

		var status = $('#checkboxControls > input, #' + whichClass).prop('checked');
		$('tr.' + whichClass).each(function() {
			status && $(this).show() || $(this).hide();
		});

		// hide season headers with no episodes under them
		$('tr.seasonheader').each(function() {
			var numRows = 0;
			var seasonNo = $(this).attr('id');
			$('tr.' + seasonNo + ' :visible').each(function() {
				numRows++
			});
			var el = $('#' + seasonNo + '-cols');
			if (0 === numRows) {
				$(this).hide();
				el.hide();
			} else {
				$(this).show();
				el.show();
			}

		});
	};

	function checkState(state){
		$('.epCheck:visible, .seasonCheck:visible').prop('checked', state)
	}
	// selects all visible episode checkboxes.
	$('.seriesCheck').on('click', function() { checkState(!0); });

	// clears all visible episode checkboxes and the season selectors
	$('.clearAll').on('click', function() { checkState(!1); });

	function setEpisodeSceneNumbering(forSeason, forEpisode, sceneSeason, sceneEpisode) {
		var show = $('#tvid-prodid').val();

		if ('' === sceneSeason) sceneSeason = null;
		if ('' === sceneEpisode) sceneEpisode = null;

		$.getJSON($.SickShift.Root + '/home/set-scene-numbering',
			{
				'tvid_prodid': show,
				'for_season': forSeason,
				'for_episode': forEpisode,
				'scene_season': sceneSeason,
				'scene_episode': sceneEpisode
			},
			function(data) {
				//	Set the values we get back
				var value = ((null === data.sceneSeason || null === data.sceneEpisode)
						? '' : data.sceneSeason + 'x' + data.sceneEpisode);
				$(document.getElementById('sceneSeasonXEpisode_' + show + '_' + forSeason + '_' + forEpisode))
					.val(value).attr('value', value);
				if (!data.success)
					alert(data.errorMessage ? data.errorMessage : 'Update failed.');
			}
		);
	}

	function setAbsoluteSceneNumbering(forSeason, forEpisode, sceneAbsolute) {
		var show = $('#tvid-prodid').val();

		if ('' === sceneAbsolute)
			sceneAbsolute = null;

		$.getJSON($.SickShift.Root + '/home/set-scene-numbering',
			{
				'tvid_prodid': show,
				'for_season': forSeason,
				'for_episode': forEpisode,
				'scene_absolute': sceneAbsolute
			},
			function(data) {
				//	Set the values we get back
				var value = (null === data.sceneAbsolute ? '' : data.sceneAbsolute);
				$(document.getElementById('sceneAbsolute_' + show + '_' + forSeason + '_' + forEpisode))
					.val(value).attr('value', value);
				if (!data.success)
					alert(data.errorMessage ? data.errorMessage : 'Update failed.');
			}
		);
	}

	function qTips(select$){
		select$.each(function() {
			$(this).qtip({
				show: {solo:true},
				position: {viewport:$(window), my:'left center', adjust:{y:-10, x:2}},
				style: {classes:'qtip-dark qtip-rounded qtip-shadow qtip-maxwidth'}
			});
		});
	}
	qTips($('.addQTip'));

	function tableInit(table$) {
		const sbroot$ = $('#sbRoot');
		sbroot$.ajaxEpSearch();
		sbroot$.ajaxEpSubtitlesSearch();

		if ($.SickShift.config.useFuzzy) {
			fuzzyMoment({
				containerClass: '.airdate',
				dateHasTime: !1,
				dateFormat: $.SickShift.config.dateFormat,
				timeFormat: $.SickShift.config.timeFormat,
				trimZero: $.SickShift.config.fuzzyTrimZero
			});
		}

		table$.each(function (i, obj) {
			$(obj).has('tbody.collapse tr').tablesorter({
				widgets: ['zebra'],
				selectorHeaders: '> thead tr.tablesorter-headerRow th',
				textExtraction: {
					'.tablesorter-ep-num': function(node) {
						var n = /(\d+)\)?$/img.exec(''+$(node).find('span').text()); return (null === n ? '' : n[1]); },
					'.tablesorter-ep-scene': function(node) {
							var n = $(node).find('input'); return n.val() || n.attr('placeholder'); },
					'.tablesorter-airdate': function(node) { return $(node).find('span').attr('data-airdate') || ''; }
				},
				headers: {
					'.tablesorter-no-sort': {sorter: !1, parser: !1},
					'.tablesorter-ep-num': {sorter: 'digit'},
					'.tablesorter-airdate': {sorter: 'digit'}
				}
			});

			$(obj).find('.seasonCheck').on('click', function() {
				var seasCheck = this, seasNo = $(seasCheck).attr('id');

				$(obj).find('.epCheck:visible').each(function() {
					var epParts = $(this).attr('id').split('x');
					if (epParts[0] === seasNo)
						this.checked = seasCheck.checked

				});
			});

			var lastCheck = null;
			$(obj).find('.epCheck').on('click', function(event) {

				if (!lastCheck || !event.shiftKey) {
					lastCheck = this;
					return;
				}

				var check = this, found = 0;
				$(obj).find('.epCheck').each(function() {
					switch(found) {
						case 2:
							return !1;
						case 1:
							this.checked = lastCheck.checked;
					}
					(this === check || this === lastCheck) && found++;
				});
				lastCheck = this;
			});

			qTips($(obj).find('.addQTip'));
			plotter($(obj).find('.plotInfo'));

			$(obj).find('.sceneSeasonXEpisode').change(function() {
				//	Strip non-numeric characters
				$(this).val($(this).val().replace(/[^0-9xX]*/g, ''));

				var forSeason = $(this).attr('data-for-season'),
					forEpisode = $(this).attr('data-for-episode'),
					m = $(this).val().match(/^(\d+)x(\d+)$/i),
					sceneSeason = m && m[1] || null, sceneEpisode = m && m[2] || null;

				setEpisodeSceneNumbering(forSeason, forEpisode, sceneSeason, sceneEpisode);
			});

			$(obj).find('.sceneAbsolute').change(function() {
				//	Strip non-numeric characters
				$(this).val($(this).val().replace(/[^0-9]*/g, ''));

				var forSeason = $(this).attr('data-for-season'),
					forEpisode = $(this).attr('data-for-episode'),
					m = $(this).val().match(/^(\d{1,4})$/i),
					sceneAbsolute = m && m[1] || null;

				setAbsoluteSceneNumbering(forSeason, forEpisode, sceneAbsolute);
			});
		});
	}
	tableInit($('.sickbeardTable'));

	$.SickShift.season = [];
	$.SickShift.run = !1;
	$('button[id*="showseason-"]').on('click', function() {
		const this$ = $('#' + this.id),
			table$ = this$.parents('.sickbeardTable');

		if (0 < table$.find('tbody').find('tr').length) {
			table$.toggleClass('open');
		} else {
			table$.find('span.images').toggleClass('hide');
			this$.toggleClass('hide');
			function fetchSeason() {
				if (0 === $.SickShift.season.length)
					return;

				var season = $.SickShift.season[0];
				$.SickShift.season.shift();
				$.getJSON($.SickShift.Root + '/home/season-render', {'tvid_prodid': $('#tvid-prodid').val(), 'season': season},
					function(data) {
						if (!data.success) {
							alert('Season listing failed.');
						} else {
							table$.find('tbody').html(data.success);
							tableInit(table$);
						}
						table$.toggleClass('open');
						this$.toggleClass('hide');
						table$.find('span.images').toggleClass('hide');
						fetchSeason()
					}
				);
			}
			$.SickShift.season.push(this.id);
			var result = [];
			$.each($.SickShift.season, function(i, e) {
				if (-1 === $.inArray(e, result)) result.push(e);
			});
			$.SickShift.season = result;
			if (!$.SickShift.run && 1 === $.SickShift.season.length) $.SickShift.run = !0 && fetchSeason();
		}
		return !1;
	});

	$('button.allseasons').on('click', function() {
		$('table.sickbeardTable:not(.display-season)').each(function() {
			$(this).find('button[id*="showseason-"]').click();
		});

		const liveStates = $('#display-show');
		liveStates.toggleClass('min');
		$.get($.SickShift.Root + '/live-panel/?allseasons='
			+ String.prototype.toLowerCase.apply(+liveStates.hasClass('min')));
		return !1;
	});

	// Click anywhere on season header bar to toggle collapse
	$(document).on('click', '.row-seasonheader', function(e) {
		if ($(e.target).closest('button, a, input, select, .btn').length > 0) {
			return;
		}
		const $btn = $(this).find('button[id*="showseason-"]');
		if ($btn.length > 0) {
			$btn.trigger('click');
		}
	});

	// Cast & Poster zoom and bluish glow on hold / mousedown
	$(document).on('mousedown', '#display-show .cast.body, #display-show .cast .thumb, #display-show .cast-bg, #display-show #posterCol, #display-show #posterCol a, #display-show #posterCol .tvshowImg', function(e) {
		const $target = $(this).closest('.cast, #posterCol');
		$target.addClass('holding-click');
		$target.find('.thumb, .cast-bg, .tvshowImg').addClass('holding-click');
	});

	$(document).on('mouseup mouseleave', '#display-show .cast.body, #display-show .cast .thumb, #display-show .cast-bg, #display-show #posterCol, #display-show #posterCol a, #display-show #posterCol .tvshowImg', function(e) {
		const $target = $(this).closest('.cast, #posterCol');
		$target.removeClass('holding-click');
		$target.find('.thumb, .cast-bg, .tvshowImg').removeClass('holding-click');
	});

	// Prevent browser native image dragging while holding
	$(document).on('dragstart', '#display-show .cast img, #display-show .cast a, #display-show #posterCol img', function(e) {
		e.preventDefault();
		return false;
	});

	// Episode Delete Handler
	let epToDelete = null;
	$(document).on('click', '.ep-delete-btn', function(e) {
		e.preventDefault();
		e.stopPropagation();

		const $btn = $(this);
		const $row = $btn.closest('tr');
		const tvidProdid = $btn.data('tvid-prodid') || $('#tvid-prodid').val();
		const season = $btn.data('season');
		const episode = $btn.data('episode');
		const hasFile = $btn.data('has-file') == '1' || $row.data('has-file') == '1';
		const location = $btn.data('location') || '';
		const showname = $btn.data('showname') || $('#showtitle').data('showname') || '';

		epToDelete = {
			$row: $row,
			$btn: $btn,
			tvidProdid: tvidProdid,
			season: season,
			episode: episode,
			hasFile: hasFile,
			location: location,
			showname: showname
		};

		// Create or show modal
		let $modal = $('#sg-delete-ep-modal');
		if (!$modal.length) {
			$('body').append(`
				<div id="sg-delete-ep-modal" style="display:none; position:fixed; z-index:999999; left:0; top:0; width:100%; height:100%; background:rgba(0,0,0,0.7); backdrop-filter:blur(3px); align-items:center; justify-content:center;">
					<div class="sg-del-card" style="background:#1b2028; border:1px solid #e05252; box-shadow:0 0 25px rgba(224,82,82,0.4); border-radius:8px; padding:24px 28px; width:440px; max-width:92vw; color:#f0f0f0; font-family:sans-serif;">
						<h3 style="margin:0 0 14px; font-size:17px; font-weight:700; color:#ff5252; display:flex; align-items:center; gap:8px;">
							<i class="sgicon-delete" style="font-size:18px;"></i> Confirmer la suppression
						</h3>
						<p style="margin:0 0 12px; font-size:13.5px; line-height:1.45; color:#ddd;">
							Êtes-vous sûr de vouloir supprimer définitivement cet épisode ?
						</p>
						<div id="sg-del-info" style="background:rgba(0,0,0,0.35); border-left:3px solid #ff5252; border-radius:4px; padding:10px 14px; margin-bottom:18px; font-size:12.5px; color:#bbb; line-height:1.5;"></div>
						<div style="display:flex; justify-content:flex-end; gap:10px;">
							<button type="button" id="sg-del-cancel" class="btn btn-default" style="padding:6px 16px; border-radius:4px; font-weight:600;">Annuler</button>
							<button type="button" id="sg-del-confirm" class="btn btn-danger" style="padding:6px 18px; border-radius:4px; font-weight:600; background:#e05252; border-color:#e05252;">Supprimer pour de vrai</button>
						</div>
					</div>
				</div>
			`);
			$modal = $('#sg-delete-ep-modal');

			$modal.on('click', function(e) {
				if (e.target === this) {
					$modal.css('display', 'none');
				}
			});

			$('#sg-del-cancel').on('click', function() {
				$modal.css('display', 'none');
			});

			$('#sg-del-confirm').on('click', function() {
				if (!epToDelete) return;
				const btn = $(this);
				btn.prop('disabled', true).text('Suppression en cours...');

				$.ajax({
					url: $.SickShift.Root + '/home/delete_episode',
					data: {
						tvid_prodid: epToDelete.tvidProdid,
						season: epToDelete.season,
						episode: epToDelete.episode,
						delete_file: '1'
					},
					dataType: 'json',
					success: function(resp) {
						btn.prop('disabled', false).text('Supprimer pour de vrai');
						$modal.css('display', 'none');
						if (resp && resp.result === 'success') {
							// Update row in table
							const $row = epToDelete.$row;
							$row.removeClass('good archived wanted').addClass('skipped');
							$row.attr('data-has-file', '0');
							$row.find('.col-status').html('<span class="quality">Ignoré</span>');
							$row.find('.col-ep span.addQTip').removeAttr('title');
							epToDelete.$btn.replaceWith('<span style="color:#666; font-size:12px;">—</span>');
							$row.css('transition', 'background-color 500ms ease').css('background-color', 'rgba(224,82,82,0.18)');
							setTimeout(() => {
								$row.css('background-color', '');
							}, 1500);
						} else {
							alert((resp && resp.message) ? resp.message : 'Erreur lors de la suppression.');
						}
					},
					error: function(xhr, status, err) {
						btn.prop('disabled', false).text('Supprimer pour de vrai');
						$modal.css('display', 'none');
						alert('Erreur serveur lors de la suppression: ' + (err || status));
					}
				});
			});
		}

		let infoHtml = `<strong>${epToDelete.showname || 'Série'}</strong> — Saison ${epToDelete.season}, Épisode ${epToDelete.episode}`;
		if (epToDelete.hasFile || epToDelete.location) {
			const fname = epToDelete.location.split('/').pop() || 'fichier';
			infoHtml += `<br><span style="color:#ff8888;">Fichier disque :</span> <span style="word-break:break-all;">${fname}</span><br><em style="color:#ffaaaa; font-size:11.5px;">⚠️ Le fichier sera physiquement effacé de votre disque dur.</em>`;
		} else {
			infoHtml += `<br><em>Aucun fichier local associé. Le statut sera réinitialisé à Ignoré.</em>`;
		}

		$('#sg-del-info').html(infoHtml);
		$modal.css('display', 'flex');
	});

});
