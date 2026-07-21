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

  /* ---- Animated count-up + ring fill for the score gauge ---- */
  function animateScore(ring) {
    try {
      var numEl = ring.querySelector(".score-num");
      var raw = ring.getAttribute("data-score") || "";
      var target = parseFloat(raw);
      if (isNaN(target)) return;
      if (ring.__lastScore === target) return;
      ring.__lastScore = target;

      var start = null;
      var duration = 950;
      function frame(ts) {
        if (start === null) start = ts;
        var p = Math.min((ts - start) / duration, 1);
        var eased = 1 - Math.pow(1 - p, 3); // easeOutCubic
        if (numEl) numEl.textContent = (target * eased).toFixed(1);
        ring.style.setProperty("--pct", (target / 10) * 100 * eased + "%");
        if (p < 1) requestAnimationFrame(frame);
      }
      // Begin the fill from zero for a satisfying sweep.
      ring.style.setProperty("--pct", "0%");
      requestAnimationFrame(frame);
    } catch (_) {}
  }

  /* ---- Observe the DOM and (re)wire elements as Gradio renders ---- */
  function scan() {
    document
      .querySelectorAll(".review-btn, .download-btn, .ghost-btn")
      .forEach(attachRipple);
    document.querySelectorAll(".score-ring[data-score]").forEach(function (r) {
      if (r.getAttribute("data-score") !== "—") animateScore(r);
    });
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
