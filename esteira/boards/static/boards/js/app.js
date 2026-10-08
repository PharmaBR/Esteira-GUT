/* Request status for the whole app.
 *
 * Rule of the project: nothing talks to the server silently. Every htmx
 * request and every page navigation lights the top bar; every failure
 * becomes a visible message instead of a spinner that just disappears.
 *
 * The bar appears at once and stays for at least MIN_VISIBLE ms, so even an
 * instant answer shows one calm pulse instead of a flicker. Per-button
 * spinners are plain CSS driven by htmx's `htmx-request` class; they wait
 * a moment before showing (--indicator-delay in tokens.css).
 *
 * When the answer arrives, keyboard focus goes to it: the message, the field
 * that is wrong, the form that opened, or the heading of the section acted on.
 */
(function () {
  "use strict";

  var root = document.documentElement;
  var statusEl = document.getElementById("request-status");
  var errorEl = document.getElementById("request-error");
  var errorText = document.getElementById("request-error-text");
  var inFlight = 0;
  var MIN_VISIBLE = 300;
  var shownAt = 0;
  var hideTimer = null;

  function showBusy() {
    clearTimeout(hideTimer);
    if (!root.classList.contains("is-busy")) shownAt = Date.now();
    root.classList.add("is-busy");
    if (statusEl) statusEl.textContent = "Processando…";
  }

  function hideBusy() {
    root.classList.remove("is-busy");
    if (statusEl) statusEl.textContent = "";
  }

  function render() {
    if (inFlight > 0) {
      showBusy();
      return;
    }
    clearTimeout(hideTimer);
    hideTimer = setTimeout(hideBusy, Math.max(0, MIN_VISIBLE - (Date.now() - shownAt)));
  }

  function showError(message) {
    if (!errorEl) return;
    errorText.textContent = message;
    errorEl.hidden = false;
  }

  function hideError() {
    if (errorEl) errorEl.hidden = true;
  }

  var pressed = null;

  document.addEventListener("htmx:beforeRequest", function () {
    inFlight += 1;
    // Disabling the control during the request drops its focus; remember it.
    pressed = document.activeElement;
    hideError();
    render();
  });

  // Fires for success, HTTP errors, network errors, timeouts and aborts alike.
  document.addEventListener("htmx:afterRequest", function (event) {
    inFlight = Math.max(0, inFlight - 1);
    render();
    if (event.detail.successful) return;
    // Nothing was swapped: give focus back to what was pressed, once it is enabled again.
    var control = pressed;
    setTimeout(function () {
      if (control && control.isConnected && document.activeElement === document.body) control.focus();
    }, 0);
  });

  document.addEventListener("htmx:responseError", function (event) {
    var status = event.detail.xhr ? event.detail.xhr.status : 0;
    if (status === 403) {
      showError("Sua sessão expirou ou a página está desatualizada. Recarregue e tente de novo.");
    } else if (status === 404) {
      showError("Essa tarefa não existe mais. Recarregue a página.");
    } else {
      showError("O servidor não conseguiu concluir a ação (erro " + status + "). Nada foi alterado.");
    }
  });

  document.addEventListener("htmx:sendError", function () {
    showError("Sem conexão com o servidor. Verifique a rede e tente de novo.");
  });

  document.addEventListener("htmx:timeout", function () {
    showError("O servidor demorou demais para responder. Tente de novo.");
  });

  if (errorEl) {
    document.getElementById("request-error-close").addEventListener("click", hideError);
  }

  // Plain (non-htmx) forms and links are full page loads: show the same bar.
  function usesHtmx(el) {
    return ["hx-get", "hx-post", "hx-put", "hx-patch", "hx-delete"].some(function (attr) {
      return el.hasAttribute(attr);
    });
  }

  document.addEventListener("submit", function (event) {
    var form = event.target;
    if (event.defaultPrevented || usesHtmx(form)) return;
    showBusy();
    form.classList.add("is-submitting");
  });

  document.addEventListener("click", function (event) {
    var link = event.target.closest ? event.target.closest("a[href]") : null;
    if (!link || event.defaultPrevented || usesHtmx(link)) return;
    if (event.metaKey || event.ctrlKey || event.shiftKey || event.button !== 0) return;
    if (link.target || link.origin !== window.location.origin) return;
    if (link.pathname === window.location.pathname && link.hash) return;
    showBusy();
  });

  // Coming back through the browser's back/forward cache must not leave the bar on.
  window.addEventListener("pageshow", function () {
    inFlight = 0;
    clearTimeout(hideTimer);
    hideBusy();
    Array.prototype.forEach.call(document.querySelectorAll(".is-submitting"), function (form) {
      form.classList.remove("is-submitting");
    });
  });

  // Swapping the board would close every <details>; remember which were open,
  // and which part of the page the person was acting on.
  var openDetails = [];
  var actedOn = null;

  document.addEventListener("htmx:beforeSwap", function (event) {
    var target = event.detail.target;
    var from = pressed && pressed.isConnected ? pressed : document.activeElement;
    var region = from && from.closest ? from.closest("section[aria-labelledby], details[id]") : null;
    actedOn = region ? region.getAttribute("aria-labelledby") || region.id : null;
    openDetails = [];
    if (!target || !target.querySelectorAll) return;
    Array.prototype.forEach.call(target.querySelectorAll("details[id][open]"), function (el) {
      if (el.hasAttribute("data-keep-open")) openDetails.push(el.id);
    });
  });

  document.addEventListener("htmx:afterSwap", function () {
    openDetails.forEach(function (id) {
      var el = document.getElementById(id);
      if (el) el.open = true;
    });
  });

  // The new content replaced whatever had focus. Put focus on the answer.
  document.addEventListener("htmx:afterSettle", function () {
    var board = document.getElementById("board");
    if (!board) return;
    var answer =
      board.querySelector(".alert") ||
      board.querySelector('[aria-invalid="true"]') ||
      board.querySelector(".task.editing input:not([type=hidden]), .task.editing select");
    if (answer) {
      // A message or a mistake is worth scrolling to.
      answer.focus();
      return;
    }
    var place = actedOn ? document.getElementById(actedOn) : null;
    if (place && place.tagName === "DETAILS") place = place.querySelector("summary");
    if (!place) place = document.getElementById("h-running");
    if (!place) return;
    if (place.tagName !== "SUMMARY") place.setAttribute("tabindex", "-1");
    // Everything went well: stay where the person is looking.
    place.focus({ preventScroll: true });
  });
})();
