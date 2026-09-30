import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from datetime import date
from cycle_predictor_algorithm import run_parallel_cycle_algorithm as run_first
from second_cycle_algorithm import run_second_cycle_algorithm as run_second, compare_all_three

sample_inputs = {
    "cycles": ["Jul 10 5", "Aug 14th 5 days", "Sep 18th to 22nd"],
    "stepper_cycle_length": 28
}
sample_app = {
    "YOU_ARE_IN": "Day 4",
    "NEXT_PERIOD": "In 32 days",
    "AVG_CYCLE": "35 days",
    "AVG_PERIOD": "5 days",
    "CYCLE_TRACKING": "Menstruation",
    "LAST_PERIOD": "Aug 14",
    "EST_NEXT": "Oct 23"
}

r1 = run_first(sample_inputs, sample_app, today_date=date(2026, 9, 21))
r2 = run_second(sample_inputs, sample_app, today_date=date(2026, 9, 21))
cmp = compare_all_three(sample_app, r1, r2)

print("\n" + "=" * 70)
print(f"  3-WAY COMPARISON VERIFICATION: Overall All Match: {cmp['all_pass']}")
print(f"  Ours (App) vs First Algorithm : [{cmp['ours_vs_first_status']}]")
print(f"  Ours (App) vs Second Algorithm: [{cmp['ours_vs_second_status']}]")
print(f"  First Algo vs Second Algorithm: [{cmp['first_vs_second_status']}]")
print("=" * 70)
print(f"{'Field':<16} | {'Ours (App)':<14} | {'First Algo':<14} | {'Second Algo':<14} | {'Status':<10}")
print("-" * 75)
for row in cmp["rows"]:
    status = "MATCH" if (row["ours_vs_first"] and row["ours_vs_second"] and row["first_vs_second"]) else "DIFF"
    print(f"{row['field']:<16} | {row['ours_value']:<14} | {row['first_algo_value']:<14} | {row['second_algo_value']:<14} | [{status}]")
print("=" * 70 + "\n")

from report_manager import load_history, generate_html_report

history = load_history()
print(f"[Report Manager] Loaded {len(history)} runs from history:")
for r in history:
    print(f"  Run ID: {r['run_id']}")
    print(f"    - First Algo Status : {r['first_algo_comparison']['overall_status']}")
    print(f"    - Second Algo Status: {r['second_algo_comparison']['overall_status']}")
    print(f"    - 3-Way Match Status: {r['three_way_comparison']['all_pass']}")

generate_html_report(history)
print("[Report Manager] cycle_tracking_report.html successfully updated with 3-way multi-algorithm comparison!")
