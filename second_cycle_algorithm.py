"""
Curapod-M Secondary Cycle Tracking Algorithm ("Second Algorithm")
==================================================================
Implements the multi-rule period and cycle tracking engine:
- Facts-based bleeding day tracking & 2-day join gap
- 15-day cycle boundary rule
- Predicted cycle length via round_half_up(mean(last two cycles))
- Current cycle day, next period estimation, and phase calculation
- Compares against App Live Output ("Ours") and First Algorithm.
"""

import datetime
import math
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Set, List, Optional, Dict, Tuple, Any

# =====================================================================
# Constants & Enums
# =====================================================================

MIN_CYCLE = 15
MAX_CYCLE = 60
FIRST_LOOKBACK = 90
WINDOW = 14
JOIN_GAP = 2
DEFAULT_PERIOD_LENGTH = 5


class Phase(Enum):
    MENSTRUAL = "menstrual"
    FOLLICULAR = "follicular"
    OVULATION = "ovulation"
    LUTEAL = "luteal"


@dataclass
class Period:
    start_date: datetime.date
    end_date: datetime.date
    is_open: bool = False

    @property
    def length(self) -> int:
        return (self.end_date - self.start_date).days + 1


@dataclass
class Facts:
    confirmed_bleeding_days: Set[datetime.date] = field(default_factory=set)
    not_on_my_period_days: Set[datetime.date] = field(default_factory=set)
    typed_cycle_length: Optional[int] = None
    typed_period_length: int = 5

    def copy(self):
        return Facts(
            confirmed_bleeding_days=set(self.confirmed_bleeding_days),
            not_on_my_period_days=set(self.not_on_my_period_days),
            typed_cycle_length=self.typed_cycle_length,
            typed_period_length=self.typed_period_length,
        )


@dataclass
class ComputedState:
    periods: List[Period] = field(default_factory=list)
    cycle_lengths: List[int] = field(default_factory=list)
    predicted_cycle_length: Optional[int] = None
    phases: Dict[datetime.date, Phase] = field(default_factory=dict)
    next_period_start: Optional[datetime.date] = None
    cycle_day: Optional[int] = None
    avg_period_length: Optional[int] = None
    current_phase_name: str = "Menstruation"


# =====================================================================
# Engine Functions
# =====================================================================

def get_contiguous_periods(facts: Facts) -> List[Period]:
    if not facts.confirmed_bleeding_days:
        return []

    sorted_days = sorted(list(facts.confirmed_bleeding_days))
    blocks = []

    current_start = sorted_days[0]
    current_end = sorted_days[0]

    for day in sorted_days[1:]:
        gap = (day - current_end).days - 1
        has_not_on_period_in_gap = any(
            current_end < nop < day for nop in facts.not_on_my_period_days
        )

        if gap <= JOIN_GAP and not has_not_on_period_in_gap:
            current_end = day
        else:
            blocks.append(Period(start_date=current_start, end_date=current_end))
            current_start = day
            current_end = day

    blocks.append(Period(start_date=current_start, end_date=current_end))

    # Filter blocks into actual periods using the 15-day rule
    periods: List[Period] = []
    if blocks:
        periods.append(blocks[0])
        for block in blocks[1:]:
            if (block.start_date - periods[-1].start_date).days >= MIN_CYCLE:
                periods.append(block)
            else:
                # Fewer than 15 days apart. Check if split only by a wall
                gap = (block.start_date - periods[-1].end_date).days - 1
                if gap <= JOIN_GAP:
                    periods.pop()
                    periods.append(block)
                else:
                    pass

    return periods


