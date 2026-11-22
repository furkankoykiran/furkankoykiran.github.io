/* Progressive enhancements; every page works without JavaScript. */
(function () {
  "use strict";

  /* GA4 event helper. Consent Mode handles storage; when analytics is not
     configured or blocked, this is a no-op. */
  function track(name, params) {
    if (typeof window.gtag === "function") window.gtag("event", name, params || {});
  }

  /* Declarative analytics: data-ga-event on a link and data-ga-param-* for
     its parameters. Outbound links without an explicit event are tracked
     once, with the destination host. */
  document.addEventListener("click", function (ev) {
    var target = ev.target;
    if (!target || !target.closest) return;
    var tagged = target.closest("[data-ga-event]");
    if (tagged) {
      var params = {};
      Array.prototype.forEach.call(tagged.attributes, function (attr) {
        if (attr.name.indexOf("data-ga-param-") === 0) {
          params[attr.name.slice(14).replace(/-/g, "_")] = attr.value;
        }
      });
      track(tagged.getAttribute("data-ga-event"), params);
      return;
    }
    var link = target.closest("a[href]");
    if (!link || link.hostname === location.hostname) return;
    track("outbound_click", {
      link_domain: link.hostname,
      link_url: link.href,
      link_text: (link.textContent || "").trim().slice(0, 80)
    });
  }, true);

  /* Live demo: nothing is requested from the embedded site until the visitor
     clicks. The iframe keeps loading="lazy" and a real title for screen
     readers; CSS gives the wrapper a 16/9 aspect ratio. */
  document.querySelectorAll("[data-embed]").forEach(function (frame) {
    var button = frame.querySelector("[data-embed-load]");
    if (!button) return;
    button.addEventListener("click", function () {
      var src = frame.getAttribute("data-embed");
      var title = frame.getAttribute("data-embed-title") || "Live demo";
      if (!src) return;
      var iframe = document.createElement("iframe");
      iframe.src = src;
      iframe.title = title;
      iframe.loading = "lazy";
      iframe.width = "960";
      iframe.height = "540";
      iframe.referrerPolicy = "strict-origin-when-cross-origin";
      iframe.setAttribute("allow", "fullscreen; clipboard-write");
      iframe.setAttribute("allowfullscreen", "");
      iframe.setAttribute(
        "sandbox",
        "allow-scripts allow-same-origin allow-forms allow-popups allow-popups-to-escape-sandbox"
      );
      frame.classList.add("is-loading");
      iframe.addEventListener("load", function () {
        frame.classList.add("is-loaded");
        button.hidden = true;
      });
      frame.appendChild(iframe);
      track("demo_embed_open", { project: title, embed_url: src });
    });
  });

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

  /* Language suggestion strip. It only appears when the browser prefers the
     other language and this page has a translation. It is never a redirect,
     and the dismissal is remembered for 30 days. */
  var langData = document.getElementById("fk-lang-suggest-data");
  if (langData && document.body) {
    try {
      var cfg = JSON.parse(langData.textContent);
      var prefs = (navigator.languages && navigator.languages.length
        ? Array.prototype.slice.call(navigator.languages)
        : [navigator.language || ""]
      ).map(function (l) { return String(l).toLowerCase(); });
      var current = String(document.documentElement.lang || "").toLowerCase();
      var wantsOther = prefs.some(function (l) { return l.indexOf(cfg.lang.toLowerCase()) === 0; });
      var knowsCurrent = prefs.some(function (l) { return current && l.indexOf(current) === 0; });
      var key = "fk_lang_suggest_" + cfg.lang + "_" + location.pathname;
      var until = 0;
      try { until = Number(localStorage.getItem(key)) || 0; } catch (e) {}
      if (wantsOther && !knowsCurrent && until < Date.now()) {
        var bar = document.createElement("aside");
        bar.className = "fk-langbar";
        bar.setAttribute("role", "region");
        bar.setAttribute("aria-label", cfg.label);
        var text = document.createElement("span");
        text.textContent = cfg.text;
        var link = document.createElement("a");
        link.href = cfg.href;
        link.hreflang = cfg.lang;
        link.textContent = cfg.action;
        link.setAttribute("data-ga-event", "language_switch");
        link.setAttribute("data-ga-param-from", current || "unknown");
        link.setAttribute("data-ga-param-to", cfg.lang);
        var close = document.createElement("button");
        close.type = "button";
        close.setAttribute("aria-label", cfg.dismiss);
        close.textContent = "\u00d7";
        close.addEventListener("click", function () {
          try { localStorage.setItem(key, String(Date.now() + 30 * 864e5)); } catch (e) {}
          bar.remove();
        });
        bar.appendChild(text);
        bar.appendChild(link);
        bar.appendChild(close);
        var anchor = document.querySelector(".fk-skip, #the-top");
        if (anchor && anchor.parentNode) {
          anchor.parentNode.insertBefore(bar, anchor.nextSibling);
        } else {
          document.body.insertBefore(bar, document.body.firstChild);
        }
      }
    } catch (e) {}
  }
})();
