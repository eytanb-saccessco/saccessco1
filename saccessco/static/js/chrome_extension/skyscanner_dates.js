/**
 * skyscanner_dates.js
 *
 * Interact with Skyscanner's date picker:
 *  - Find a date cell by aria-label and ensure it is visible (scroll/navigate months).
 *
 * Note: Designed for Chrome Extension content scripts (MV3).
 * Exposes functions on window.skyscannerDates.
 */

/* ======================= Helpers ======================= */

/**
 * Minimal wait helper.
 * @param {number} ms
 * @returns {Promise<void>}
 */
function wait(ms) {
  return new Promise(r => setTimeout(r, ms));
}

/**
 * Checks if an element is visible in the viewport.
 * @param {HTMLElement} el
 * @returns {boolean}
 */
function isElementVisible(el) {
  if (!el) return false;
  const style = window.getComputedStyle(el);
  if (style.display === 'none' || style.visibility === 'hidden' || parseFloat(style.opacity) === 0) {
    return false;
  }
  const rect = el.getBoundingClientRect();
  return (
    rect.top < (window.innerHeight || document.documentElement.clientHeight) &&
    rect.left < (window.innerWidth || document.documentElement.clientWidth) &&
    rect.bottom > 0 &&
    rect.right > 0
  );
}

/**
 * Ensure selector includes >= current year; replace any year < current with current.
 * If no 4-digit year exists, appends one additional [aria-label*="YYYY"] token.
 * @param {string} selector
 * @param {number} minYear defaults to current year
 * @returns {string}
 */