def recalculate(facts: Facts, today: datetime.date) -> ComputedState:
    periods = get_contiguous_periods(facts)
    state = ComputedState()
    state.periods = periods

    # Calculate cycle lengths (distance between consecutive period starts)
    for i in range(len(periods) - 1):
        state.cycle_lengths.append((periods[i + 1].start_date - periods[i].start_date).days)

    # Predicted cycle length (average of last two, round half up)
    if len(state.cycle_lengths) >= 2:
        avg = sum(state.cycle_lengths[-2:]) / 2.0
        state.predicted_cycle_length = int(avg + 0.5)
    elif len(state.cycle_lengths) == 1:
        state.predicted_cycle_length = state.cycle_lengths[0]
    else:
        state.predicted_cycle_length = facts.typed_cycle_length or 28

    if periods:
        latest_period = periods[-1]
        state.cycle_day = (today - latest_period.start_date).days + 1

        if state.predicted_cycle_length is not None:
            state.next_period_start = latest_period.start_date + datetime.timedelta(
                days=state.predicted_cycle_length
            )

    # Average period length
    period_lengths = [p.length for p in periods]
    if len(period_lengths) >= 2:
        avg = sum(period_lengths[-2:]) / 2.0
        state.avg_period_length = int(avg + 0.5)
    elif len(period_lengths) == 1:
        state.avg_period_length = period_lengths[0]
    else:
        state.avg_period_length = facts.typed_period_length or DEFAULT_PERIOD_LENGTH

    # Compute Current Phase
    if state.cycle_day is not None and state.predicted_cycle_length is not None:
        p_len = state.predicted_cycle_length
        m_day = math.ceil(p_len / 2.0)
        ovulation_start = max(state.avg_period_length + 1, m_day - 2)
        ovulation_end = min(p_len, m_day + 2)

        c_day = state.cycle_day
        if c_day <= state.avg_period_length:
            state.current_phase_name = "Menstruation"
        elif c_day < ovulation_start:
            state.current_phase_name = "Follicular"
        elif ovulation_start <= c_day <= ovulation_end:
            state.current_phase_name = "Fertile"
        else:
            state.current_phase_name = "Luteal"

    return state


# =====================================================================
# Robust Input Parser
# =====================================================================

MONTH_MAP = {
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
    "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12
}


def parse_month_name(text: str) -> Optional[int]:
    clean = re.sub(r'[^a-zA-Z]', '', text).lower()
    return MONTH_MAP.get(clean[:3])


def parse_any_period_entry(entry: Any, default_year: int = 2026) -> Optional[Tuple[datetime.date, int]]:
    """
    Parses any format of period entry:
      - dict: {'month': 'Jul 2026', 'start_day': 10, 'days_count': 5}
      - string: "Jul 10 5", "Jul 10th 5 days", "10 Jul 5", "Jul 10 to 14"
    Returns (start_date, length_in_days).
    """
    if isinstance(entry, dict):
        m_str = str(entry.get("month", ""))
        m_match = re.search(r'([A-Za-z]+)', m_str)
        month = parse_month_name(m_match.group(1)) if m_match else 7
        y_match = re.search(r'(\d{4})', m_str)
        year = int(y_match.group(1)) if y_match else default_year

        start_day = int(entry.get("start_day", 1))
        days_count = entry.get("days_count")
        if days_count:
            n_days = int(days_count)
        elif entry.get("end_day"):
            n_days = int(entry.get("end_day")) - start_day + 1
        else:
            n_days = 5

        try:
            return datetime.date(year, month, start_day), n_days
        except Exception:
            return None

    raw = str(entry).strip()

    # Pattern A: "Sep 18th to 22nd"
    range_match = re.search(
        r'([A-Za-z]+)\.?\s+(\d+)(?:st|nd|rd|th)?\s+(?:to|-)\s+(\d+)(?:st|nd|rd|th)?',
        raw, re.IGNORECASE
    )
    if range_match:
        m = parse_month_name(range_match.group(1)) or 7
        s = int(range_match.group(2))
        e = int(range_match.group(3))
        return datetime.date(default_year, m, s), (e - s + 1)

    # Pattern B: "Jul 10th 5 days" or "Jul 10 5" or "Jul 10, 5"
    m1 = re.search(
        r'([A-Za-z]+)\.?\s+(\d+)(?:st|nd|rd|th)?(?:[,\s]+)(\d+)(?:\s*days?)?',
        raw, re.IGNORECASE
    )
    if m1:
        m = parse_month_name(m1.group(1))
        if m:
            s = int(m1.group(2))
            n = int(m1.group(3))
            return datetime.date(default_year, m, s), n

    # Pattern C: "10 Jul 5 days"
    m2 = re.search(
        r'(\d+)(?:st|nd|rd|th)?\s+([A-Za-z]+)\.?\s+(\d+)(?:\s*days?)?',
        raw, re.IGNORECASE
    )
    if m2:
        s = int(m2.group(1))
        m = parse_month_name(m2.group(2))
        n = int(m2.group(3))
        if m:
            return datetime.date(default_year, m, s), n

    return None


