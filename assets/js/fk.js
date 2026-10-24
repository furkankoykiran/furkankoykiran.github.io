/* Progressive enhancements; every page works without JavaScript. */
(function () {
  "use strict";

  /* E-mail: the address is never plain text in the HTML. Links carry it
     base64-encoded in data-e and get a real mailto: here. */
  document.querySelectorAll("[data-e]").forEach(function (el) {
    try {
      var addr = atob(el.getAttribute("data-e"));
      el.setAttribute("href", "mailto:" + addr);
      var label = el.querySelector("[data-e-label]");
      if (label) label.textContent = addr;
      el.removeAttribute("aria-disabled");
    } catch (e) {}
  });

  /* Project filter on the list page. The selected category is kept in the
     URL hash so a filtered view can be shared. */
  var bar = document.querySelector("[data-filter-bar]");
  if (bar) {
    var cards = document.querySelectorAll("[data-filter-item]");
    var groups = document.querySelectorAll("[data-filter-group]");
    var status = document.querySelector("[data-filter-status]");
    bar.addEventListener("click", function (ev) {
      var btn = ev.target.closest("button[data-filter]");
      if (!btn) return;
      var f = btn.getAttribute("data-filter");
      bar.querySelectorAll("button[data-filter]").forEach(function (b) {
        b.setAttribute("aria-pressed", b === btn ? "true" : "false");
      });
      var shown = 0;
      cards.forEach(function (c) {
        var ok = f === "all" || c.getAttribute("data-cat") === f;
        c.classList.toggle("fk-hidden", !ok);
        if (ok) shown++;
      });
      groups.forEach(function (g) {
        var any = g.querySelector("[data-filter-item]:not(.fk-hidden)");
        g.classList.toggle("fk-hidden", !any);
      });
      if (status) status.textContent = status.getAttribute("data-template").replace("%d", shown);
      if (history.replaceState) history.replaceState(null, "", f === "all" ? location.pathname : "#" + f);
    });
    var initial = location.hash.slice(1);
    if (initial) {
      var b = bar.querySelector('button[data-filter="' + CSS.escape(initial) + '"]');
      if (b) b.click();
    }
  }

  /* Light/dark switch. The initial mode is set inline in <head>; the
     button's data attributes hold its label for each mode. */
  var sw = document.getElementById("appearance-switcher");
  if (sw) {
    var root = document.documentElement;
    var meta = document.querySelector('meta[name="theme-color"]');
    var sync = function () {
      var mode = root.classList.contains("dark") ? "dark" : "light";
      var label = sw.getAttribute(mode === "dark" ? "data-label-dark" : "data-label-light");
      sw.setAttribute("aria-label", label);
      sw.setAttribute("title", label);
      if (meta) meta.setAttribute("content", mode === "dark" ? "#11151D" : "#FFFFFF");
      return mode;
    };
    sync();
    sw.addEventListener("click", function () {
      root.classList.toggle("dark");
      var mode = sync();
      try { localStorage.setItem("appearance", mode); } catch (e) {}
    });
  }

  /* Mobile menu: close when clicking outside or pressing Escape. */
  var menu = document.querySelector(".fk-mnav");
  if (menu) {
    document.addEventListener("click", function (ev) {
      if (menu.open && !menu.contains(ev.target)) menu.open = false;
    });
    document.addEventListener("keydown", function (ev) {
      if (ev.key === "Escape" && menu.open) {
        menu.open = false;
        menu.querySelector("summary").focus();
      }
    });
  }

  /* "Cookie preferences" link: the consent banner, when loaded, handles the
     cancelable "fk:consent-open" event; otherwise the link opens the
     privacy page. */
  document.querySelectorAll("[data-fk-consent-open]").forEach(function (a) {
    a.addEventListener("click", function (ev) {
      var e = new CustomEvent("fk:consent-open", { cancelable: true });
      if (!document.dispatchEvent(e)) ev.preventDefault();
    });
  });
})();
