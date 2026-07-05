/* ============================================================================
   Shared personal countdown clock, used by all 4 landing pages.

   How it works:
   - The first time a visitor lands on ANY of the 4 pages, we start a 1-minute
     personal window and store its deadline in localStorage (key below). This
     is a real, honest "your access window" timer -- not a fake per-page reset --
     so if the same visitor moves between landing pages, or refreshes, they see
     one consistent countdown instead of it jumping back to 01:00 every time.
   - If the window expires, a fresh 1-minute window starts automatically. This
     keeps the timer always useful instead of getting stuck at 00:00.
   - Every element with class "cd-mins" / "cd-secs" on the page is kept in
     sync, once per second. Any ancestor/element with class "countdown-clock"
     gets a "cc-critical" class added in the final 30 seconds, so the visual
     clock (see the .countdown-clock CSS on each page) can intensify -- faster
     pulse, redder glow -- to build urgency as time runs out.
   - Call initCountdown() after the DOM is ready.
   ============================================================================ */
(function () {
  var KEY = 'do_access_deadline';
  var DURATION_MS = 60 * 1000;     // 1 minute
  var CRITICAL_MS = 30 * 1000;     // last 30 seconds = "critical" styling

  function getDeadline() {
    var d = 0;
    try { d = parseInt(localStorage.getItem(KEY), 10); } catch (e) {}
    if (!d || isNaN(d) || d <= Date.now()) {
      d = Date.now() + DURATION_MS;
      try { localStorage.setItem(KEY, String(d)); } catch (e) {}
    }
    return d;
  }

  function pad(n) { return String(n).padStart(2, '0'); }

  window.initCountdown = function initCountdown() {
    var deadline;
    try { deadline = getDeadline(); } catch (e) { deadline = Date.now() + DURATION_MS; }

    function tick() {
      var diff = deadline - Date.now();
      if (diff <= 0) {
        deadline = Date.now() + DURATION_MS;
        try { localStorage.setItem(KEY, String(deadline)); } catch (e) {}
        diff = DURATION_MS;
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
})();
