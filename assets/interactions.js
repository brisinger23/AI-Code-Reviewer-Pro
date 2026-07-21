/* AI Code Reviewer Pro — micro-interactions.
   Self-installing and fully defensive: if anything is unavailable the UI still
   works, it just loses the extra polish. Injected once into <head>. */
(function () {
  "use strict";

  /* ---- Ripple effect on primary buttons ---- */
  function attachRipple(btn) {
    if (btn.__rippleBound) return;
    btn.__rippleBound = true;
    btn.style.position = btn.style.position || "relative";
    btn.style.overflow = "hidden";
    btn.addEventListener("click", function (e) {
      try {
        var rect = btn.getBoundingClientRect();
        var span = document.createElement("span");
        var size = Math.max(rect.width, rect.height);
        span.className = "rc-ripple";
        span.style.width = span.style.height = size + "px";
        span.style.left = e.clientX - rect.left - size / 2 + "px";
        span.style.top = e.clientY - rect.top - size / 2 + "px";
        btn.appendChild(span);
        setTimeout(function () {
          span.remove();
        }, 650);
      } catch (_) {}
    });
  }

  /* ---- Animated count-up for the score label ---- */
  function animateScore(el) {
    try {
      var raw = (el.textContent || "").trim();
      var match = raw.match(/([0-9]+(?:\.[0-9]+)?)\s*\/\s*10/);
      if (!match) return;
      var target = parseFloat(match[1]);
      if (el.__lastScore === target) return;
      el.__lastScore = target;

      var start = null;
      var duration = 900;
      function frame(ts) {
        if (start === null) start = ts;
        var p = Math.min((ts - start) / duration, 1);
        var eased = 1 - Math.pow(1 - p, 3); // easeOutCubic
        var val = (target * eased).toFixed(1);
        el.textContent = val + " / 10";
        // Drive the score bar width via a CSS variable on :root scope.
        var bar = document.querySelector(".score-bar > span");
        if (bar) bar.style.width = (target / 10) * 100 * eased + "%";
        if (p < 1) requestAnimationFrame(frame);
      }
      requestAnimationFrame(frame);
    } catch (_) {}
  }

  /* ---- Observe the DOM and (re)wire elements as Gradio renders ---- */
  function scan() {
    document
      .querySelectorAll(".review-btn, .download-btn, .ghost-btn")
      .forEach(attachRipple);
    var score = document.querySelector(".score-value");
    if (score) animateScore(score);
  }

  function boot() {
    scan();
    try {
      var mo = new MutationObserver(function () {
        window.requestAnimationFrame(scan);
      });
      mo.observe(document.body, { childList: true, subtree: true, characterData: true });
    } catch (_) {}
    // Fallback polling in case observation misses fast updates.
    setInterval(scan, 1200);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot);
  } else {
    boot();
  }
})();