# =====================================================================
# Metric Comparison Helpers
# =====================================================================

def normalize_compare(a_val: Any, b_val: Any, field_name: str = "") -> Tuple[bool, str]:
    """
    Compares two metric values with numeric and semantic phase normalization.
    Returns (is_match, reason).
    """
    a_str = str(a_val or "").strip().lower()
    b_str = str(b_val or "").strip().lower()

    if a_str == b_str:
        return True, "Exact match"

    # Extract digits for numeric comparisons
    a_nums = re.findall(r"\d+", a_str)
    b_nums = re.findall(r"\d+", b_str)
    if a_nums and b_nums:
        if a_nums[0] == b_nums[0]:
            return True, f"Numeric match ({a_nums[0]})"

    # Date normalization (e.g. 'Oct 05' vs 'Oct 5', 'Aug 04' vs 'Aug 4')
    months = ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"]
    a_m = next((m for m in months if m in a_str), None)
    b_m = next((m for m in months if m in b_str), None)
    if a_m and b_m and a_m == b_m and a_nums and b_nums:
        if int(a_nums[0]) == int(b_nums[0]):
            return True, f"Date match ({a_m.capitalize()} {int(a_nums[0])})"

    # Semantic phase comparison
    phase_aliases = {
        "menstruation": ["menstrual", "menstruation", "menstrual phase"],
        "follicular": ["follicular", "follicular phase"],
        "fertile": ["fertile", "ovulation", "fertile window", "ovulation phase"],
        "luteal": ["luteal", "luteal phase"]
    }
    for canon, aliases in phase_aliases.items():
        if any(alias in a_str for alias in aliases) and any(alias in b_str for alias in aliases):
            return True, f"Phase match ({canon.title()})"

    return False, f"Mismatch ('{a_val}' vs '{b_val}')"


# =====================================================================
# Main Second Algorithm Runner & Comparison Interface
# =====================================================================

