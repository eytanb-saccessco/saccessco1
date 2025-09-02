// saccessco/static/js/chrome_extension/page_manipulator.js
// Executes AI-produced plans against the live page (content script).
// Works with split helpers: window.skyscannerDates + window.skyscannerLocations.

(function (window) {
  'use strict';

  /* ----------------------- Utilities & Helpers ----------------------- */
  function _sleep(ms) { return new Promise(r => setTimeout(r, ms)); }
  function _dbg(msg) { try { if (window.debug && typeof window.debug.message === 'function') window.debug.message(msg); } catch (_) { /* no-op */ } }
  function _visible(el) {
    if (!el) return false;
    var s = getComputedStyle(el);
    if (s.display === 'none' || s.visibility === 'hidden' || +s.opacity === 0) return false;
    var r = el.getBoundingClientRect();
    return r.width > 0 && r.height > 0 && r.bottom > 0 && r.right > 0 && r.top < innerHeight && r.left < innerWidth;
  }

  function _robustClick(el) {
    if (!el) return false;
    var target = el;
    if (!target.matches('button,[role="button"],a,[role="option"],[data-testid],.bpk-autosuggest__suggestion')) {
      var inner = el.querySelector('button,[role="button"],a,[role="option"],.bpk-autosuggest__suggestion');
      if (inner) target = inner;
    }
    try {
      target.dispatchEvent(new PointerEvent('pointerdown', { pointerId: 1, pointerType: 'mouse', isPrimary: true, bubbles: true }));
      target.dispatchEvent(new MouseEvent('mousedown', { bubbles: true, cancelable: true, button: 0 }));
      target.dispatchEvent(new PointerEvent('pointerup', { pointerId: 1, pointerType: 'mouse', isPrimary: true, bubbles: true }));
      target.dispatchEvent(new MouseEvent('mouseup', { bubbles: true, cancelable: true, button: 0 }));
      target.click();
      return true;
    } catch (e) {
      try { target.click(); return true; } catch (e2) { return false; }
    }
  }

  function _extractAriaText(selector) {
    var m = String(selector).match(/\[(aria-label|aria-labelledby)\*?=\s*(["'])((?:.|\n|\r)*?)\2/i);
    return m ? m[3] : null;
  }
  function _fallbackClickByText(text) {
    if (!text) return false;
    var want = _collapseSpaces(String(text).trim().toLowerCase());
    var nodes = Array.prototype.slice.call(document.querySelectorAll('button,[role="button"],[data-testid],li,span,a,[role="option"]')).filter(_visible);
    function norm(n) { return _collapseSpaces((n.innerText || n.textContent || '').replace(/\s+/g, ' ').trim().toLowerCase()); }
    var chosen = nodes.find(function (n) { return norm(n) === want; }) || nodes.find(function (n) { return norm(n).indexOf(want) !== -1; });
    return chosen ? _robustClick(chosen) : false;
  }

  /* ----------------------- Parameter Manager ----------------------- */
  class parameterManager {
    constructor(initialParams = {}) {
      if (typeof initialParams !== 'object' || initialParams === null) {
        console.warn("ParameterManager: initialParams provided is not a valid object. Initializing with empty parameters.");
        this._parameters = {};
      } else {
        this._parameters = { ...initialParams };
      }
      console.log("ParameterManager initialized with parameters:", this._parameters);
    }
    async get(key, promptMessage, isSensitive = false) {
      if (key == null || key === 'undefined') return null;
      if (key in this._parameters) {
        console.log(`ParameterManager: Found '${key}' in internal parameters.`);
        return this._parameters[key];
      }
      console.log(`ParameterManager: '${key}' not found. Attempting to prompt user.`);
      if (!window.speechModule || typeof window.speechModule.askUserInput !== 'function') {
        console.error(`ParameterManager: window.speechModule.askUserInput is not available. Cannot prompt user for '${key}'.`);
        return null;
      }
      try {
        const defaultPrompt = `Please provide the value for ${key}:`;
        const finalPromptMessage = promptMessage || defaultPrompt;
        const userInput = await window.speechModule.askUserInput(finalPromptMessage, isSensitive);
        if (userInput === null || typeof userInput === 'undefined' || (typeof userInput === 'string' && userInput.trim() === '')) {
          const message = `Input for '${key}' was not provided or cancelled. Action may be incomplete.`;
          console.warn("ParameterManager:", message);
          if (window.chatModule && typeof window.chatModule.addMessage === 'function') {
            window.chatModule.addMessage("Saccessco", message);
          }
          return null;
        }
        this._parameters[key] = userInput;
        return userInput;
      } catch (e) {
        console.error(`ParameterManager: Error while prompting user for '${key}':`, e);
        if (window.chatModule && typeof window.chatModule.addMessage === 'function') {
          window.chatModule.addMessage("Saccessco", `Error retrieving input for '${key}': ${e && e.message ? e.message : 'Unknown error.'}`);
        }
        return null;
      }
    }
    set(key, value) { this._parameters[key] = value; }
    getAll() { return { ...this._parameters }; }
  }

  // Mock for manual testing if speechModule not present
  if (!window.speechModule || typeof window.speechModule.askUserInput !== 'function') {
    window.speechModule = window.speechModule || {};
    window.speechModule.askUserInput = async function (message, sensitive) {
      console.log("(MOCK) askUserInput:", message, "Sensitive:", !!sensitive);
      return new Promise(function (resolve) {
        var mockInput = prompt("(MOCK UI) " + message + "\n(Type 'null' to simulate no input/cancel)");
        resolve(mockInput === 'null' ? null : mockInput);
      });
    };
    console.log("Mock speechModule.askUserInput initialized.");
  }

  /* ---------------- Trip type guard (One way vs Return/Roundtrip) ---------------- */
  function _qVisible(sel){ try { var el=document.querySelector(sel); return _visible(el)?el:null; } catch(_) { return null; } }
  function _clickIfVisible(sel){ var el=_qVisible(sel); return el? _robustClick(el):false; }
  function _collapseSpaces(t){ t=String(t||''); return t.replace(/\s+/g,' ').trim(); }
  function _findClickableContainsText(text){ if(!text) return null; var want=_collapseSpaces(String(text).toLowerCase()); var nodes=Array.prototype.slice.call(document.querySelectorAll('button,[role="button"],[data-testid],li,span,a')).filter(_visible); function norm(n){return _collapseSpaces((n.innerText||n.textContent||'').toLowerCase());} for(var i=0;i<nodes.length;i++){ if(norm(nodes[i]).indexOf(want)!==-1) return nodes[i]; } return null; }
  async function _openTripTypeMenuOnce(){
    var triggers=["[data-testid*='trip']","[aria-label*='Trip']","[aria-label*='Travel']"];
    for(var i=0;i<triggers.length;i++){ if(_clickIfVisible(triggers[i])){ await _sleep(150); return true; } }
    var chip=_findClickableContainsText('one way')||_findClickableContainsText('roundtrip')||_findClickableContainsText('round trip')||_findClickableContainsText('return')||_findClickableContainsText('multi');
    if(chip){ _robustClick(chip); await _sleep(150); return true; }
    return false;
  }
  function _findTripOptionByMode(mode){
    mode=(mode||'RETURN').toUpperCase();
    var map={ RETURN:["[data-testid='RETURN']","[data-testid='ROUNDTRIP']","[data-testid='ROUND_TRIP']"], ONE_WAY:["[data-testid='ONE_WAY']","[data-testid='ONEWAY']"], MULTICITY:["[data-testid='MULTICITY']","[data-testid='MULTI_CITY']"] };
    var texts={ RETURN:['Roundtrip','Round trip','Return'], ONE_WAY:['One way','One-way'], MULTICITY:['Multi-city','Multi city','Multicity'] };
    var sels=map[mode]||[]; for(var i=0;i<sels.length;i++){ var el=_qVisible(sels[i]); if(el) return el; }
    var labels=texts[mode]||[]; for(var j=0;j<labels.length;j++){ var el2=_findClickableContainsText(labels[j]); if(el2) return el2; }
    return null;
  }
  function _tripModeFromSelector(sel){ var s=String(sel||'').toLowerCase(); if(/one\s*-?\s*way/.test(s)) return 'ONE_WAY'; if(/round\s*-?\s*trip|roundtrip|return/.test(s)) return 'RETURN'; if(/multi/.test(s)) return 'MULTICITY'; return 'RETURN'; }
  async function _ensureTripMode(mode){
    var opt=_findTripOptionByMode(mode); if(opt){ _robustClick(opt); await _sleep(120); return true; }
    var opened=await _openTripTypeMenuOnce();
    if(opened){ await _sleep(120); opt=_findTripOptionByMode(mode); if(opt){ _robustClick(opt); await _sleep(150); return true; } }
    var fallback=_findClickableContainsText((String(mode).toUpperCase()==='RETURN')?'round':(String(mode).toUpperCase()==='ONE_WAY')?'one way':'multi');
    if(fallback){ _robustClick(fallback); await _sleep(120); return true; }
    return false;
  }
  function _selectorImpliesReturn(selector){ var s=String(selector||'').toLowerCase(); return /\breturn\b/.test(s) || /\bround\s*-?\s*trip\b/.test(s) || /\broundtrip\b/.test(s) || /\breturn-btn\b/.test(s) || /\bret-?btn\b/.test(s); }

  /* ---------------- Dates: fast-path via window.skyscannerDates ---------------- */
  function _isDateSelector(selector) {
    try { return !!(window.skyscannerDates && typeof window.skyscannerDates.isDateSelector === 'function' && window.skyscannerDates.isDateSelector(selector)); }
    catch (_) { return false; }
  }
  async function _ensureDateVisibleIfNeeded(selector) {
    if (!_isDateSelector(selector)) return;
    try {
      if (window.skyscannerDates && typeof window.skyscannerDates.scrollToDate === 'function') {
        await window.skyscannerDates.scrollToDate(selector);
        await _sleep(60);
      }
    } catch (e) { console.warn('[pageManipulator] date helper failed for', selector, e); }
  }

  /* ---------------- Locations: fast-path via window.skyscannerLocations ---------------- */
  function _isOriginButtonSelector(s) { if (!s) return false; var x = String(s); return /\borigin\b/i.test(x) || /\bflying\s+from\b/i.test(x) || /\bfrom\b/i.test(x) || /data-testid\s*=\s*['\"]?origin/i.test(x); }
  function _isDestinationButtonSelector(s) { if (!s) return false; var x = String(s); return /\bdestination\b/i.test(x) || /\bflying\s+to\b/i.test(x) || /\bto\b/i.test(x) || /data-testid\s*=\s*['\"]?destination/i.test(x); }
  function _looksLikeLocationStep(step) {
    if (!step) return false;
    var sel = String(step.selector || '');
    if (step.action === 'click' && (_isOriginButtonSelector(sel) || _isDestinationButtonSelector(sel))) return true;
    if (step.action === 'typeInto' && /(input\[role=['"]combobox['"]]|input\[type=['"](search|text)['"]]|#(origin|destination)Input)/i.test(sel)) return true;
    if ((step.action === 'waitForElement' || step.action === 'click') && (/[\[]role=['"]listbox['"][\]]/i.test(sel) || /-menu['"]?\]/i.test(sel))) return true;
    if (step.action === 'click' && /\((?:[A-Z]{3})\)/.test(sel)) return true; // IATA in selector
    return false;
  }
  async function _tryHandleLocationSequence(plan, parameterManagerInstance) {
    if (!Array.isArray(plan) || !window.skyscannerLocations || typeof window.skyscannerLocations.selectLocation !== 'function') {
      return { handled: false };
    }
    var mode = null;           // 'origin' | 'destination'
    var textParamName = null;  // parameter name to read (e.g., 'origin_text')

    for (var i = 0; i < plan.length; i++) {
      var step = plan[i];
      var sel = step && step.selector ? String(step.selector) : '';
      if (!mode && step && step.action === 'click') {
        if (_isOriginButtonSelector(sel)) mode = 'origin';
        if (_isDestinationButtonSelector(sel)) mode = 'destination';
      } else if (mode && step && step.action === 'typeInto' && typeof step.data === 'string' && step.data) {
        textParamName = step.data; // the parameter key which holds the user's text
        break;
      }
    }
    if (!mode || !textParamName) return { handled: false };

    var text = await parameterManagerInstance.get(textParamName);
    if (!text) return { handled: false };

    try {
      await window.skyscannerLocations.selectLocation(mode, String(text), { selectFirst: true });
      return { handled: true, mode: mode, value: text };
    } catch (e) {
      console.warn('[pageManipulator] location fast-path failed; fallback will proceed.', e);
      return { handled: false };
    }
  }

  /* ----------------------- Core Page Manipulator ----------------------- */
  var pageManipulator = {
    _findElementAndAssertVisible: async function (selector, timeoutMs, checkIntervalMs) {
      if (typeof selector !== 'string' || !selector) {
        console.error("PageManipulator: _findElementAndAssertVisible invalid/null selector.");
        if (window.chatModule && typeof window.chatModule.addMessage === 'function') {
          window.chatModule.addMessage("Saccessco", "Error finding element: Invalid selector provided.");
        }
        return null;
      }
      // If selector implies a return date control, ensure trip mode supports return first
      if (_selectorImpliesReturn(selector)) {
        try { await _ensureTripMode('RETURN'); } catch (e) { console.warn('[pageManipulator] ensureTripMode RETURN failed:', e); }
      }

      // Date selectors: reveal target cell before querying element again
      if (_selectorImpliesReturn(selector)) { await _ensureTripMode('RETURN'); }
      await _ensureDateVisibleIfNeeded(selector);

      var startTime = Date.now();
      var deadline = startTime + (timeoutMs || 10000);

      while (Date.now() < deadline) {
        var element = null;
        try { element = document.querySelector(selector); } catch (e) { element = null; }
        if (element) {
          element.scrollIntoView({ block: 'center', inline: 'nearest', behavior: 'smooth' });
          await _sleep(100);
          if (_visible(element)) {
            var duration = Date.now() - startTime;
            console.log('PageManipulator: element "%s" visible in %dms.', selector, duration);
            _dbg('Element "' + selector + '" found and visible in ' + duration + 'ms.');
            return element;
          }
        }
        await _sleep(checkIntervalMs || 100);
      }

      var errorMsg = 'PageManipulator: timeout waiting for "' + selector + '" after ' + (timeoutMs || 10000) + 'ms.';
      console.warn(errorMsg);
      if (window.chatModule && typeof window.chatModule.addMessage === 'function') {
        window.chatModule.addMessage("Saccessco", "Element not found or visible: " + selector + ".");
      }
      return null;
    },

    /* -------------------- Public action methods -------------------- */
    waitForElement: async function (selector /*, data */) {
      try {
        await _ensureDateVisibleIfNeeded(selector);
        var element = await pageManipulator._findElementAndAssertVisible(selector);
        if (element) {
          console.log('PageManipulator: Successfully waited for "%s".', selector);
          return { success: true };
        }
        return { success: false, error: 'waitForElement: "' + selector + '" not found/visible after timeout.' };
      } catch (e) {
        return { success: false, error: 'waitForElement error for "' + selector + '": ' + e.message };
      }
    },

    typeInto: function (element, data) {
      if (!element) return { success: false, error: "typeInto: element is null." };
      if (element.tagName === 'INPUT' || element.tagName === 'TEXTAREA') {
        element.value = data != null ? data : '';
        element.dispatchEvent(new Event('input', { bubbles: true }));
        element.dispatchEvent(new Event('change', { bubbles: true }));
        console.log('PageManipulator: Typed "%s" into element.', data);
        return { success: true };
      } else if (element.isContentEditable) {
        element.textContent = data != null ? data : '';
        element.dispatchEvent(new Event('input', { bubbles: true }));
        element.dispatchEvent(new Event('change', { bubbles: true }));
        console.log('PageManipulator: Set contentEditable to "%s".', data);
        return { success: true };
      }
      return { success: false, error: "Element is not input/textarea/contenteditable." };
    },

    click: function (element /*, data */) {
      try {
        var ok = _robustClick(element);
        if (!ok) throw new Error("robust click failed");
        console.log('PageManipulator: Clicked element.');
        return { success: true };
      } catch (e) {
        return { success: false, error: "click error: " + e.message };
      }
    },

    scrollTo: function (element /*, data */) {
      try {
        element.scrollIntoView({ block: 'center', inline: 'nearest', behavior: 'smooth' });
        console.log('PageManipulator: Scrolled to element.');
        return { success: true };
      } catch (e) {
        return { success: false, error: "scrollTo error: " + e.message };
      }
    },

    checkCheckbox: function (element, data) {
      if (data == null) data = true;
      if (!element || element.type !== 'checkbox') return { success: false, error: "Not a checkbox." };
      try {
        element.checked = !!data;
        element.dispatchEvent(new Event('change', { bubbles: true }));
        console.log('PageManipulator: %s checkbox.', data ? 'Checked' : 'Unchecked');
        return { success: true };
      } catch (e) {
        return { success: false, error: "checkCheckbox error: " + e.message };
      }
    },

    checkRadioButton: function (element, data) {
      if (data == null) data = true;
      if (!element || element.type !== 'radio') return { success: false, error: "Not a radio button." };
      try {
        if (data) element.checked = true;
        element.dispatchEvent(new Event('change', { bubbles: true }));
        console.log('PageManipulator: Checked radio button.');
        return { success: true };
      } catch (e) {
        return { success: false, error: "checkRadioButton error: " + e.message };
      }
    },

    selectOptionByValue: function (element, data) {
      if (!element || element.tagName !== 'SELECT') return { success: false, error: "Not a <select>." };
      try {
        element.value = String(data != null ? data : '');
        element.dispatchEvent(new Event('change', { bubbles: true }));
        console.log('PageManipulator: Selected value "%s".', data);
        return { success: true };
      } catch (e) {
        return { success: false, error: "selectOptionByValue error: " + e.message };
      }
    },

    selectOptionByIndex: function (element, data) {
      if (!element || element.tagName !== 'SELECT') return { success: false, error: "Not a <select>." };
      var index = parseInt(data, 10);
      if (!isFinite(index) || index < 0 || index >= element.options.length) {
        return { success: false, error: 'Invalid index "' + data + '".' };
      }
      try {
        element.selectedIndex = index;
        element.dispatchEvent(new Event('change', { bubbles: true }));
        console.log('PageManipulator: Selected index "%d".', index);
        return { success: true };
      } catch (e) {
        return { success: false, error: "selectOptionByIndex error: " + e.message };
      }
    },

    enter: function (element /*, data */) {
      if (!element) return { success: false, error: "enter: element not found." };
      try {
        var kd = new KeyboardEvent('keydown', { key: 'Enter', bubbles: true, cancelable: true });
        var ku = new KeyboardEvent('keyup', { key: 'Enter', bubbles: true, cancelable: true });
        element.dispatchEvent(kd);
        element.dispatchEvent(ku);
        console.log('PageManipulator: Simulated Enter on element.');
        return { success: true };
      } catch (e) {
        return { success: false, error: "enter error: " + e.message };
      }
    },

    focusElement: function (element /*, data */) {
      if (!element) return { success: false, error: "focusElement: element not found." };
      if (typeof element.focus === 'function') {
        element.focus();
        console.log('PageManipulator: Focused element.');
        return { success: true };
      }
      return { success: false, error: "Element cannot be focused." };
    },

    submitForm: function (element /*, data */) {
      var formElement = null;
      if (element && element.tagName === 'FORM') formElement = element;
      else if (element && element.form) formElement = element.form;
      if (!formElement) return { success: false, error: "No form to submit." };
      try {
        var submitEvent = new Event('submit', { bubbles: true, cancelable: true });
        var notCancelled = formElement.dispatchEvent(submitEvent);
        if (notCancelled && typeof formElement.submit === 'function') {
          formElement.submit();
        }
        console.log('PageManipulator: submit dispatched (defaultPrevented=%s).', (!notCancelled).toString());
        return { success: true };
      } catch (e) {
        return { success: false, error: "submitForm error: " + e.message };
      }
    },

    /* ----------------------- Plan Executor ----------------------- */
    executePlan: async function (plan, parameters) {
      _dbg("Executing Plan: " + JSON.stringify(plan) + " with parameters: " + JSON.stringify(parameters));
      var individualActionResults = [];
      var overallStatus = "completed";

      try {
        if (!Array.isArray(plan)) {
          console.error("PageManipulator: executePlan received non-array plan:", plan);
          return { status: "failed", results: [{ success: false, error: "Invalid plan: not an array." }] };
        }

        var params = new parameterManager(parameters);

        // 1) Try LOCATION fast-path (do NOT return early; still run plan, but skip redundant steps later)
        var locationHandled = false;
        try {
          var fp = await _tryHandleLocationSequence(plan, params);
          if (fp && fp.handled) {
            locationHandled = true;
            individualActionResults.push({ action: "selectLocation", selector: "(collapsed origin/destination flow)", value: fp.value || null, success: true });
          }
        } catch (e) {
          console.warn("[pageManipulator] location fast-path detection error; continuing with fallback.", e);
        }

        // 2) If the plan includes any step that implies a return action, proactively ensure RETURN mode once
        try {
          var needsReturn = plan.some(function(st){ return st && typeof st.selector==='string' && _selectorImpliesReturn(st.selector); });
          if (needsReturn) { await _ensureTripMode('RETURN'); }
        } catch (e) { console.warn('[pageManipulator] pre-ensure RETURN failed:', e); }

        // 3) Step-by-step execution
        for (var i = 0; i < plan.length; i++) {
          var step = plan[i];

          // Skip location steps if handled by fast-path
          if (locationHandled && _looksLikeLocationStep(step)) {
            individualActionResults.push({ action: step.action, selector: step.selector, value: null, success: true });
            await _sleep(30);
            continue;
          }

          var actionResult = { success: true };
          var element = null;
          var data = null;

          console.log("PageManipulator: Executing action:", step.action, "selector:", step.selector);

          if (step.action === 'waitForElement') {
            actionResult = await this.waitForElement(step.selector, null);
          } else {
            // Ensure date cells are navigated into view just before a click
            if (step.action === 'click' && _isDateSelector(step.selector)) {
              await _ensureDateVisibleIfNeeded(step.selector);
            }

            element = await this._findElementAndAssertVisible(step.selector);

            if (!element) {
              // 1) Trip-type fallback: plans sometimes target brittle labels like "Round-trip".
              if (step.action === 'click' && /round\s*-?\s*trip|roundtrip|one\s*-?\s*way|multi|return/i.test(String(step.selector))) {
                try {
                  var _mode = _tripModeFromSelector(step.selector);
                  var _ok = await _ensureTripMode(_mode);
                  if (_ok) {
                    individualActionResults.push({ action: step.action, selector: step.selector + ' (trip-mode fallback)', value: null, success: true });
                    await _sleep(40);
                    continue; // next plan step
                  }
                } catch (e) { /* ignore and fall through */ }
              }

              // 2) Fallback: click by visible text contained in aria-label
              if (step.action === 'click') {
                var ok = _fallbackClickByText(_extractAriaText(step.selector));
                if (ok) {
                  individualActionResults.push({ action: step.action, selector: step.selector + " (fallback text)", value: null, success: true });
                  await _sleep(40);
                  continue;
                }
              }

              actionResult = { success: false, error: 'Element "' + step.selector + '" not found/visible for "' + step.action + '".' };
            } else {
              if (step.data !== null && step.data !== undefined) { data = await params.get(step.data); }
              var actionFunction = this[step.action];
              if (typeof actionFunction === 'function') {
                _dbg("Executing " + step.action + " on " + step.selector + " with data: " + data);
                actionResult = actionFunction(element, data);
              } else {
                actionResult = { success: false, error: 'Unknown action: ' + step.action };
              }
            }
          }

          _dbg("Step result: " + JSON.stringify({ action: step.action, selector: step.selector, value: data, success: actionResult.success, error: actionResult.error }));

          individualActionResults.push({ action: step.action, selector: step.selector, value: data, success: actionResult.success, error: actionResult.error });

          if (!actionResult.success) { overallStatus = "failed"; _dbg("Failed step: " + JSON.stringify(individualActionResults[individualActionResults.length - 1])); break; }
          if (actionResult.success) { await _sleep(50); }
        }

        console.log("PageManipulator: Plan finished. Overall status:", overallStatus, "Results:", individualActionResults);
        return { status: overallStatus, results: individualActionResults };

      } catch (topLevelError) {
        console.error("PageManipulator: Top-level execution error:", topLevelError);
        return { status: "failed", results: individualActionResults.length ? individualActionResults : [{ success: false, error: "Top-level execution error: " + (topLevelError && topLevelError.message ? topLevelError.message : "Unknown") }] };
      }
    }
  };

  // Aliases
  pageManipulator.enterValue = pageManipulator.typeInto;
  pageManipulator.setValue  = pageManipulator.typeInto;

  // Expose globally
  window.pageManipulatorModule = pageManipulator;
  console.log("Page Manipulator module loaded (split-aware: dates + locations + resilient trip-type switching).");
})(window);
