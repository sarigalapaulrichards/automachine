"""
run_excel_suite.py
Executes the full Curapod-M test suite driven by the Excel sheet row-by-row:
  Location: C:\\Users\\Admin\\Downloads\\test_curapod_m_dates.xlsx

Workflow per iteration:
1. Parse configured cycle dates, cycle length, and SKIP flag from Excel.
2. Complete onboarding (Login, Terms, Profile info, Height/Weight, Calendar date selection, Cycle length stepper, Pain pattern, Shapes).
3. Verify Home Dashboard metrics.
4. Pain Relief Session:
   - If Column 4 == 'SKIP': Bypasses pod connection, session start, 2-minute timer, and pain sliders.
   - If not skipped: Runs full pod connection and 2-minute pain session verification.
5. Navigate to My Cycle tab:
   - Extract 'YOU ARE IN', 'NEXT PERIOD', 'AVG CYCLE', 'AVG PERIOD'.
   - Dynamically capture all 4 calendar months (Jul, Aug, Sep, Oct) from the phone display.
6. Delete account from Profile screen to reset back to Welcome screen for the next iteration (Photo step excluded).
7. Execute 3-way parallel algorithm verification (App Live vs First Algorithm vs Second Algorithm).
8. Record test run into test_history.json and update cycle_tracking_report.html.
"""

import os
import sys
import time
import argparse
import openpyxl
from datetime import date

# Add workspace and test directory to path
WORKSPACE = os.path.dirname(os.path.abspath(__file__))
TEST_DIR = os.path.join(WORKSPACE, "test")
if WORKSPACE not in sys.path:
    sys.path.insert(0, WORKSPACE)
if TEST_DIR not in sys.path:
    sys.path.insert(0, TEST_DIR)

from appium import webdriver
from appium.options.android import UiAutomator2Options

import test_pain_tracking as tpt
from report_manager import clear_history, record_test_run
from Algo1 import run_algo1 as run_first_algo
from second_cycle_algorithm import run_second_cycle_algorithm as run_second_algo, compare_all_three

EXCEL_PATH = os.environ.get("EXCEL_PATH", tpt.EXCEL_PATH)


def load_excel_iterations(excel_path=EXCEL_PATH):
    """
    Parses test iterations from the connected Excel file via test_pain_tracking parser.
    """
    return tpt.load_excel_iterations(excel_path)


# Dataset specified by user prompt:
# count | dates | cycle_length | status | close the app after the My Cycle page
USER_SPECIFIED_DATASET = [
    {"iteration_num": 1, "row_index": 1, "num_cycles": 1, "raw_dates": "Jul 13th 5days", "cycles": [{"month": "Jul 2026", "start_day": "13", "end_day": "17", "days_count": 5}], "cycle_length": 15, "skip_session": True, "close_app": True},
    {"iteration_num": 2, "row_index": 2, "num_cycles": 1, "raw_dates": "Jul 13th 5days", "cycles": [{"month": "Jul 2026", "start_day": "13", "end_day": "17", "days_count": 5}], "cycle_length": 16, "skip_session": True, "close_app": False},
    {"iteration_num": 3, "row_index": 3, "num_cycles": 1, "raw_dates": "Jul 13th 5days", "cycles": [{"month": "Jul 2026", "start_day": "13", "end_day": "17", "days_count": 5}], "cycle_length": 17, "skip_session": True, "close_app": True},
    {"iteration_num": 4, "row_index": 4, "num_cycles": 1, "raw_dates": "Jul 13th 5days", "cycles": [{"month": "Jul 2026", "start_day": "13", "end_day": "17", "days_count": 5}], "cycle_length": 18, "skip_session": True, "close_app": True},
    {"iteration_num": 5, "row_index": 5, "num_cycles": 1, "raw_dates": "Jul 13th 5days", "cycles": [{"month": "Jul 2026", "start_day": "13", "end_day": "17", "days_count": 5}], "cycle_length": 19, "skip_session": True, "close_app": True},
    {"iteration_num": 6, "row_index": 6, "num_cycles": 1, "raw_dates": "Jul 13th 5days", "cycles": [{"month": "Jul 2026", "start_day": "13", "end_day": "17", "days_count": 5}], "cycle_length": 20, "skip_session": True, "close_app": True},
    {"iteration_num": 7, "row_index": 7, "num_cycles": 1, "raw_dates": "Jul 13th 5days", "cycles": [{"month": "Jul 2026", "start_day": "13", "end_day": "17", "days_count": 5}], "cycle_length": 21, "skip_session": True, "close_app": True},
    {"iteration_num": 8, "row_index": 8, "num_cycles": 1, "raw_dates": "Jul 13th 5days", "cycles": [{"month": "Jul 2026", "start_day": "13", "end_day": "17", "days_count": 5}], "cycle_length": 22, "skip_session": True, "close_app": True},
    {"iteration_num": 9, "row_index": 9, "num_cycles": 1, "raw_dates": "Jul 13th 5days", "cycles": [{"month": "Jul 2026", "start_day": "13", "end_day": "17", "days_count": 5}], "cycle_length": 23, "skip_session": True, "close_app": False},
    {"iteration_num": 10, "row_index": 10, "num_cycles": 1, "raw_dates": "Jul 13th 5days", "cycles": [{"month": "Jul 2026", "start_day": "13", "end_day": "17", "days_count": 5}], "cycle_length": 24, "skip_session": True, "close_app": False},
    {"iteration_num": 11, "row_index": 11, "num_cycles": 1, "raw_dates": "Jul 13th 5days", "cycles": [{"month": "Jul 2026", "start_day": "13", "end_day": "17", "days_count": 5}], "cycle_length": 25, "skip_session": True, "close_app": False},
]


