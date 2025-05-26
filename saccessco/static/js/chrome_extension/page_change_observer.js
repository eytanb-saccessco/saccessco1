// page_change_observer.js

let previousHtmlHash = ""; // Stores the hash of the previously sent HTML content
let urlCheckIntervalId = null; // To store the interval ID for cleanup
let mutationObserverInstance = null; // To store the MutationObserver instance for cleanup

// --- Helper Functions ---

/**
 * Extracts relevant content from HTML, mirroring the Python HTMLHasher.
 * @param {string} html - The full HTML string of the page.
 * @returns {string} The extracted relevant text content.
 */
function extractRelevantContent(html) {
  const parser = new DOMParser();
  const doc = parser.parseFromString(html, "text/html");

  // Extract the title
  const titleElement = doc.querySelector("title");
  const title = titleElement ? titleElement.textContent.trim() : "";

  // Extract the main text content from paragraphs within <main> or globally
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
 * Calculates the SHA-256 hash of a given string content.
 * @param {string} content - The string content to hash.
 * @returns {Promise<string>} A promise that resolves with the SHA-256 hash as a hex string.
 */
async function calculateHash(content) {
  const textEncoder = new TextEncoder();
  const data = textEncoder.encode(content);
  const hashBuffer = await crypto.subtle.digest('SHA-256', data);
  const hashArray = Array.from(new Uint8Array(hashBuffer));
  return hashArray.map(b => b.toString(16).padStart(2, '0')).join('');
}

/**
 * Sends the current page's HTML content to the backend.
 * @param {string} htmlContent - The full HTML content to send.
 * @param {string} mutationType - The type of event that triggered the notification (for logging).
 */
async function notifyBackend(htmlContent, mutationType) {
  console.log(`Page change (${mutationType}) detected. Sending HTML to backend. Length: ${htmlContent.length}`);
  try {
    // window.backendCommunicatorModule.sendPageChange expects only html as per latest fixed version
    await window.backendCommunicatorModule.sendPageChange(htmlContent);
    console.log(`Successfully sent page change (${mutationType}) to backend.`);
  } catch (e) {
    console.error(`Error sending page change (${mutationType}) to backend:`, e);
  }
}

/**
 * Checks for HTML content changes, calculates hash, and notifies backend if changed.
 * This function is reused by MutationObserver and URL change listeners.
 * @param {string} triggerType - The type of event that triggered this check (e.g., "DOM mutation", "popstate").
 */
async function checkAndNotifyHtmlChange(triggerType) {
  const newHtml = document.documentElement.outerHTML;
  const newRelevantContent = extractRelevantContent(newHtml);

  try {
    const newHtmlHash = await calculateHash(newRelevantContent);

    if (newHtmlHash !== previousHtmlHash) {
      console.log(`HTML content hash changed due to ${triggerType}.`);
      previousHtmlHash = newHtmlHash; // Update the stored hash
      await notifyBackend(newHtml, triggerType);
    } else {
      console.log(`HTML content hash unchanged after ${triggerType}.`);
    }
  } catch (e) {
    console.error(`Error calculating hash during ${triggerType} check:`, e);
  }
}

// --- Event Handlers for URL Changes (defined as named functions for removal) ---
let currentUrl = window.location.href; // Keep track of current URL for polling

const popstateHandler = () => {
  console.log("popstate event: URL changed to", window.location.href);
  checkAndNotifyHtmlChange("popstate");
};

const hashchangeHandler = () => {
  console.log("hashchange event: URL changed to", window.location.href);
  checkAndNotifyHtmlChange("hashchange");
};

const urlPollingCheck = () => {
  if (window.location.href !== currentUrl) {
    currentUrl = window.location.href;
    console.log("URL changed (polling) to", currentUrl);
    checkAndNotifyHtmlChange("url polling");
  }
};


// --- Main Setup Function ---

/**
 * Sets up listeners to detect URL and HTML changes and notifies the backend.
 */
async function setupChangeObserver() {
  // 1. Initial page state load and send
  const initialHtml = document.documentElement.outerHTML;
  const initialRelevantContent = extractRelevantContent(initialHtml);
  try {
    previousHtmlHash = await calculateHash(initialRelevantContent);
    await notifyBackend(initialHtml, "initial load");
  } catch (e) {
    console.error("Error calculating or sending initial HTML hash:", e);
  }

  // 2. Observe DOM mutations for HTML changes.
  // The callback directly calls checkAndNotifyHtmlChange
  mutationObserverInstance = new MutationObserver((mutationsList) => {
    // We don't need to iterate mutationsList here, as we always check the whole document
    // and only notify if the hash of the whole document's relevant content changes.
    // This debounces multiple rapid mutations into one check.
    checkAndNotifyHtmlChange("DOM mutation");
  });

  // Start observing the entire document body for all relevant changes
  mutationObserverInstance.observe(document.body, {
    childList: true,    // Monitor additions/removals of child nodes
    subtree: true,      // Monitor changes in the entire subtree
    attributes: true,   // Monitor changes to attributes.
    characterData: true // Monitor changes to text content.
  });
  console.log("MutationObserver started.");


  // 3. Listen for URL changes using History API and hash changes.
  window.addEventListener("popstate", popstateHandler);
  window.addEventListener("hashchange", hashchangeHandler);
  console.log("URL change listeners (popstate, hashchange) added.");


  // 4. Fallback: Poll for URL changes every second.
  urlCheckIntervalId = setInterval(urlPollingCheck, 1000);
  console.log("URL polling started.");


  // 5. Cleanup function (important for extension context)
  window.cleanupChangeObserver = () => {
    if (urlCheckIntervalId) {
      clearInterval(urlCheckIntervalId);
      urlCheckIntervalId = null;
      console.log("URL polling stopped.");
    }
    if (mutationObserverInstance) {
      mutationObserverInstance.disconnect();
      mutationObserverInstance = null;
      console.log("MutationObserver disconnected.");
    }
    window.removeEventListener("popstate", popstateHandler);
    window.removeEventListener("hashchange", hashchangeHandler);
    console.log("History API listeners removed.");
    console.log("Change observer and listeners cleaned up.");
  };
}

// Expose the setup function globally for the extension to call
window.changeObserver = {
  setupChangeObserver,
};

// Example of how it might be called from background.js or another module:
// window.changeObserver.setupChangeObserver().then();
