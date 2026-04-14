/* ============================================================
   DIGITAL ONLINE — Master Tracking Script
   Tracks: page identity, A/B variant, button clicks,
   WhatsApp clicks, form submits, scroll depth,
   video play/complete, time on page
   Fires to: dataLayer (GTM → GA4) + fbq() (Facebook Pixel)
   ============================================================ */

(function () {
  'use strict';

  /* ── 1. PAGE IDENTITY ─────────────────────────────────── */
  var path  = window.location.pathname.toLowerCase();
  var query = window.location.search;
  var params = new URLSearchParams(query);

  var PAGE_MAP = {
    'landing_option1': { type: 'landing', variant: 'landing_A', funnel_step: 'entry', ab_group: 'A' },
    'landing_option2': { type: 'landing', variant: 'landing_B', funnel_step: 'entry', ab_group: 'B' },
    'landing_option3': { type: 'landing', variant: 'landing_C', funnel_step: 'entry', ab_group: 'C' },
    'lp':              { type: 'lp',      variant: 'lp_' + (params.get('p') || '1'), funnel_step: 'entry', ab_group: 'lp_' + (params.get('p') || '1') },
    'funnel-video-1':  { type: 'video',   variant: 'funnel_video', funnel_step: 'video_1', ab_group: 'video' },
    'funnel-video-2':  { type: 'video',   variant: 'funnel_video', funnel_step: 'video_2', ab_group: 'video' },
    'funnel-video-3':  { type: 'video',   variant: 'funnel_video', funnel_step: 'video_3', ab_group: 'video' },
    'funnel-video-4':  { type: 'video',   variant: 'funnel_video', funnel_step: 'video_4', ab_group: 'video' },
    'thankyou':        { type: 'thankyou', variant: 'thankyou',   funnel_step: 'lead_confirmed', ab_group: 'conversion' },
    'webinar':         { type: 'webinar', variant: 'webinar',     funnel_step: 'webinar', ab_group: 'webinar' },
    'lp':              { type: 'lp',      variant: 'lp_' + (params.get('p') || '1'), funnel_step: 'entry', ab_group: 'lp' },
    'index':           { type: 'home',    variant: 'home',        funnel_step: 'home', ab_group: 'home' },
  };

  var pageMeta = { type: 'unknown', variant: 'unknown', funnel_step: 'unknown', ab_group: 'unknown' };
  for (var key in PAGE_MAP) {
    if (path.indexOf(key) !== -1) {
      pageMeta = PAGE_MAP[key];
      break;
    }
  }

  pageMeta.page_path = path;
  pageMeta.page_url  = window.location.href;
  pageMeta.referrer  = document.referrer || 'direct';
  pageMeta.utm_source   = params.get('utm_source')   || '';
  pageMeta.utm_medium   = params.get('utm_medium')   || '';
  pageMeta.utm_campaign = params.get('utm_campaign') || '';
  pageMeta.utm_content  = params.get('utm_content')  || '';
  pageMeta.lp_variant   = params.get('p')            || '';

  /* ── 2. HELPERS ───────────────────────────────────────── */
  window.dataLayer = window.dataLayer || [];

  function push(eventName, extra) {
    var payload = Object.assign({ event: eventName }, pageMeta, extra || {});
    window.dataLayer.push(payload);
  }

  function fbEvent(eventName, params) {
    if (typeof fbq === 'function') {
      fbq('trackCustom', eventName, Object.assign({}, pageMeta, params || {}));
    }
  }

  /* ── 3. PAGE VIEW WITH FULL CONTEXT ───────────────────── */
  push('page_view_detailed');
  fbEvent('PageViewDetailed');

  /* ── 4. BUTTON & LINK CLICKS ──────────────────────────── */
  document.addEventListener('click', function (e) {
    var el = e.target;
    // Walk up to find button/a
    while (el && el !== document.body) {
      var tag = el.tagName ? el.tagName.toLowerCase() : '';
      if (tag === 'button' || tag === 'a' || el.getAttribute('role') === 'button' ||
          el.classList.contains('btn') || el.classList.contains('button') ||
          el.classList.contains('cta') || el.classList.contains('submit')) {
        break;
      }
      el = el.parentElement;
    }
    if (!el || el === document.body) return;

    var text      = (el.innerText || el.textContent || el.value || '').trim().substring(0, 80);
    var href      = el.href || '';
    var classes   = el.className || '';
    var id        = el.id || '';
    var isWA      = href.indexOf('wa.me') !== -1 || href.indexOf('whatsapp') !== -1 ||
                    href.indexOf('api.whatsapp') !== -1 || classes.indexOf('whatsapp') !== -1 ||
                    classes.indexOf('wa-') !== -1 || text.indexOf('ווטסאפ') !== -1 ||
                    text.indexOf('WhatsApp') !== -1 || el.getAttribute('data-wa') !== null;
    var isForm    = classes.indexOf('submit') !== -1 || el.type === 'submit' ||
                    text.indexOf('שלח') !== -1 || text.indexOf('הרשם') !== -1 ||
                    text.indexOf('להרשמה') !== -1 || text.indexOf('קבל') !== -1;

    var clickData = {
      button_text:    text,
      button_href:    href.substring(0, 200),
      button_id:      id,
      button_classes: classes.substring(0, 100),
      is_whatsapp:    isWA,
      is_form_submit: isForm,
    };

    // Generic click
    push('button_click', clickData);

    // WhatsApp specific
    if (isWA) {
      push('whatsapp_click', clickData);
      fbEvent('WhatsAppClick', clickData);
      if (typeof fbq === 'function') fbq('track', 'Contact', { content_name: pageMeta.variant });
    }

    // Form submit CTA
    if (isForm) {
      push('cta_click', clickData);
      fbEvent('CTAClick', clickData);
    }

  }, true); // capture phase = catches everything

  /* ── 5. FORM SUBMITS ──────────────────────────────────── */
  document.addEventListener('submit', function (e) {
    var form = e.target;
    var formData = {};
    try {
      var inputs = form.querySelectorAll('input, select, textarea');
      inputs.forEach(function (inp) {
        var name = inp.name || inp.id || inp.type;
        var val  = inp.value;
        // Don't log password or sensitive fields
        if (inp.type === 'password' || name.indexOf('pass') !== -1) return;
        formData[name] = val.substring(0, 100);
      });
    } catch (err) {}

    push('form_submit', {
      form_id:     form.id || '',
      form_action: form.action || '',
      form_data:   JSON.stringify(formData).substring(0, 300),
    });
    fbEvent('FormSubmit', { form_id: form.id });
    if (typeof fbq === 'function') fbq('track', 'Lead', { content_name: pageMeta.variant });
  }, true);

  /* ── 6. SCROLL DEPTH ──────────────────────────────────── */
  var scrollFired = {};
  var thresholds  = [25, 50, 75, 90, 100];

  function getScrollPct() {
    var scrollTop = window.pageYOffset || document.documentElement.scrollTop;
    var docHeight = Math.max(
      document.body.scrollHeight, document.documentElement.scrollHeight,
      document.body.offsetHeight, document.documentElement.offsetHeight
    ) - window.innerHeight;
    return docHeight > 0 ? Math.round((scrollTop / docHeight) * 100) : 100;
  }

  window.addEventListener('scroll', function () {
    var pct = getScrollPct();
    thresholds.forEach(function (t) {
      if (pct >= t && !scrollFired[t]) {
        scrollFired[t] = true;
        push('scroll_depth', { scroll_pct: t });
        fbEvent('ScrollDepth', { depth: t });
      }
    });
  }, { passive: true });

  /* ── 7. TIME ON PAGE ──────────────────────────────────── */
  var timeFired = {};
  var timeMilestones = [15, 30, 60, 120, 180];

  timeMilestones.forEach(function (sec) {
    setTimeout(function () {
      if (!timeFired[sec]) {
        timeFired[sec] = true;
        push('time_on_page', { seconds: sec });
        fbEvent('TimeOnPage', { seconds: sec });
      }
    }, sec * 1000);
  });

  /* ── 8. VIMEO VIDEO TRACKING ──────────────────────────── */
  // Works with the Vimeo Player SDK already loaded on funnel-video pages
  function initVimeoTracking() {
    if (typeof Vimeo === 'undefined' || !Vimeo.Player) return;

    var iframes = document.querySelectorAll('iframe[src*="vimeo"]');
    iframes.forEach(function (iframe, idx) {
      try {
        var player = new Vimeo.Player(iframe);
        var videoId = idx + 1;

        player.on('play', function (data) {
          push('video_play', { video_index: videoId, video_seconds: Math.round(data.seconds || 0) });
          fbEvent('VideoPlay', { video_index: videoId });
          if (typeof fbq === 'function') fbq('track', 'ViewContent', { content_name: pageMeta.funnel_step + '_video' });
        });

        player.on('pause', function (data) {
          push('video_pause', { video_index: videoId, video_seconds: Math.round(data.seconds || 0), video_pct: Math.round(data.percent * 100 || 0) });
        });

        player.on('ended', function () {
          push('video_complete', { video_index: videoId });
          fbEvent('VideoComplete', { video_index: videoId });
        });

        // Milestones: 25%, 50%, 75%
        var videoPctFired = {};
        player.on('timeupdate', function (data) {
          var pct = Math.round((data.percent || 0) * 100);
          [25, 50, 75].forEach(function (t) {
            if (pct >= t && !videoPctFired[t]) {
              videoPctFired[t] = true;
              push('video_progress', { video_index: videoId, video_pct: t });
              fbEvent('VideoProgress', { video_index: videoId, pct: t });
            }
          });
        });

      } catch (err) {}
    });
  }

  // Try immediately, then retry after SDK loads
  initVimeoTracking();
  window.addEventListener('load', initVimeoTracking);
  setTimeout(initVimeoTracking, 2000);

  /* ── 9. VISIBILITY / TAB FOCUS ────────────────────────── */
  document.addEventListener('visibilitychange', function () {
    push('page_visibility', { visible: !document.hidden });
  });

  /* ── 10. EXIT INTENT ──────────────────────────────────── */
  var exitFired = false;
  document.addEventListener('mouseleave', function (e) {
    if (!exitFired && e.clientY <= 5) {
      exitFired = true;
      push('exit_intent', { scroll_pct: getScrollPct() });
      fbEvent('ExitIntent', { scroll_pct: getScrollPct() });
    }
  });

  /* ── 11. SESSION ID (link leads across pages) ─────────── */
  function getSessionId() {
    var key = 'do_session';
    var sid = sessionStorage.getItem(key);
    if (!sid) {
      sid = 'do_' + Date.now() + '_' + Math.random().toString(36).substring(2, 8);
      sessionStorage.setItem(key, sid);
    }
    return sid;
  }

  pageMeta.session_id = getSessionId();

  // Re-push page_view with session_id now that it's set
  push('session_page_view');

})();
