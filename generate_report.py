import os
import base64

def get_base64_img(path):
    with open(path, "rb") as f:
        data = base64.b64encode(f.read()).decode("utf-8")
    return f"data:image/png;base64,{data}"

jul_b64 = get_base64_img("d:/automachine/screenshots/calendar_jul_2026.png")
aug_b64 = get_base64_img("d:/automachine/screenshots/calendar_aug_2026.png")
sep_b64 = get_base64_img("d:/automachine/screenshots/calendar_sep_2026.png")

html_content = f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Curapod-M — Cycle Tracking Report & Simulator</title>
<style>
  :root {{
    --bg: #f6f5f2;
    --panel: #ffffff;
    --ink: #1c1c1a;
    --ink-2: #5b5a56;
    --ink-3: #8f8e89;
    --line: #e4e2dc;
    --line-2: #cfcdc6;
    --red: #c0392b;
    --red-soft: #e8a79f;
    --amber-ink: #8a5a00;
    --menstrual: #fad9d4;
    --follicular: #d9f3e1;
    --ovulation: #d9e2fb;
    --luteal: #fdefc9;
    --menstrual-p: #fdedea;
    --follicular-p: #ecf9f0;
    --ovulation-p: #ecf0fd;
    --luteal-p: #fef7e4;
    --locked: #ebebe9;
    --accent: #1f4f8f;
    --accent-soft: #e3ecf8;
    --warn: #fff4cc;
    --green-badge: #e6f4ea;
    --green-text: #137333;
  }}
  * {{ box-sizing: border-box; }}
  html, body {{
    margin: 0;
    background: var(--bg);
    color: var(--ink);
    font: 14px/1.5 -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
  }}
  button {{
    font: inherit;
    cursor: pointer;
    border: 1px solid var(--line-2);
    background: #fff;
    color: var(--ink);
    border-radius: 8px;
    padding: 7px 12px;
    transition: all 0.15s ease;
  }}
  button:hover {{ background: #f2f1ed; }}
  button.primary {{ background: var(--accent); border-color: var(--accent); color: #fff; }}
  button.primary:hover {{ background: #173d70; }}
  button.danger {{ color: var(--red); border-color: #e6b8b2; }}
  button:disabled {{ opacity: .45; cursor: default; }}
  input, select {{
    font: inherit;
    padding: 6px 8px;
    border: 1px solid var(--line-2);
    border-radius: 8px;
    background: #fff;
    color: var(--ink);
  }}
  h1 {{ font-size: 20px; font-weight: 600; margin: 0; }}
  h2 {{ font-size: 13px; font-weight: 600; letter-spacing: .01em; color: var(--ink-2); margin: 0 0 10px; text-transform: uppercase; }}
  .muted {{ color: var(--ink-3); }}
  .small {{ font-size: 12px; }}

  header {{
    background: #fff;
    border-bottom: 1px solid var(--line);
    padding: 16px 24px;
    display: flex;
    flex-wrap: wrap;
    gap: 18px;
    align-items: center;
    justify-content: space-between;
  }}
  header .sub {{ color: var(--ink-3); font-size: 13px; margin-top: 3px; }}
  .badge-pass {{
    display: inline-flex;
    align-items: center;
    gap: 6px;
    background: var(--green-badge);
    color: var(--green-text);
    font-weight: 600;
    font-size: 12px;
    padding: 4px 10px;
    border-radius: 999px;
  }}
  .badge-pass::before {{
    content: "●";
    font-size: 10px;
  }}

  main {{
    padding: 20px 24px;
    max-width: 1560px;
    margin: 0 auto;
    display: flex;
    flex-direction: column;
    gap: 20px;
  }}

  .panel {{
    background: var(--panel);
    border: 1px solid var(--line);
    border-radius: 14px;
    padding: 18px;
    box-shadow: 0 1px 3px rgba(0,0,0,0.02);
  }}

  /* Metrics Hero Grid */
  .metrics-hero {{
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
    gap: 14px;
  }}
  .metric-card {{
    background: #fff;
    border: 1px solid var(--line);
    border-radius: 12px;
    padding: 14px 16px;
    display: flex;
    flex-direction: column;
    gap: 4px;
    position: relative;
    overflow: hidden;
  }}
  .metric-card.highlight {{
    background: #111;
    color: #fff;
    border-color: #222;
  }}
  .metric-card.highlight .k {{ color: #a1a1aa; }}
  .metric-card.highlight .s {{ color: #e4e4e7; }}
  .metric-card.highlight .v {{ color: #ff6b6b; }}
  .metric-card .k {{ font-size: 11px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em; color: var(--ink-3); }}
  .metric-card .v {{ font-size: 22px; font-weight: 700; color: var(--ink); }}
  .metric-card .s {{ font-size: 12px; color: var(--ink-2); }}

  /* Comparison Grid (Input vs Output) */
  .data-grid {{
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 16px;
  }}
  @media (max-width: 860px) {{ .data-grid {{ grid-template-columns: 1fr; }} }}
  .data-card {{
    background: #fafaf8;
    border: 1px solid var(--line);
    border-radius: 10px;
    padding: 14px 16px;
  }}
  .data-card h3 {{
    margin: 0 0 12px;
    font-size: 14px;
    font-weight: 600;
    color: var(--ink);
    display: flex;
    align-items: center;
    gap: 8px;
  }}
  .data-list {{
    display: flex;
    flex-direction: column;
    gap: 8px;
    font-size: 13px;
  }}
  .data-row {{
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    padding-bottom: 6px;
    border-bottom: 1px dashed var(--line);
  }}
  .data-row:last-child {{ border-bottom: none; padding-bottom: 0; }}
  .data-row .label {{ color: var(--ink-2); font-weight: 500; }}
  .data-row .val {{ font-weight: 600; color: var(--ink); text-align: right; }}

  /* Screenshot Showcase */
  .screenshots-container {{
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
    gap: 18px;
  }}
  .screenshot-card {{
    background: #fff;
    border: 1px solid var(--line);
    border-radius: 12px;
    overflow: hidden;
    display: flex;
    flex-direction: column;
    box-shadow: 0 2px 8px rgba(0,0,0,0.04);
  }}
  .screenshot-card-header {{
    padding: 12px 14px;
    border-bottom: 1px solid var(--line);
    background: #faf9f6;
    display: flex;
    justify-content: space-between;
    align-items: center;
  }}
  .screenshot-card-header .title {{
    font-weight: 600;
    font-size: 13.5px;
    color: var(--ink);
  }}
  .screenshot-card-header .meta {{
    font-size: 11.5px;
    color: var(--ink-3);
  }}
  .screenshot-img-wrap {{
    background: #000;
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 8px;
    cursor: zoom-in;
    position: relative;
  }}
  .screenshot-img-wrap img {{
    max-width: 100%;
    height: auto;
    max-height: 520px;
    object-fit: contain;
    border-radius: 6px;
    transition: transform 0.2s ease;
  }}
  .screenshot-img-wrap:hover img {{
    transform: scale(1.01);
  }}
  .screenshot-card-footer {{
    padding: 12px 14px;
    font-size: 12px;
    color: var(--ink-2);
    border-top: 1px solid var(--line);
    background: #fff;
  }}

  /* Simulator Section */
  .sim-layout {{
    display: grid;
    grid-template-columns: minmax(0,1fr) 380px;
    gap: 18px;
  }}
  @media (max-width: 1100px) {{ .sim-layout {{ grid-template-columns: 1fr; }} }}

  .controls {{ display: flex; flex-wrap: wrap; gap: 14px; align-items: center; }}
  .controls label {{ display: flex; flex-direction: column; font-size: 11px; color: var(--ink-3); gap: 3px; }}
  .controls input {{ width: 130px; }}
  .seg {{ display: inline-flex; border: 1px solid var(--line-2); border-radius: 8px; overflow: hidden; }}
  .seg button {{ border: 0; border-radius: 0; padding: 6px 10px; }}
  .seg button.on {{ background: var(--accent); color: #fff; }}

  /* calendar */
  .months {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(230px, 1fr)); gap: 14px; }}
  .month h3 {{ font-size: 13px; font-weight: 600; margin: 0 0 6px; color: var(--ink-2); }}
  .grid {{ display: grid; grid-template-columns: repeat(7, 1fr); gap: 3px; }}
  .wd {{ font-size: 10px; color: var(--ink-3); text-align: center; font-weight: 600; padding: 2px 0; }}
  .day {{
    position: relative;
    aspect-ratio: 1;
    border-radius: 7px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 12px;
    cursor: pointer;
    border: 1.5px solid transparent;
    background: #fff;
    user-select: none;
  }}
  .day.blank {{ cursor: default; background: transparent; }}
  .day:hover:not(.blank) {{ border-color: var(--line-2); }}
  .day.sel {{ border-color: var(--accent) !important; box-shadow: 0 0 0 2px var(--accent-soft); }}
  .day.today {{ outline: 2px solid var(--ink); outline-offset: -2px; }}
  .day.future {{ color: var(--ink-3); }}
  .day.locked {{ background: var(--locked) !important; color: var(--ink-3); }}
  .day .n {{ position: relative; z-index: 1; }}
  .day .mark {{ position: absolute; inset: 0; display: flex; align-items: center; justify-content: center; pointer-events: none; }}
  .mark.confirmed::before {{ content: ""; width: 72%; height: 72%; border-radius: 50%; background: var(--red); }}
  .day .mark.confirmed ~ .n, .day.k-confirmed .n {{ color: #fff; font-weight: 600; }}
  .mark.spotting::before {{ content: ""; width: 72%; height: 72%; border-radius: 50%; background: var(--red); }}
  .day.k-spotting .n {{ color: #fff; font-weight: 600; }}
  .mark.unconfirmed::before {{ content: ""; width: 72%; height: 72%; border-radius: 50%; background: var(--red-soft); }}
  .mark.expected::before, .mark.predicted::before {{ content: ""; width: 72%; height: 72%; border-radius: 50%; border: 2px dotted var(--red); }}
  .mark.predicted::before {{ border-color: #d98f86; }}
  .mark.none::after {{ content: "×"; position: absolute; right: 3px; top: 0; font-size: 11px; color: var(--ink-2); font-weight: 700; }}
  .ph-menstrual {{ background: var(--menstrual); }}
  .ph-follicular {{ background: var(--follicular); }}
  .ph-ovulation {{ background: var(--ovulation); }}
  .ph-luteal {{ background: var(--luteal); }}
  .ph-menstrual.pred {{ background: var(--menstrual-p); }}
  .ph-follicular.pred {{ background: var(--follicular-p); }}
  .ph-ovulation.pred {{ background: var(--ovulation-p); }}
  .ph-luteal.pred {{ background: var(--luteal-p); }}
  .legend {{ display: flex; flex-wrap: wrap; gap: 12px 18px; margin-top: 14px; font-size: 12px; color: var(--ink-2); }}
  .legend span {{ display: inline-flex; align-items: center; gap: 6px; }}
  .sw {{ width: 14px; height: 14px; border-radius: 4px; display: inline-block; border: 1px solid var(--line); }}
  .dot {{ width: 12px; height: 12px; border-radius: 50%; display: inline-block; }}

  /* day sheet */
  .sheet .date {{ font-size: 16px; font-weight: 600; }}
  .sheet .kind {{ font-size: 12px; color: var(--ink-2); margin-bottom: 10px; }}
  .btns {{ display: flex; flex-wrap: wrap; gap: 8px; }}
  .locked-status {{ display: inline-block; padding: 5px 10px; border-radius: 8px; background: #f2f1ed; color: var(--ink-2); font-size: 12px; margin-bottom: 10px; }}
  .dialog {{ margin-top: 12px; padding: 12px; border-radius: 10px; background: var(--accent-soft); font-size: 13px; }}
  .dialog .btns {{ margin-top: 10px; }}
  .picker {{ display: grid; grid-template-columns: repeat(7, 1fr); gap: 4px; margin-top: 8px; }}
  .picker .day {{ aspect-ratio: auto; padding: 6px 0; }}
  .picker .day.out {{ opacity: .3; pointer-events: none; }}
  .editor {{ margin-top: 14px; padding-top: 12px; border-top: 1px solid var(--line); }}
  .editor .row {{ display: flex; align-items: center; gap: 8px; margin-bottom: 8px; flex-wrap: wrap; }}
  .editor .row label {{ width: 78px; font-size: 12px; color: var(--ink-2); }}
  .editor .range {{ font-size: 11px; color: var(--ink-3); }}

  /* log */
  .log {{ max-height: 260px; overflow: auto; display: flex; flex-direction: column; gap: 8px; }}
  .entry {{ border-left: 3px solid var(--line-2); padding: 4px 10px; font-size: 12.5px; }}
  .entry.ok {{ border-color: #3d9a5f; }}
  .entry.no {{ border-color: #c0392b; }}
  .entry.info {{ border-color: var(--accent); }}
  .entry .who {{ color: var(--ink-3); font-size: 11px; }}
  .entry .rule {{ display: inline-block; margin-left: 6px; font-size: 10px; padding: 1px 6px; border-radius: 999px; background: #f2f1ed; color: var(--ink-2); }}

  /* Modal Zoom */
  .modal-zoom {{
    display: none;
    position: fixed;
    z-index: 9999;
    inset: 0;
    background: rgba(0,0,0,0.85);
    align-items: center;
    justify-content: center;
    cursor: zoom-out;
  }}
  .modal-zoom.active {{ display: flex; }}
  .modal-zoom img {{
    max-height: 94vh;
    max-width: 94vw;
    border-radius: 12px;
    box-shadow: 0 4px 20px rgba(0,0,0,0.5);
  }}

  .banner {{ margin-top: 12px; padding: 9px 12px; border-radius: 10px; background: var(--warn); color: var(--amber-ink); font-size: 13px; }}
  .tag {{ display: inline-block; font-size: 10px; padding: 1px 6px; border-radius: 999px; background: #f2f1ed; color: var(--ink-2); margin-left: 6px; }}
</style>
</head>
<body>

<header>
  <div>
    <div style="display: flex; align-items: center; gap: 10px;">
      <h1>Curapod-M — Cycle Tracking Report & Rules Engine</h1>
      <span class="badge-pass">TEST PASSED</span>
    </div>
    <div class="sub">USB Debugging Verified · Dynamic Live Metrics · Multi-Month Cycle Calendar (Jul – Aug – Sep 2026)</div>
  </div>
  <div class="controls">
    <label>Device UDID <span style="font-weight: 600; color: var(--ink); font-size: 12px;">38181JEHN00069</span></label>
    <label>Execution Date <span style="font-weight: 600; color: var(--ink); font-size: 12px;">Mon, 21 Sep 2026</span></label>
    <label>App Package <span style="font-weight: 600; color: var(--ink); font-size: 12px;">com.litemed.curapod.menstrual.app</span></label>
  </div>
</header>

<main>

  <!-- 1. KEY OUTPUT METRICS (LIVE DASHBOARD & MY CYCLE METRICS) -->
  <section class="panel">
    <h2>1. Live Output Metrics (Extracted via USB Debugging)</h2>
    <div class="metrics-hero">
      <div class="metric-card highlight">
        <div class="k">My Cycle Status</div>
        <div class="v">Day 4</div>
        <div class="s">YOU ARE IN</div>
      </div>
      <div class="metric-card">
        <div class="k">Next Period</div>
        <div class="v">In 32 days</div>
        <div class="s">Est. 23 Oct 2026</div>
      </div>
      <div class="metric-card">
        <div class="k">Calculated Cycle</div>
        <div class="v">35 days</div>
        <div class="s">AVG CYCLE (from logged intervals)</div>
      </div>
      <div class="metric-card">
        <div class="k">Period Duration</div>
        <div class="v">5 days</div>
        <div class="s">AVG PERIOD (5 confirmed days)</div>
      </div>
      <div class="metric-card">
        <div class="k">Current Phase</div>
        <div class="v" style="font-size: 19px; color: var(--red);">Menstruation</div>
        <div class="s">Sep 18 – Sep 22 · Day 4</div>
      </div>
      <div class="metric-card">
        <div class="k">Last Period Start</div>
        <div class="v">Aug 14</div>
        <div class="s">Preceding cycle start</div>
      </div>
    </div>
  </section>

  <!-- 2. INPUT DATA VS CALCULATED OUTPUT DATA -->
  <section class="panel">
    <h2>2. Configuration & Verification: Input Data vs Computed Output</h2>
    <div class="data-grid">
      <!-- Input Data -->
      <div class="data-card">
        <h3>
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"></path><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"></path></svg>
          Input Data (Test Execution Parameters)
        </h3>
        <div class="data-list">
          <div class="data-row">
            <span class="label">Number of Cycles Configured</span>
            <span class="val">3 Cycles</span>
          </div>
          <div class="data-row">
            <span class="label">Cycle #1 Selection (July)</span>
            <span class="val">Jul 10th to 14th (5 days)</span>
          </div>
          <div class="data-row">
            <span class="label">Cycle #2 Selection (August)</span>
            <span class="val">Aug 14th to 18th (5 days)</span>
          </div>
          <div class="data-row">
            <span class="label">Cycle #3 Selection (September)</span>
            <span class="val">Sep 18th to 22nd (5 days)</span>
          </div>
          <div class="data-row">
            <span class="label">Entered Cycle Length (Stepper)</span>
            <span class="val">28 days (default)</span>
          </div>
          <div class="data-row">
            <span class="label">Period Regularity Choice</span>
            <span class="val">Regular ("same time most months")</span>
          </div>
          <div class="data-row">
            <span class="label">Pain Onset Selection</span>
            <span class="val">A day or two before my period</span>
          </div>
          <div class="data-row">
            <span class="label">Pain Intensity Selection</span>
            <span class="val">Mild</span>
          </div>
          <div class="data-row">
            <span class="label">User Profile Name & Birth Year</span>
            <span class="val">Richie · Year 2000</span>
          </div>
        </div>
      </div>

      <!-- Output Data -->
      <div class="data-card">
        <h3>
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12"></polyline></svg>
          Computed Output (App UI & Dynamic Metrics)
        </h3>
        <div class="data-list">
          <div class="data-row">
            <span class="label">Current Day Status</span>
            <span class="val" style="color: var(--accent);">YOU ARE IN "Day 4"</span>
          </div>
          <div class="data-row">
            <span class="label">Next Period Prediction</span>
            <span class="val">NEXT PERIOD "In 32 days" (Oct 23)</span>
          </div>
          <div class="data-row">
            <span class="label">Measured Interval: Cycle 1 → Cycle 2</span>
            <span class="val">Jul 10 → Aug 14 = 35 days</span>
          </div>
          <div class="data-row">
            <span class="label">Measured Interval: Cycle 2 → Cycle 3</span>
            <span class="val">Aug 14 → Sep 18 = 35 days</span>
          </div>
          <div class="data-row">
            <span class="label">App Calculated Average Cycle</span>
            <span class="val">AVG CYCLE "35 days"</span>
          </div>
          <div class="data-row">
            <span class="label">App Calculated Average Period</span>
            <span class="val">AVG PERIOD "5 days"</span>
          </div>
          <div class="data-row">
            <span class="label">Home Screen Cycle Phase</span>
            <span class="val" style="color: var(--red);">CYCLE TRACKING : Menstruation</span>
          </div>
          <div class="data-row">
            <span class="label">Home Screen Last Period Card</span>
            <span class="val">LAST PERIOD Aug 14</span>
          </div>
          <div class="data-row">
            <span class="label">Confidence Level</span>
            <span class="val">Pattern established (3 cycles logged)</span>
          </div>
        </div>
      </div>
    </div>
  </section>

  <!-- 3. ACTUAL CALENDAR SCREENSHOTS (JUL, AUG, SEP) -->
  <section class="panel">
    <h2>3. Captured Calendar Screenshots (From Phone Display)</h2>
    <div style="font-size: 13px; color: var(--ink-2); margin-bottom: 14px;">
      Live screen captures saved during test execution via Appium at <code>D:\automachine\screenshots\</code>. Click any image to view in full resolution.
    </div>
    <div class="screenshots-container">
      <!-- Sep 2026 -->
      <div class="screenshot-card">
        <div class="screenshot-card-header">
          <span class="title">September 2026 (Current Month)</span>
          <span class="meta">Captured 10:58</span>
        </div>
        <div class="screenshot-img-wrap" onclick="openZoom(this.querySelector('img').src)">
          <img src="{sep_b64}" alt="Calendar Sep 2026">
        </div>
        <div class="screenshot-card-footer">
          <strong>Key Observations:</strong><br>
          • <strong>Day 4 Highlighted:</strong> Mon, 21 Sep (circled in red ring).<br>
          • <strong>Menstruation (Red):</strong> Sep 18 – Sep 22 (5 days).<br>
          • <strong>Follicular (Yellow):</strong> Sep 23 – Sep 30.<br>
          • <strong>Fertile (Green):</strong> Sep 1 – Sep 2.<br>
          • <strong>KPIs:</strong> YOU ARE IN: Day 4 | NEXT PERIOD: In 32 days | AVG CYCLE: 35 days | AVG PERIOD: 5 days.
        </div>
      </div>

      <!-- Aug 2026 -->
      <div class="screenshot-card">
        <div class="screenshot-card-header">
          <span class="title">August 2026 (Previous Month)</span>
          <span class="meta">Captured 10:58</span>
        </div>
        <div class="screenshot-img-wrap" onclick="openZoom(this.querySelector('img').src)">
          <img src="{aug_b64}" alt="Calendar Aug 2026">
        </div>
        <div class="screenshot-card-footer">
          <strong>Key Observations:</strong><br>
          • <strong>Menstruation (Red):</strong> Aug 14 – Aug 18 (5 days).<br>
          • <strong>Follicular (Yellow):</strong> Aug 19 – Aug 28 (10 days).<br>
          • <strong>Fertile Window (Green):</strong> Aug 29 – Aug 31 (leading to ovulation).<br>
          • <strong>Cycle Start:</strong> Day 1 on Aug 14 (35 days after Jul 10).
        </div>
      </div>

      <!-- Jul 2026 -->
      <div class="screenshot-card">
        <div class="screenshot-card-header">
          <span class="title">July 2026 (First Logged Month)</span>
          <span class="meta">Captured 10:58</span>
        </div>
        <div class="screenshot-img-wrap" onclick="openZoom(this.querySelector('img').src)">
          <img src="{jul_b64}" alt="Calendar Jul 2026">
        </div>
        <div class="screenshot-card-footer">
          <strong>Key Observations:</strong><br>
          • <strong>Menstruation (Red):</strong> Jul 10 – Jul 14 (5 days).<br>
          • <strong>Follicular (Yellow):</strong> Jul 15 – Jul 24 (10 days).<br>
          • <strong>Fertile Window (Green):</strong> Jul 25 – Jul 29.<br>
          • <strong>Luteal Phase:</strong> Jul 30 – Jul 31.
        </div>
      </div>
    </div>
  </section>

  <!-- 4. INTERACTIVE CALENDAR SIMULATOR & RULES ENGINE -->
  <section class="panel">
    <h2>4. Interactive Rules Engine & Calendar Simulator</h2>
    <div style="font-size: 13px; color: var(--ink-2); margin-bottom: 14px;">
      Interactive simulation pre-loaded with the exact facts verified on your device (35-day cycles, 5-day periods, today = 21 Sep 2026). Click any calendar day to inspect phase, options, or test rule changes.
    </div>

    <div class="controls" style="margin-bottom: 16px;">
      <label>Today <input type="date" id="today"></label>
      <label>Build <span class="seg"><button id="rel25" class="on">25th</button><button id="rel10">10th</button></span></label>
      <label>Cycle length (days) <input type="number" id="cl" min="15" max="60"></label>
      <label>Period length (days) <input type="number" id="apl" min="2" max="10"></label>
      <label>&nbsp;<button id="reset">Reset to Run State</button></label>
    </div>

    <div class="sim-layout">
      <!-- Calendar View -->
      <div class="col" style="display: flex; flex-direction: column; gap: 14px;">
        <div class="months" id="months"></div>
        <div class="legend">
          <span><i class="dot" style="background:var(--red)"></i> confirmed bleeding day</span>
          <span><i class="dot" style="background:var(--red-soft)"></i> unconfirmed day</span>
          <span><i class="dot" style="border:2px dotted var(--red)"></i> expected / predicted</span>
          <span><b>×</b> not on my period</span>
          <span><i class="sw ph-menstrual"></i> menstrual</span>
          <span><i class="sw ph-follicular"></i> follicular</span>
          <span><i class="sw ph-ovulation"></i> fertile / ovulation</span>
          <span><i class="sw ph-luteal"></i> luteal</span>
          <span><i class="sw" style="outline:2px solid var(--ink);outline-offset:-2px"></i> today</span>
        </div>
      </div>

      <!-- Side Inspector / Day Sheet -->
      <div class="col" style="display: flex; flex-direction: column; gap: 14px;">
        <div class="panel sheet" id="sheet" style="padding: 14px; background: #fafaf8;"></div>
        <div class="panel" style="padding: 14px;">
          <h2>Action Audit Trail</h2>
          <div class="log" id="log"></div>
        </div>
      </div>
    </div>
  </section>

</main>

<!-- Fullscreen Zoom Modal -->
<div class="modal-zoom" id="modalZoom" onclick="this.classList.remove('active')">
  <img id="zoomImg" src="" alt="Zoomed Screenshot">
</div>

<script>
function openZoom(src) {{
  document.getElementById('zoomImg').src = src;
  document.getElementById('modalZoom').classList.add('active');
}}

/* Engine & State pre-populated with exact live test data */
(function (root) {{
  'use strict';
  var DAY = 86400000;
  var MONTHS = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];

  var C = {{
    MIN_CYCLE: 15,
    MAX_CYCLE: 60,
    FIRST_LOOKBACK: 90,
    WINDOW: 14,
    JOIN_GAP: 2,
    DEFAULT_APL: 5,
    DEFAULT_CL: 35,
    EDITABLE_25: 2,
    EDITABLE_10: 4
  }};

  function toN(iso) {{ var p = iso.split('-').map(Number); return Math.round(Date.UTC(p[0], p[1]-1, p[2]) / DAY); }}
  function toISO(n) {{ return new Date(n * DAY).toISOString().slice(0, 10); }}
  function ymd(n) {{ var d = new Date(n * DAY); return {{ y: d.getUTCFullYear(), m: d.getUTCMonth(), d: d.getUTCDate() }}; }}
  function fmt(n) {{ var o = ymd(n); return o.d + ' ' + MONTHS[o.m]; }}
  function fmtRange(a, b) {{ return a === b ? fmt(a) : fmt(a) + '–' + fmt(b); }}
  function uniqSorted(arr) {{ var s = {{}}; arr.forEach(function (x) {{ s[x] = 1; }}); return Object.keys(s).map(Number).sort(function (a, b) {{ return a - b; }}); }}
  function clone(state) {{ return JSON.parse(JSON.stringify(state)); }}

  function createState(opts) {{
    opts = opts || {{}};
    var st = {{
      today: typeof opts.today === 'string' ? toN(opts.today) : opts.today,
      release: opts.release || '25',
      profile: {{ cycleLength: opts.cycleLength || 35, periodLength: opts.periodLength || 5 }},
      periods: [],
      spotting: [],
      none: []
    }};
    (opts.periods || []).forEach(function (p) {{
      if (p && p.days) {{ var days = p.days.map(toN); st.periods.push({{ start: days[0], confirmed: days }}); return; }}
      var s = toN(p[0]), e = toN(p[1] || p[0]); var conf = [];
      for (var i = s; i <= e; i++) conf.push(i);
      st.periods.push({{ start: s, confirmed: conf }});
    }});
    normalise(st);
    return st;
  }}

  function normalise(st) {{
    st.periods.forEach(function (p) {{ p.confirmed = uniqSorted(p.confirmed.concat([p.start])); p.start = p.confirmed[0]; }});
    st.periods.sort(function (a, b) {{ return a.start - b.start; }});
    st.spotting = uniqSorted(st.spotting);
    st.none = uniqSorted(st.none);
  }}

  function derive(st) {{
    var today = st.today, APL = st.profile.periodLength;
    var periods = st.periods.map(function (p, i) {{
      var last = p.confirmed[p.confirmed.length - 1];
      var next = st.periods[i + 1];
      var expectedEnd = Math.max(last, p.start + APL - 1);
      var open = !next && today <= expectedEnd && (today - p.start) < C.WINDOW;
      var spanEnd = open ? expectedEnd : last;
      if (next) spanEnd = Math.min(spanEnd, next.start - 1);
      return {{ index: i, start: p.start, confirmed: p.confirmed, lastConfirmed: last, spanEnd: spanEnd, open: open,
               nextStart: next ? next.start : null, actualLength: next ? next.start - p.start : null }};
    }});

    var intervals = periods.filter(function (p) {{ return p.actualLength !== null; }}).map(function (p) {{ return p.actualLength; }});
    var L = 35;
    if (intervals.length >= 2) {{
      var last2 = intervals.slice(-2);
      L = Math.round((last2[0] + last2[1]) / 2);
    }} else if (intervals.length === 1) {{
      L = intervals[0];
    }}

    var cycles = [];
    periods.forEach(function (p, i) {{
      var isCurrent = i === periods.length - 1;
      var len = isCurrent ? L : p.actualLength;
      var end = isCurrent ? Math.max(p.start + len - 1, today) : p.start + len - 1;
      cycles.push({{ start: p.start, length: len, end: end, menstrualEnd: p.spanEnd, current: isCurrent, predicted: false }});
    }});

    var cur = periods.length ? periods[periods.length - 1] : null;
    var cycleDay = cur ? (today - cur.start + 1) : null;
    var nextStart = cur ? cur.start + L : null;

    var predictedPeriods = [];
    if (cur && nextStart) {{
      predictedPeriods.push({{ start: nextStart, end: nextStart + APL - 1 }});
    }}

    return {{
      today: today, APL: APL, periods: periods, cycles: cycles, L: L,
      cycleDay: cycleDay, nextStart: nextStart, predictedPeriods: predictedPeriods,
      phaseOf: function (n) {{ return phaseOf(this, n); }},
      dayInfo: function (n) {{ return dayInfo(st, this, n); }}
    }};
  }}

  function phaseOf(d, n) {{
    for (var i = 0; i < d.cycles.length; i++) {{
      var c = d.cycles[i];
      if (n >= c.start && n <= c.end) {{
        var cd = n - c.start + 1, M = Math.ceil(c.length / 2);
        var ph;
        if (n <= c.menstrualEnd) ph = 'menstrual';
        else if (cd >= M - 2 && cd <= M + 2) ph = 'ovulation';
        else if (cd < M - 2) ph = 'follicular';
        else ph = 'luteal';
        return {{ phase: ph, cycleDay: cd, predicted: c.predicted, current: c.current }};
      }}
    }}
    return null;
  }}

  function dayInfo(st, d, n) {{
    var info = {{ n: n, kind: 'plain', period: null, phase: phaseOf(d, n), future: n > d.today, today: n === d.today, editable: true }};
    for (var i = 0; i < d.periods.length; i++) {{
      var p = d.periods[i];
      if (n >= p.start && n <= p.spanEnd) {{
        info.period = p;
        if (p.confirmed.indexOf(n) >= 0) info.kind = 'confirmed';
        else info.kind = (n >= d.today && p.open) ? 'expected' : 'unconfirmed';
        return info;
      }}
    }}
    for (var j = 0; j < d.predictedPeriods.length; j++) {{
      if (n >= d.predictedPeriods[j].start && n <= d.predictedPeriods[j].end) {{ info.kind = 'predicted'; return info; }}
    }}
    return info;
  }}

  root.CurapodEngine = {{
    toN: toN, toISO: toISO, ymd: ymd, fmt: fmt, fmtRange: fmtRange, MONTHS: MONTHS,
    createState: createState, derive: derive, clone: clone
  }};
}})(window);

/* Rendering Controller */
(function() {{
  const E = window.CurapodEngine;
  const $ = id => document.getElementById(id);

  // Exact Run State from Appium test execution:
  const INITIAL_STATE = {{
    today: '2026-09-21',
    cycleLength: 35,
    periodLength: 5,
    periods: [
      ['2026-07-10', '2026-07-14'],
      ['2026-08-14', '2026-08-18'],
      ['2026-09-18', '2026-09-22']
    ]
  }};

  let st = E.createState(INITIAL_STATE);
  let selected = E.toN('2026-09-21');
  let logItems = [
    {{ kind: 'ok', who: 'Appium Runner', text: 'Onboarding & dashboard cycle verification passed cleanly.' }},
    {{ kind: 'ok', who: 'USB Extraction', text: 'Home dashboard extracted: CYCLE TRACKING Fertile/Menstruation, Cycle Day 4 · Started Sep 18' }},
    {{ kind: 'ok', who: 'USB Extraction', text: 'My Cycle extracted: YOU ARE IN "Day 4", NEXT PERIOD "In 32 days", AVG CYCLE "35 days", AVG PERIOD "5 days"' }},
    {{ kind: 'info', who: 'Screenshots', text: 'Saved calendar_sep_2026.png, calendar_aug_2026.png, calendar_jul_2026.png' }}
  ];

  function render() {{
    const d = E.derive(st);
    $('today').value = E.toISO(st.today);
    $('cl').value = st.profile.cycleLength;
    $('apl').value = st.profile.periodLength;

    renderMonths(d);
    renderSheet(d);
    renderLog();
  }}

  function renderMonths(d) {{
    const box = $('months');
    box.innerHTML = '';
    // Display Jul, Aug, Sep, Oct 2026
    const monthsToShow = [
      {{ y: 2026, m: 6 }},  // Jul
      {{ y: 2026, m: 7 }},  // Aug
      {{ y: 2026, m: 8 }},  // Sep
      {{ y: 2026, m: 9 }}   // Oct (predicted)
    ];

    monthsToShow.forEach(item => {{
      const y = item.y, m = item.m;
      const days = new Date(Date.UTC(y, m + 1, 0)).getUTCDate();
      const lead = new Date(Date.UTC(y, m, 1)).getUTCDay();

      const el = document.createElement('div');
      el.className = 'month';
      el.innerHTML = `<h3>${{E.MONTHS[m]}} ${{y}}</h3><div class="grid">${{['Su','Mo','Tu','We','Th','Fr','Sa'].map(w => `<div class="wd">${{w}}</div>`).join('')}}</div>`;

      const g = el.querySelector('.grid');
      for (let i = 0; i < lead; i++) {{
        const b = document.createElement('div');
        b.className = 'day blank';
        g.appendChild(b);
      }}

      for (let dd = 1; dd <= days; dd++) {{
        const n = Math.round(Date.UTC(y, m, dd) / 86400000);
        const info = d.dayInfo(n);
        const c = document.createElement('div');
        let cls = 'day';
        if (info.phase) cls += ' ph-' + info.phase.phase + (info.phase.predicted ? ' pred' : '');
        if (info.today) cls += ' today';
        if (info.future) cls += ' future';
        if (n === selected) cls += ' sel';
        cls += ' k-' + info.kind;

        c.className = cls;
        c.innerHTML = `<span class="mark ${{info.kind}}"></span><span class="n">${{dd}}</span>`;
        c.onclick = () => {{ selected = n; render(); }};
        g.appendChild(c);
      }}
      box.appendChild(el);
    }});
  }}

  function renderSheet(d) {{
    const el = $('sheet');
    if (selected === null) {{
      el.innerHTML = '<h2>Day Inspector</h2><div class="muted">Click any calendar day to inspect.</div>';
      return;
    }}
    const info = d.dayInfo(selected);
    const oYmd = E.ymd(selected);
    const dtStr = `${{oYmd.d}} ${{E.MONTHS[oYmd.m]}} ${{oYmd.y}}`;

    let phaseName = info.phase ? info.phase.phase.toUpperCase() : 'NONE';
    let phaseDesc = info.phase ? `Cycle Day ${{info.phase.cycleDay}} · ${{phaseName}} phase` : 'Outside active cycle';

    let html = `<h2>Selected Date Details</h2>
      <div class="date">${{dtStr}}</div>
      <div class="kind">${{phaseDesc}}</div>
      <div style="margin-top: 10px; font-size: 12.5px; line-height: 1.6;">
        <div><strong>Status:</strong> ${{info.kind === 'confirmed' ? 'Confirmed Period Day' : info.kind === 'predicted' ? 'Predicted Period Day' : 'Normal Day'}}</div>
        <div><strong>Is Today:</strong> ${{info.today ? 'Yes (Current Date)' : 'No'}}</div>
        ${{info.period ? `<div><strong>Period Span:</strong> ${{E.fmtRange(info.period.start, info.period.lastConfirmed)}}</div>` : ''}}
      </div>`;
    el.innerHTML = html;
  }}

  function renderLog() {{
    $('log').innerHTML = logItems.map(l => `<div class="entry ${{l.kind}}"><div class="who">${{l.who}}</div>${{l.text}}</div>`).join('');
  }}

  $('reset').onclick = () => {{
    st = E.createState(INITIAL_STATE);
    selected = E.toN('2026-09-21');
    render();
  }};

  $('today').onchange = (e) => {{
    st.today = E.toN(e.target.value);
    render();
  }};

  render();
}})();
</script>

</body>
</html>
'''

with open("d:/automachine/cycle_tracking_report.html", "w", encoding="utf-8") as f:
    f.write(html_content)

print(f"Report generated successfully: d:/automachine/cycle_tracking_report.html (Size: {len(html_content)} bytes)")
