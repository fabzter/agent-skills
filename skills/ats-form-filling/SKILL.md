---
name: ats-form-filling
description: "Use when filling job application forms in live Chrome."
tags: [career, jobs, workday, ats, browser, cdp, forms]
---

# ATS Form Filling (live Chrome via CDP relay)

Fill job-application forms (Workday, Greenhouse, etc.) in the user's **real, logged-in Chrome tab**
through the omp browser relay. Verified end-to-end on a Workday application (LexisNexis/RELX,
11 work-experience entries, zero validation errors, 2026-09-25).

**Transport mechanics** (relay health, tab discovery, attach/evaluate skeleton) live in the
hub skill `chrome-relay-live-tab` — read it first. This skill covers the **form-filling layer**.

## Operating protocol with this user (non-negotiable)

1. **He navigates, you fill.** Never navigate, submit, or click anything beyond the section being
   filled without explicit permission for that action.
2. **Confirm factual assertions before writing them.** Employment dates, "I currently work here",
   salary expectations — anything a recruiter could treat as a legal statement gets a `clarify`
   first if sources conflict (e.g. CV says "Present" but he actually left the job).
3. **Entries must match the attached CV.** Workday auto-attaches the last-used resume; recruiters
   compare form vs CV. Source of truth: CV v3 + the mapping doc (below). Do not paraphrase dates
   or titles from memory.
4. **The final submit is HIS, with automation disconnected.** Workday fails submits while CDP is
   attached. "Save and Continue" between steps has never failed with the relay attached, but the
   final Review→Submit must happen with the relay/extension off. Tell him when you reach that point.
5. Workday persists a step **only** on "Save and Continue" — save each step before touching another.

## Data sources (read before filling)

- **CV (current):** `~/Library/CloudStorage/GoogleDrive-faboster@gmail.com/My Drive/LifeStyle/cv/cv-internal-ats-v4.docx`
  (`read_file` auto-extracts docx). **v4 = v3 + Azure edits** (Azure PaaS since 2012, CAF landing-zone
  design areas, Terraform/Bicep as *used not expert*, K8s/Docker). Older versions (v3, v2, ats, plain)
  sit beside it — **use v4** unless the target specifically needs the Azure-lean baseline (v3 was the
  one submitted to LexisNexis/RELX). Never overstate Azure beyond
  `02_areas/career/azure-landing-zone-research.md` §7/§10 — those are the red lines.
- **Mapping + headline lessons:** vault `02_areas/career/workday-cv-mapping.md` — the 11 experience
  entries in order, degree mapping (UAM Ingeniería en Computación → "Bachelor of Engineering (BE)"),
  website URLs (LinkedIn URL needs percent-encoding: the `á` breaks plain-text fields).

## The two React input patterns (the core technique)

Workday/Greenhouse are React apps. Which pattern you need depends on the widget:

### Pattern A — native setter (text inputs, textareas)

Plain `.value =` assignment does NOT update React state. Use:

```js
const set = (el, value) => {
  const proto = el.tagName === 'TEXTAREA' ? HTMLTextAreaElement.prototype : HTMLInputElement.prototype;
  Object.getOwnPropertyDescriptor(proto, 'value').set.call(el, value);
  el.dispatchEvent(new Event('input', {bubbles: true}));
  el.dispatchEvent(new Event('change', {bubbles: true}));
};
```

### Pattern B — real CDP keystrokes (`role="spinbutton"` date fields)

Workday month/year fields are **spinbuttons, not dropdowns**. Pattern A writes a value that the
component ignores (readback shows empty). They need real input events:

1. `el.scrollIntoView({block:'center'}); el.focus()` via `Runtime.evaluate`
2. confirm `document.activeElement === el`
3. `Input.insertText {text: "02"}` over the CDP **sessionId** (month is numeric; "2" renders "02")
4. dispatch input/change + `el.blur()` to commit
5. verify via the sibling display: `el.closest('[role="group"]').innerText` → `"02 / 2026"`

**Diagnostic tell:** `role="spinbutton"` + a `getBoundingClientRect()` that stays **0×0** even after
scrollIntoView. It's a hidden proxy input beside a rendered date display. Do NOT hunt for
`[role="option"]` listbox items — there are none, and a global option query will surface some
*other* widget's listbox (observed: Education's "Computer Engineering" option appeared while
probing the month field) and mislead you into thinking the dropdown is broken.

## Workday "My Experience" structure (verified)

- Steps: 1 My Information → 2 My Experience → 3 Application Questions → 4 Review.
  `useMyLastApplication` pre-fills Education + attaches the last CV.
- Field ids: `workExperience-{blockId}--{jobTitle|companyName|location|currentlyWorkHere|roleDescription}`
  and `workExperience-{blockId}--{startDate|endDate}-dateSection{Month|Year}-input`.
  Education: `education-{id}--schoolName` etc. Skills: `skills--skills` (multiselect).
