/* Request status for the whole app.
 *
 * Rule of the project: nothing talks to the server silently. Every htmx
 * request and every page navigation lights the top bar; every failure
 * becomes a visible message instead of a spinner that just disappears.
 * Per-button spinners are plain CSS driven by htmx's `htmx-request` class.
 */
(function () {
  "use strict";

  var root = document.documentElement;
  var statusEl = document.getElementById("request-status");
  var errorEl = document.getElementById("request-error");
  var errorText = document.getElementById("request-error-text");
  var inFlight = 0;

  function render() {
    var busy = inFlight > 0;
    root.classList.toggle("is-busy", busy);
    if (statusEl) statusEl.textContent = busy ? "Processando…" : "";
  }

  function showError(message) {
    if (!errorEl) return;
    errorText.textContent = message;
    errorEl.hidden = false;
  }

  function hideError() {
    if (errorEl) errorEl.hidden = true;
  }

  document.addEventListener("htmx:beforeRequest", function () {
    inFlight += 1;
    hideError();
    render();
  });

  // Fires for success, HTTP errors, network errors, timeouts and aborts alike.
  document.addEventListener("htmx:afterRequest", function () {
    inFlight = Math.max(0, inFlight - 1);
    render();
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
    root.classList.add("is-busy");
    form.classList.add("is-submitting");
  });

  document.addEventListener("click", function (event) {
    var link = event.target.closest ? event.target.closest("a[href]") : null;
    if (!link || event.defaultPrevented || usesHtmx(link)) return;
    if (event.metaKey || event.ctrlKey || event.shiftKey || event.button !== 0) return;
    if (link.target || link.origin !== window.location.origin) return;
    if (link.pathname === window.location.pathname && link.hash) return;
    root.classList.add("is-busy");
  });

  // Coming back through the browser's back/forward cache must not leave the bar on.
  window.addEventListener("pageshow", function () {
    inFlight = 0;
    render();
    Array.prototype.forEach.call(document.querySelectorAll(".is-submitting"), function (form) {
      form.classList.remove("is-submitting");
    });
  });

  // Swapping the board would close every <details>; remember which were open.
  var openDetails = [];

  document.addEventListener("htmx:beforeSwap", function (event) {
    var target = event.detail.target;
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
})();
