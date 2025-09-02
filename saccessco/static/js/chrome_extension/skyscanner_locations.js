/**
 * skyscanner_locations.js — robust origin/destination selector for Skyscanner
 *
 * Exposes on window.skyscannerLocations:
 *   selectLocation(mode, text, options?) => Promise<boolean>
 *     - mode: 'origin' | 'destination'
 *     - text: user text (city/airport/country, may include IATA in parens e.g., "Paris (CDG)")
 *     - options: { timeout?: number, selectFirst?: boolean, match?: string }
 *         • selectFirst (default true): if no good match, pick the first suggestion.
 *         • match: optional hint to prefer suggestions containing this substring.
 */
(function(window){
  'use strict';

  /* ================= Helpers ================= */
  function wait(ms){ return new Promise(r=>setTimeout(r,ms)); }
  function visible(el){
    if(!el) return false; var s=getComputedStyle(el);
    if(s.display==='none'||s.visibility==='hidden'||+s.opacity===0) return false;
    var r=el.getBoundingClientRect();
    return r.width>0 && r.height>0 && r.bottom>0 && r.right>0 && r.top < (innerHeight||document.documentElement.clientHeight) && r.left < (innerWidth||document.documentElement.clientWidth);
  }
  function scrollIntoView(el){ if(el) el.scrollIntoView({behavior:'smooth', block:'center'}); }
  function robustClick(el){
    if(!el) return false; var t=el;
    try {
      t.dispatchEvent(new PointerEvent('pointerdown',{pointerId:1,pointerType:'mouse',isPrimary:true,bubbles:true}));
      t.dispatchEvent(new MouseEvent('mousedown',{bubbles:true,cancelable:true,button:0}));
      t.dispatchEvent(new PointerEvent('pointerup',{pointerId:1,pointerType:'mouse',isPrimary:true,bubbles:true}));
      t.dispatchEvent(new MouseEvent('mouseup',{bubbles:true,cancelable:true,button:0}));
      t.click();
      return true;
    } catch(_) {
      try { t.click(); return true; } catch(_2){ return false; }
    }
  }
  function q(sel){ try { return document.querySelector(sel); } catch(_) { return null; } }
  function qVisible(sel){ var el=q(sel); return visible(el)?el:null; }
  function allVisible(sel){ try{ return Array.prototype.slice.call(document.querySelectorAll(sel)).filter(visible); }catch(_){ return []; } }
  function collapseSpaces(s){ return String(s||'').replace(/\s+/g,' ').trim(); }
  function normText(s){ return collapseSpaces(String(s||'')).toLowerCase(); }

  function iataFromString(s){ var m=String(s||'').match(/\(([A-Za-z]{3})\)/); return m? m[1].toUpperCase():null; }
  function stripParens(s){ return String(s||'').replace(/\([^)]*\)/g,'').trim(); }

  function fireInput(el){ el.dispatchEvent(new Event('input',{bubbles:true})); el.dispatchEvent(new Event('change',{bubbles:true})); }
  function setInputValue(el, value){ el.value=''; fireInput(el); el.value=value; fireInput(el); }

  /* -------- find & open inputs -------- */
  function originTriggers(){ return ["#originInput-input","[id='originInput-input']","[aria-controls='originInput-menu']","[data-testid*='origin']","[aria-label*='From']","[aria-label*='from']"]; }
  function destinationTriggers(){ return ["#destinationInput-input","[id='destinationInput-input']","[aria-controls='destinationInput-menu']","[data-testid*='destination']","[aria-label*='To']","[aria-label*='to']"]; }

  function findInput(mode){
    var sels = mode==='destination' ? destinationTriggers() : originTriggers();
    for (var i=0;i<sels.length;i++){
      var el = qVisible(sels[i]);
      if (el && (el.tagName==='INPUT' || el.getAttribute('role')==='combobox')) return el;
    }
    // generic fallback: pick the visible combobox within the search panel
    var generic = allVisible("input[role='combobox'], input[type='search'], input[type='text']");
    return generic.length ? generic[0] : null;
  }

  async function openField(mode){
    var sels = mode==='destination' ? destinationTriggers() : originTriggers();
    for (var i=0;i<sels.length;i++){
      var el=qVisible(sels[i]); if(el){ scrollIntoView(el); robustClick(el); await wait(100); var input=findInput(mode); if(input) return input; }
    }
    return findInput(mode);
  }

  function menuRoots(mode){
    var roots = [];
    if (mode==='destination') roots.push("#destinationInput-menu","[id='destinationInput-menu']");
    else roots.push("#originInput-menu","[id='originInput-menu']");
    roots.push("[role='listbox']","ul[role='listbox']","div[role='listbox']");
    return roots;
  }

  function visibleOptions(mode){
    var roots = menuRoots(mode);
    for (var i=0;i<roots.length;i++){
      var root = q(roots[i]);
      if (!root) continue;
      var opts = Array.prototype.slice.call(root.querySelectorAll("[role='option'], li[role='option']"));
      opts = opts.filter(visible);
      if (opts.length) return opts;
    }
    // global fallback (shouldn't normally be needed)
    return allVisible("[role='option'], li[role='option']");
  }

  function optionText(opt){
    if(!opt) return '';
    var t = (opt.getAttribute('aria-label') || opt.innerText || opt.textContent || '').trim();
    return collapseSpaces(t);
  }

  function scoreOption(opt, wantText, hint){
    var text = optionText(opt);
    var ntext = normText(text);
    var want = normText(wantText);
    var wantCity = normText(stripParens(wantText));
    var wantIata = iataFromString(wantText);

    var score = 0;
    if (hint){ var nh = normText(hint); if (ntext.indexOf(nh)!==-1) score += 50; }
    if (wantIata){ // prioritize exact IATA presence
      if (/\(([A-Za-z]{3})\)/.test(text) && ntext.indexOf('(' + wantIata.toLowerCase() + ')') !== -1) score += 40;
    }
    if (ntext === want) score += 30;
    if (ntext.indexOf(want)!==-1) score += 20;
    if (ntext.indexOf(wantCity)!==-1) score += 15;
    // prefer (Any) for city-only queries if nothing else matches strongly
    if (!wantIata && /\(Any\)/i.test(text)) score += 5;

    return score;
  }

  function pickBestOption(opts, wantText, hint){
    if (!opts || !opts.length) return null;
    var best = null, bestScore = -1;
    for (var i=0;i<opts.length;i++){
      var sc = scoreOption(opts[i], wantText, hint);
      if (sc > bestScore){ best = opts[i]; bestScore = sc; }
    }
    return best || null;
  }

  async function selectLocation(mode, text, options){
    options = options || {};
    var timeout = options.timeout || 9000;
    var selectFirst = (options.selectFirst !== false);
    var hint = options.match || null;

    mode = (String(mode||'origin').toLowerCase().indexOf('dest')!==-1) ? 'destination' : 'origin';

    // 1) Open the correct field and type
    var input = await openField(mode);
    if (!input) throw new Error('Input for ' + mode + ' not found');

    scrollIntoView(input);
    setInputValue(input, text);
    await wait(150);

    // 2) Wait for the suggestions to appear
    var start = Date.now();
    var opts = visibleOptions(mode);
    while (!opts.length && Date.now() - start < timeout){ await wait(120); opts = visibleOptions(mode); }

    if (!opts.length){
      // Sometimes a small additional key to trigger results helps
      input.value = text + ' ';
      fireInput(input);
      await wait(200);
      opts = visibleOptions(mode);
    }

    if (!opts.length){ throw new Error('No suggestions became visible for ' + mode); }

    // 3) Choose best or first
    var choice = pickBestOption(opts, text, hint);
    if (!choice && selectFirst) choice = opts[0];
    if (!choice) throw new Error('No suitable option for ' + mode);

    scrollIntoView(choice);
    robustClick(choice);
    await wait(150);

    // verify field is populated/closed (best-effort)
    return true;
  }

  window.skyscannerLocations = { selectLocation };
  console.log('skyscanner_locations.js loaded (robust dropdown selection with safe fallbacks).');
})(window);
