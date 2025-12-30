/**
 * skyscanner_locations.js — robust origin/destination selector for Skyscanner
 *
 * Exposes on window.skyscannerLocations:
 *   - selectLocation(mode, cityText, options?) => Promise<boolean>
 *
 * mode: 'origin' | 'destination'
 * cityText: string provided by user (e.g. "Paris")
 * options: { selectFirst?: boolean } (default true)
 */
(function(window){
  'use strict';

  function wait(ms){ return new Promise(r=>setTimeout(r,ms)); }

  function isVisible(el){
    if(!el) return false;
    var s = window.getComputedStyle(el);
    if (s.display==='none' || s.visibility==='hidden' || +s.opacity===0) return false;
    var r = el.getBoundingClientRect();
    return r.width>0 && r.height>0 && r.bottom>0 && r.right>0;
  }

  async function selectLocation(mode, cityText, options){
    options = options||{};
    var selectFirst = options.selectFirst!==false;
    var btnId   = (mode==='origin')? '#OriginButton' : '#DestinationButton';
    var inputId = (mode==='origin')? '#originInput-input' : '#destinationInput-input';
    var menuId  = (mode==='origin')? '#originInput-menu' : '#destinationInput-menu';

    // 1. Click button to open input
    var btn = document.querySelector(btnId);
    if(btn){ btn.click(); await wait(300); }

    // 2. Type into input
    var input = document.querySelector(inputId);
    if(input){
      input.value = cityText;
      input.dispatchEvent(new Event('input',{bubbles:true}));
      input.dispatchEvent(new Event('change',{bubbles:true}));
      await wait(500);
    } else {
      console.warn('[skyscannerLocations] Input not found for', mode);
      return false;
    }

    // 3. Wait for dropdown to appear
    var deadline = Date.now()+4000; var listEl=null;
    while(Date.now()<deadline && !listEl){
      listEl = document.querySelector(menuId);
      if(!listEl) await wait(100);
    }
    if(!listEl){
      console.warn('[skyscannerLocations] Dropdown menu not found for', mode);
      return false;
    }

    // 4. Collect options
    var items = listEl.querySelectorAll('[id*="item"][role="option"]');
    if(!items.length){
      console.warn('[skyscannerLocations] No options found in menu');
      return false;
    }

    // 5. Try to match by aria-label/text
    var norm = cityText.toLowerCase();
    var match=null;
    for(var i=0;i<items.length;i++){
      var lab = (items[i].getAttribute('aria-label')||'').toLowerCase();
      if(lab.includes(norm)){ match=items[i]; break; }
    }

    if(!match && selectFirst){ match=items[0]; }

    if(match){
      match.click();
      console.log('[skyscannerLocations] Selected option:', match.getAttribute('aria-label'));
      return true;
    }

    console.warn('[skyscannerLocations] No matching option for', cityText);
    return false;
  }

  window.skyscannerLocations = { selectLocation };
  console.log('skyscanner_locations.js loaded.');
})(window);