LOCATION_INSTRUCTIONS = """
5. When selecting an option in a dropdown list (autosuggest menus, listboxes):

Do not invent option labels. Only click options that actually exist in the DOM.

Prefer “contains” matching (case-insensitive) over exact matches.

Use these attribute sources in order of preference (whichever exists on the option items):

aria-label → [aria-label*="<user input>" i]

text content (fallback when attributes are absent)

data-testid → [data-testid*="<user input>" i]

value (only if present) → [value*="<user input>" i]

If no option contains the user’s text, select the first visible option in the list.

Skip non-option utilities (e.g. “Include nearby airports” toggles) if present.

Skyscanner location flow (origin/destination)

When the user asks to set origin or destination:

Open/focus the input

Origin: click the origin control, then type:

{"action":"click","selector":"[id*='Origin']","data":null}
{"action":"typeInto","selector":"#originInput-input, [id*='originInput']","data":"origin_city"}


Destination: click the destination control, then type:

{"action":"click","selector":"[id*='Destination']","data":null}
{"action":"typeInto","selector":"#destinationInput-input, [id*='destinationInput']","data":"destination_city"}


Wait for the autosuggest menu
(listbox appears under the input; ID is typically *Input-menu)

{"action":"waitForElement","selector":"[id*='originInput-menu'], [id*='destinationInput-menu'], [role='listbox']","data":null}


Choose the best-match option by “contains”; else choose first

Preferred (aria-label contains, case-insensitive):

{"action":"click","selector":"[id*='originInput-item'][aria-label*='{{origin_city}}' i], [role='option'][aria-label*='{{origin_city}}' i]","data":null}


Fallbacks (try in order):

{"action":"click","selector":"[id*='originInput-item'][data-testid*='{{origin_city}}' i], [role='option'][data-testid*='{{origin_city}}' i]","data":null}
{"action":"click","selector":"[id*='originInput-item'][value*='{{origin_city}}' i], [role='option'][value*='{{origin_city}}' i]","data":null}


Final fallback (always succeeds): click the first option

{"action":"click","selector":"#originInput-item-0, [id^='originInput-item-'], [id*='originInput-menu'] [role='option']:first-child","data":null}


Use the analogous selectors for destination (replace originInput → destinationInput).

Notes

Keep the “contains” match; do not generate selectors like "Paris (PAR)" unless that exact text exists.

When both a city aggregate (e.g., “Paris (Any)”) and specific airports appear, either is acceptable unless the user explicitly asks for a specific airport code.
"""