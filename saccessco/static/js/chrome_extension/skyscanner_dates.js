/**
 * skyscanner_dates.js
 *
 * This module provides functionality to interact with Skyscanner's custom date picker,
 * specifically to find a date element and scroll it into view by simulating navigation
 * through "Next month" or "Previous month" buttons.
 *
 * NOTE: This version is adapted for Chrome Extension content scripts (Manifest V3)
 * which do not natively support ES Module 'export' keywords when loaded via manifest.json.
 * Functions are exposed via the 'window' object.
 */

// --- Helper Functions (Internal to this module) ---

/**
 * Checks if an element is visible within the viewport.
 * Accounts for display, visibility, opacity, and bounding box.
 * @param {HTMLElement} el The element to check.
 * @returns {boolean} True if the element is visible, false otherwise.
 */
function isElementVisible(el) {
    if (!el) {
        return false;
    }
    const style = window.getComputedStyle(el);
    if (style.display === 'none' || style.visibility === 'hidden' || parseFloat(style.opacity) === 0) {
        return false;
    }

    const rect = el.getBoundingClientRect();
    // Check if any part of the element is within the viewport
    return (
        rect.top < (window.innerHeight || document.documentElement.clientHeight) &&
        rect.left < (window.innerWidth || document.documentElement.clientWidth) &&
        rect.bottom > 0 &&
        rect.right > 0
    );
}

/**
 * Scrolls an element into view smoothly.
 * @param {HTMLElement} el The element to scroll.
 */
function scrollElementIntoView(el) {
    if (el) {
        el.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }
}

/**
 * Parses an aria-label string (e.g., "July 2025" or "15 July 2025") into a Date object
 * representing the first day of that month.
 * @param {string} ariaLabelString The aria-label string.
 * @returns {Date|null} A Date object for the first day of the month, or null if parsing fails.
 */
function getMonthYearFromAriaLabel(ariaLabelString) {
    if (!ariaLabelString) return null;

    // Try to match "Month Year" (e.g., "July 2025")
    let match = ariaLabelString.match(/([A-Za-z]+)\s+(\d{1,2}),?\s+(\d{4})/i);
    if (match) {
        const monthName = match[1];
        const year = parseInt(match[2], 10);
        const monthIndex = new Date(Date.parse(monthName + " 1, " + year)).getMonth();
        if (!isNaN(monthIndex)) {
            return new Date(year, monthIndex, 1);
        }
    }

    // Try to match "Day Month Year" (e.g., "15 July 2025")
    match = ariaLabelString.match(/\d{1,2}\s+([A-Za-z]+)\s+(\d{4})/);
    if (match) {
        const monthName = match[1];
        const year = parseInt(match[2], 10);
        const monthIndex = new Date(Date.parse(monthName + " 1, " + year)).getMonth();
        if (!isNaN(monthIndex)) {
            return new Date(year, monthIndex, 1);
        }
    }

    return null;
}

/**
 * Finds all visible month header elements in the calendar.
 * Assumes month headers have aria-labels like "Month Year".
 * @returns {HTMLElement[]} An array of visible month header elements.
 */
function findVisibleMonthHeaders() {
    const monthHeaders = document.querySelectorAll('[aria-label]'); // Select all elements with aria-label
    const visibleHeaders = [];

    monthHeaders.forEach(header => {
        const ariaLabel = header.getAttribute('aria-label');
        // Check if aria-label looks like a month header (e.g., "July 2025")
        // and if it's visible.
        if (ariaLabel && /\b[A-Za-z]+\s+\d{4}\b/.test(ariaLabel) && isElementVisible(header)) {
            visibleHeaders.push(header);
        }
    });
    return visibleHeaders;
}

/**
 * Determines the earliest visible month in the calendar.
 * @returns {Date|null} A Date object representing the first day of the earliest visible month, or null.
 */
