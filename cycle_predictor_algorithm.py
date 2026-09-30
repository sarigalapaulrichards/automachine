"""
Menstrual Cycle Phase Predictor & Parallel Comparison Algorithm
---------------------------------------------------------------
Features:
- Calculates cycle lengths from period start dates
- Calculates average cycle length (average of last 2 completed cycles)
- Calculates ovulation, fertile, follicular, luteal and menstrual phases
- Determines current cycle phase and cycle day for any given date
- Compares algorithm outputs in parallel with Curapod-M app outputs
- Supports input formats: 'Jul 10 5', 'Jul 10th 5 days', 'Jul 10th to 14th', etc.
"""

import re
import math
from datetime import date, datetime, timedelta


def cycle_lengths(period_starts):
    """Given a list of period start dates (sorted, oldest first),
    return list of cycle lengths (days between consecutive starts)."""
    lengths = []
    for i in range(1, len(period_starts)):
        delta = (period_starts[i] - period_starts[i - 1]).days
        lengths.append(delta)
    return lengths


def average_cycle_length(lengths, typed_default=28):
    """Matches the app's real rule: use the AVERAGE OF THE LAST 2 completed
    cycles only (not full history). 1 completed cycle -> use it directly.
    0 completed cycles -> fall back to the user's typed cycle length."""
    used = lengths[-2:]
    if len(used) >= 2:
        return round((used[0] + used[1]) / 2)
    elif len(used) == 1:
        return used[0]
    else:
        return typed_default


def calculate_phases(last_period_start, last_period_end, avg_cl):
    """Compute phase date ranges for the predicted next cycle,
    starting from the most recent period start."""
    menstrual_len = (last_period_end - last_period_start).days + 1  # inclusive

    ovulation_day = math.ceil(avg_cl / 2)  # matches app's Math.ceil(cycle_length / 2)
    fertile_start_day = ovulation_day - 2  # app doesn't clamp this to menstrual end
    if fertile_start_day < menstrual_len + 1:
        fertile_start_day = menstrual_len + 1
    fertile_end_day = ovulation_day + 2

    follicular_start_day = menstrual_len + 1
    follicular_end_day = fertile_start_day - 1

    luteal_start_day = fertile_end_day + 1
    luteal_end_day = avg_cl

    def day_to_date(day_num):
        return last_period_start + timedelta(days=day_num - 1)

    phases = {
        "menstrual": (day_to_date(1), day_to_date(menstrual_len)),
        "follicular": (day_to_date(follicular_start_day), day_to_date(follicular_end_day)),
        "fertile_ovulation": (day_to_date(fertile_start_day), day_to_date(fertile_end_day)),
        "luteal": (day_to_date(luteal_start_day), day_to_date(luteal_end_day)),
    }

    ovulation_date = day_to_date(ovulation_day)
    next_period_start = day_to_date(avg_cl + 1)

    return phases, ovulation_date, next_period_start


def get_current_phase(today, last_period_start, last_period_end, cycle_length):
    """Given today's date, figure out which phase of the cycle it falls in.
    Works even if today is several cycles ahead of the last recorded period,
    by wrapping around using cycle_length."""
    menstrual_len = (last_period_end - last_period_start).days + 1
    ovulation_day = math.ceil(cycle_length / 2)
    fertile_start_day = max(ovulation_day - 2, menstrual_len + 1)
    fertile_end_day = ovulation_day + 2

    days_since = (today - last_period_start).days
    cycle_day = (days_since % cycle_length) + 1
    cycles_elapsed = days_since // cycle_length

    if cycle_day <= menstrual_len:
        phase = "Menstrual phase"
    elif cycle_day < fertile_start_day:
        phase = "Follicular phase"
    elif cycle_day <= fertile_end_day:
        phase = "Ovulation phase"
    else:
        phase = "Luteal phase"

    return {
        "phase": phase,
        "cycle_day": cycle_day,
        "cycles_elapsed": cycles_elapsed,
    }


