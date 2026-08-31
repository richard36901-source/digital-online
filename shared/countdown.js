/* ============================================================================
   Shared countdown clock, used by the landing pages.

   How it works:
   - The deadline is stored in sessionStorage, so refreshing the page (or
     coming back to it later in the same tab) does NOT reset the clock back
     to 01:00 -- it keeps counting from where it really was. This matters
     because visitors who reload or return (retargeting, checking a price
     twice) would otherwise see an obviously-fake timer that always reads
     ~1:00, which quietly kills trust right at the moment they're deciding
     whether to leave their details. A brand new tab/session still starts
     a fresh clock.
   - If it reaches 0, it restarts at 1 minute automatically (and clears the
     stored deadline so the new cycle is also fresh), so it never gets stuck.
   - Every element with class "cd-mins" / "cd-secs" on the page is kept in
     sync, once per second. Any ancestor/element with class "countdown-clock"
     gets a "cc-critical" class added in the final 30 seconds, so the visual
     clock (see the .countdown-clock CSS on each page) can intensify -- faster
     pulse, redder glow -- to build urgency as time runs out.
   - Call initCountdown() after the DOM is ready. As a safety net, this file
     also starts the clock on its own (see the bottom of this file) so the
     countdown is guaranteed to start even if a page's own "call initCountdown
     on DOMContentLoaded" wiring never fires (e.g. because that listener was
     attached too late and the event had already passed).
   ============================================================================ */
(function () {
  var DURATION_MS = (window.COUNTDOWN_DURATION_MS || 60 * 1000);  // 1 minute default, overridable via window.COUNTDOWN_DURATION_MS
  var CRITICAL_MS = 30 * 1000;     // last 30 seconds = "critical" styling
  var STORAGE_KEY = 'cd_deadline_' + location.pathname;
  var started = false;             // guard against double-starting the clock

  function pad(n) { return String(n).padStart(2, '0'); }

  function readStoredDeadline() {
    try {
      var v = parseInt(sessionStorage.getItem(STORAGE_KEY), 10);
      return (v && v > Date.now()) ? v : null;
    } catch (e) { return null; }
  }
  function storeDeadline(deadline) {
    try { sessionStorage.setItem(STORAGE_KEY, String(deadline)); } catch (e) {}
  }

  window.initCountdown = function initCountdown() {
    if (started) return;           // already running -- don't stack intervals
    started = true;

    var deadline = readStoredDeadline() || Date.now() + DURATION_MS;
    storeDeadline(deadline);

    function tick() {
      var diff = deadline - Date.now();
      if (diff <= 0) {
        deadline = Date.now() + DURATION_MS;
        diff = DURATION_MS;
        storeDeadline(deadline);
      }
      var m = Math.floor(diff / 60000);
      var s = Math.floor((diff % 60000) / 1000);
      var mins = document.querySelectorAll('.cd-mins');
      var secs = document.querySelectorAll('.cd-secs');
      for (var i = 0; i < mins.length; i++) mins[i].textContent = pad(m);
      for (var j = 0; j < secs.length; j++) secs[j].textContent = pad(s);

      var critical = diff <= CRITICAL_MS;
      var clocks = document.querySelectorAll('.countdown-clock');
      for (var k = 0; k < clocks.length; k++) clocks[k].classList.toggle('cc-critical', critical);
    }
    tick();
    setInterval(tick, 1000);
  };

  // Safety net: this script loads in <head>, well before the page body is
  // parsed, so document.readyState here is reliably "loading" -- meaning we
  // can register a DOMContentLoaded listener now and be certain it will
  // fire. If for any reason this code runs after the DOM is already ready,
  // start immediately instead of waiting for an event that already passed.
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', window.initCountdown);
  } else {
    window.initCountdown();
  }
})();