function normalizeAriaLabelDateSelector(selector, minYear = new Date().getFullYear()) {
  let s = String(selector);

  // Append a year token if missing altogether
  if (!/\b\d{4}\b/.test(s)) {
    s += `[aria-label*="${minYear}"]`;
  }

  // For each aria-label*="...": bump any 4-digit year lower than minYear up to minYear
  s = s.replace(/aria-label\*=(["'“”‘’])([\s\S]*?)\1/giu, (full, q, val) => {
    const newVal = val.replace(/\b(\d{4})\b/g, (m, yStr) => {
      const y = +yStr;
      return (y >= 1900 && y < minYear) ? String(minYear) : yStr;
    });
    return `aria-label*=${q}${newVal}${q}`;
  });

  return s;
}

/**
 * Smoothly scroll element into view.
 * @param {HTMLElement} el
 */
function scrollElementIntoView(el) {
  if (el) el.scrollIntoView({ behavior: 'smooth', block: 'center' });
}

/**
 * Parse an aria-label string OR a full selector like:
 *   [aria-label*='October 22, 2025']  or  [aria-label*='October 22'][aria-label*='2025']
 * Returns Date(year, monthIndex, 1) or null.
 * Extremely tolerant to curly quotes, NBSP/RTL marks, extra punctuation/words.
 * @param {string} input
 * @returns {Date|null}
 */
function getMonthYearFromAriaLabel(input) {
  if (!input) return null;
  let s = String(input);

  // Collect ALL aria-label*="..."/curly-quoted values and join them (so tokens like "October 22" + "2025" are combined).
  const allVals = [...s.matchAll(/aria-label\*=\s*(['"'“”‘’])([\s\S]*?)\1/giu)].map(m => m[2]);
  if (allVals.length) s = allVals.join(' ');

  // Normalize: remove BOM/format marks, fold spaces, keep only content words/digits.
  s = s.normalize('NFKC')
       .replace(/^\uFEFF+/, '')
       .replace(/\p{Cf}|\u00A0|\u2007|\u202F/gu, ' ')
       .replace(/\s+/g, ' ')
       .trim();

  // Month map (long + short)
  const MONTHS = {
    jan:0,january:0, feb:1,february:1, mar:2,march:2, apr:3,april:3, may:4,
    jun:5,june:5, jul:6,july:6, aug:7,august:7,
    sep:8,sept:8,september:8, oct:9,october:9, nov:10,november:10, dec:11,december:11
  };
  const monthIdx = w => (w ? (MONTHS[w.toLowerCase()] ?? MONTHS[w.toLowerCase().slice(0,3)] ?? -1) : -1);

  // Find month token and any 4-digit year (in any order in the normalized text).
  const mMonth = s.match(/\b(jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|jul(?:y)?|aug(?:ust)?|sep(?:t(?:ember)?)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)\b/i);
  const mYear  = s.match(/(?:^|\D)(\d{4})(?=\D|$)/);

  if (mMonth && mYear) {
    const mi = monthIdx(mMonth[1]);
    const y  = +mYear[1];
    if (mi >= 0 && y >= 1900) return new Date(y, mi, 1);
  }

  if (getMonthYearFromAriaLabel.DEBUG) {
    const codes = Array.from(s).map(ch => ch.charCodeAt(0).toString(16).padStart(4,'0'));
    console.warn('[getMonthYearFromAriaLabel] parse failed', { normalized: s, codes });
  }
  return null;
}
getMonthYearFromAriaLabel.VERSION = '2025-08-20b';
getMonthYearFromAriaLabel.DEBUG = false;

/**
 * Click helper.
 * @param {HTMLElement} el
 */
function simulateClick(el) {
  if (el) el.click();
}

/* ======================= Core ======================= */

/**
 * Try to find a date cell by aria-label* selector and ensure it becomes visible.
 * Strategy:
 *   1) Try to find + direct-scroll if present.
 *   2) Otherwise, brute-force click Next/Previous month buttons until found (no header dependency).
 *
 * @param {string} cssSelector Example: `[aria-label*='15 September, 2025']`
 *                             Works with comma/no-comma, and with an extra `[aria-label*="YYYY"]` token.
 * @param {Object} [options]
 * @param {number} [options.maxNavigationAttempts=36] Max month-clicks to try.
 * @param {"auto"|"next"|"prev"} [options.direction="auto"] Preferred direction; "auto" picks a heuristic, else falls back to "next".
 * @param {number} [options.postClickWaitMs=700] Wait after each month navigation click (ms).
 * @returns {Promise<HTMLElement|null>}
 */
async function scrollToDate(cssSelector, options = {}) {
  const {
    maxNavigationAttempts = 36,
    direction: preferredDirection = 'auto',
    postClickWaitMs = 700,
  } = options;

  // Ensure year >= current, and add year if missing
  cssSelector = normalizeAriaLabelDateSelector(cssSelector);
  console.log('[scrollToDate] Attempting to scroll to:', cssSelector);

  // 1) Initial find
  let targetElement = document.querySelector(cssSelector);
  if (targetElement) {
    if (isElementVisible(targetElement)) {
      console.log(`[scrollToDate] Element for "${cssSelector}" found and is visible.`);
      return targetElement;
    }
    console.log(`[scrollToDate] Element for "${cssSelector}" found but not visible. Attempting direct scroll...`);
    scrollElementIntoView(targetElement);
    await wait(500);
    if (isElementVisible(targetElement)) {
      console.log(`[scrollToDate] Element for "${cssSelector}" is now visible after direct scroll.`);
      return targetElement;
    }
    console.warn(`[scrollToDate] Element for "${cssSelector}" not visible even after direct scroll.`);
  }

  console.log(`[scrollToDate] Element for "${cssSelector}" not found or not initially visible. Attempting calendar navigation...`);

  // Parse month/year from the FULL selector (parser merges all aria-label tokens).
  const targetMonthDate = getMonthYearFromAriaLabel(cssSelector);
  if (!targetMonthDate) {
    console.error(`[scrollToDate] Could not extract valid month/year from selector: "${cssSelector}".`);
    return null;
  }

  // Navigation controls
  const nextBtnSel = "[aria-label*='Next month']";
  const prevBtnSel = "[aria-label*='Previous month']";

  // Decide a direction (heuristic), but don't depend on headers; fall back to 'next'.
  let direction = preferredDirection;
  if (direction === 'auto') {
    // Try to infer from any visible month header (optional heuristic)
    let inferred = null;
    try {
      const headers = Array.from(document.querySelectorAll('[aria-label]'))
        .filter(h => /\b[A-Za-z]+\s+\d{4}\b/.test(h.getAttribute('aria-label') || ''))
        .map(h => getMonthYearFromAriaLabel(h.getAttribute('aria-label')))
        .filter(Boolean)
        .sort((a, b) => a - b);
      if (headers.length) {
        inferred = (targetMonthDate.getTime() >= headers[0].getTime()) ? 'next' : 'prev';
      }
    } catch (_) { /* ignore */ }
    direction = inferred || 'next';
  }

  // Brute-force click months until the cell appears.
  let attempts = 0;
  while (attempts < maxNavigationAttempts) {
    // Re-check if the target is now available/visible
    const hit = document.querySelector(cssSelector);
    if (hit) {
      if (!isElementVisible(hit)) {
        scrollElementIntoView(hit);
        await wait(300);
      }
      if (isElementVisible(hit)) {
        console.log(`[scrollToDate] Found target after ${attempts} navigation click(s).`);
        return hit;
      }
    }

    const nextBtn = document.querySelector(nextBtnSel);
    const prevBtn = document.querySelector(prevBtnSel);

    if (!nextBtn && !prevBtn) {
      console.warn(`[scrollToDate] Calendar controls not found (picker likely closed). Re-open it, then call scrollToDate again.`);
      return null;
    }

    // Choose which button to click this iteration
    let btn = null;
    if (direction === 'next') {
      btn = nextBtn || prevBtn;          // prefer next; fall back to prev if next missing
    } else if (direction === 'prev') {
      btn = prevBtn || nextBtn;          // prefer prev
    } else { // safety
      btn = nextBtn || prevBtn;
    }

    if (!btn) {
      // Flip direction once if needed
      direction = (direction === 'next') ? 'prev' : 'next';
      attempts++;
      continue;
    }

    console.log(`[scrollToDate] Clicking "${btn === nextBtn ? 'Next month' : 'Previous month'}"`);
    simulateClick(btn);
    await wait(postClickWaitMs);
    attempts++;
  }

  // Final attempt to grab and scroll
  targetElement = document.querySelector(cssSelector);
  if (targetElement) {
    scrollElementIntoView(targetElement);
    await wait(300);
    if (isElementVisible(targetElement)) {
      console.log(`[scrollToDate] Original element for "${cssSelector}" became visible after navigation.`);
      return targetElement;
    }
  }

  console.warn(`[scrollToDate] Gave up after ${maxNavigationAttempts} navigation attempts.`);
  console.log("Tip: Ensure the Skyscanner date picker is open/active before calling this function.");
  return null;
}

/**
 * Validate selector format:
 * Accepts Month-first or Day-first, comma optional, quotes preserved (single/double/curly).
 * Examples:
 *   [aria-label*='September 15, 2025']
 *   [aria-label*="15 September 2025"]
 *   [aria-label*='September 15'][aria-label*='2025']  // also valid after normalization
 * @param {string} selector
 * @returns {boolean}
 */
function isDateSelector(selector) {
  // Accept the common single-token patterns; multi-token selectors still pass usage even if this returns false.
  const re =
    /^\[aria-label\*=(["'“”‘’])(?:(?:[A-Za-z]+)\s+\d{1,2}|\d{1,2}\s+[A-Za-z]+)(?:,\s*|\s+)\d{4}\.?\1\]$/iu;
  return re.test(selector) || /\[aria-label\*\=.*?\]\[aria-label\*\=.*?\]/i.test(selector);
}

/* ======================= Exports ======================= */

window.skyscannerDates = {
  scrollToDate,
  isDateSelector,
  normalizeAriaLabelDateSelector,
  getMonthYearFromAriaLabel
};
