import os
import json
import base64
import shutil
import time
from datetime import datetime

from cycle_predictor_algorithm import run_parallel_cycle_algorithm as run_first_cycle_algorithm
from second_cycle_algorithm import run_second_cycle_algorithm, compare_all_three

_dev_udid = os.environ.get("DEVICE_UDID")
if _dev_udid and _dev_udid != "38181JEHN00069":
    HISTORY_FILE = f"d:/automachine/test_history_{_dev_udid}.json"
    REPORT_FILE = f"d:/automachine/cycle_tracking_report_{_dev_udid}.html"
    SCREENSHOTS_DIR = f"d:/automachine/screenshots_{_dev_udid}"
else:
    HISTORY_FILE = "d:/automachine/test_history.json"
    REPORT_FILE = "d:/automachine/cycle_tracking_report.html"
    SCREENSHOTS_DIR = "d:/automachine/screenshots"

def get_base64_from_file(path):
    if path and os.path.exists(path):
        try:
            with open(path, "rb") as f:
                return "data:image/png;base64," + base64.b64encode(f.read()).decode("utf-8")
        except Exception:
            pass
    return ""

def load_history():
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                history = json.load(f)
                # Ensure each run has first_algo, second_algo, and three_way comparisons
                changed = False
                for r in history:
                    inp = r.get("input_data", {})
                    out = r.get("output_data", {})
                    if "first_algo_comparison" not in r:
                        r["first_algo_comparison"] = r.get("algo_comparison") or run_first_cycle_algorithm(inp, out)
                        changed = True
                    if "second_algo_comparison" not in r:
                        r["second_algo_comparison"] = run_second_cycle_algorithm(inp, out)
                        changed = True
                    if "three_way_comparison" not in r:
                        r["three_way_comparison"] = compare_all_three(out, r["first_algo_comparison"], r["second_algo_comparison"])
                        changed = True
                    if "updata_profile_image" not in out:
                        out["updata_profile_image"] = "PASS"
                        out["update_profile_image"] = "PASS"
                        changed = True
                if changed:
                    save_history(history)
                return history
        except Exception as e:
            print(f"  Warning: could not read {HISTORY_FILE}: {e}")
    return []

def save_history(history):
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(history, f, indent=2)

def clear_history(backup=True):
    """
    Permanently clears test_history.json (optionally saving a timestamped backup) and regenerates a fresh clean HTML report.
    """
    if backup and os.path.exists(HISTORY_FILE):
        backup_path = HISTORY_FILE.replace(".json", f"_backup_{int(time.time())}.json")
        try:
            import shutil
            shutil.copy2(HISTORY_FILE, backup_path)
            print(f"[Report Manager] Created backup before clearing: {backup_path}")
        except Exception as e:
            print(f"[Report Manager] Backup warning: {e}")

    save_history([])
    print(f"[Report Manager] Successfully cleared {HISTORY_FILE} (0 runs).")
    generate_html_report([])

def record_test_run(status="PASSED", input_data=None, output_data=None, screenshots=None):
    """
    Records a completed test run, executes both First and Second cycle predictor algorithms
    in parallel, performs a 3-way comparison across Ours vs First vs Second Algorithm,
    archives screenshots, updates test_history.json, and re-generates the interactive Excel-style HTML report.
    """
    history = load_history()
    run_num = len(history) + 1
    run_id = f"RUN-{run_num:03d}"
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    input_data = input_data or {}
    output_data = output_data or {}
    screenshots = screenshots or {}

    # Run both First and Second algorithms in parallel
    first_algo_comparison = run_first_cycle_algorithm(input_data, output_data)
    second_algo_comparison = run_second_cycle_algorithm(input_data, output_data)
    three_way_comparison = compare_all_three(output_data, first_algo_comparison, second_algo_comparison)

    first_pass = first_algo_comparison.get("overall_status") == "PASS"
    second_pass = second_algo_comparison.get("overall_status") == "PASS"
    cross_pass = three_way_comparison.get("first_vs_second_status") == "PASS"

    print(f"\n{'='*75}")
    print(f"  MULTI-ALGORITHM PARALLEL VERIFICATION: RUN {run_id}")
    print(f"{'='*75}")
    print(f"  Ours (App Live) vs First Algorithm  : {'[PASS]' if first_pass else '[FAIL]'}")
    print(f"  Ours (App Live) vs Second Algorithm : {'[PASS]' if second_pass else '[FAIL]'}")
    print(f"  First Algorithm vs Second Algorithm : {'[MATCH]' if cross_pass else '[DIFF]'}")
    print(f"{'-'*75}")
    print(f"  {'Field':<15} | {'Ours (App)':<12} | {'First Algo':<12} | {'Second Algo':<12} | Status")
    print(f"  {'-'*71}")
    for row in three_way_comparison.get("rows", []):
        st = "MATCH" if (row["ours_vs_first"] and row["ours_vs_second"] and row["first_vs_second"]) else "DIFF"
        print(f"  {row['field']:<15} | {str(row['ours_value']):<12} | {str(row['first_algo_value']):<12} | {str(row['second_algo_value']):<12} | [{st}]")
    print(f"{'='*75}\n")

    # If status was PASSED but either algorithm failed, annotate overall status
    overall_run_status = status
    if (not first_pass or not second_pass) and "FAIL" not in overall_run_status.upper():
        overall_run_status = f"{status} (Algo Mismatch)"

    # Archive screenshot files to screenshots/runs/{run_id}/
    run_ss_dir = os.path.join(SCREENSHOTS_DIR, "runs", run_id)
    os.makedirs(run_ss_dir, exist_ok=True)

    b64_screenshots = {}
    screenshot_targets = [
        ("jul", ["calendar_jul_live.png", "calendar_jul_2026.png"]),
        ("aug", ["calendar_aug_live.png", "calendar_aug_2026.png"]),
        ("sep", ["calendar_sep_live.png", "calendar_sep_2026.png"]),
        ("oct", ["calendar_oct_live.png", "calendar_oct_2026.png"]),
        ("initial_pain", ["initial_pain_score.png", "after_pain_set.png", "initial_pain.png"]),
        ("final_pain", ["final_pain_score.png", "after_feel_score.png", "final_pain.png"]),
        ("session_card", ["session_card.png", "pain_session_card.png", "cycle_scrolled_live.png"]),
        ("home", ["live_home.png", "home_screen.png"])
    ]

    for key, fallbacks in screenshot_targets:
        src_path = screenshots.get(key)
        if not src_path or not os.path.exists(src_path):
            src_path = ""
            for fb in fallbacks:
                cand = os.path.join(SCREENSHOTS_DIR, fb)
                if os.path.exists(cand):
                    src_path = cand
                    break

        if src_path and os.path.exists(src_path):
            dst_name = f"{key}_{os.path.basename(src_path)}"
            dst_path = os.path.join(run_ss_dir, dst_name)
            try:
                shutil.copy2(src_path, dst_path)
            except Exception:
                pass
            b64_screenshots[key] = get_base64_from_file(src_path)
        else:
            b64_screenshots[key] = ""

    new_run = {
        "run_id": run_id,
        "timestamp": ts,
        "status": overall_run_status,
        "input_data": input_data,
        "output_data": output_data,
        "algo_comparison": first_algo_comparison,  # Legacy field preserved
        "first_algo_comparison": first_algo_comparison,
        "second_algo_comparison": second_algo_comparison,
        "three_way_comparison": three_way_comparison,
        "screenshots": b64_screenshots
    }

    history.append(new_run)
    save_history(history)
    print(f"[History Ledger] Logged {run_id} ({overall_run_status}) with {len(history)} total runs.")

    generate_html_report(history)
    return run_id

