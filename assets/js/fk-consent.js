/* Analytics consent banner. Loaded only when an analytics ID is configured.
   The choice is kept for six months in a first-party cookie on the parent
   domain, so every site under that domain shares it. Texts and the cookie
   domain come from window.__fkConsentConfig (layouts/partials/fk/analytics.html). */
(function () {
  "use strict";
  var C = window.__fkConsentConfig;
  if (!C) return;
  var MAX_AGE = 15552000; // 180 days

  function save(value) {
    var host = location.hostname;
    var onDomain = C.domain && (host === C.domain || host.slice(-C.domain.length - 1) === "." + C.domain);
    document.cookie = "fk_consent=" + value + (onDomain ? ";Domain=" + C.domain : "") +
      ";Path=/;Max-Age=" + MAX_AGE + ";SameSite=Lax;Secure";
  }

  function apply(value) {
    var granted = value === "granted" ? "granted" : "denied";
    if (window.gtag) window.gtag("consent", "update", { analytics_storage: granted });
    if (window.clarity) {
      if (granted === "granted") window.clarity("consentv2", { ad_Storage: "denied", analytics_Storage: "granted" });
      else window.clarity("consent", false);
    }
  }

  function el(tag, attrs, text) {
    var node = document.createElement(tag);
    for (var k in attrs) node.setAttribute(k, attrs[k]);
    if (text) node.textContent = text;
    return node;
  }

  function show(focus) {
    var existing = document.getElementById("fk-cc");
    if (existing) {
      if (focus) existing.querySelector("button").focus();
      return;
    }
    var box = el("section", { id: "fk-cc", "aria-label": C.label });
    var p = el("p", {}, C.text + " ");
    p.appendChild(el("a", { href: C.href }, C.more));
    var actions = el("div", {});
    actions.appendChild(el("button", { type: "button", "data-v": "denied" }, C.reject));
    actions.appendChild(el("button", { type: "button", "data-v": "granted" }, C.accept));
    box.appendChild(p);
    box.appendChild(actions);
    box.addEventListener("click", function (ev) {
      var value = ev.target.getAttribute && ev.target.getAttribute("data-v");
      if (!value) return;
      save(value);
      apply(value);
      box.remove();
    });
    // Right after the skip link, so keyboard users reach it early.
    var skip = document.querySelector(".fk-skip");
    document.body.insertBefore(box, skip ? skip.nextSibling : document.body.firstChild);
    if (focus) actions.querySelector("button").focus();
  }

  if (!window.__fkConsent) show(false);

  // Reopened from the "Cookie preferences" link in the footer.
  document.addEventListener("fk:consent-open", function (ev) {
    ev.preventDefault();
    show(true);
  });
})();
