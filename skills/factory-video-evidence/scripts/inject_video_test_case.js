async page => {
  const encodedTestCase = "__FACTORY_TEST_CASE_BASE64__";

  const injectTestCase = encodedLabel => {
    const labelBytes = Uint8Array.from(
      atob(encodedLabel),
      character => character.charCodeAt(0),
    );
    const label = new TextDecoder().decode(labelBytes);
    const elementId = "factory-video-evidence-test-case";

    const addElement = () => {
      const existingElement = document.getElementById(elementId);
      if (existingElement) {
        existingElement.textContent = label;
        return;
      }

      const element = document.createElement("aside");
      element.id = elementId;
      element.setAttribute("aria-label", "Test case");
      element.textContent = label;
      Object.assign(element.style, {
        position: "fixed",
        top: "12px",
        left: "12px",
        zIndex: "2147483647",
        maxWidth: "calc(100vw - 24px)",
        padding: "8px 12px",
        borderRadius: "6px",
        background: "rgba(15, 23, 42, 0.72)",
        color: "#ffffff",
        font: "600 14px/1.4 system-ui, sans-serif",
        whiteSpace: "pre-wrap",
        pointerEvents: "none",
      });
      document.body.appendChild(element);
    };

    if (document.body) {
      addElement();
      return;
    }

    document.addEventListener("DOMContentLoaded", addElement, { once: true });
  };

  await page.addInitScript(injectTestCase, encodedTestCase);
  await page.evaluate(injectTestCase, encodedTestCase);
}