def create_appium_driver():
    options = UiAutomator2Options()
    options.platform_name = "Android"
    options.automation_name = "UiAutomator2"
    options.udid = tpt.DEV_PROFILE.udid
    options.set_capability("systemPort", tpt.DEV_PROFILE.system_port)
    options.app_package = tpt.APP_PACKAGE
    options.app_activity = tpt.APP_ACTIVITY
    options.no_reset = True
    options.auto_grant_permissions = True
    options.set_capability("forceAppLaunch", True)
    options.set_capability("appWaitPackage", "*")
    options.set_capability("newCommandTimeout", 7200)
    options.set_capability("ignoreHiddenApiPolicyError", True)

    appium_url = tpt.APPIUM_HOST
    print(f"[Appium] Connecting to Appium server at {appium_url} for {tpt.DEV_PROFILE.display_name} (SystemPort: {tpt.DEV_PROFILE.system_port})...")
    driver = webdriver.Remote(appium_url, options=options)
    driver.implicitly_wait(0)
    return driver


def run_single_iteration(driver, iteration_data):
    """
    Executes one full iteration from the Excel sheet.
    """
    iter_idx = iteration_data["iteration_num"]
    num_cycles = iteration_data["num_cycles"]
    cl = iteration_data["cycle_length"]
    cycles = iteration_data["cycles"]
    skip_session = iteration_data["skip_session"]

    print("\n" + "=" * 80)
    print(f"  EXECUTING EXCEL ITERATION #{iter_idx} (Cycles: {num_cycles}, Length: {cl} days, Skip Session: {skip_session})")
    print(f"  Dates: {iteration_data['raw_dates']}")
    print("=" * 80)

    tpt.CONVERSION_ISSUES.clear()
    tpt.SKIP_PAIN_SESSION = skip_session
    tpt.PROMPTED_SKIP_PAIN = True  # Avoid interactive console prompt

    tpt.CURRENT_RUN_DATA["inputs"] = {
        "profile_name": tpt.TEST_NAME,
        "birth_year": tpt.TEST_BIRTH_YEAR,
        "period_regularity": tpt.CYCLE_REGULARITY,
        "pain_onset": tpt.CYCLE_PAIN_ONSET,
        "pain_intensity": tpt.CYCLE_PAIN_INTENSITY,
        "stepper_cycle_length": cl,
        "num_cycles": num_cycles,
        "cycles": cycles
    }
    tpt.CURRENT_RUN_DATA["outputs"] = {}
    tpt.CURRENT_RUN_DATA["screenshots"] = {}

    try:
        # 1. Onboarding flow
        tpt.login_with_google(driver)
        tpt.accept_terms_and_privacy(driver)
        tpt.tap_skip_then_continues(driver)

        tpt.about_you_name_screen(driver)
        tpt.about_you_birth_year_screen(driver)

        tpt.quick_health_check_conditions(driver)
        tpt.height_screen_with_conversion_check(driver)
        tpt.weight_screen_with_conversion_check(driver)

        # 2. Cycle Selection driven by Excel inputs
        tpt.cycle_calendar_screen(driver, selections=cycles)
        tpt.cycle_length_screen(driver, target_days=cl)
        tpt.cycle_regularity_screen(driver)
        tpt.cycle_pain_pattern_screen(driver)
        tpt.cycle_shapes_screen(driver)

        # TEST CASE: 'Has your period started?' popup
        tpt.handle_period_started_popup(driver, iteration_data=iteration_data, timeout=12)

        # 3. Home Dashboard verification & extract Home metrics
        tpt.verify_dashboard_screen(driver)

        # 4. Bluetooth pod connection and pain score test case OR skip
        is_close_app = bool(iteration_data.get("close_app"))
        if not skip_session:
            b_score, a_score = 7, 2
            try:
                tpt.connect_curapod_pod(driver)
                b_score, a_score = tpt.run_pain_session(driver)
            except Exception as ps_err:
                print(f"  Warning: pain score session error: {ps_err}")
                tpt.CURRENT_RUN_DATA["outputs"]["pain_score"] = {"status": "FAIL", "error": str(ps_err)}

            tpt.go_to_cycle_tab(driver, suffix="before" if is_close_app else "")
            tpt.verify_pain_score_test_case(driver, expected_before=b_score, expected_after=a_score)
        else:
            print("\n" + "=" * 75)
            print(f"  [SKIP] PAIN RELIEF SESSION & PAIN SCORE SKIPPED FOR ITERATION #{iter_idx}")
            print("  Directly navigating to My Cycle screen...")
            print("=" * 75 + "\n")
            tpt.CURRENT_RUN_DATA["outputs"]["pain_score"] = {
                "status": "SKIPPED",
                "initial_score": "N/A",
                "before_score": "N/A",
                "before_match": True,
                "final_score": "N/A",
                "after_score": "N/A",
                "after_match": True,
                "duration": "SKIPPED",
                "time": "SKIPPED",
                "details": "Skipped via Excel input (Direct Cycle run)"
            }
            # Directly navigate to My Cycle tab: captures all 4 calendar months & reads dynamic metrics
            tpt.go_to_cycle_tab(driver, suffix="before" if is_close_app else "")

        # 5. App Lifecycle Persistence Check (Close app after My Cycle -> reopen -> compare Home & My Cycle)
        if iteration_data.get("close_app"):
            tpt.verify_app_lifecycle_persistence(driver, iter_idx=iter_idx)
        else:
            print(f"  [App Lifecycle] 'close the app after My Cycle page' = No (lifecycle restart skipped for Iter #{iter_idx})")
            tpt.CURRENT_RUN_DATA["outputs"]["app_lifecycle_persistence"] = {
                "close_app_executed": False,
                "overall_status": "SKIPPED (close_app=No)"
            }

        # 6. Reset for next iteration: navigate to Profile and delete account
        # (Photo step excluded as requested by user)
        tpt.go_to_profile(driver)
        tpt.delete_account(driver)

        # 6. Multi-Algorithm Parallel Verification
        first_res = run_first_algo(
            tpt.CURRENT_RUN_DATA["inputs"],
            tpt.CURRENT_RUN_DATA["outputs"],
            today_date=date.today()
        )
        second_res = run_second_algo(
            tpt.CURRENT_RUN_DATA["inputs"],
            tpt.CURRENT_RUN_DATA["outputs"],
            today_date=date.today()
        )
        cmp_3way = compare_all_three(
            tpt.CURRENT_RUN_DATA["outputs"],
            first_res,
            second_res
        )

        print("\n" + "=" * 75)
        print(f"  PARALLEL MULTI-ALGORITHM VERIFICATION: ITERATION #{iter_idx}")
        print("=" * 75)
        print(f"  Ours (App Live) vs First Algorithm  : [{first_res['overall_status']}]")
        print(f"  Ours (App Live) vs Second Algorithm : [{second_res['overall_status']}]")
        print(f"  First Algorithm vs Second Algorithm : [{cmp_3way['first_vs_second_status']}]")
        print("-" * 75)
        print(f"  {'Field':<15} | {'Ours (App)':<12} | {'First Algo':<12} | {'Second Algo':<12} | Status")
        print(f"  {'-'*71}")
        for row in cmp_3way.get("rows", []):
            st = "MATCH" if (row["ours_vs_first"] and row["ours_vs_second"] and row["first_vs_second"]) else "DIFF"
            print(f"  {row['field']:<15} | {str(row['ours_value']):<12} | {str(row['first_algo_value']):<12} | {str(row['second_algo_value']):<12} | [{st}]")
        print("=" * 75 + "\n")

        # 7. Record into HTML report
        run_id = record_test_run(
            status="PASSED",
            input_data=tpt.CURRENT_RUN_DATA["inputs"],
            output_data=tpt.CURRENT_RUN_DATA["outputs"],
            screenshots=tpt.CURRENT_RUN_DATA["screenshots"]
        )
        print(f"  -> SUCCESS: Iteration #{iter_idx} recorded as {run_id} in HTML report.\n")
        return True

    except Exception as e:
        print(f"  -> FAILED Iteration #{iter_idx}: {e}")
        try:
            record_test_run(
                status=f"FAILED: {e}",
                input_data=tpt.CURRENT_RUN_DATA["inputs"],
                output_data=tpt.CURRENT_RUN_DATA["outputs"],
                screenshots=tpt.CURRENT_RUN_DATA["screenshots"]
            )
        except Exception:
            pass

        # Attempt to recover by resetting to Welcome screen
        try:
            tpt.go_to_profile(driver)
            tpt.delete_account(driver)
        except Exception:
            pass
        return False


