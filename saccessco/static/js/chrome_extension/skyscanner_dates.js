/**
 * skyscanner_dates.js — robust date picker helper for Skyscanner
 *
 * Exposes on window.skyscannerDates:
 *   - scrollToDate(cssSelector, options?) => Promise<HTMLElement|null>
 *   - isDateSelector(selector) => boolean
 *   - ensureDateVisible(cssSelector, options?) => Promise<HTMLElement|null>
 *
 * Notes:
 *  - Accepts selectors like: [aria-label*='December 20, 2025'] or [aria-label*="20 December 2025"]
 *  - Will open/navigate calendar months via the native next/prev controls until the date cell appears.
 */

(function(window){
  'use strict';

  /* ======================= Helpers ======================= */
  function wait(ms){ return new Promise(r=>setTimeout(r,ms)); }

  function isElementVisible(el){
    if(!el) return false;
    var s = window.getComputedStyle(el);
    if (s.display === 'none' || s.visibility === 'hidden' || +s.opacity === 0) return false;
    var r = el.getBoundingClientRect();
    return r.width>0 && r.height>0 && r.bottom>0 && r.right>0 && r.top < (window.innerHeight||document.documentElement.clientHeight) && r.left < (window.innerWidth||document.documentElement.clientWidth);
  }

  function scrollElementIntoView(el){ if(el) el.scrollIntoView({behavior:'smooth', block:'center'}); }

  function monthIndexFromName(name){
    if(!name) return -1; var n = String(name).toLowerCase();
    var map = { jan:0,january:0, feb:1,february:1, mar:2,march:2, apr:3,april:3, may:4, jun:5,june:5, jul:6,july:6, aug:7,august:7, sep:8,sept:8,september:8, oct:9,october:9, nov:10,november:10, dec:11,december:11 };
    return (n in map) ? map[n] : (n.length>3 && (map[n.slice(0,3)] ?? -1));
  }

  function normalizeTextSpaces(s){
    return String(s||'')
      .replace(/\u00A0|\u2007|\u202F/g, ' ')        // NBSP variants
      .replace(/[\u200B-\u200F\u202A-\u202E]/g,'') // bidi/format marks
      .replace(/\s+/g,' ').trim();
  }

  /**
   * Ensure selector includes a year token; if a year is present and < currentYear, bump it up.
   */
  function normalizeAriaLabelDateSelector(selector, minYear){
    var s = String(selector||'');
    var yearNow = (typeof minYear==='number') ? minYear : (new Date()).getFullYear();
    if (!/\b\d{4}\b/.test(s)) { s = s.replace(/\]$/, "[aria-label*='"+yearNow+"']]"); }
    s = s.replace(/aria-label\*=(["'])(.*?)\1/ig, function(_,q,val){
      var v = String(val).replace(/\b(\d{4})\b/g, function(m,y){ var yy=+y; return (yy>=1900 && yy<yearNow)? String(yearNow) : y; });
      return "aria-label*="+q+v+q;
    });
    return s;
  }

  /**
   * Parse any of:
   *   - "December 20, 2025"
   *   - "20 December 2025"
   *   - or a FULL selector string containing aria-label* tokens (we'll join them)
   * Returns new Date(year, monthIdx, 1) or null
   */
  function getMonthYearFromAriaSource(input){
    if(!input) return null; var s = String(input);
    // If it's a full selector, collect all aria-label* values and join them
    var allVals = [];
    var re = /aria-label\*=\s*(["'])([\s\S]*?)\1/ig; var m; while((m=re.exec(s))){ allVals.push(m[2]); }
    if (allVals.length) s = allVals.join(' ');
    s = normalizeTextSpaces(s);
    // Try "Month D, YYYY" (comma optional)
    var m1 = s.match(/\b([A-Za-z]+)\s+(\d{1,2})(?:,\s*|\s+)(\d{4})\b/);
    if (m1){ var mi1 = monthIndexFromName(m1[1]); var y1=+m1[3]; if(mi1>=0 && y1>=1900) return new Date(y1, mi1, 1); }
    // Try "D Month YYYY"
    var m2 = s.match(/\b(\d{1,2})\s+([A-Za-z]+)\s+(\d{4})\b/);
    if (m2){ var mi2 = monthIndexFromName(m2[2]); var y2=+m2[3]; if(mi2>=0 && y2>=1900) return new Date(y2, mi2, 1); }
    return null;
  }

  function simulateClick(el){ if(el){ try{ el.click(); } catch(_){} } }

  function findVisibleMonthHeaders(){
    var nodes = Array.prototype.slice.call(document.querySelectorAll('[aria-label]'));
    var out = [];
    for (var i=0;i<nodes.length;i++){
      var a = nodes[i].getAttribute('aria-label')||''; var d = getMonthYearFromAriaSource(a);
      if (d && isElementVisible(nodes[i])) out.push({el:nodes[i], d});
    }
    out.sort(function(a,b){ return a.d - b.d; });
    return out;
  }

  /* ======================= Core ======================= */
  async function scrollToDate(cssSelector, options){
    options = options || {};
    var maxNavigationAttempts = options.maxNavigationAttempts || 36; // up to 3 years
    var postClickWaitMs = options.postClickWaitMs || 700;

    // Normalize selector year token behavior and try fast path
    cssSelector = normalizeAriaLabelDateSelector(cssSelector);
    console.log('[skyscannerDates.scrollToDate] target:', cssSelector);

    var target = document.querySelector(cssSelector);
    if (target){
      if (isElementVisible(target)) return target;
      scrollElementIntoView(target); await wait(400);
      if (isElementVisible(target)) return target;
    }

    // Determine target month from the selector itself
    var targetMonthDate = getMonthYearFromAriaSource(cssSelector);
    if (!targetMonthDate){ console.warn('[skyscannerDates] Could not parse month/year from selector:', cssSelector); return null; }

    var nextBtnSel = "button[aria-label*='Next month'], [data-testid*='next-month'], button[aria-label*='Next']";
    var prevBtnSel = "button[aria-label*='Previous month'], [data-testid*='prev'], [data-testid*='previous-month'], button[aria-label*='Previous']";

    var attempts = 0; var direction = 'auto'; var flipped = false;

    while(attempts < maxNavigationAttempts){
      // Re-check for the date cell each loop
      var hit = document.querySelector(cssSelector);
      if (hit){
        if (!isElementVisible(hit)){ scrollElementIntoView(hit); await wait(250); }
        if (isElementVisible(hit)) return hit;
      }

      // Determine direction using visible headers if available
      var headers = findVisibleMonthHeaders();
      var nextBtn = document.querySelector(nextBtnSel);
      var prevBtn = document.querySelector(prevBtnSel);

      if (!nextBtn && !prevBtn){
        console.warn('[skyscannerDates] Calendar controls not found; is the picker open?');
        break;
      }

      var btnToClick = nextBtn || prevBtn; // default safeguard
      if (headers.length){
        var earliest = headers[0].d; var latest = headers[headers.length-1].d;
        if (targetMonthDate > latest) { btnToClick = nextBtn || prevBtn; direction='next'; }
        else if (targetMonthDate < earliest) { btnToClick = prevBtn || nextBtn; direction='prev'; }
        else {
          // Target month is within the current range; small nudge next then prev if not found
          btnToClick = nextBtn || prevBtn;
          if (flipped) btnToClick = prevBtn || nextBtn;
          flipped = !flipped;
        }
      }

      if (!btnToClick){ break; }
      simulateClick(btnToClick);
      await wait(postClickWaitMs);
      attempts++;
    }

    // Final re-check
    target = document.querySelector(cssSelector);
    if (target){ scrollElementIntoView(target); await wait(250); if (isElementVisible(target)) return target; }

    console.warn('[skyscannerDates] Gave up after', attempts, 'attempts for', cssSelector);
    return null;
  }

  function isDateSelector(selector){
    var s = String(selector||'');
    // Accept: [aria-label*='December 20, 2025'] OR [aria-label*="20 December 2025"]
    var re1 = /^\[aria-label\*=(["'])([A-Za-z]+)\s+\d{1,2}(?:,\s*|\s+)\d{4}\1\]$/;
    var re2 = /^\[aria-label\*=(["'])\d{1,2}\s+[A-Za-z]+\s+\d{4}\1\]$/;
    return re1.test(s) || re2.test(s);
  }

  // Alias used by page_manipulator
  async function ensureDateVisible(cssSelector, options){ return scrollToDate(cssSelector, options); }

  window.skyscannerDates = { scrollToDate, isDateSelector, ensureDateVisible, normalizeAriaLabelDateSelector, getMonthYearFromAriaSource };
  console.log('skyscanner_dates.js loaded (robust month/year parsing & navigation).');
})(window);
