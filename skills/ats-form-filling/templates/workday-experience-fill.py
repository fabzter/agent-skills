"""Fill a Workday "My Experience" Work Experience section via the omp CDP relay.

VERIFIED 2026-09-25 on relx.wd3.myworkdayjobs.com (11 entries, 0 validation errors).
Run with: ~/.hermes/hermes-agent/venv/bin/python workday-experience-fill.py

ADAPT BEFORE RUNNING:
  1. TARGET   — the tab id from `curl -s http://127.0.0.1:9224/json` (match by URL, not title!)
  2. ENTRIES  — from CV v3 + vault 02_areas/career/workday-cv-mapping.md. Never from memory.
  3. If a "currentlyWorkHere" entry exists, set endMonth/endYear to None for it.

Safety: fills only; never clicks Save/Submit. Per the user protocol, the final submit
is his, with the relay disconnected (Workday fails submits with CDP attached).
"""
import asyncio
import json
import sys

import websockets

TARGET = "PAGE1319817405"  # <-- ADAPT: relay tab id of the Workday application

# <-- ADAPT: entries in CV order (newest first). sm/sy/em/ey are 2-digit month + 4-digit year strings.
ENTRIES = [
    # {
    #     "jobTitle": "Technical Manager · Sr Staff Engineer / Architect",
    #     "companyName": "LucaEdu",
    #     "location": "Mexico City",
    #     "sm": "02", "sy": "2026", "em": None, "ey": None,  # None = current job
    #     "current": True,
    #     "description": "...",
    # },
]

RELAY = "ws://127.0.0.1:9224/cdp"

SET_TEXT = """(el, value) => {
  const proto = el.tagName === 'TEXTAREA' ? window.HTMLTextAreaElement.prototype : window.HTMLInputElement.prototype;
  const setter = Object.getOwnPropertyDescriptor(proto, 'value').set;
  setter.call(el, value);
  el.dispatchEvent(new Event('input', {bubbles: true}));
  el.dispatchEvent(new Event('change', {bubbles: true}));
}"""

# "Add"/"Add Another" buttons exist in Education/Languages too — scope by section heading.
FIND_WE_ADD = """(() => {
  const btns = Array.from(document.querySelectorAll('button')).filter(b => {
    const t = (b.innerText||'').trim();
    return t === 'Add Another' || t === 'Add';
  });
  for (const b of btns) {
    let el = b;
    for (let k=0; k<10 && el; k++) {
      el = el.parentElement;
      if (!el) break;
      const h = el.querySelector('h1,h2,h3,h4,legend');
      if (h && /work experience/i.test(h.innerText||'')) { b.click(); return 'clicked'; }
    }
  }
  return 'NOT_FOUND';
})()"""

# New block = the workExperience-{id} prefix whose jobTitle is still empty.
FIND_EMPTY_PREFIX = """(() => {
  const ids = Array.from(document.querySelectorAll('input[id^="workExperience-"]'))
    .map(e => e.id.match(/workExperience-(\\d+)--/)[1]);
  for (const p of Array.from(new Set(ids))) {
    const jt = document.getElementById('workExperience-'+p+'--jobTitle');
    if (jt && jt.value.trim() === '') return p;
  }
  return null;
})()"""