def main():
    parser = argparse.ArgumentParser(description="Run Curapod-M test suite driven by Excel sheet or User Dataset")
    parser.add_argument("--excel", default=EXCEL_PATH, help=f"Path to Excel file (default: {EXCEL_PATH})")
    parser.add_argument("--use-excel", action="store_true", help="Load test iterations from Excel instead of the default user prompt dataset")
    parser.add_argument("--start", type=int, default=1, help="Starting iteration number (1-based, default: 1)")
    parser.add_argument("--count", type=int, default=None, help="Number of iterations to run (default: all)")
    parser.add_argument("--row", type=int, default=None, help="Specific iteration number to run")
    parser.add_argument("--clear-history", action="store_true", help="Clear existing HTML report history (default: False, keeps and appends history)")
    args = parser.parse_args()

    print("\n" + "#" * 80)
    print("  CURAPOD-M AUTOMATED TEST SUITE EXECUTION")
    print(f"  Source: {'Excel File: ' + args.excel if args.use_excel else 'User Prompt Dataset (Jul 13th 5days, lengths 15..25, close_app matrix)'}")
    print("#" * 80)

    # 1. Parse iterations (User specified dataset by default or Excel if --use-excel)
    if args.use_excel:
        all_iterations = load_excel_iterations(args.excel)
        print(f"\n[Excel Parser] Successfully loaded {len(all_iterations)} test iterations from Excel.")
    else:
        all_iterations = USER_SPECIFIED_DATASET
        print(f"\n[User Dataset] Loaded {len(all_iterations)} test iterations matching user prompt:")
        for it in all_iterations:
            print(f"    - Iter #{it['iteration_num']}: {it['raw_dates']} | {it['cycle_length']} days | Skip: {it['skip_session']} | Close App: {it['close_app']}")

    if args.row:
        target_iterations = [it for it in all_iterations if it["iteration_num"] == args.row]
        if not target_iterations:
            print(f"Error: Iteration #{args.row} not found (available: 1 to {len(all_iterations)})")
            return
    else:
        start_idx = max(1, args.start) - 1
        end_idx = len(all_iterations) if args.count is None else min(len(all_iterations), start_idx + args.count)
        target_iterations = all_iterations[start_idx:end_idx]

    print(f"\n[Execution Plan] Selected {len(target_iterations)} iteration(s) to execute:")
    for it in target_iterations:
        print(f"  • Iteration #{it['iteration_num']}: {it['num_cycles']} cycles | {it['cycle_length']} days | Skip: {it['skip_session']} | Close App: {it.get('close_app', False)} | Dates: {it['raw_dates']}")

    # 2. Preserve existing history ledger (Do not delete data in HTML page - add down)
    if args.clear_history:
        print("\n[Report Cleanup] Clearing old test run data from HTML report as requested...")
        clear_history(backup=True)
    else:
        print("\n[Report Ledger] Preserving all existing test runs in HTML report (New runs will append below).")

    success_count = 0
    failure_count = 0
    driver = None

    def get_or_recreate_driver(drv):
        if drv is not None:
            try:
                drv.current_activity
                return drv
            except Exception:
                try:
                    drv.quit()
                except Exception:
                    pass
        print("\n[Appium] Connecting clean driver session...", flush=True)
        return create_appium_driver()

    try:
        # 4. Run loop across all target iterations
        for it in target_iterations:
            driver = get_or_recreate_driver(driver)
            success = run_single_iteration(driver, it)
            if success:
                success_count += 1
            else:
                failure_count += 1
                try:
                    driver.quit()
                except Exception:
                    pass
                driver = None

            time.sleep(3)

    finally:
        if driver:
            try:
                driver.quit()
            except Exception:
                pass

    print("\n" + "#" * 80)
    print("  EXCEL TEST SUITE EXECUTION SUMMARY")
    print("#" * 80)
    print(f"  Total Iterations Attempted: {len(target_iterations)}")
    print(f"  Passed: {success_count}")
    print(f"  Failed: {failure_count}")
    print(f"  HTML Report Updated: file:///d:/automachine/cycle_tracking_report.html")
    print("#" * 80 + "\n")


if __name__ == "__main__":
    main()
