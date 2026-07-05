/* ============================================================================
   Shared countdown clock, used by all 4 landing pages.

   How it works:
   - Every time this page loads (first visit, refresh, or coming back later),
     the clock always starts fresh at exactly 1 minute and counts down to 0.
     There is no persistence across page loads -- so it's simple and always
     predictable: land on the page, the clock says 01:00 / 00:00 and starts
     ticking down.
   - If it reaches 0, it simply restarts at 1 minute automatically, so it
     never gets stuck.
   - Every element with class "cd-mins" / "cd-secs" on the page is kept in
     sync, once per second. Any ancestor/element with class "countdown-clock"
     gets a "cc-critical" class added in the final 30 seconds, so the visual
     clock (see the .countdown-clock CSS on each page) can intensify -- faster
     pulse, redder glow -- to build urgency as time runs out.
   - Call initCountdown() after the DOM is ready.
   ============================================================================ */
(function () {
  var DURATION_MS = 60 * 1000;     // 1 minute
  var CRITICAL_MS = 30 * 1000;     // last 30 seconds = "critical" styling

  function pad(n) { return String(n).padStart(2, '0'); }

  window.initCountdown = function initCountdown() {
    var deadline = Date.now() + DURATION_MS;

    function tick() {
      var diff = deadline - Date.now();
      if (diff <= 0) {
        deadline = Date.now() + DURATION_MS;
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