- **Block ids increment per Add** (392 → 415 → 442 → …). After clicking Add, find the new block by
  collecting all `workExperience-(\d+)--` prefixes and picking the one whose `jobTitle` is empty.
- **"Add"/"Add Another" buttons are ambiguous** — Education and Languages sections have their own.
  Scope by walking up ≤10 ancestors to the nearest heading and matching `/work experience/i`.
- **"I currently work here" checkbox**: `cb.click()` if unchecked → the endDate inputs are removed
  from the DOM (readback returns null — that's success, not data loss).
- Validation scan: `[role="alert"]` texts, excluding noise like "cv-…docx successfully uploaded".

## Workflow per section

1. **Read the live form first** (all controls + labels + current values) before writing anything.
2. Probe structural widgets (one Add click) and **map the new block's field ids** before batch-filling.
3. Fill entry-by-entry; **readback-verify every entry** (values + date-group display text + validation alerts).
4. Batch script template: `templates/workday-experience-fill.py` — adapt the ENTRIES list and the
   TARGET tab id; it handles Add-scoping, empty-block discovery, both input patterns, and the final
   all-blocks verification pass. Run with the Hermes venv python (`websockets` lib lives there).
5. Report a table of what was written, plus **every judgment call you made** (overlaps kept, entries
   split, wording choices) so the user can veto before Save and Continue.
6. Hand off: he clicks Save and Continue (or authorizes you to), and the final submit is his with the relay off.

## Pitfalls

- **Overlapping dates are OK** when the CV lists them that way (freelance parallel to full-time —
  Shifta 07/2023–02/2024 overlaps EY). Workday does not flag it. Keep CV order and wording.
- **One company, two roles** = two entries (Lagash Technical Leader + Senior SWE), as in the CV.
- `Input.insertText` goes to whatever has focus — always verify `document.activeElement` immediately
  before sending, or you'll type into the wrong field.
- After any write, trust **readback**, not transport success. A CDP `result` with no error means the
  expression ran, not that React accepted the value.
- The relay tab list shows page `<title>` from history, which can be stale ("Sign In" on a
  logged-in application page) — match tabs by **URL**, and confirm session state by reading the
  page's own header (e.g. the signed-in email).
- Long textareas: `\n` in JSON-encoded strings survives `insertText`/native-setter fine; verified
  1,184-char descriptions with bullets.
- **Skills multiselect may be UNFILLABLE — verify before promising it.** Workday's "Type to Add
  Skills" is a **server-side curated dictionary**, not free text: it calls
  `/wday/calypso/cxs/<tenant>/skillsearch` and only accepts picks from the response. Enter/Tab does
  NOT create a custom chip. Some tenants ship an **empty** dictionary (RELX confirmed 2026-09-28:
  every query — including single letters — returned `[]` with HTTP 200, verified by replaying the
  app's own request with its `X-CALYPSO-CSRF-TOKEN`). Symptom: the dropdown always shows
  "No Items." regardless of input. **Diagnose in 3 steps:** (1) type a common term, check
  `[data-automation-id="activeListContainer"]` for "No Items."; (2) monkeypatch `window.fetch` from
  CDP to capture the real request shape (method/headers/params); (3) replay it directly with the
  CSRF header. If the dictionary is empty, the section is optional — **skip it and say so**, don't
  burn the session. The skills still reach the ATS via the attached CV and the role descriptions.
- **React can hold STALE state after a native-setter write — the DOM lies.** Confirmed 2026-09-28 on
  Workday: one jobTitle field of 11 showed the correct `.value` in the DOM, yet Save and Continue
  failed with *"The field Job Title is required and must have a value."* React's internal state never
  registered the synthetic-event write (likely a re-render race when "Add Another" repainted the
  list). **Fix:** re-type that field with real CDP input — focus+select via JS, clear with a real
  `Backspace` dispatchKeyEvent (no `text` prop), `Input.insertText` the value, commit with a real
  `Tab`. **Prevention: the form's own validation is the only truth.** After filling, have the user
  click Save and Continue, then re-scan `[aria-invalid="true"]` and resolve each field's
  `aria-describedby` to read the actual message. Never declare a section done on `.value` readback alone.
- `Input.dispatchKeyEvent` with a `text` prop **doubles every character** ("Node" → "NNooddee"). Use
  `Input.insertText` for text; use `dispatchKeyEvent` *without* `text` (only `key` /
  `windowsVirtualKeyCode`) for Enter/Tab/Backspace/arrows.

## Related

- `chrome-relay-live-tab` (hub skill) — relay transport, attach skeleton, safety rules
- Vault: `02_areas/career/workday-cv-mapping.md` — entry list, degree mapping, submit rule origin (Edelman 2026-08-25)
- `job-lead-verification` — screening leads BEFORE applying
