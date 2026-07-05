/* ============================================================================
   Shared personal countdown timer, used by all 4 landing pages.

   How it works:
   - The first time a visitor lands on ANY of the 4 pages, we start a 25-minute
     personal window and store its deadline in localStorage (key below). This
     is a real, honest "your access window" timer — not a fake per-page reset —
     so if the same visitor moves between landing pages, or refreshes, they see
     one consistent countdown instead of it jumping back to 25:00 every time.
   - If the window expires (visitor comes back after 25+ minutes), a fresh
     25-minute window starts automatically. This keeps the timer always useful
     instead of getting stuck at 00:00.
   - Any element with class "cd-mins" / "cd-secs" on the page is kept in sync,
     once per second. Call initCountdown() after the DOM is ready.
   ============================================================================ */
(function () {
  var KEY = 'do_access_deadline';
  var DURATION_MS = 25 * 60 * 1000; // 25 minutes

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
    }
    tick();
    setInterval(tick, 1000);
  };
})();