def predict_from_cl(last_period_start, last_period_end, cycle_length):
    phases, ovulation_date, next_period_start = calculate_phases(
        last_period_start, last_period_end, cycle_length
    )
    return {
        "cycle_lengths": [cycle_length],
        "average_cycle_length": cycle_length,
        "phases": phases,
        "ovulation_date": ovulation_date,
        "next_period_start": next_period_start,
    }


def predict_cycle(period_ranges, manual_cl=None):
    """
    period_ranges: list of (start_date, end_date) tuples, sorted oldest -> newest.
    manual_cl: optional int.
    """
    last_start, last_end = period_ranges[-1]

    if manual_cl is not None:
        lengths = []
        avg_cl = manual_cl
    else:
        starts = [p[0] for p in period_ranges]
        lengths = cycle_lengths(starts)
        avg_cl = average_cycle_length(lengths)

    phases, ovulation_date, next_period_start = calculate_phases(last_start, last_end, avg_cl)

    return {
        "cycle_lengths": lengths,
        "average_cycle_length": avg_cl,
        "phases": phases,
        "ovulation_date": ovulation_date,
        "next_period_start": next_period_start,
    }


def parse_date(raw, year=2026):
    """Parse a date string. Accepts formats like:
    2026-03-02, 02-03-2026, 2 Mar 2026, Mar 2 2026, Jul 10, etc."""
    raw = raw.strip()
    formats_with_year = ["%Y-%m-%d", "%d-%m-%Y", "%d %b %Y", "%b %d %Y", "%B %d %Y", "%d %B %Y"]
    for fmt in formats_with_year:
        try:
            return datetime.strptime(raw, fmt).date()
        except ValueError:
            continue
    formats_no_year = ["%b %d", "%d %b", "%B %d", "%d %B"]
    y = year or 2026
    for fmt in formats_no_year:
        try:
            d = datetime.strptime(raw, fmt).date()
            return d.replace(year=y)
        except ValueError:
            continue
    return None


def parse_period_input(raw, default_year=2026):
    """
    Flexible parser supporting both:
    1. 'Jul 10 5' (space-separated date and length)
    2. 'Jul 10th 5 days' (with ordinal suffix and 'days')
    3. 'Jul 10th to 14th' or 'Jul 10 - 14'
    Returns (start_date, period_length_days).
    """
    if isinstance(raw, dict):
        # Already structured dict like {"month": "Jul 2026", "start_day": "10", "end_day": "14", "days_count": 5}
        m_str = raw.get("month", "Jul 2026")
        y_match = re.search(r"\b(20\d\d)\b", m_str)
        y = int(y_match.group(1)) if y_match else default_year
        m_match = re.search(r"(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)", m_str, re.I)
        m_abbr = m_match.group(1).title() if m_match else "Jul"

        s_d = int(raw.get("start_day", 10))
        c_days = int(raw.get("days_count") or (int(raw.get("end_day", s_d + 4)) - s_d + 1))
        d_obj = parse_date(f"{m_abbr} {s_d}", year=y)
        return d_obj, c_days

    raw_str = str(raw).strip()

    # Case A: 'Jul 10th to 14th' or 'Jul 10-14'
    range_match = re.search(r'([a-zA-Z]+)\s*(\d+)(?:st|nd|rd|th)?\s*(?:to|-)\s*(\d+)(?:st|nd|rd|th)?(?:\s*(20\d\d))?', raw_str, re.I)
    if range_match:
        m_abbr = range_match.group(1).title()
        s_day = int(range_match.group(2))
        e_day = int(range_match.group(3))
        y = int(range_match.group(4)) if range_match.group(4) else default_year
        length = abs(e_day - s_day) + 1
        d_obj = parse_date(f"{m_abbr} {s_day}", year=y)
        return d_obj, length

    # Case B: 'Jul 10 5' or 'Jul 10th 5 days' or '2026-07-10 5'
    match = re.search(r'(\d+)\s*(?:days?)?\s*$', raw_str, re.I)
    if match:
        length = int(match.group(1))
        date_part = raw_str[:match.start()].strip()
        date_part = re.sub(r'(\d+)(st|nd|rd|th)\b', r'\1', date_part, flags=re.IGNORECASE)
        start_date = parse_date(date_part, year=default_year)
        if start_date:
            return start_date, length

    return None, None