async def main():
    async with websockets.connect(RELAY, max_size=None) as ws:
        mid = 0

        async def send(method, params=None, session_id=None):
            nonlocal mid
            mid += 1
            msg = {"id": mid, "method": method, "params": params or {}}
            if session_id:
                msg["sessionId"] = session_id
            await ws.send(json.dumps(msg))
            while True:
                raw = json.loads(await ws.recv())
                if raw.get("id") == mid:
                    return raw

        r = await send("Target.attachToTarget", {"targetId": TARGET, "flatten": True})
        sid = r["result"]["sessionId"]

        async def ev(expr):
            r = await send("Runtime.evaluate",
                           {"expression": expr, "returnByValue": True, "awaitPromise": True}, sid)
            res = r["result"].get("result", {})
            if res.get("subtype") == "error":
                return {"JS_ERROR": res.get("description", "")[:400]}
            return res.get("value")

        async def spin_insert(field_id, text):
            """Pattern B: real CDP keystrokes into a role=spinbutton date field.
            Pattern A (native setter) is IGNORED by these widgets."""
            foc = await ev(f"""(() => {{
              const el = document.getElementById('{field_id}');
              if (!el) return 'MISSING';
              el.scrollIntoView({{block:'center'}});
              el.focus();
              return document.activeElement === el ? 'focused' : 'FOCUS_FAIL';
            }})()""")
            if foc != "focused":
                return f"focus:{foc}"
            await send("Input.insertText", {"text": text}, sid)
            await asyncio.sleep(0.25)
            return await ev(f"""(() => {{
              const el = document.getElementById('{field_id}');
              el.dispatchEvent(new Event('input', {{bubbles:true}}));
              el.dispatchEvent(new Event('change', {{bubbles:true}}));
              el.blur();
              return el.value;
            }})()""")

        for i, e in enumerate(ENTRIES, start=1):
            clicked = await ev(FIND_WE_ADD)
            if clicked != "clicked":
                print(f"ENTRY {i} ({e['companyName']}): ADD BUTTON FAILED: {clicked}")
                sys.exit(1)
            await asyncio.sleep(1.8)

            p = await ev(FIND_EMPTY_PREFIX)
            if not p:
                print(f"ENTRY {i} ({e['companyName']}): NO EMPTY BLOCK FOUND")
                sys.exit(1)
            B = f"workExperience-{p}--"

            # Pattern A: text fields
            res = await ev(f"""(() => {{
              const set = {SET_TEXT};
              const byId = id => document.getElementById(id);
              const B = '{B}';
              set(byId(B+'jobTitle'), {json.dumps(e['jobTitle'])});
              set(byId(B+'companyName'), {json.dumps(e['companyName'])});
              set(byId(B+'location'), {json.dumps(e['location'])});
              set(byId(B+'roleDescription'), {json.dumps(e['description'])});
              return {{
                jt: byId(B+'jobTitle').value.slice(0,40),
                co: byId(B+'companyName').value,
                dl: byId(B+'roleDescription').value.length
              }};
            }})()""")

            sm = await spin_insert(B + "startDate-dateSectionMonth-input", e["sm"])
            sy = await spin_insert(B + "startDate-dateSectionYear-input", e["sy"])
            em = ey = None
            if e.get("em"):
                em = await spin_insert(B + "endDate-dateSectionMonth-input", e["em"])
                ey = await spin_insert(B + "endDate-dateSectionYear-input", e["ey"])
            if e.get("current"):
                cur = await ev(f"""(() => {{
                  const cb = document.getElementById('{B}currentlyWorkHere');
                  if (cb && !cb.checked) cb.click();
                  return cb ? cb.checked : 'MISSING';
                }})()""")
                await asyncio.sleep(0.5)
            else:
                cur = False

            print(f"ENTRY {i} block={p} | {res.get('co')} | {res.get('jt')} | "
                  f"start={sm}/{sy} end={em}/{ey} | cur={cur} | desc={res.get('dl')}")
            await asyncio.sleep(0.5)

        # FINAL verification pass — every block + validation alerts
        final = await ev("""(() => {
          const ids = Array.from(document.querySelectorAll('input[id^="workExperience-"]'))
            .map(e => e.id.match(/workExperience-(\\d+)--/)[1]);
          const uniq = Array.from(new Set(ids));
          const blocks = uniq.map(p => {
            const g = s => { const el = document.getElementById('workExperience-'+p+'--'+s); return el ? el.value : null; };
            const grpTxt = id => {
              const el = document.getElementById('workExperience-'+p+'--'+id);
              if (!el) return '';
              const g2 = el.closest('[role="group"]');
              return g2 ? (g2.innerText||'').replace(/\\n/g,' ').trim().slice(0,20) : '';
            };
            const cb = document.getElementById('workExperience-'+p+'--currentlyWorkHere');
            return {
              p, title: g('jobTitle'), company: g('companyName'),
              start: grpTxt('startDate-dateSectionMonth-input'),
              end: grpTxt('endDate-dateSectionMonth-input'),
              current: cb ? cb.checked : null,
              descLen: (g('roleDescription')||'').length
            };
          });
          const alerts = Array.from(document.querySelectorAll('[role="alert"]'))
            .map(e => (e.innerText||'').trim()).filter(t => t && !/successfully/i.test(t));
          return {count: blocks.length, blocks, validationErrors: alerts.slice(0,10)};
        })()""")
        print()
        print("=== FINAL STATE ===")
        print(f"total blocks: {final['count']}")
        for b in final["blocks"]:
            print(f"  [{b['p']}] {str(b['company'])[:28]:<28} | {str(b['title'])[:38]:<38} | "
                  f"{b['start']} -> {b['end'] or 'present'} | cur={b['current']} | desc={b['descLen']}")
        print("validation errors:", final["validationErrors"] or "NONE")
        print()
        print("DONE. Do NOT click Save and Continue or Submit from here —")
        print("hand back to the user (final submit requires the relay disconnected).")


if __name__ == "__main__":
    asyncio.run(main())