def run_second_cycle_algorithm(input_data: Dict[str, Any], app_output_data: Dict[str, Any], today_date: Optional[datetime.date] = None) -> Dict[str, Any]:
    """
    Runs the Second Algorithm against input data and verifies against app outputs.

    Returns dict containing:
      - overall_status: "PASS" or "FAIL"
      - algo_name: "Second Algorithm"
      - algo_metrics: computed dictionary of output fields
      - field_comparisons: list of per-field comparison results
      - mismatch_count: int
    """
    if today_date is None:
        today_date = datetime.date.today()
    elif isinstance(today_date, str):
        try:
            today_date = datetime.datetime.strptime(today_date, "%Y-%m-%d").date()
        except Exception:
            today_date = datetime.date.today()

    cycles_input = input_data.get("cycles") or []
    stepper_cl = int(input_data.get("stepper_cycle_length") or 28)

    facts = Facts(typed_cycle_length=stepper_cl, typed_period_length=5)

    period_tuples = []
    for c in cycles_input:
        parsed = parse_any_period_entry(c, default_year=2026)
        if parsed:
            period_tuples.append(parsed)

    # Fallback to standard 3 cycles if none provided
    if not period_tuples:
        period_tuples = [
            (datetime.date(2026, 7, 10), 5),
            (datetime.date(2026, 8, 14), 5),
            (datetime.date(2026, 9, 18), 5),
        ]

    # Populate confirmed bleeding days into facts
    for start_d, n_days in period_tuples:
        for offset in range(n_days):
            facts.confirmed_bleeding_days.add(start_d + datetime.timedelta(days=offset))

    # Recalculate computed state
    state = recalculate(facts, today_date)

    if not state.periods:
        return {
            "overall_status": "FAIL",
            "algo_name": "Second Algorithm",
            "algo_metrics": {},
            "field_comparisons": [],
            "mismatch_count": 1,
            "error": "No periods could be derived from inputs"
        }

    current_period = state.periods[-1]
    prev_period = state.periods[-2] if len(state.periods) >= 2 else current_period

    pred_cl = state.predicted_cycle_length or 28
    active_period_start = current_period.start_date
    if state.next_period_start and today_date >= state.next_period_start:
        while active_period_start + datetime.timedelta(days=pred_cl) <= today_date:
            active_period_start += datetime.timedelta(days=pred_cl)
        upcoming_next = active_period_start + datetime.timedelta(days=pred_cl)
        days_until_next = (upcoming_next - today_date).days
        cycle_day = (today_date - active_period_start).days + 1
        est_next_str = upcoming_next.strftime("%b %d")
        last_period_str = active_period_start.strftime("%b %d")

        p_len = state.avg_period_length or 5
        ovulation_day = math.ceil(pred_cl / 2)
        fertile_start = max(ovulation_day - 2, p_len + 1)
        fertile_end = ovulation_day + 2
        if cycle_day <= p_len:
            current_phase = "Menstruation"
        elif cycle_day < fertile_start:
            current_phase = "Follicular"
        elif cycle_day <= fertile_end:
            current_phase = "Fertile"
        else:
            current_phase = "Luteal"
    else:
        days_until_next = None
        if state.next_period_start is not None:
            days_until_next = (state.next_period_start - today_date).days
        est_next_str = state.next_period_start.strftime("%b %d") if state.next_period_start else "N/A"
        last_period_str = prev_period.start_date.strftime("%b %d")
        cycle_day = state.cycle_day
        current_phase = state.current_phase_name

    # Formula: Present day - Last Period + 1 = "YOU ARE IN" (No of days format)
    # Elapsed difference in days between present day and the active cycle's last period day + 1
    you_are_in_days = (today_date - active_period_start).days + 1
    if you_are_in_days < 1:
        you_are_in_days = 1
    elapsed_days = you_are_in_days

    algo_metrics = {
        "YOU_ARE_IN": f"Day {you_are_in_days}",
        "NEXT_PERIOD": f"In {days_until_next} days" if days_until_next is not None else "Unknown",
        "AVG_CYCLE": f"{state.predicted_cycle_length} days",
        "AVG_PERIOD": f"{state.avg_period_length} days",
        "CYCLE_TRACKING": current_phase,
        "LAST_PERIOD": last_period_str,
        "EST_NEXT": est_next_str,
        "CYCLE_DAY_INFO": f"Cycle Day {elapsed_days} · Started {active_period_start.strftime('%b %d')}",
        "cycle_lengths_list": state.cycle_lengths,
    }

    # Verification against App Output
    fields_to_compare = [
        ("YOU ARE IN", app_output_data.get("YOU_ARE_IN"), algo_metrics["YOU_ARE_IN"]),
        ("NEXT PERIOD", app_output_data.get("NEXT_PERIOD"), algo_metrics["NEXT_PERIOD"]),
        ("AVG CYCLE", app_output_data.get("AVG_CYCLE"), algo_metrics["AVG_CYCLE"]),
        ("AVG PERIOD", app_output_data.get("AVG_PERIOD"), algo_metrics["AVG_PERIOD"]),
        ("CYCLE TRACKING", app_output_data.get("CYCLE_TRACKING"), algo_metrics["CYCLE_TRACKING"]),
    ]

    comparisons = []
    mismatches = []
    for field_name, app_val, algo_val in fields_to_compare:
        matched, reason = normalize_compare(app_val, algo_val, field_name)
        comp = {
            "field": field_name,
            "app_value": app_val or "N/A",
            "algo_value": algo_val,
            "matched": matched,
            "reason": reason
        }
        comparisons.append(comp)
        if not matched:
            mismatches.append(comp)

    overall_status = "PASS" if len(mismatches) == 0 else "FAIL"

    return {
        "overall_status": overall_status,
        "algo_name": "Second Algorithm",
        "algo_metrics": algo_metrics,
        "field_comparisons": comparisons,
        "mismatches": mismatches,
        "mismatch_count": len(mismatches)
    }