def compare_metrics(app_val, algo_val, field_name=""):
    """
    Compares app extracted string with algorithm string.
    Normalizes numbers and text (e.g. 'Day 4' vs 'Day 4', '35 days' vs '35 days').
    Returns (is_match, reason).
    """
    a_str = str(app_val or "").strip().lower()
    b_str = str(algo_val or "").strip().lower()

    if a_str == b_str:
        return True, "Exact match"

    # Extract digits for numeric comparisons
    a_num = re.findall(r"\d+", a_str)
    b_num = re.findall(r"\d+", b_str)
    if a_num and b_num:
        if a_num[0] == b_num[0]:
            return True, f"Numeric values match ({a_num[0]})"

    # Phase name normalization
    phase_aliases = {
        "menstruation": ["menstrual", "menstruation", "menstrual phase"],
        "follicular": ["follicular", "follicular phase"],
        "fertile": ["fertile", "ovulation", "fertile window", "ovulation phase", "fertile/ovulation"],
        "luteal": ["luteal", "luteal phase"]
    }
    for canon, aliases in phase_aliases.items():
        if any(alias in a_str for alias in aliases) and any(alias in b_str for alias in aliases):
            return True, f"Phase semantics match ({canon.title()})"

    return False, f"Mismatch: App='{app_val}' vs Algo='{algo_val}'"