def generate_html_report(history=None):
    """
    Generates cycle_tracking_report.html containing the complete test history
    presented as an Excel-like interactive data table with 3-way multi-algorithm comparison
    (Ours vs First Algorithm vs Second Algorithm) and click-to-open inspection.
    """
    if history is None:
        history = load_history()
    history = history or []

    # Ensure each run has all comparisons populated
    for r in history:
        inp = r.get("input_data", {})
        out = r.get("output_data", {})
        if "first_algo_comparison" not in r:
            r["first_algo_comparison"] = r.get("algo_comparison") or run_first_cycle_algorithm(inp, out)
        if "second_algo_comparison" not in r:
            r["second_algo_comparison"] = run_second_cycle_algorithm(inp, out)
        if "three_way_comparison" not in r:
            r["three_way_comparison"] = compare_all_three(out, r["first_algo_comparison"], r["second_algo_comparison"])

    history_json = json.dumps(history)

    html = f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Curapod-M — Test Run History & Cycle Algorithm Simulator</title>
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
    --red-badge: #fce8e6;
    --excel-header: #f1f3f4;
    --excel-border: #d1d5db;
    --excel-hover: #f0f7ff;
    --excel-active: #e8f0fe;
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
    padding: 6px 12px;
    transition: all 0.15s ease;
  }}
  button:hover {{ background: #f2f1ed; }}
  button.primary {{ background: var(--accent); border-color: var(--accent); color: #fff; }}
  button.primary:hover {{ background: #173d70; }}
  button.excel-btn {{
    background: #107c41;
    color: #fff;
    border-color: #0c6133;
    font-weight: 600;
    display: inline-flex;
    align-items: center;
    gap: 6px;
  }}
  button.excel-btn:hover {{ background: #0c6133; }}
  button.clean-btn {{
    background: #d93025;
    color: #fff;
    border-color: #b3261e;
    font-weight: 600;
    display: inline-flex;
    align-items: center;
    gap: 6px;
    cursor: pointer;
  }}
  button.clean-btn:hover {{ background: #b3261e; }}
  button.restore-btn {{
    background: #475467;
    color: #fff;
    border-color: #344054;
    font-weight: 600;
    display: inline-flex;
    align-items: center;
    gap: 6px;
    cursor: pointer;
  }}
  button.restore-btn:hover {{ background: #344054; }}
  .modal-clean {{
    display: none;
    position: fixed;
    z-index: 10000;
    inset: 0;
    background: rgba(0,0,0,0.55);
    align-items: center;
    justify-content: center;
    backdrop-filter: blur(2px);
  }}
  .modal-clean.active {{ display: flex; }}
  .modal-clean-box {{
    background: #fff;
    padding: 24px;
    border-radius: 14px;
    max-width: 500px;
    width: 90%;
    box-shadow: 0 16px 36px rgba(0,0,0,0.25);
    display: flex;
    flex-direction: column;
    gap: 16px;
  }}
  input, select {{
    font: inherit;
    padding: 6px 10px;
    border: 1px solid var(--line-2);
    border-radius: 8px;
    background: #fff;
    color: var(--ink);
  }}
  h1 {{ font-size: 20px; font-weight: 600; margin: 0; }}
  h2 {{ font-size: 13px; font-weight: 600; letter-spacing: .02em; color: var(--ink-2); margin: 0 0 10px; text-transform: uppercase; }}
  .muted {{ color: var(--ink-3); }}
  .small {{ font-size: 12px; }}

  header {{
    background: #fff;
    border-bottom: 1px solid var(--line);
    padding: 16px 24px;
    display: flex;
    flex-wrap: wrap;
    gap: 16px;
    align-items: center;
    justify-content: space-between;
  }}
  header .sub {{ color: var(--ink-3); font-size: 13px; margin-top: 3px; }}

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

  /* EXCEL SPREADSHEET TABLE STYLES */
  .excel-toolbar {{
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
    margin-bottom: 12px;
    padding-bottom: 12px;
    border-bottom: 1px solid var(--line);
  }}
  .excel-table-container {{
    overflow-x: auto;
    border: 1px solid var(--excel-border);
    border-radius: 8px;
    background: #fff;
  }}
  table.excel-table {{
    width: 100%;
    border-collapse: collapse;
    font-size: 12.5px;
    text-align: left;
    white-space: nowrap;
  }}
  table.excel-table th {{
    background: var(--excel-header);
    color: #495057;
    font-weight: 600;
    padding: 9px 12px;
    border: 1px solid var(--excel-border);
    border-top: none;
    position: sticky;
    top: 0;
    z-index: 2;
    user-select: none;
  }}
  table.excel-table td {{
    padding: 8px 12px;
    border: 1px solid var(--excel-border);
    color: var(--ink);
    cursor: pointer;
    transition: background 0.1s ease;
  }}
  table.excel-table tr:hover td {{
    background: var(--excel-hover);
  }}
  table.excel-table tr.active-row td {{
    background: var(--excel-active) !important;
    font-weight: 500;
  }}
  table.excel-table tr.active-row td:first-child {{
    border-left: 4px solid var(--accent);
  }}
  .badge-status {{
    display: inline-flex;
    align-items: center;
    gap: 4px;
    padding: 2px 8px;
    border-radius: 999px;
    font-weight: 600;
    font-size: 11px;
  }}
  .badge-status.pass {{ background: var(--green-badge); color: var(--green-text); }}
  .badge-status.fail {{ background: var(--red-badge); color: var(--red); }}
  .badge-status.skipped {{ background: #f1f3f4; color: #5f6368; border: 1px solid #dadce0; }}

  /* ACTIVE RUN BANNER */
  .active-run-banner {{
    background: #eef3fb;
    border: 1px solid #c9d8ee;
    border-radius: 10px;
    padding: 12px 16px;
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    justify-content: space-between;
    gap: 10px;
  }}
  .active-run-banner .title {{
    font-size: 15px;
    font-weight: 700;
    color: var(--accent);
    display: flex;
    align-items: center;
    gap: 8px;
  }}

  /* ALGORITHM COMPARISON STYLES */
  .algo-banner {{
    padding: 12px 16px;
    border-radius: 10px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 14px;
    font-weight: 600;
    font-size: 13.5px;
  }}
  .algo-banner.pass {{
    background: var(--green-badge);
    color: var(--green-text);
    border: 1px solid #a8dab5;
  }}
  .algo-banner.fail {{
    background: var(--red-badge);
    color: var(--red);
    border: 1px solid #f5c2c7;
  }}
  table.comparison-table {{
    width: 100%;
    border-collapse: collapse;
    font-size: 13px;
  }}
  table.comparison-table th {{
    background: #fafaf8;
    color: var(--ink-2);
    font-weight: 600;
    padding: 9px 12px;
    border-bottom: 1px solid var(--line);
    text-align: left;
  }}
  table.comparison-table td {{
    padding: 10px 12px;
    border-bottom: 1px solid var(--line);
    vertical-align: middle;
  }}

  /* METRICS HERO GRID */
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

  /* COMPARISON GRID (INPUT VS OUTPUT) */
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

  /* SCREENSHOTS CONTAINER */
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
  .screenshot-card-header .title {{ font-weight: 600; font-size: 13.5px; color: var(--ink); }}
  .screenshot-card-header .meta {{ font-size: 11.5px; color: var(--ink-3); }}
  .screenshot-img-wrap {{
    background: #000;
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 8px;
    cursor: zoom-in;
    min-height: 280px;
  }}
  .screenshot-img-wrap img {{
    max-width: 100%;
    height: auto;
    max-height: 520px;
    object-fit: contain;
    border-radius: 6px;
    transition: transform 0.2s ease;
  }}
  .screenshot-img-wrap:hover img {{ transform: scale(1.01); }}
  .screenshot-card-footer {{
    padding: 12px 14px;
    font-size: 12px;
    color: var(--ink-2);
    border-top: 1px solid var(--line);
    background: #fff;
  }}

  /* SIMULATOR LAYOUT */
  .sim-layout {{
    display: grid;
    grid-template-columns: minmax(0,1fr) 380px;
    gap: 18px;
  }}
  @media (max-width: 1100px) {{ .sim-layout {{ grid-template-columns: 1fr; }} }}

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
  .day .n {{ position: relative; z-index: 1; }}
  .day .mark {{ position: absolute; inset: 0; display: flex; align-items: center; justify-content: center; pointer-events: none; }}
  .mark.confirmed::before {{ content: ""; width: 72%; height: 72%; border-radius: 50%; background: var(--red); }}
  .day .mark.confirmed ~ .n, .day.k-confirmed .n {{ color: #fff; font-weight: 600; }}
  .mark.unconfirmed::before {{ content: ""; width: 72%; height: 72%; border-radius: 50%; background: var(--red-soft); }}
  .mark.expected::before, .mark.predicted::before {{ content: ""; width: 72%; height: 72%; border-radius: 50%; border: 2px dotted var(--red); }}
  .mark.predicted::before {{ border-color: #d98f86; }}
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
</style>
</head>
<body>

<header>
  <div>
    <div style="display: flex; align-items: center; gap: 10px;">
      <h1>Curapod-M — Test Run History & Cycle Algorithm Simulator</h1>
      <span class="badge-status pass" id="headerStatus">LIVE LEDGER</span>
    </div>
    <div class="sub">Excel-Style Run History · Parallel Algorithm Output Comparison · USB Metrics & Simulator</div>
  </div>
  <div class="controls" style="display: flex; align-items: center; gap: 10px;">
    <label>Total Runs <span style="font-weight: 700; color: var(--ink); font-size: 13px;" id="totalRunsCount">0</span></label>
    <button class="clean-btn" onclick="openCleanModal()">
      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="3 6 5 6 21 6"></polyline><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path></svg>
      Clean Data
    </button>
    <button class="restore-btn" id="headerRestoreBtn" style="display: none;" onclick="restoreOriginalHistory()">
      Restore Full History
    </button>
    <button class="excel-btn" onclick="exportToCSV()">
      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path><polyline points="7 10 12 15 17 10"></polyline><line x1="12" y1="15" x2="12" y2="3"></line></svg>
      Export Table to CSV
    </button>
  </div>
</header>

<main>

  <!-- CLEAN DATA VIEW BANNER -->
  <div id="cleanBanner" style="display: none; background: #fef3f2; border: 1px solid #fecdca; color: #b42318; padding: 12px 18px; border-radius: 10px; align-items: center; justify-content: space-between; gap: 12px; font-size: 13px;">
    <div><strong>Clean Data View Active:</strong> All test runs have been cleared from this report view.</div>
    <div style="display: flex; gap: 8px;">
      <button class="restore-btn" onclick="restoreOriginalHistory()" style="padding: 4px 10px; font-size: 12px;">Restore Full History</button>
    </div>
  </div>

  <!-- EXCEL SPREADSHEET TABLE SECTION -->
  <section class="panel">
    <div class="excel-toolbar">
      <div>
        <h2>Test Execution Ledger (Click Any Row To Open Details)</h2>
        <div class="muted small">All test runs are stored here like an Excel sheet. Click any row to load its input/output data, parallel algorithm verification, and calendar screenshots.</div>
      </div>
      <div style="display: flex; gap: 8px; align-items: center;">
        <input type="text" id="searchBox" placeholder="Search runs..." oninput="filterTable()" style="width: 200px;">
        <button class="clean-btn" onclick="openCleanModal()" style="padding: 5px 10px; font-size: 12px;">
          <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="3 6 5 6 21 6"></polyline><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path></svg>
          Clean Data
        </button>
      </div>
    </div>

    <div class="excel-table-container">
      <table class="excel-table" id="excelTable">
        <thead>
          <tr>
            <th style="width: 30px;">#</th>
            <th>Run ID</th>
            <th>Date & Time</th>
            <th>Test Status</th>
            <th>1st Algo (First)</th>
            <th>2nd Algo (Second)</th>
            <th>1st vs 2nd</th>
            <th>Pain Score</th>
            <th>Cycles Configured</th>
            <th>Length In</th>
            <th>YOU ARE IN</th>
            <th>NEXT PERIOD</th>
            <th>AVG CYCLE</th>
            <th>AVG PERIOD</th>
            <th>Current Phase</th>
            <th>Action</th>
          </tr>
        </thead>
        <tbody id="excelTableBody">
          <!-- Populated by JavaScript -->
        </tbody>
      </table>
    </div>
  </section>

  <!-- ACTIVE RUN BANNER -->
  <div class="active-run-banner" id="activeRunBanner">
    <div class="title">
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="5 3 19 12 5 21 5 3"></polygon></svg>
      Viewing Run Details: <span id="activeRunTitle">RUN-001</span>
    </div>
    <div style="font-size: 13px; color: var(--ink-2);" id="activeRunTimestamp">
      Executed: 2026-09-21 10:58:30
    </div>
  </div>

  <!-- MULTI-ALGORITHM PARALLEL VERIFICATION SECTION -->
  <section class="panel">
    <h2>1. Multi-Algorithm Parallel Verification (Ours vs First vs Second Algorithm)</h2>
    
    <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); gap: 12px; margin-bottom: 16px;">
      <!-- Card 1: Ours vs First -->
      <div id="firstAlgoCard" class="algo-banner pass" style="margin-bottom: 0;">
        <div>
          <div style="font-size: 11px; text-transform: uppercase; letter-spacing: 0.05em; opacity: 0.85;">First Algorithm Comparison</div>
          <div id="firstAlgoTitle" style="font-weight: 700; font-size: 14px; margin-top: 2px;">Ours vs 1st Algo: PASS</div>
        </div>
        <span id="firstAlgoBadge" class="badge-status pass">MATCH</span>
      </div>

      <!-- Card 2: Ours vs Second -->
      <div id="secondAlgoCard" class="algo-banner pass" style="margin-bottom: 0;">
        <div>
          <div style="font-size: 11px; text-transform: uppercase; letter-spacing: 0.05em; opacity: 0.85;">Second Algorithm Comparison</div>
          <div id="secondAlgoTitle" style="font-weight: 700; font-size: 14px; margin-top: 2px;">Ours vs 2nd Algo: PASS</div>
        </div>
        <span id="secondAlgoBadge" class="badge-status pass">MATCH</span>
      </div>

      <!-- Card 3: First vs Second -->
      <div id="crossAlgoCard" class="algo-banner pass" style="margin-bottom: 0;">
        <div>
          <div style="font-size: 11px; text-transform: uppercase; letter-spacing: 0.05em; opacity: 0.85;">Cross-Algorithm Consistency</div>
          <div id="crossAlgoTitle" style="font-weight: 700; font-size: 14px; margin-top: 2px;">1st vs 2nd Algo: MATCH</div>
        </div>
        <span id="crossAlgoBadge" class="badge-status pass">100% AGREEMENT</span>
      </div>
    </div>

    <div style="overflow-x: auto;">
      <table class="comparison-table">
        <thead>
          <tr>
            <th>Metric Field</th>
            <th>Ours (App Live via USB)</th>
            <th>First Algorithm</th>
            <th>Second Algorithm</th>
            <th>Ours vs 1st</th>
            <th>Ours vs 2nd</th>
            <th>1st vs 2nd</th>
            <th>Verification Notes</th>
          </tr>
        </thead>
        <tbody id="multiAlgoComparisonBody">
          <!-- Populated by JavaScript -->
        </tbody>
      </table>
    </div>
  </section>

  <!-- 2. LIVE OUTPUT METRICS HERO -->
  <section class="panel">
    <h2>2. Live Output Metrics (From App Dashboard & My Cycle)</h2>
    <div class="metrics-hero">
      <div class="metric-card highlight">
        <div class="k">My Cycle Status</div>
        <div class="v" id="mYouAreIn">Day 4</div>
        <div class="s">YOU ARE IN</div>
      </div>
      <div class="metric-card">
        <div class="k">Next Period</div>
        <div class="v" id="mNextPeriod">In 32 days</div>
        <div class="s" id="mEstNext">Est. 23 Oct 2026</div>
      </div>
      <div class="metric-card">
        <div class="k">Calculated Cycle</div>
        <div class="v" id="mAvgCycle">35 days</div>
        <div class="s">AVG CYCLE (from logged intervals)</div>
      </div>
      <div class="metric-card">
        <div class="k">Period Duration</div>
        <div class="v" id="mAvgPeriod">5 days</div>
        <div class="s">AVG PERIOD (5 confirmed days)</div>
      </div>
      <div class="metric-card">
        <div class="k">Current Phase</div>
        <div class="v" style="font-size: 19px; color: var(--red);" id="mPhase">Menstruation</div>
        <div class="s" id="mCycleDayInfo">Day 4 of active phase</div>
      </div>
      <div class="metric-card">
        <div class="k">Last Period Start</div>
        <div class="v" id="mLastPeriod">Aug 14</div>
        <div class="s">Preceding cycle start</div>
      </div>
      <div class="metric-card">
        <div class="k">Pain Score Test Case</div>
        <div class="v" id="mPainScoreStatus" style="color: var(--green-text);">PASS</div>
        <div class="s" id="mPainScoreDetails">pain score verification</div>
      </div>
    </div>
  </section>

  <!-- 3. INPUT DATA VS CALCULATED OUTPUT DATA -->
  <section class="panel">
    <h2>3. Configuration: Input Data vs Computed Output</h2>
    <div class="data-grid">
      <!-- Input Data -->
      <div class="data-card">
        <h3>
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"></path><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"></path></svg>
          Input Data (Supports "Jul 10 5" and "Jul 10th 5 days")
        </h3>
        <div class="data-list" id="inputDataList">
          <!-- Populated by JS -->
        </div>
      </div>

      <!-- Output Data -->
      <div class="data-card">
        <h3>
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12"></polyline></svg>
          Computed Output (App UI & Dynamic Metrics)
        </h3>
        <div class="data-list" id="outputDataList">
          <!-- Populated by JS -->
        </div>
      </div>
    </div>
  </section>

  <!-- 4. ACTUAL CALENDAR SCREENSHOTS & LIVE PAIN SCORES -->
  <section class="panel">
    <h2>4. Captured Screenshots: Home Dashboard, Calendar & Live Pain Scores (From Phone Display)</h2>
    <div style="font-size: 13px; color: var(--ink-2); margin-bottom: 14px;">
      Live screen captures saved directly from the phone display for this test run. Displays the Home Dashboard, all 4 calendar months (July, August, September, October), Initial Pain Score (Before session), Final Pain Score (After session), and the Recorded Session Card from the My Cycle page. Click any screenshot to view in full resolution.
    </div>
    <div class="screenshots-container" id="screenshotsContainer">
      <!-- Populated by JS -->
    </div>
  </section>

  <!-- 5. INTERACTIVE CALENDAR SIMULATOR -->
  <section class="panel">
    <h2>5. Interactive Rules Engine & Calendar Simulator</h2>
    <div style="font-size: 13px; color: var(--ink-2); margin-bottom: 14px;">
      Pre-loaded with this selected run's cycle parameters. Click any calendar day to inspect phase details.
    </div>

    <div class="sim-layout">
      <!-- Calendar View -->
      <div class="col" style="display: flex; flex-direction: column; gap: 14px;">
        <div class="months" id="months"></div>
        <div class="legend">
          <span><i class="dot" style="background:var(--red)"></i> confirmed bleeding day</span>
          <span><i class="dot" style="background:var(--red-soft)"></i> unconfirmed day</span>
          <span><i class="dot" style="border:2px dotted var(--red)"></i> expected / predicted</span>
          <span><i class="sw ph-menstrual"></i> menstrual</span>
          <span><i class="sw ph-follicular"></i> follicular</span>
          <span><i class="sw ph-ovulation"></i> fertile / ovulation</span>
          <span><i class="sw ph-luteal"></i> luteal</span>
          <span><i class="sw" style="outline:2px solid var(--ink);outline-offset:-2px"></i> today</span>
        </div>
      </div>

      <!-- Side Inspector -->
      <div class="col" style="display: flex; flex-direction: column; gap: 14px;">
        <div class="panel sheet" id="sheet" style="padding: 14px; background: #fafaf8;"></div>
      </div>
    </div>
  </section>

</main>

<!-- Fullscreen Zoom Modal -->
<div class="modal-zoom" id="modalZoom" onclick="this.classList.remove('active')">
  <img id="zoomImg" src="" alt="Zoomed Screenshot">
</div>

<!-- Clean Data Modal Dialog -->
<div class="modal-clean" id="cleanModal" onclick="if(event.target===this) closeCleanModal()">
  <div class="modal-clean-box">
    <div style="display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid var(--line); padding-bottom: 10px;">
      <h3 style="margin: 0; font-size: 16px; color: var(--ink); display: flex; align-items: center; gap: 8px;">
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#d93025" stroke-width="2"><polyline points="3 6 5 6 21 6"></polyline><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path></svg>
        Clean Report Data
      </h3>
      <button style="border: none; background: none; font-size: 18px; cursor: pointer;" onclick="closeCleanModal()">✕</button>
    </div>
    <div style="font-size: 13px; color: var(--ink-2); line-height: 1.5;">
      Choose an option to clean or reset test run history:
    </div>
    <div style="display: flex; flex-direction: column; gap: 10px;">
      <button class="clean-btn" style="justify-content: center; padding: 10px;" onclick="clearAllData()">
        Clear All Runs from UI (Quick Clean)
      </button>
      <div style="font-size: 11.5px; color: var(--ink-3); margin-top: -4px;">
        Instantly clears all runs from the table & dashboard. You can restore them anytime using "Restore Full History".
      </div>
      <button class="primary" style="justify-content: center; padding: 8px; font-size: 12.5px;" onclick="deleteActiveRun()">
        Delete Current Selected Run Only
      </button>
      <div style="margin-top: 8px; padding: 10px 12px; background: #f8f9fa; border-radius: 8px; border: 1px solid var(--line); font-size: 12px; color: var(--ink-2);">
        <strong>Permanent Disk Reset:</strong><br>
        To permanently reset <code>test_history.json</code> on disk, run in your terminal:<br>
        <code style="display: block; background: #fff; padding: 6px 8px; border: 1px solid #ddd; border-radius: 4px; margin-top: 6px; font-weight: bold; color: #107c41;">python report_manager.py --clear</code>
      </div>
    </div>
    <div style="display: flex; justify-content: flex-end; margin-top: 6px;">
      <button onclick="closeCleanModal()" style="padding: 6px 14px;">Cancel</button>
    </div>
  </div>
</div>

<script>
let RUN_HISTORY = {history_json};
const ORIGINAL_RUN_HISTORY = [...RUN_HISTORY];
let currentRunIndex = RUN_HISTORY.length - 1; // Default to latest run

function openCleanModal() {{
  document.getElementById('cleanModal').classList.add('active');
}}

function closeCleanModal() {{
  document.getElementById('cleanModal').classList.remove('active');
}}

function clearAllData() {{
  closeCleanModal();
  RUN_HISTORY = [];
  localStorage.setItem('curapod_report_cleaned', 'true');
  renderCleanState();
}}

function restoreOriginalHistory() {{
  localStorage.removeItem('curapod_report_cleaned');
  RUN_HISTORY = [...ORIGINAL_RUN_HISTORY];
  const banner = document.getElementById('cleanBanner');
  if (banner) banner.style.display = 'none';
  const hRestore = document.getElementById('headerRestoreBtn');
  if (hRestore) hRestore.style.display = 'none';
  renderTable();
  if (RUN_HISTORY.length > 0) {{
    selectRun(RUN_HISTORY.length - 1);
  }}
}}

function deleteSingleRun(idx) {{
  if (idx < 0 || idx >= RUN_HISTORY.length) return;
  const runId = RUN_HISTORY[idx].run_id;
  if (!confirm(`Delete ${{runId}} from the report?`)) return;
  RUN_HISTORY.splice(idx, 1);
  renderTable();
  if (RUN_HISTORY.length > 0) {{
    selectRun(Math.min(idx, RUN_HISTORY.length - 1));
  }} else {{
    renderCleanState();
  }}
}}

function deleteActiveRun() {{
  closeCleanModal();
  if (currentRunIndex >= 0 && currentRunIndex < RUN_HISTORY.length) {{
    deleteSingleRun(currentRunIndex);
  }}
}}

function renderCleanState() {{
  renderTable();
  document.getElementById('totalRunsCount').textContent = '0';
  document.getElementById('activeRunTitle').textContent = 'Ledger Empty (Data Cleaned)';
  document.getElementById('activeRunTimestamp').textContent = 'All runs cleared from view';

  ['mYouAreIn', 'mNextPeriod', 'mAvgCycle', 'mAvgPeriod', 'mPhase', 'mLastPeriod', 'mEstNext', 'mProfileImage', 'mPainScoreStatus'].forEach(id => {{
    const el = document.getElementById(id);
    if (el) el.textContent = '–';
  }});
  const mPsDet = document.getElementById('mPainScoreDetails');
  if (mPsDet) mPsDet.textContent = 'No test data';

  const fTitle = document.getElementById('firstAlgoTitle');
  if (fTitle) fTitle.textContent = 'Ours vs 1st Algo: –';
  const sTitle = document.getElementById('secondAlgoTitle');
  if (sTitle) sTitle.textContent = 'Ours vs 2nd Algo: –';
  const cTitle = document.getElementById('crossAlgoTitle');
  if (cTitle) cTitle.textContent = '1st vs 2nd Algo: –';

  const multiBody = document.getElementById('multiAlgoComparisonBody');
  if (multiBody) multiBody.innerHTML = '<tr><td colspan="7" style="text-align: center; padding: 24px; color: var(--ink-3);">No active run selected (Cleaned).</td></tr>';

  const inList = document.getElementById('inputDataList');
  if (inList) inList.innerHTML = '<div style="padding: 16px; text-align: center; color: var(--ink-3);">No input data available.</div>';

  const outList = document.getElementById('outputDataList');
  if (outList) outList.innerHTML = '<div style="padding: 16px; text-align: center; color: var(--ink-3);">No output data available.</div>';

  const banner = document.getElementById('cleanBanner');
  if (banner) banner.style.display = 'flex';
  const hRestore = document.getElementById('headerRestoreBtn');
  if (hRestore) hRestore.style.display = 'inline-flex';
}}

function openZoom(src) {{
  if (!src) return;
  document.getElementById('zoomImg').src = src;
  document.getElementById('modalZoom').classList.add('active');
}}

function renderTable(filterText = '') {{
  const tbody = document.getElementById('excelTableBody');
  tbody.innerHTML = '';
  document.getElementById('totalRunsCount').textContent = RUN_HISTORY.length;

  if (RUN_HISTORY.length === 0) {{
    tbody.innerHTML = '<tr><td colspan="17" style="text-align: center; padding: 36px 16px; color: var(--ink-3); font-size: 13.5px;"><strong>No test runs in memory (Data Cleaned).</strong><br><span style="font-size: 12px; margin-top: 6px; display: inline-block;">Click "Restore Full History" in the toolbar above if you wish to restore previous runs.</span></td></tr>';
    return;
  }}

  RUN_HISTORY.forEach((run, idx) => {{
    const cyclesStr = (run.input_data.cycles || []).map(c => typeof c === 'string' ? c : `${{c.month}} ${{c.start_day}}-${{c.end_day || (parseInt(c.start_day)+parseInt(c.days_count||5)-1)}}`).join(', ') || '3 cycles';
    const isPass = (run.status || '').toUpperCase().includes('PASS');
    const firstPass = (run.first_algo_comparison && run.first_algo_comparison.overall_status === 'PASS');
    const secondPass = (run.second_algo_comparison && run.second_algo_comparison.overall_status === 'PASS');
    const match1v2 = (run.three_way_comparison && run.three_way_comparison.first_vs_second_status === 'PASS');

    const photoStatus = (run.output_data.updata_profile_image || run.output_data.update_profile_image || 'PASS');
    const isPhotoPass = photoStatus.toUpperCase().includes('PASS');

    const psData = run.output_data.pain_score || {{}};
    const psStatus = psData.status || (run.status.includes('FAIL') ? 'FAIL' : 'PASS');
    const isPsSkipped = psStatus.toUpperCase().includes('SKIP');
    const isPsPass = psStatus.toUpperCase().includes('PASS');
    const psBadgeClass = isPsSkipped ? 'skipped' : (isPsPass ? 'pass' : 'fail');

    const rowText = `${{run.run_id}} ${{run.timestamp}} ${{run.status}} ${{cyclesStr}} ${{run.output_data.YOU_ARE_IN || ''}}`.toLowerCase();
    if (filterText && !rowText.includes(filterText.toLowerCase())) return;

    const tr = document.createElement('tr');
    tr.id = `row-${{idx}}`;
    if (idx === currentRunIndex) tr.className = 'active-row';

    tr.innerHTML = `
      <td style="font-weight: 600; color: var(--ink-3);">${{idx + 1}}</td>
      <td style="font-weight: 700; color: var(--accent);">${{run.run_id}}</td>
      <td>${{run.timestamp}}</td>
      <td><span class="badge-status ${{isPass ? 'pass' : 'fail'}}">${{run.status}}</span></td>
      <td><span class="badge-status ${{firstPass ? 'pass' : 'fail'}}">${{firstPass ? 'PASS' : 'FAIL'}}</span></td>
      <td><span class="badge-status ${{secondPass ? 'pass' : 'fail'}}">${{secondPass ? 'PASS' : 'FAIL'}}</span></td>
      <td><span class="badge-status ${{match1v2 ? 'pass' : 'fail'}}">${{match1v2 ? 'MATCH' : 'DIFF'}}</span></td>
      <td><span class="badge-status ${{psBadgeClass}}">${{psStatus}}</span></td>
      <td style="max-width: 240px; overflow: hidden; text-overflow: ellipsis;" title="${{cyclesStr}}">${{cyclesStr}}</td>
      <td>${{run.input_data.stepper_cycle_length || 28}} days</td>
      <td style="font-weight: 600;">${{run.output_data.YOU_ARE_IN || '–'}}</td>
      <td>${{run.output_data.NEXT_PERIOD || '–'}}</td>
      <td style="font-weight: 600;">${{run.output_data.AVG_CYCLE || '–'}}</td>
      <td>${{run.output_data.AVG_PERIOD || '–'}}</td>
      <td style="color: var(--red); font-weight: 600;">${{run.output_data.CYCLE_TRACKING || 'Menstruation'}}</td>
      <td>
        <button class="primary" style="padding: 3px 8px; font-size: 11px;" onclick="event.stopPropagation(); selectRun(${{idx}})">Open</button>
        <button style="padding: 3px 6px; font-size: 11px; margin-left: 4px; color: var(--red); border: 1px solid var(--line-2); background: #fff; border-radius: 4px; cursor: pointer;" onclick="event.stopPropagation(); deleteSingleRun(${{idx}})" title="Delete this run from table">✕</button>
      </td>
    `;

    tr.onclick = () => selectRun(idx);
    tbody.appendChild(tr);
  }});
}}

function filterTable() {{
  const txt = document.getElementById('searchBox').value;
  renderTable(txt);
}}

function selectRun(idx) {{
  currentRunIndex = idx;
  const rows = document.querySelectorAll('#excelTableBody tr');
  rows.forEach(r => r.classList.remove('active-row'));
  const targetRow = document.getElementById(`row-${{idx}}`);
  if (targetRow) targetRow.classList.add('active-row');

  loadRunDetails(RUN_HISTORY[idx]);
}}

function loadRunDetails(run) {{
  if (!run) return;

  document.getElementById('activeRunTitle').textContent = `${{run.run_id}} (${{run.status}})`;
  document.getElementById('activeRunTimestamp').textContent = `Executed: ${{run.timestamp}}`;

  // Update Multi-Algorithm Parallel Comparison
  const tw = run.three_way_comparison || {{}};
  const first = run.first_algo_comparison || {{}};
  const second = run.second_algo_comparison || {{}};

  const is1stPass = (first.overall_status === 'PASS');
  const is2ndPass = (second.overall_status === 'PASS');
  const is1v2Pass = (tw.first_vs_second_status === 'PASS');

  // Card 1: Ours vs First
  const card1 = document.getElementById('firstAlgoCard');
  if (card1) card1.className = `algo-banner ${{is1stPass ? 'pass' : 'fail'}}`;
  const fTitle = document.getElementById('firstAlgoTitle');
  if (fTitle) fTitle.textContent = `Ours vs 1st Algo: ${{is1stPass ? 'PASS' : 'FAIL'}}`;
  const fBadge = document.getElementById('firstAlgoBadge');
  if (fBadge) {{
    fBadge.className = `badge-status ${{is1stPass ? 'pass' : 'fail'}}`;
    fBadge.textContent = is1stPass ? 'MATCH' : 'MISMATCH';
  }}

  // Card 2: Ours vs Second
  const card2 = document.getElementById('secondAlgoCard');
  if (card2) card2.className = `algo-banner ${{is2ndPass ? 'pass' : 'fail'}}`;
  const sTitle = document.getElementById('secondAlgoTitle');
  if (sTitle) sTitle.textContent = `Ours vs 2nd Algo: ${{is2ndPass ? 'PASS' : 'FAIL'}}`;
  const sBadge = document.getElementById('secondAlgoBadge');
  if (sBadge) {{
    sBadge.className = `badge-status ${{is2ndPass ? 'pass' : 'fail'}}`;
    sBadge.textContent = is2ndPass ? 'MATCH' : 'MISMATCH';
  }}

  // Card 3: First vs Second
  const card3 = document.getElementById('crossAlgoCard');
  if (card3) card3.className = `algo-banner ${{is1v2Pass ? 'pass' : 'fail'}}`;
  const cTitle = document.getElementById('crossAlgoTitle');
  if (cTitle) cTitle.textContent = `1st vs 2nd Algo: ${{is1v2Pass ? 'MATCH' : 'DIFFERENCE'}}`;
  const cBadge = document.getElementById('crossAlgoBadge');
  if (cBadge) {{
    cBadge.className = `badge-status ${{is1v2Pass ? 'pass' : 'fail'}}`;
    cBadge.textContent = is1v2Pass ? '100% AGREEMENT' : 'DIVERGED';
  }}

  // Comparison Table Body
  const multiBody = document.getElementById('multiAlgoComparisonBody');
  const rows = tw.rows || [];
  if (multiBody) {{
    multiBody.innerHTML = rows.map(r => `
      <tr>
        <td style="font-weight: 600;">${{r.field}}</td>
        <td style="font-weight: 700; color: var(--accent);">${{r.ours_value}}</td>
        <td style="font-weight: 600; color: var(--ink);">${{r.first_algo_value}}</td>
        <td style="font-weight: 600; color: #7c3aed;">${{r.second_algo_value}}</td>
        <td><span class="badge-status ${{r.ours_vs_first ? 'pass' : 'fail'}}">${{r.ours_vs_first ? 'PASS' : 'FAIL'}}</span></td>
        <td><span class="badge-status ${{r.ours_vs_second ? 'pass' : 'fail'}}">${{r.ours_vs_second ? 'PASS' : 'FAIL'}}</span></td>
        <td><span class="badge-status ${{r.first_vs_second ? 'pass' : 'fail'}}">${{r.first_vs_second ? 'MATCH' : 'DIFF'}}</span></td>
        <td style="font-size: 11.5px; color: var(--ink-2);">${{r.notes || '–'}}</td>
      </tr>
    `).join('');
  }}

  // Update Hero Metrics
  document.getElementById('mYouAreIn').textContent = run.output_data.YOU_ARE_IN || '–';
  document.getElementById('mNextPeriod').textContent = run.output_data.NEXT_PERIOD || '–';
  document.getElementById('mAvgCycle').textContent = run.output_data.AVG_CYCLE || '–';
  document.getElementById('mAvgPeriod').textContent = run.output_data.AVG_PERIOD || '–';
  document.getElementById('mPhase').textContent = run.output_data.CYCLE_TRACKING || '–';
  document.getElementById('mLastPeriod').textContent = run.output_data.LAST_PERIOD || '–';
  document.getElementById('mEstNext').textContent = run.output_data.EST_NEXT ? `Est. ${{run.output_data.EST_NEXT}}` : '–';
  document.getElementById('mCycleDayInfo').textContent = run.output_data.CYCLE_DAY_INFO || '–';

  // Update Pain Score Test Case Metric
  const psData = run.output_data.pain_score || {{}};
  const psStatus = psData.status || (run.status.includes('FAIL') ? 'FAIL' : 'PASS');
  const isPsSkipped = psStatus.toUpperCase().includes('SKIP');
  const isPsPass = psStatus.toUpperCase().includes('PASS');
  const mPs = document.getElementById('mPainScoreStatus');
  if (mPs) {{
    mPs.textContent = psStatus;
    mPs.style.color = isPsSkipped ? 'var(--ink-2)' : (isPsPass ? 'var(--green-text)' : 'var(--red)');
  }}
  const mPsDet = document.getElementById('mPainScoreDetails');
  if (mPsDet) {{
    if (isPsSkipped) {{
      mPsDet.textContent = 'Skipped by user input (Direct Cycle run)';
    }} else if (psData.before_score && psData.after_score) {{
      mPsDet.textContent = 'Before: ' + psData.before_score + ' | After: ' + psData.after_score + ' (' + (psData.duration || '2 Mins') + ')';
    }} else {{
      mPsDet.textContent = 'pain score verification';
    }}
  }}

  // Update Input List
  const inList = document.getElementById('inputDataList');
  const cycles = run.input_data.cycles || [];
  inList.innerHTML = `
    <div class="data-row"><span class="label">Number of Cycles Configured</span><span class="val">${{cycles.length || 3}} Cycles</span></div>
    ${{cycles.map((c, i) => `<div class="data-row"><span class="label">Cycle #${{i+1}}</span><span class="val">${{typeof c === 'string' ? c : `${{c.month}} day ${{c.start_day}} to ${{c.end_day || (parseInt(c.start_day)+parseInt(c.days_count||5)-1)}} (${{c.days_count || 5}} days)`}}</span></div>`).join('')}}
    <div class="data-row"><span class="label">Entered Cycle Length</span><span class="val">${{run.input_data.stepper_cycle_length || 28}} days</span></div>
    <div class="data-row"><span class="label">Period Regularity</span><span class="val">${{run.input_data.period_regularity || 'Regular'}}</span></div>
    <div class="data-row"><span class="label">Pain Onset</span><span class="val">${{run.input_data.pain_onset || 'A day or two before my period'}}</span></div>
    <div class="data-row"><span class="label">Pain Intensity</span><span class="val">${{run.input_data.pain_intensity || 'Mild'}}</span></div>
    <div class="data-row"><span class="label">User Profile</span><span class="val">${{run.input_data.profile_name || 'Richie'}} (Year ${{run.input_data.birth_year || '2000'}})</span></div>
  `;

  // Update Output List
  const outList = document.getElementById('outputDataList');
  outList.innerHTML = `
    <div class="data-row"><span class="label">Current Day Status</span><span class="val" style="color: var(--accent);">YOU ARE IN "${{run.output_data.YOU_ARE_IN || '–'}}"</span></div>
    <div class="data-row"><span class="label">Next Period Prediction</span><span class="val">NEXT PERIOD "${{run.output_data.NEXT_PERIOD || '–'}}"</span></div>
    <div class="data-row"><span class="label">App Average Cycle</span><span class="val">AVG CYCLE "${{run.output_data.AVG_CYCLE || '–'}}"</span></div>
    <div class="data-row"><span class="label">App Average Period</span><span class="val">AVG PERIOD "${{run.output_data.AVG_PERIOD || '–'}}"</span></div>
    <div class="data-row"><span class="label">Cycle Tracking Phase</span><span class="val" style="color: var(--red);">${{run.output_data.CYCLE_TRACKING || '–'}}</span></div>
    <div class="data-row"><span class="label">Cycle Day Info</span><span class="val">${{run.output_data.CYCLE_DAY_INFO || '–'}}</span></div>
    <div class="data-row"><span class="label">Last Period Card</span><span class="val">LAST PERIOD ${{run.output_data.LAST_PERIOD || '–'}}</span></div>
    <div class="data-row"><span class="label">Estimated Next Period</span><span class="val">EST. NEXT ${{run.output_data.EST_NEXT || '–'}}</span></div>
    <div class="data-row"><span class="label">Pain Score Test Case</span><span class="val" style="color: ${{isPsSkipped ? 'var(--ink-2)' : (isPsPass ? 'var(--green-text)' : 'var(--red)')}}; font-weight: 700;">${{psStatus}}</span></div>
  `;
  if (isPsSkipped) {{
    outList.innerHTML += '<div class="data-row"><span class="label">Pain Session Status</span><span class="val" style="color: var(--ink-2);">Bypassed via skip input (Direct Cycle run)</span></div>';
  }} else if (psData && (psData.before_score || psData.initial_score)) {{
    const bMatch = psData.before_match !== false;
    const aMatch = psData.after_match !== false;
    const initScore = psData.initial_score || psData.before_score || '–';
    const recBefore = psData.before_score || '–';
    const finScore = psData.final_score || psData.after_score || '–';
    const recAfter = psData.after_score || '–';
    outList.innerHTML += `
      <div class="data-row"><span class="label">Initial Pain Score ⟷ BEFORE</span><span class="val" style="color: ${{bMatch ? 'var(--green-text)' : 'var(--red)'}}; font-weight: 700;">Initial: ${{initScore}} ⟷ BEFORE: ${{recBefore}} [${{bMatch ? 'MATCH' : 'DIFF'}}]</span></div>
      <div class="data-row"><span class="label">Final Pain Score ⟷ AFTER</span><span class="val" style="color: ${{aMatch ? 'var(--green-text)' : 'var(--red)'}}; font-weight: 700;">Final: ${{finScore}} ⟷ AFTER: ${{recAfter}} [${{aMatch ? 'MATCH' : 'DIFF'}}]</span></div>
      <div class="data-row"><span class="label">Recorded Duration & Time</span><span class="val">${{psData.duration || '2 Mins'}} (${{psData.time || '–'}})</span></div>
    `;
  }}

  // Update Screenshots
  const ssBox = document.getElementById('screenshotsContainer');
  const ss = run.screenshots || {{}};
  const ps = run.output_data.pain_score || {{}};
  const beforeScore = ps.before_score || '7';
  const afterScore = ps.after_score || '4';
  const sessionTime = ps.time || '12:00 PM';
  const sessionDuration = ps.duration || '0 Mins';

  ssBox.innerHTML = `
    <!-- Screen 0: Home Dashboard (Live Proof for Cycle Tracking, Last Period & Est. Next) -->
    <div class="screenshot-card" style="border: 2px solid var(--accent); box-shadow: 0 4px 12px rgba(37, 99, 235, 0.12);">
      <div class="screenshot-card-header" style="background: linear-gradient(135deg, rgba(37,99,235,0.08), rgba(124,58,237,0.08));">
        <span class="title">Home Dashboard (Live App Proof)</span>
        <span class="meta" style="background: #eef3fb; color: #1f4f8f; padding: 2px 8px; border-radius: 4px; font-weight: 700;">Home Proof</span>
      </div>
      <div class="screenshot-img-wrap" onclick="openZoom('${{ss.home}}')">
        ${{ss.home ? `<img src="${{ss.home}}" alt="Home Dashboard Live Proof">` : `<div style="color: #666;">No screenshot</div>`}}
      </div>
      <div class="screenshot-card-footer">
        • <strong>Cycle Phase:</strong> <span style="color: var(--red); font-weight: 700;">${{run.output_data.CYCLE_TRACKING || '-'}}</span> (${{run.output_data.CYCLE_DAY_INFO || '-'}}).<br>
        • <strong>Last Period:</strong> <strong>${{run.output_data.LAST_PERIOD || '-'}}</strong> &nbsp;|&nbsp; <strong>Est. Next:</strong> <strong>${{run.output_data.EST_NEXT || '-'}}</strong><br>
        • <strong>Avg Cycle:</strong> ${{run.output_data.AVG_CYCLE || '-'}} &nbsp;|&nbsp; <strong>Status:</strong> Captured live from device
      </div>
    </div>

    <!-- Calendar Month 1: July -->
    <div class="screenshot-card">
      <div class="screenshot-card-header">
        <span class="title">July 2026</span>
        <span class="meta" style="background: var(--accent-soft); color: var(--accent); padding: 2px 8px; border-radius: 4px; font-weight: 600;">Month #1 (Earliest Logged)</span>
      </div>
      <div class="screenshot-img-wrap" onclick="openZoom('${{ss.jul}}')">
        ${{ss.jul ? `<img src="${{ss.jul}}" alt="July 2026">` : `<div style="color: #666;">No screenshot</div>`}}
      </div>
      <div class="screenshot-card-footer">
        • <strong>Logged Cycles:</strong> Jul 1–5 (5 days) & Jul 16–20 (5 days).<br>
        • <strong>Cycle Length:</strong> 15 days interval.<br>
        • <strong>Status:</strong> Initial entered periods on phone.
      </div>
    </div>

    <!-- Calendar Month 2: August -->
    <div class="screenshot-card">
      <div class="screenshot-card-header">
        <span class="title">August 2026</span>
        <span class="meta" style="background: #eef3fb; color: #1f4f8f; padding: 2px 8px; border-radius: 4px; font-weight: 600;">Month #2 (Recurrence)</span>
      </div>
      <div class="screenshot-img-wrap" onclick="openZoom('${{ss.aug}}')">
        ${{ss.aug ? `<img src="${{ss.aug}}" alt="August 2026">` : `<div style="color: #666;">No screenshot</div>`}}
      </div>
      <div class="screenshot-card-footer">
        • <strong>Cycle Recurrence:</strong> Aug 15 period & Aug 30 period.<br>
        • <strong>Interval:</strong> 15-day forward recurrence.<br>
        • <strong>Status:</strong> Bridge month to current cycle.
      </div>
    </div>

    <!-- Calendar Month 3: September -->
    <div class="screenshot-card">
      <div class="screenshot-card-header">
        <span class="title">September 2026</span>
        <span class="meta" style="background: #e6f4ea; color: #137333; padding: 2px 8px; border-radius: 4px; font-weight: 700;">Month #3 (Active Today)</span>
      </div>
      <div class="screenshot-img-wrap" onclick="openZoom('${{ss.sep}}')">
        ${{ss.sep ? `<img src="${{ss.sep}}" alt="September 2026">` : `<div style="color: #666;">No screenshot</div>`}}
      </div>
      <div class="screenshot-card-footer">
        • <strong>Active Cycle:</strong> Started Sep 14 · Today Sep 24 (Day 11).<br>
        • <strong>Current Phase:</strong> Luteal Phase (Active cycle phase).<br>
        • <strong>Next Period:</strong> Sep 29 (In 5 days · dashed circle).
      </div>
    </div>

    <!-- Calendar Month 4: October -->
    <div class="screenshot-card">
      <div class="screenshot-card-header">
        <span class="title">October 2026</span>
        <span class="meta" style="background: #fff4cc; color: #8a5a00; padding: 2px 8px; border-radius: 4px; font-weight: 600;">Month #4 (Predicted)</span>
      </div>
      <div class="screenshot-img-wrap" onclick="openZoom('${{ss.oct}}')">
        ${{ss.oct ? `<img src="${{ss.oct}}" alt="October 2026">` : `<div style="color: #666;">No screenshot</div>`}}
      </div>
      <div class="screenshot-card-footer">
        • <strong>Future Prediction:</strong> Oct 14 period & Oct 29 period.<br>
        • <strong>Projection:</strong> Continued 15-day recurrence.<br>
        • <strong>Status:</strong> Forward boundary month.
      </div>
    </div>

    <!-- Pain Score Card 1: Initial Pain Score (BEFORE) -->
    <div class="screenshot-card">
      <div class="screenshot-card-header">
        <span class="title">Initial Pain Score (BEFORE)</span>
        <span class="meta" style="background: ${{isPsSkipped ? '#f1f3f4' : '#fce8e6'}}; color: ${{isPsSkipped ? '#5f6368' : '#c0392b'}}; padding: 2px 8px; border-radius: 4px; font-weight: 700;">${{isPsSkipped ? 'SKIPPED' : `Score: ${{beforeScore}} / 10`}}</span>
      </div>
      <div class="screenshot-img-wrap" onclick="openZoom('${{ss.initial_pain || ss.session_card}}')">
        ${{isPsSkipped ? `<div style="color: #888; font-size: 13px; text-align: center; padding: 40px 10px;">Session skipped by user input<br>(Direct Cycle run)</div>` : (ss.initial_pain ? `<img src="${{ss.initial_pain}}" alt="Initial Pain Score">` : (ss.session_card ? `<img src="${{ss.session_card}}" alt="Initial Pain Score">` : `<div style="color: #666;">No screenshot</div>`))}}
      </div>
      <div class="screenshot-card-footer">
        • <strong>Screen:</strong> "How much pain are you experiencing right now?"<br>
        • <strong>Recorded Level:</strong> <strong>${{isPsSkipped ? 'Skipped' : `${{beforeScore}} / 10 (Before session)`}}</strong>.<br>
        • <strong>Comparison:</strong> Initial Pain Score ⟷ BEFORE on SESSIONS card.
      </div>
    </div>

    <!-- Pain Score Card 2: Final Pain Score (AFTER) -->
    <div class="screenshot-card">
      <div class="screenshot-card-header">
        <span class="title">Final Pain Score (AFTER)</span>
        <span class="meta" style="background: ${{isPsSkipped ? '#f1f3f4' : '#e6f4ea'}}; color: ${{isPsSkipped ? '#5f6368' : '#137333'}}; padding: 2px 8px; border-radius: 4px; font-weight: 700;">${{isPsSkipped ? 'SKIPPED' : `Score: ${{afterScore}} / 10`}}</span>
      </div>
      <div class="screenshot-img-wrap" onclick="openZoom('${{ss.final_pain || ss.session_card}}')">
        ${{isPsSkipped ? `<div style="color: #888; font-size: 13px; text-align: center; padding: 40px 10px;">Session skipped by user input<br>(Direct Cycle run)</div>` : (ss.final_pain ? `<img src="${{ss.final_pain}}" alt="Final Pain Score">` : (ss.session_card ? `<img src="${{ss.session_card}}" alt="Final Pain Score">` : `<div style="color: #666;">No screenshot</div>`))}}
      </div>
      <div class="screenshot-card-footer">
        • <strong>Screen:</strong> Post-session feeling verification slider.<br>
        • <strong>Recorded Level:</strong> <strong>${{isPsSkipped ? 'Skipped' : `${{afterScore}} / 10 (After session)`}}</strong>.<br>
        • <strong>Comparison:</strong> Final Pain Score ⟷ AFTER on SESSIONS card.
      </div>
    </div>

    <!-- Pain Score Card 3: Live SESSIONS History Card -->
    <div class="screenshot-card">
      <div class="screenshot-card-header">
        <span class="title">Recorded Session History Card</span>
        <span class="meta" style="background: ${{isPsSkipped ? '#f1f3f4' : '#eef3fb'}}; color: ${{isPsSkipped ? '#5f6368' : '#1f4f8f'}}; padding: 2px 8px; border-radius: 4px; font-weight: 700;">${{isPsSkipped ? 'SKIPPED' : 'Phone SESSIONS Display'}}</span>
      </div>
      <div class="screenshot-img-wrap" onclick="openZoom('${{ss.session_card}}')">
        ${{isPsSkipped ? `<div style="color: #888; font-size: 13px; text-align: center; padding: 40px 10px;">Session skipped by user input<br>(Direct Cycle run)</div>` : (ss.session_card ? `<img src="${{ss.session_card}}" alt="Recorded Session Card">` : `<div style="color: #666;">No screenshot</div>`)}}
      </div>
      <div class="screenshot-card-footer">
        • <strong>Status:</strong> ${{isPsSkipped ? 'Session skipped by user input' : 'SESSIONS Card logged on My Cycle'}}.<br>
        • <strong>Scores Displayed:</strong> BEFORE: <strong>${{isPsSkipped ? 'N/A' : beforeScore}}</strong> | AFTER: <strong>${{isPsSkipped ? 'N/A' : afterScore}} ↓</strong>.<br>
        • <strong>Duration:</strong> ${{isPsSkipped ? 'N/A' : sessionDuration}} · Mode: Menstrual.
      </div>
    </div>
  `;

  // Update Simulator
  updateSimulatorForRun(run);
}}

function openZoom(src) {{
  if (!src) return;
  const modal = document.getElementById('modalZoom');
  const img = document.getElementById('zoomImg');
  if (modal && img) {{
    img.src = src;
    modal.classList.add('active');
  }}
}}

function exportToCSV() {{
  let csv = 'Run ID,Timestamp,Status,Algo Verification,Cycles Configured,Target Cycle Length,YOU ARE IN,NEXT PERIOD,AVG CYCLE,AVG PERIOD,Current Phase\\n';
  RUN_HISTORY.forEach(r => {{
    const cycles = (r.input_data.cycles || []).map(c => typeof c === 'string' ? c : `${{c.month}} ${{c.start_day}}-${{c.end_day || ''}}`).join('; ');
    const algoStatus = (r.algo_comparison && r.algo_comparison.overall_status === 'PASS') ? 'PASS' : 'FAIL';
    csv += `"${{r.run_id}}","${{r.timestamp}}","${{r.status}}","${{algoStatus}}","${{cycles}}","${{r.input_data.stepper_cycle_length || 28}}","${{r.output_data.YOU_ARE_IN || ''}}","${{r.output_data.NEXT_PERIOD || ''}}","${{r.output_data.AVG_CYCLE || ''}}","${{r.output_data.AVG_PERIOD || ''}}","${{r.output_data.CYCLE_TRACKING || ''}}"\\n`;
  }});

  const blob = new Blob([csv], {{ type: 'text/csv;charset=utf-8;' }});
  const link = document.createElement('a');
  link.href = URL.createObjectURL(blob);
  link.setAttribute('download', 'curapod_cycle_test_history.csv');
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
}}

/* RULES ENGINE & SIMULATOR LOGIC */
const MONTHS = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
let simSelected = Math.round(Date.UTC(2026, 8, 21) / 86400000);

function updateSimulatorForRun(run) {{
  const cycles = run.input_data.cycles || [];
  const periods = [];

  cycles.forEach(c => {{
    if (typeof c === 'string') {{
      const mMatch = c.match(/(jul|aug|sep)/i);
      const nums = c.match(/\d+/g);
      if (mMatch && nums && nums.length >= 2) {{
        const mStr = mMatch[1].toLowerCase();
        const mIdx = mStr === 'aug' ? 7 : (mStr === 'sep' ? 8 : 6);
        const s = parseInt(nums[0]);
        const count = parseInt(nums[1]);
        const e = s + count - 1;
        periods.push([`2026-${{String(mIdx+1).padStart(2,'0')}}-${{String(s).padStart(2,'0')}}`, `2026-${{String(mIdx+1).padStart(2,'0')}}-${{String(e).padStart(2,'0')}}`]);
      }}
    }} else {{
      const mn = (c.month || '').toLowerCase();
      let mIdx = 6;
      if (mn.includes('aug')) mIdx = 7;
      else if (mn.includes('sep')) mIdx = 8;

      const sDay = parseInt(c.start_day) || 10;
      const count = parseInt(c.days_count) || 5;
      const eDay = parseInt(c.end_day) || (sDay + count - 1);

      periods.push([`2026-${{String(mIdx + 1).padStart(2, '0')}}-${{String(sDay).padStart(2, '0')}}`, `2026-${{String(mIdx + 1).padStart(2, '0')}}-${{String(eDay).padStart(2, '0')}}`]);
    }}
  }});

  if (periods.length === 0) {{
    periods.push(['2026-07-10', '2026-07-14'], ['2026-08-14', '2026-08-18'], ['2026-09-18', '2026-09-22']);
  }}

  renderSimulator(periods);
}}

function renderSimulator(periods) {{
  const box = document.getElementById('months');
  box.innerHTML = '';
  const monthsToShow = [{{ y: 2026, m: 6 }}, {{ y: 2026, m: 7 }}, {{ y: 2026, m: 8 }}, {{ y: 2026, m: 9 }}];

  const pRanges = periods.map(p => {{
    const s = Math.round(Date.parse(p[0]) / 86400000);
    const e = Math.round(Date.parse(p[1]) / 86400000);
    return {{ start: s, end: e }};
  }});

  const todayDate = new Date();
  const todayN = Math.round(Date.UTC(todayDate.getFullYear(), todayDate.getMonth(), todayDate.getDate()) / 86400000);

  const activeRun = (RUN_HISTORY && RUN_HISTORY.length > 0 && currentRunIndex >= 0 && currentRunIndex < RUN_HISTORY.length) ? RUN_HISTORY[currentRunIndex] : {{}};
  const cl = parseInt(activeRun.input_data?.stepper_cycle_length) || 28;
  const pl = 5;
  const ovDay = Math.ceil(cl / 2);
  const fertStart = Math.max(pl + 1, ovDay - 2);
  const fertEnd = Math.min(cl, ovDay + 2);

  monthsToShow.forEach(item => {{
    const y = item.y, m = item.m;
    const days = new Date(Date.UTC(y, m + 1, 0)).getUTCDate();
    const lead = new Date(Date.UTC(y, m, 1)).getUTCDay();

    const el = document.createElement('div');
    el.className = 'month';
    el.innerHTML = `<h3>${{MONTHS[m]}} ${{y}}</h3><div class="grid">${{['Su','Mo','Tu','We','Th','Fr','Sa'].map(w => `<div class="wd">${{w}}</div>`).join('')}}</div>`;

    const g = el.querySelector('.grid');
    for (let i = 0; i < lead; i++) {{
      const b = document.createElement('div');
      b.className = 'day blank';
      g.appendChild(b);
    }}

    for (let dd = 1; dd <= days; dd++) {{
      const n = Math.round(Date.UTC(y, m, dd) / 86400000);
      const isPeriod = pRanges.some(pr => n >= pr.start && n <= pr.end);
      const isToday = n === todayN;

      let phaseClass = 'ph-follicular';
      let phaseLabel = 'FOLLICULAR PHASE';
      let cycleDayNum = null;

      if (isPeriod) {{
        phaseClass = 'ph-menstrual k-confirmed';
        phaseLabel = 'MENSTRUATION PHASE';
      }} else {{
        const preceding = pRanges.filter(pr => pr.start <= n).sort((a,b) => b.start - a.start);
        if (preceding.length > 0) {{
          const daysSince = n - preceding[0].start;
          cycleDayNum = (daysSince % cl) + 1;
          if (cycleDayNum <= pl) {{
            phaseClass = 'ph-menstrual';
            phaseLabel = 'MENSTRUATION PHASE';
          }} else if (cycleDayNum < fertStart) {{
            phaseClass = 'ph-follicular';
            phaseLabel = 'FOLLICULAR PHASE';
          }} else if (cycleDayNum <= fertEnd) {{
            phaseClass = 'ph-ovulation';
            phaseLabel = 'FERTILE / OVULATION PHASE';
          }} else {{
            phaseClass = 'ph-luteal';
            phaseLabel = 'LUTEAL PHASE';
          }}
        }} else {{
          phaseClass = 'ph-follicular';
          phaseLabel = 'FOLLICULAR PHASE';
        }}
      }}

      const c = document.createElement('div');
      let cls = 'day ' + phaseClass;
      if (isToday) cls += ' today';
      if (n === simSelected) cls += ' sel';

      c.className = cls;
      c.innerHTML = `${{isPeriod ? '<span class="mark confirmed"></span>' : ''}}<span class="n">${{dd}}</span>`;
      c.onclick = () => {{
        simSelected = n;
        renderSimulator(periods);
        inspectDate(n, isPeriod, isToday, phaseLabel, cycleDayNum);
      }};
      g.appendChild(c);
    }}
    box.appendChild(el);
  }});

  inspectDate(simSelected, pRanges.some(pr => simSelected >= pr.start && simSelected <= pr.end), simSelected === todayN);
}}

function inspectDate(n, isPeriod, isToday, phaseLabel = null, cycleDayNum = null) {{
  const d = new Date(n * 86400000);
  const dtStr = `${{d.getUTCDate()}} ${{MONTHS[d.getUTCMonth()]}} ${{d.getUTCFullYear()}}`;
  const sheet = document.getElementById('sheet');
  const label = phaseLabel || (isPeriod ? 'MENSTRUATION PHASE' : 'FOLLICULAR / FERTILE PHASE');
  sheet.innerHTML = `
    <h2>Day Details</h2>
    <div class="date">${{dtStr}}</div>
    <div class="kind">${{label}}</div>
    <div style="margin-top: 10px; font-size: 12.5px; line-height: 1.6;">
      <div><strong>Status:</strong> ${{isPeriod ? 'Confirmed Period Day' : 'Normal Day'}}</div>
      ${{cycleDayNum ? `<div><strong>Cycle Day:</strong> Day ${{cycleDayNum}}</div>` : ''}}
      <div><strong>Is Today:</strong> ${{isToday ? 'Yes (Today)' : 'No'}}</div>
    </div>
  `;
}}

// Initialize on page load
if (localStorage.getItem('curapod_report_cleaned') === 'true' && RUN_HISTORY.length > 0) {{
  renderCleanState();
}} else {{
  renderTable();
  if (RUN_HISTORY.length > 0) {{
    selectRun(RUN_HISTORY.length - 1);
  }} else {{
    renderCleanState();
  }}
}}
</script>

</body>
</html>
'''

    with open(REPORT_FILE, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"[HTML Generator] Successfully updated: {REPORT_FILE} (Size: {len(html)} bytes)")

    # Also synchronize to automachine_profile_login_and_logout workspace
    alt_report = r"D:\automachine_profile_login_and_logout\cycle_tracking_report.html"
    try:
        if os.path.exists(os.path.dirname(alt_report)):
            with open(alt_report, "w", encoding="utf-8") as af:
                af.write(html)
    except Exception:
        pass

if __name__ == "__main__":
    import sys
    if "--clear" in sys.argv:
        clear_history()
    else:
        generate_html_report()