function getEarliestVisibleCalendarMonth() {
    const visibleHeaders = findVisibleMonthHeaders();
    if (visibleHeaders.length === 0) {
        return null;
    }

    // Sort headers by their month/year to find the earliest one
    visibleHeaders.sort((a, b) => {
        const dateA = getMonthYearFromAriaLabel(a.getAttribute('aria-label'));
        const dateB = getMonthYearFromAriaLabel(b.getAttribute('aria-label'));
        if (!dateA || !dateB) return 0; // Should not happen if findVisibleMonthHeaders is good
        return dateA.getTime() - dateB.getTime();
    });

    return getMonthYearFromAriaLabel(visibleHeaders[0].getAttribute('aria-label'));
}

/**
 * Simulates a click on a given element.
 * @param {HTMLElement} el The element to click.
 */
function simulateClick(el) {
    if (el) {
        el.click();
    }
}

// --- Main Exposed Functions ---

/**
 * Attempts to find and return a DOM element representing a specific date in Skyscanner's
 * date picker. If the element is not initially visible, it tries to navigate the calendar
 * by clicking "Next month" or "Previous month" buttons until the target month is visible.
 *
 * @param {string} cssSelector A CSS selector in the form: `aria-label*='<Day of month> <Month name> <Year>'`.
 * Example: `"aria-label*='30 July 2025'"` or `"aria-label*='10 October 2025.'"`
 * @returns {Promise<HTMLElement|null>} A promise that resolves with the found HTMLElement
 * if the date is found and made visible, or `null` otherwise.
 */