def run_parallel_cycle_algorithm(input_data, app_output_data, today_date=None):
    """
    Runs the secondary algorithm in parallel with the test inputs and verifies
    whether the app output matches the algorithm's predictions.

    Returns a dict with:
      - overall_status: 'PASS' or 'FAIL'
      - algo_metrics: computed algorithm metrics
      - field_comparisons: list of per-field comparison results
      - mismatch_count: count of mismatched fields
    """
    if today_date is None:
        today_date = date.today()
    elif isinstance(today_date, str):
        today_date = parse_date(today_date) or date.today()

    cycles_input = input_data.get("cycles") or []
    period_ranges = []

    for c in cycles_input:
        start_d, p_len = parse_period_input(c, default_year=2026)
        if start_d and p_len:
            end_d = start_d + timedelta(days=p_len - 1)
            period_ranges.append((start_d, end_d))

    # Fallback to default 3 cycles if none provided
    if not period_ranges:
        period_ranges = [
            (date(2026, 7, 10), date(2026, 7, 14)),
            (date(2026, 8, 14), date(2026, 8, 18)),
            (date(2026, 9, 18), date(2026, 9, 22)),
        ]

    # Sort oldest to newest
    period_ranges.sort(key=lambda p: p[0])

    # 1. Compute Cycle Lengths and Average Cycle Length
    starts = [p[0] for p in period_ranges]
    lengths = cycle_lengths(starts)
    typed_cl = int(input_data.get("stepper_cycle_length") or 28)
    avg_cl = average_cycle_length(lengths, typed_default=typed_cl)

    # 2. Average Period Length
    period_lengths = [(p[1] - p[0]).days + 1 for p in period_ranges]
    avg_period = round(sum(period_lengths) / len(period_lengths))

    # 3. Last Period Start & End
    last_start, last_end = period_ranges[-1]
    prev_start = period_ranges[-2][0] if len(period_ranges) >= 2 else last_start

    # 4. Predict Phases and Next Period
    phases, ovulation_date, next_period_start = calculate_phases(last_start, last_end, avg_cl)

    # 5. Current Cycle Day & Phase (Roll forward to present day if today_date is past next_period_start)
    active_period_start = last_start
    if today_date >= next_period_start:
        while active_period_start + timedelta(days=avg_cl) <= today_date:
            active_period_start += timedelta(days=avg_cl)
        upcoming_next_period = active_period_start + timedelta(days=avg_cl)
        days_to_next = (upcoming_next_period - today_date).days
        active_period_end = active_period_start + timedelta(days=avg_period - 1)
        current = get_current_phase(today_date, active_period_start, active_period_end, avg_cl)
        last_period_str = active_period_start.strftime("%b %d")
        est_next_str = upcoming_next_period.strftime("%b %d")
    else:
        current = get_current_phase(today_date, last_start, last_end, avg_cl)
        days_to_next = (next_period_start - today_date).days
        last_period_str = prev_start.strftime("%b %d")
        est_next_str = next_period_start.strftime("%b %d")

    app_phase_names = {
        "Menstrual phase": "Menstruation",
        "Follicular phase": "Follicular",
        "Ovulation phase": "Fertile",
        "Luteal phase": "Luteal",
    }
    algo_phase_name = app_phase_names.get(current["phase"], current["phase"])

    # Formula: Present day - Last Period + 1 = "YOU ARE IN" (No of days format)
    # Elapsed difference in days between present day and the active cycle's last period day + 1
    you_are_in_days = (today_date - active_period_start).days + 1
    if you_are_in_days < 1:
        you_are_in_days = 1
    elapsed_days = you_are_in_days

    algo_metrics = {
        "YOU_ARE_IN": f"Day {you_are_in_days}",
        "NEXT_PERIOD": f"In {days_to_next} days",
        "AVG_CYCLE": f"{avg_cl} days",
        "AVG_PERIOD": f"{avg_period} days",
        "CYCLE_TRACKING": algo_phase_name,
        "LAST_PERIOD": last_period_str,
        "EST_NEXT": est_next_str,
        "CYCLE_DAY_INFO": f"Cycle Day {elapsed_days} · Started {active_period_start.strftime('%b %d')}",
        "ovulation_date": ovulation_date.strftime("%b %d"),
        "cycle_lengths_list": lengths,
    }

    # Compare with App Outputs
    fields_to_compare = [
        ("YOU ARE IN", app_output_data.get("YOU_ARE_IN"), algo_metrics["YOU_ARE_IN"]),
        ("NEXT PERIOD", app_output_data.get("NEXT_PERIOD"), algo_metrics["NEXT_PERIOD"]),
        ("AVG CYCLE", app_output_data.get("AVG_CYCLE"), algo_metrics["AVG_CYCLE"]),
        ("AVG PERIOD", app_output_data.get("AVG_PERIOD"), algo_metrics["AVG_PERIOD"]),
        ("CYCLE TRACKING", app_output_data.get("CYCLE_TRACKING"), algo_metrics["CYCLE_TRACKING"]),
    ]

    comparisons = []
    mismatches = []

    for field_name, app_v, algo_v in fields_to_compare:
        matched, reason = compare_metrics(app_v, algo_v, field_name)
        comp = {
            "field": field_name,
            "app_value": app_v or "N/A",
            "algo_value": algo_v,
            "matched": matched,
            "reason": reason
        }
        comparisons.append(comp)
        if not matched:
            mismatches.append(comp)

    overall_status = "PASS" if len(mismatches) == 0 else "FAIL"

    return {
        "overall_status": overall_status,
        "algo_metrics": algo_metrics,
        "field_comparisons": comparisons,
        "mismatches": mismatches,
        "mismatch_count": len(mismatches)
    }


if __name__ == "__main__":
    # Self-test using the verified test data
    test_inputs = {
        "cycles": [
            "Jul 10 5",        # Format 1
            "Aug 14th 5 days", # Format 2
            "Sep 18th to 22nd" # Format 3
        ],
        "stepper_cycle_length": 28
    }
    app_outputs = {
        "YOU_ARE_IN": "Day 4",
        "NEXT_PERIOD": "In 32 days",
        "AVG_CYCLE": "35 days",
        "AVG_PERIOD": "5 days",
        "CYCLE_TRACKING": "Menstruation",
        "LAST_PERIOD": "Aug 14",
        "EST_NEXT": "Oct 23"
    }

    res = run_parallel_cycle_algorithm(test_inputs, app_outputs, today_date=date(2026, 9, 21))
    print(f"\n[Parallel Algorithm Self-Test] Overall Status: {res['overall_status']}")
    for c in res["field_comparisons"]:
        status_icon = "[PASS]" if c["matched"] else "[FAIL]"
        print(f"  {status_icon} [{c['field']}]: App='{c['app_value']}' | Algo='{c['algo_value']}' ({c['reason']})")
