(function () {
  if (window.__supportpilotWidgetLoaded) {
    return;
  }

  window.__supportpilotWidgetLoaded = true;

  var script = document.currentScript;
  var organizationSlug = script && script.getAttribute("data-org");
  var buttonText =
    (script && script.getAttribute("data-button-text")) || "Support";
  var position =
    (script && script.getAttribute("data-position")) || "bottom-right";
  var baseUrl =
    (script && script.getAttribute("data-base-url")) ||
    new URL(script.src).origin;

  if (!organizationSlug) {
    console.error("SupportPilot widget: missing data-org attribute.");
    return;
  }

  var launcher = document.createElement("button");
  launcher.type = "button";
  launcher.innerText = buttonText;
  launcher.setAttribute("aria-label", "Open support widget");

  var launcherStyle = {
    position: "fixed",
    zIndex: "2147483647",
    border: "0",
    borderRadius: "999px",
    padding: "14px 20px",
    background: "#2563eb",
    color: "#ffffff",
    fontSize: "15px",
    fontWeight: "700",
    cursor: "pointer",
    boxShadow: "0 18px 40px rgba(37, 99, 235, 0.35)",
  };

  Object.assign(launcher.style, launcherStyle);

  if (position === "bottom-left") {
    launcher.style.left = "24px";
    launcher.style.bottom = "24px";
  } else {
    launcher.style.right = "24px";
    launcher.style.bottom = "24px";
  }

  var iframeWrap = document.createElement("div");

  var iframeWrapStyle = {
    position: "fixed",
    zIndex: "2147483647",
    width: "420px",
    height: "680px",
    maxWidth: "calc(100vw - 32px)",
    maxHeight: "calc(100vh - 32px)",
    display: "none",
    borderRadius: "24px",
    overflow: "hidden",
    boxShadow: "0 24px 80px rgba(15, 23, 42, 0.24)",
    background: "#ffffff",
  };

  Object.assign(iframeWrap.style, iframeWrapStyle);

  if (position === "bottom-left") {
    iframeWrap.style.left = "24px";
    iframeWrap.style.bottom = "88px";
  } else {
    iframeWrap.style.right = "24px";
    iframeWrap.style.bottom = "88px";
  }

  var iframe = document.createElement("iframe");
  iframe.title = "SupportPilot Support Widget";
  iframe.src =
    baseUrl + "/embed/support?org=" + encodeURIComponent(organizationSlug);

  var iframeStyle = {
    width: "100%",
    height: "100%",
    border: "0",
    background: "#ffffff",
  };

  Object.assign(iframe.style, iframeStyle);

  iframeWrap.appendChild(iframe);

  var isOpen = false;

  function openWidget() {
    isOpen = true;
    iframeWrap.style.display = "block";
    launcher.innerText = "Close";
  }

  function closeWidget() {
    isOpen = false;
    iframeWrap.style.display = "none";
    launcher.innerText = buttonText;
  }

  launcher.addEventListener("click", function () {
    if (isOpen) {
      closeWidget();
    } else {
      openWidget();
    }
  });

  window.addEventListener("message", function (event) {
    if (!event.data || typeof event.data !== "object") {
      return;
    }

    if (event.data.type === "SUPPORTPILOT_CLOSE_WIDGET") {
      closeWidget();
    }

    if (event.data.type === "SUPPORTPILOT_TICKET_CREATED") {
      console.log(
        "SupportPilot ticket created:",
        event.data.ticketNumber || ""
      );
    }
  });

  document.body.appendChild(launcher);
  document.body.appendChild(iframeWrap);
})();