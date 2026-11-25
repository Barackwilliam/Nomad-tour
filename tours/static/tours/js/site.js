/* Nomad Explorer Tours — small progressive enhancements (the site works without JS). */
(function () {
  "use strict";
  var reduceMotion = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  // ---------------------------------------------------------------- Header: transparent over the hero, solid on scroll
  var header = document.getElementById("header");
  var masthead = document.getElementById("masthead");
  var overHero = document.body.classList.contains("has-hero");
  if (header && overHero) {
    var ticking = false;
    var onScroll = function () {
      ticking = false;
      var stuck = window.scrollY > (masthead ? masthead.offsetHeight + 40 : 160);
      header.classList.toggle("is-stuck", stuck);
    };
    window.addEventListener("scroll", function () {
      if (!ticking) { ticking = true; requestAnimationFrame(onScroll); }
    }, { passive: true });
    onScroll();
  }

  // ---------------------------------------------------------------- Land exactly on #book / #dates even if the page
  // grew while loading (photos, fonts), e.g. when coming from a group departure link.
  if (location.hash && /^#[\w-]+$/.test(location.hash)) {
    window.addEventListener("load", function () {
      var target = document.querySelector(location.hash);
      if (target) setTimeout(function () { target.scrollIntoView({ block: "start" }); }, 60);
    });
  }

  // ---------------------------------------------------------------- Mobile menu
  var burger = document.getElementById("burger");
  var nav = document.getElementById("nav");
  if (burger && nav) {
    burger.addEventListener("click", function () {
      nav.style.setProperty("--nav-top", header.getBoundingClientRect().bottom + "px");
      var open = nav.classList.toggle("is-open");
      burger.setAttribute("aria-expanded", open ? "true" : "false");
      header.classList.toggle("menu-open", open);
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

  // ---------------------------------------------------------------- Hero slideshow (extra photos load after the page)
  var hero = document.querySelector("[data-hero]");
  if (hero) {
    var slides = hero.querySelectorAll(".hero__slide");
    var dots = hero.querySelectorAll(".hero__dot");
    if (slides.length > 1) {
      var current = 0, timer = null;
      var loadSlide = function (slide) {
        var im = slide.querySelector("img[data-src]");
        if (!im) return;
        if (im.dataset.srcset) im.srcset = im.dataset.srcset;
        im.src = im.dataset.src;
        im.removeAttribute("data-src");
      };
      var show = function (i) {
        loadSlide(slides[i]);
        slides[current].classList.remove("is-active");
        if (dots[current]) dots[current].classList.remove("is-active");
        current = i;
        slides[current].classList.add("is-active");
        if (dots[current]) { void dots[current].offsetWidth; dots[current].classList.add("is-active"); }
      };
      var next = function () { show((current + 1) % slides.length); };
      var start = function () { clearInterval(timer); if (!reduceMotion) timer = setInterval(next, 7000); };
      window.addEventListener("load", function () {
        // Fetch the next photos only once the page is fully loaded, so the first view stays fast.
        setTimeout(function () { for (var i = 1; i < slides.length; i++) loadSlide(slides[i]); start(); }, 1200);
      });
      dots.forEach(function (d) {
        d.addEventListener("click", function () { show(+d.getAttribute("data-slide")); start(); });
      });
    }
  }

  // ---------------------------------------------------------------- Scroll reveal (with a gentle stagger)
  var revealEls = document.querySelectorAll("[data-reveal]");
  if ("IntersectionObserver" in window && !reduceMotion) {
    var ro = new IntersectionObserver(function (entries) {
      var batch = 0;
      entries.forEach(function (en) {
        if (!en.isIntersecting) return;
        en.target.style.transitionDelay = Math.min(batch++ * 90, 450) + "ms";
        en.target.classList.add("is-visible");
        ro.unobserve(en.target);
      });
    }, { rootMargin: "0px 0px -8% 0px", threshold: 0.08 });
    revealEls.forEach(function (el) { ro.observe(el); });
  } else {
    revealEls.forEach(function (el) { el.classList.add("is-visible"); });
  }

  // ---------------------------------------------------------------- Home: filter trips by category
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
      grid.querySelectorAll(".card, .poster").forEach(function (card) {
        card.classList.toggle("is-hidden", value !== "all" && card.getAttribute("data-cat") !== value);
      });
      if (grid.classList.contains("rail")) grid.scrollTo({ left: 0, behavior: "smooth" });
    });
  });

  // ---------------------------------------------------------------- Trips rail arrows
  var rail = document.querySelector(".rail");
  document.querySelectorAll("[data-rail]").forEach(function (btn) {
    btn.addEventListener("click", function () {
      if (!rail) return;
      var card = rail.querySelector(".poster:not(.is-hidden)");
      var step = card ? card.getBoundingClientRect().width + 18 : 360;
      rail.scrollBy({ left: step * +btn.getAttribute("data-rail"), behavior: "smooth" });
    });
  });

  // ---------------------------------------------------------------- When to go: month tabs (opens on the current month)
  var seasons = document.querySelector("[data-seasons]");
  if (seasons) {
    var months = seasons.querySelectorAll("[data-month]");
    var panels = seasons.querySelectorAll("[data-panel]");
    var pick = function (i) {
      months.forEach(function (m, k) {
        m.classList.toggle("is-active", k === i);
        m.setAttribute("aria-selected", k === i ? "true" : "false");
      });
      panels.forEach(function (p, k) { p.hidden = k !== i; });
    };
    months.forEach(function (m, i) { m.addEventListener("click", function () { pick(i); }); });
    pick(new Date().getMonth());
  }

  // ---------------------------------------------------------------- Auto-submit filter forms
  document.querySelectorAll("form[data-autosubmit]").forEach(function (form) {
    form.addEventListener("change", function (e) {
      if (e.target.matches("select, input[type=radio]")) form.submit();
    });
  });

  // ---------------------------------------------------------------- Tour page: expand / collapse itinerary
  var expand = document.querySelector("[data-expand-all]");
  if (expand) {
    expand.addEventListener("click", function () {
      var days = document.querySelectorAll(".itinerary details");
      var openAll = expand.textContent.indexOf("Expand") === 0;
      days.forEach(function (d) { d.open = openAll; });
      expand.textContent = openAll ? "Collapse all" : "Expand all";
    });
  }

  // ---------------------------------------------------------------- Tour page: highlight current section in the sub-menu
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

  // ---------------------------------------------------------------- Gallery lightbox
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

  // ---------------------------------------------------------------- Group departures: "Join group" modal
  var modal = document.getElementById("join-modal");
  if (modal && typeof modal.showModal === "function") {
    var waBase = (modal.querySelector("[data-join-wa]") || {}).href || "";
    var openFor = function (btn) {
      modal.querySelector("[data-join-id]").value = btn.getAttribute("data-join");
      modal.querySelector("[data-join-title]").textContent = btn.getAttribute("data-name");
      modal.querySelector("[data-join-meta]").textContent = btn.getAttribute("data-date") + " · " + btn.getAttribute("data-price") + " per person";
      var date = modal.querySelector("input[name=travel_date]");
      if (date) date.value = btn.getAttribute("data-iso");
      var msg = "Hello, I would like to join the " + btn.getAttribute("data-name") + " group departure on " + btn.getAttribute("data-date") + ".";
      var wa = modal.querySelector("[data-join-wa]");
      if (wa) wa.href = waBase.split("?")[0] + "?text=" + encodeURIComponent(msg);
      modal.showModal();
    };
    document.querySelectorAll("[data-join]").forEach(function (btn) {
      btn.addEventListener("click", function () { openFor(btn); });
    });
    modal.querySelectorAll("[data-close]").forEach(function (b) { b.addEventListener("click", function () { modal.close(); }); });
    modal.addEventListener("click", function (e) { if (e.target === modal) modal.close(); });
    if (modal.getAttribute("data-open")) modal.showModal();  // re-open after a failed submit
  } else if (modal) {
    modal.setAttribute("open", "");
    document.querySelectorAll("[data-join]").forEach(function (btn) {
      btn.addEventListener("click", function () {
        modal.querySelector("[data-join-id]").value = btn.getAttribute("data-join");
        modal.scrollIntoView();
      });
    });
  }
})();