async function scrollToDate(cssSelector) {
    // 1. Initial attempt to find the exact date element
    let targetElement = document.querySelector(cssSelector);

    if (targetElement) {
        if (isElementVisible(targetElement)) {
            console.log(`[scrollToDate] Element for "${cssSelector}" found and is visible.`);
            return targetElement;
        } else {
            console.log(`[scrollToDate] Element for "${cssSelector}" found but not visible. Attempting direct scroll...`);
            scrollElementIntoView(targetElement);
            await new Promise(resolve => setTimeout(resolve, 500)); // Give a small moment for the scroll to complete
            if (isElementVisible(targetElement)) {
                console.log(`[scrollToDate] Element for "${cssSelector}" is now visible after direct scroll.`);
                return targetElement;
            } else {
                console.warn(`[scrollToDate] Element for "${cssSelector}" not visible even after direct scroll.`);
            }
        }
    }

    console.log(`[scrollToDate] Element for "${cssSelector}" not found or not initially visible. Attempting calendar navigation...`);

    // Extract the target month and year from the selector
    const match = cssSelector.match(/aria-label\*=["']([A-Za-z]+)\s+\d{1,2},\s+\d{4}["']\]?$/i);
    let targetMonthString = null;
    if (match && match[1]) {
        targetMonthString = match[1]; // e.g., "July 302025"
    }

    const targetMonthDate = getMonthYearFromAriaLabel(targetMonthString);

    if (!targetMonthDate) {
        console.error(`[scrollToDate] Could not extract valid month/year from selector: "${cssSelector}".`);
        return null;
    }

    let attempts = 0;
    const maxNavigationAttempts = 24; // Max attempts (e.g., 2 years worth of months)

    while (attempts < maxNavigationAttempts) {
        const currentCalendarMonthDate = getEarliestVisibleCalendarMonth();

        if (!currentCalendarMonthDate) {
            console.warn(`[scrollToDate] No visible month headers found. Calendar might not be open or loaded.`);
            break; // Exit if no calendar is detected
        }

        // Check if the target month is now visible
        const targetMonthHeaderSelector = `[aria-label*='${targetMonthDate.toLocaleString('en-US', { month: 'long', year: 'numeric' })}']`;
        const targetMonthHeader = document.querySelector(targetMonthHeaderSelector);

        if (targetMonthHeader && isElementVisible(targetMonthHeader)) {
            console.log(`[scrollToDate] Target month "${targetMonthDate.toLocaleString('en-US', { month: 'long', year: 'numeric' })}" is now visible.`);
            break; // Target month is visible, exit navigation loop
        }

        let navigationButton = null;
        if (targetMonthDate.getTime() > currentCalendarMonthDate.getTime()) {
            // Target month is in the future, click "Next month"
            navigationButton = document.querySelector("[aria-label*='Next month']");
            if (navigationButton && isElementVisible(navigationButton)) {
                console.log(`[scrollToDate] Clicking "Next month" button.`);
                simulateClick(navigationButton);
            } else {
                console.warn(`[scrollToDate] "Next month" button not found or not visible. Cannot navigate forward.`);
                break; // Cannot navigate, exit loop
            }
        } else if (targetMonthDate.getTime() < currentCalendarMonthDate.getTime()) {
            // Target month is in the past, click "Previous month"
            navigationButton = document.querySelector("[aria-label*='Previous month']");
            if (navigationButton && isElementVisible(navigationButton)) {
                console.log(`[scrollToDate] Clicking "Previous month" button.`);
                simulateClick(navigationButton);
            } else {
                console.warn(`[scrollToDate] "Previous month" button not found or not visible. Cannot navigate backward.`);
                break; // Cannot navigate, exit loop
            }
        } else {
            // This case means currentCalendarMonthDate is the targetMonthDate, but the header wasn't found visible.
            // This could happen if the header is just slightly out of view or has a different aria-label format.
            // We'll try a direct scroll as a fallback here before giving up.
            console.warn(`[scrollToDate] Current calendar month matches target, but header not directly visible. Attempting direct scroll.`);
            const potentialHeader = document.querySelector(targetMonthHeaderSelector);
            if (potentialHeader) {
                scrollElementIntoView(potentialHeader);
                await new Promise(resolve => setTimeout(resolve, 500));
                if (isElementVisible(potentialHeader)) {
                    console.log(`[scrollToDate] Target month header made visible via direct scroll.`);
                    break;
                }
            }
            console.warn(`[scrollToDate] Could not confirm target month visibility after matching. Exiting navigation.`);
            break; // Exit loop if no navigation needed or possible
        }

        await new Promise(resolve => setTimeout(resolve, 700)); // Wait for calendar animation/load after click
        attempts++;
    }

    // After navigation, re-attempt to find the exact date element
    targetElement = document.querySelector(cssSelector);
    if (targetElement) {
        if (isElementVisible(targetElement)) {
            console.log(`[scrollToDate] Original element for "${cssSelector}" found and is now visible after navigation.`);
            return targetElement;
        } else {
            console.log(`[scrollToDate] Original element for "${cssSelector}" found, but still not fully visible. Scrolling directly.`);
            scrollElementIntoView(targetElement);
            await new Promise(resolve => setTimeout(resolve, 500));
            if (isElementVisible(targetElement)) {
                console.log(`[scrollToDate] Original element for "${cssSelector}" is now visible after final direct scroll.`);
                return targetElement;
            } else {
                console.warn(`[scrollToDate] Original element for "${cssSelector}" still not visible after all attempts.`);
            }
        }
    } else {
        console.warn(`[scrollToDate] Original element for "${cssSelector}" still not found after calendar navigation.`);
    }

    console.warn(`[scrollToDate] Failed to find or make visible the element for "${cssSelector}".`);
    console.log("Tip: Ensure the Skyscanner date picker is open/active before calling this function.");
    return null;
}

/**
 * Checks if a given CSS selector string matches the expected aria-label date format.
 * The format is: "[aria-label*='<Day of month (no leading zeroes)> <Month name> <Year>']"
 * It now also recognizes an optional dot '.' after the year.
 *
 * @param {string} selector The CSS selector string to validate.
 * @returns {boolean} True if the selector matches the format, false otherwise.
 */
function isDateSelector(selector) {
    const regex = /^\[aria-label\*=(["'])([A-Za-z]+)\s+(\d{1,2})(?:,\s*|\s+)(\d{4})\.?\1\]$/i;
    return regex.test(selector);
}

// Expose functions to the global window object for access from other content scripts
window.skyscannerDates = {
    scrollToDate: scrollToDate,
    isDateSelector: isDateSelector
};