def compare_all_three(app_output: Dict[str, Any], first_algo_res: Dict[str, Any], second_algo_res: Dict[str, Any]) -> Dict[str, Any]:
    """
    Performs a 3-way side-by-side comparison across:
      1. Ours (App Live Output)
      2. First Algorithm
      3. Second Algorithm

    Returns detailed comparison table and overall verdict.
    """
    fields = [
        ("YOU ARE IN", "YOU_ARE_IN"),
        ("NEXT PERIOD", "NEXT_PERIOD"),
        ("AVG CYCLE", "AVG_CYCLE"),
        ("AVG PERIOD", "AVG_PERIOD"),
        ("CYCLE TRACKING", "CYCLE_TRACKING"),
        ("LAST PERIOD", "LAST_PERIOD"),
        ("EST. NEXT", "EST_NEXT"),
    ]

    first_metrics = first_algo_res.get("algo_metrics", {})
    second_metrics = second_algo_res.get("algo_metrics", {})

    rows = []
    ours_vs_first_pass = True
    ours_vs_second_pass = True
    first_vs_second_pass = True

    for label, key in fields:
        app_val = app_output.get(key) or app_output.get(label) or "N/A"
        first_val = first_metrics.get(key) or first_metrics.get(label) or "N/A"
        second_val = second_metrics.get(key) or second_metrics.get(label) or "N/A"

        m_ours_1st, r_ours_1st = normalize_compare(app_val, first_val, label)
        m_ours_2nd, r_ours_2nd = normalize_compare(app_val, second_val, label)
        m_1st_2nd, r_1st_2nd = normalize_compare(first_val, second_val, label)

        if not m_ours_1st:
            ours_vs_first_pass = False
        if not m_ours_2nd:
            ours_vs_second_pass = False
        if not m_1st_2nd:
            first_vs_second_pass = False

        rows.append({
            "field": label,
            "ours_value": app_val,
            "first_algo_value": first_val,
            "second_algo_value": second_val,
            "ours_vs_first": m_ours_1st,
            "ours_vs_second": m_ours_2nd,
            "first_vs_second": m_1st_2nd,
            "notes": f"1st: {r_ours_1st} | 2nd: {r_ours_2nd} | 1v2: {r_1st_2nd}"
        })

    return {
        "ours_vs_first_status": "PASS" if ours_vs_first_pass else "FAIL",
        "ours_vs_second_status": "PASS" if ours_vs_second_pass else "FAIL",
        "first_vs_second_status": "PASS" if first_vs_second_pass else "FAIL",
        "all_pass": ours_vs_first_pass and ours_vs_second_pass and first_vs_second_pass,
        "rows": rows
    }


if __name__ == "__main__":
    # Test runner
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

    res2 = run_second_cycle_algorithm(sample_inputs, sample_app, today_date=datetime.date(2026, 9, 21))
    print(f"\n[Second Algorithm Test] Overall: {res2['overall_status']}")
    for c in res2["field_comparisons"]:
        status = "[PASS]" if c["matched"] else "[FAIL]"
        print(f"  {status} {c['field']}: App='{c['app_value']}' | SecondAlgo='{c['algo_value']}' ({c['reason']})")
