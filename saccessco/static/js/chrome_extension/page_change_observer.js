// contentChangeDetector.js

/**
 * Extracts relevant content from HTML, mirroring the Python HTMLHasher.
 */
function extractRelevantContent(html) {
  const parser = new DOMParser();
  const doc = parser.parseFromString(html, "text/html");

  // Extract the title
  const titleElement = doc.querySelector("title");
  const title = titleElement ? titleElement.textContent.trim() : "";

  // Extract the main text content
  let paragraphs;
  const mainElement = doc.querySelector("main");
  if (mainElement) {
    paragraphs = mainElement.querySelectorAll("p");
  } else {
    paragraphs = doc.querySelectorAll("p");
  }

  const textContent = Array.from(paragraphs)
    .map((p) => p.textContent.trim())
    .join("\n");

  const relevantText = `${title}\n${textContent}`;
  return relevantText;
}

/**
 * Sends the current page's URL and HTML content to the backend.
 */
async function notifyBackend(mutationType = "initial load", previousHash = "") {
  const newUrl = window.location.href;
  const newHtml = document.documentElement.outerHTML;

  // Extract relevant content
  const relevantContent = extractRelevantContent(newHtml);

  // Calculate SHA-256 hash of the relevant content
  const textEncoder = new TextEncoder();
  const data = textEncoder.encode(relevantContent);
  try{
    const hashBufferPromise =  crypto.subtle.digest('SHA-256', data);
    const hashBuffer = await hashBufferPromise;
    const hashArray = Array.from(new Uint8Array(hashBuffer));
    const htmlHash = hashArray.map(b => b.toString(16).padStart(2, '0')).join('');
    console.log(`Notifying backend of ${mutationType}: URL: ${newUrl}, HTML Hash: ${htmlHash}`);
    window.backendCommunicatorModule.sendPageChange(newUrl, newHtml, htmlHash); // Send the hash
    return htmlHash;
  }
  catch(e){
    console.error("Error calculating or sending hash",e);
    return "";
  }


}

/**
 * Sets up listeners to detect URL and HTML changes.
 */
async function setupChangeObserver() {
  let previousHtmlHash = ""; // Store the previous hash

  // 1. Listen for URL changes using the History API and hash changes.
  window.addEventListener("popstate", async () => {
    console.log("popstate event: URL changed to", window.location.href);
    previousHtmlHash = await notifyBackend("popstate", previousHtmlHash);
  });
  window.addEventListener("hashchange", async () => {
    console.log("hashchange event: URL changed to", window.location.href);
    previousHtmlHash = await notifyBackend("hashchange", previousHtmlHash);
  });

  // 2. Fallback: Poll for URL changes every second.
  let currentUrl = window.location.href;
  const urlCheckInterval = setInterval(async () => {
    if (window.location.href !== currentUrl) {
      currentUrl = window.location.href;
      console.log("URL changed (polling) to", currentUrl);
      previousHtmlHash = await notifyBackend("url polling", previousHtmlHash);
    }
  }, 1000);

  // 3. Observe DOM mutations for HTML changes.
  const observer = new MutationObserver(async (mutationsList) => { //make the callback async
    for (const mutation of mutationsList) {
      if (
        mutation.type === "childList" ||
        mutation.type === "subtree" ||
        mutation.type === "attributes" ||
        mutation.type === "characterData"
      ) {
        console.log("DOM mutation detected");

        const newHtml = document.documentElement.outerHTML;
        const relevantContent = extractRelevantContent(newHtml);
        const textEncoder = new TextEncoder();
        const data = textEncoder.encode(relevantContent);
        try{
          const hashBufferPromise =  crypto.subtle.digest('SHA-256', data);
          const hashBuffer = await hashBufferPromise;
          const hashArray = Array.from(new Uint8Array(hashBuffer));
          const newHtmlHash = hashArray.map(b => b.toString(16).padStart(2, '0')).join('');
          if (newHtmlHash !== previousHtmlHash) {
            // Only notify if the hash has changed
            previousHtmlHash = await notifyBackend("DOM mutation", previousHtmlHash);

          }
        }
        catch(e){
          console.error("Error calculating hash",e);
        }

        break; // important: only send one update per mutation event.
      }
    }
  });

  // Start observing the entire body (including changes within its children)
  observer.observe(document.body, {
    childList: true,    // Monitor additions/removals of child nodes
    subtree: true,    // Monitor changes in the entire subtree
    attributes: true,  // Monitor changes to attributes.
    characterData: true // Monitor changes to text content.
  });

  // 4. Send initial page state on load
  const initialHtml = document.documentElement.outerHTML;
  const initialRelevantContent = extractRelevantContent(initialHtml);
  const textEncoder = new TextEncoder();
  const data = textEncoder.encode(initialRelevantContent);
  try{
    const hashBufferPromise =  crypto.subtle.digest('SHA-256', data);
    const hashBuffer = await hashBufferPromise;
    const hashArray = Array.from(new Uint8Array(hashBuffer));
    previousHtmlHash = hashArray.map(b => b.toString(16).padStart(2, '0')).join('');
    notifyBackend("initial load", previousHtmlHash);
  }
  catch(e){
     console.error("Error calculating initial hash",e);
  }


  // 5. Cleanup function (important for extension context)
  window.cleanupChangeObserver = () => {
    clearInterval(urlCheckInterval);
    observer.disconnect();
    window.removeEventListener("popstate", () => {}); //remove listener
    window.removeEventListener("hashchange", () => {});
    console.log("Change observer and listeners cleaned up.");
  };
}

// Initialize URL and HTML change detection.
window.changeObserver = {
  setupChangeObserver,
};


