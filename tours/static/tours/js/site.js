/* Nomad Explorer Tours — small progressive enhancements (the site works without JS). */
(function () {
  "use strict";

  // Mobile menu
  var burger = document.getElementById("burger");
  var nav = document.getElementById("nav");
  if (burger && nav) {
    burger.addEventListener("click", function () {
      // The menu starts right under the header, wherever the header is on screen.
      var header = document.getElementById("header");
      nav.style.setProperty("--nav-top", header.getBoundingClientRect().bottom + "px");
      var open = nav.classList.toggle("is-open");
      burger.setAttribute("aria-expanded", open ? "true" : "false");
      document.body.classList.toggle("nav-open", open);
    });
    nav.querySelectorAll(".nav__toggle").forEach(function (btn) {
      btn.addEventListener("click", function () {
        var drop = btn.parentElement.querySelector(".drop");
        var open = drop.classList.toggle("is-open");
        btn.setAttribute("aria-expanded", open ? "true" : "false");
      });
    });
  }

  // Home page: filter popular trips by category
  document.querySelectorAll(".tabs [data-filter]").forEach(function (tab, _, all) {
    tab.addEventListener("click", function () {
      var value = tab.getAttribute("data-filter");
      all.forEach(function (t) {
        var active = t === tab;
        t.classList.toggle("is-active", active);
        t.setAttribute("aria-selected", active ? "true" : "false");
      });
      var grid = document.querySelector("[data-filter-grid]");
      if (!grid) return;
      grid.querySelectorAll(".card").forEach(function (card) {
        card.classList.toggle("is-hidden", value !== "all" && card.getAttribute("data-cat") !== value);
      });
    });
  });

  // Auto-submit filter forms when a select / radio changes
  document.querySelectorAll("form[data-autosubmit]").forEach(function (form) {
    form.addEventListener("change", function (e) {
      if (e.target.matches("select, input[type=radio]")) form.submit();
    });
  });

  // Tour page: expand / collapse all itinerary days
  var expand = document.querySelector("[data-expand-all]");
  if (expand) {
    expand.addEventListener("click", function () {
      var days = document.querySelectorAll(".itinerary details");
      var openAll = expand.textContent.indexOf("Expand") === 0;
      days.forEach(function (d) { d.open = openAll; });
      expand.textContent = openAll ? "Collapse all" : "Expand all";
    });
  }

  // Tour page: highlight the current section in the sticky sub-menu
  var subnav = document.querySelector(".subnav");
  if (subnav && "IntersectionObserver" in window) {
    var links = {};
    subnav.querySelectorAll("a[href^='#']").forEach(function (a) { links[a.getAttribute("href").slice(1)] = a; });
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (en) {
        if (en.isIntersecting && links[en.target.id]) {
          Object.keys(links).forEach(function (k) { links[k].classList.remove("is-active"); });
          links[en.target.id].classList.add("is-active");
        }
      });
    }, { rootMargin: "-40% 0px -55% 0px" });
    Object.keys(links).forEach(function (id) { var el = document.getElementById(id); if (el) io.observe(el); });
  }

  // Simple gallery lightbox
  document.querySelectorAll("[data-gallery] a").forEach(function (a) {
    a.addEventListener("click", function (e) {
      e.preventDefault();
      var box = document.createElement("div");
      box.className = "lightbox";
      box.setAttribute("role", "dialog");
      box.setAttribute("aria-label", "Photo");
      box.innerHTML = '<img alt=""><button type="button" aria-label="Close">×</button>';
      box.querySelector("img").src = a.getAttribute("href");
      box.querySelector("img").alt = (a.querySelector("img") || {}).alt || "";
      function close() { box.remove(); document.removeEventListener("keydown", onKey); }
      function onKey(ev) { if (ev.key === "Escape") close(); }
      box.addEventListener("click", function (ev) { if (ev.target === box || ev.target.tagName === "BUTTON") close(); });
      document.addEventListener("keydown", onKey);
      document.body.appendChild(box);
      box.querySelector("button").focus();
    });
  });

  // Group departures: "Join group" modal
  var modal = document.getElementById("join-modal");
  if (modal && typeof modal.showModal === "function") {
    var waBase = (modal.querySelector("[data-join-wa]") || {}).href || "";
    function openFor(btn) {
      modal.querySelector("[data-join-id]").value = btn.getAttribute("data-join");
      modal.querySelector("[data-join-title]").textContent = btn.getAttribute("data-name");
      modal.querySelector("[data-join-meta]").textContent = btn.getAttribute("data-date") + " · " + btn.getAttribute("data-price") + " per person";
      var date = modal.querySelector("input[name=travel_date]");
      if (date) date.value = btn.getAttribute("data-iso");
      var msg = "Hello, I would like to join the " + btn.getAttribute("data-name") + " group departure on " + btn.getAttribute("data-date") + ".";
      var wa = modal.querySelector("[data-join-wa]");
      if (wa) wa.href = waBase.split("?")[0] + "?text=" + encodeURIComponent(msg);
      modal.showModal();
    }
    document.querySelectorAll("[data-join]").forEach(function (btn) {
      btn.addEventListener("click", function () { openFor(btn); });
    });
    modal.querySelectorAll("[data-close]").forEach(function (b) { b.addEventListener("click", function () { modal.close(); }); });
    modal.addEventListener("click", function (e) { if (e.target === modal) modal.close(); });
    // Re-open the form after a failed submit so the visitor sees the errors.
    var reopen = modal.getAttribute("data-open");
    if (reopen) { modal.showModal(); }
  } else if (modal) {
    // Very old browsers: show the form inline.
    modal.setAttribute("open", "");
    document.querySelectorAll("[data-join]").forEach(function (btn) {
      btn.addEventListener("click", function () {
        modal.querySelector("[data-join-id]").value = btn.getAttribute("data-join");
        modal.scrollIntoView();
      });
    });
  }
})();
