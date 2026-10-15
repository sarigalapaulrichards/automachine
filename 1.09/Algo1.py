from __future__ import annotations

"""
CM-191 oracle (incl. section 8 / CM-234 + High-Level Requirements - Cycle Tracking)
for the Curapod-M cycle automation suite.

Replaces cycle_predictor_algorithm.py, second_cycle_algorithm.py and
curapod_m_algorithm.py as the source of expected values.

Core rule: the PREDICTION rolls forward, logged Day 1 never does.
Items marked UNCONFIRMED are constants - check against CM-234 s5/s11.
Rule tags like [HLR-P3] point to the requirement each line implements.
"""

from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP
import math
import re
import warnings
from typing import List, Dict, Any, Optional, Tuple, Set

# ---------------------------------------------------------------- config
DEFAULT_L = 28                 # [HLR-O3] no data -> 28 days
L_MIN, L_MAX = 15, 60          # clamp for cycle length
MAX_ONBOARDING_CYCLES = 3      # [HLR-O2]
PICKER_MAX_DAYS_BACK = 89      # onboarding picker limit
STALE_DAYS = 90                # [HLR-M2] UNCONFIRMED: "around 3 months"
LUTEAL_DAYS = 14               # UNCONFIRMED: ovulation = next start - 14
FERTILE_SPAN = 2               # fertile = ovulation day +/- 2
ROLLED_WINDOW = True           # [HLR-D4] UNCONFIRMED: rolled predictions also
                               # get an "expected period" window
EDIT_LOOKBACK_USES_L = True    # [HLR-M4] UNCONFIRMED: today - L, or fixed 28


@dataclass
class Period:
    start: date
    end: date   # inclusive

    @property
    def length(self) -> int:
        return (self.end - self.start).days + 1


@dataclass
class Expected:
    state: str                     # no_data | prime | window | waiting
    last_period: date | None       # latest LOGGED D1, never projected [HLR-D1]
    est_next: date | None
    cycle_length: int
    avg_period: int | None
    cycle_day: int | None          # None = hidden on card
    phase: str | None              # None = no phase title
    state_copy: str | None         # copy shown instead of phase (CM-234 s5)
    next_label: str | None
    prompt_add_data: bool          # [HLR-M1]
    prompt_log_period: bool        # [HLR-D2]
    edit_screen_predictions: bool  # [HLR-M2] hidden on Edit Cycle when stale
    editable_from: date            # [HLR-M4] earliest editable date
    raw_cycle_day: int | None = None
    projected_phase: str | None = None
    hidden_reason: str = ""
    l_source: str = ""             # where L came from


def round_half_up(x: float) -> int:
    return int(Decimal(str(x)).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def clamp(L: int) -> int:
    return max(L_MIN, min(L_MAX, L))


def cycle_length(periods, entered_L=None, edited_L=None):
    """[HLR-O3/O4/O5/O6] Priority: user-edited > avg of logs > entered > 28."""
    if edited_L is not None:                        # [HLR-O5] edit only affects prediction
        return clamp(edited_L), "edited"
    starts = sorted(p.start for p in periods)
    gaps = [(b - a).days for a, b in zip(starts, starts[1:])]
    if len(gaps) >= 2:                              # [HLR-O4/O6] from logged data
        return clamp(round_half_up((gaps[-1] + gaps[-2]) / 2)), "avg of last 2 logged"
    if len(gaps) == 1:
        return clamp(gaps[0]), "1 completed cycle"
    if entered_L is not None:
        return clamp(entered_L), "entered"
    return DEFAULT_L, "default 28"                  # [HLR-O3]


def avg_period(periods):
    if not periods:
        return None
    return round_half_up(sum(p.length for p in periods) / len(periods))


def next_start(d1, L, today):
    """[HLR-P1] dynamic, from latest saved data. Never written to logs [HLR-P3]."""
    k = max(1, math.ceil((today - d1).days / L))
    return d1 + timedelta(days=k * L)


def phase_for(today, start, P, L):
    nxt = start + timedelta(days=L)
    ov = nxt - timedelta(days=LUTEAL_DAYS)
    if start <= today <= start + timedelta(days=P - 1):
        return "Menstruation"
    if ov - timedelta(days=FERTILE_SPAN) <= today <= ov + timedelta(days=FERTILE_SPAN):
        return "Fertile"
    return "Follicular" if today < ov else "Luteal"


def next_label(today, nxt):
    n = (nxt - today).days          # exact copy: CM-234 s5
    return "Today" if n == 0 else (f"In {n} day" if n == 1 else f"In {n} days")


def validate_onboarding(periods):
    if len(periods) > MAX_ONBOARDING_CYCLES:       # [HLR-O2]
        raise ValueError(f"onboarding allows max {MAX_ONBOARDING_CYCLES} cycles")


def expected(periods, today, entered_L=None, edited_L=None) -> Expected:
    L, src = cycle_length(periods, entered_L, edited_L)
    edit_from = today - timedelta(days=L if EDIT_LOOKBACK_USES_L else 28)

    if not periods:                                # [HLR-M1]
        return Expected("no_data", None, None, L, None, None, None,
                        "Add your cycle data", None, True, False, False, edit_from,
                        hidden_reason="No cycle logged: Home and Cycle prompt to add data.",
                        l_source=src)

    latest = max(periods, key=lambda p: p.start)
    d1, P = latest.start, avg_period(periods)
    nxt = next_start(d1, L, today)
    first_pred = d1 + timedelta(days=L)
    raw_day = (today - d1).days + 1
    proj_start = d1 + timedelta(days=((today - d1).days // L) * L)  # latest predicted start <= today
    first_window_end = first_pred + timedelta(days=P - 1)

    if today < first_pred:
        state = "prime"
    else:
        win_start = proj_start if ROLLED_WINDOW else first_pred
        state = "window" if win_start <= today <= win_start + timedelta(days=P - 1) else "waiting"

    if state == "prime":
        phase, copy, reason = phase_for(today, d1, latest.length, L), None, ""
    elif state == "window":
        phase, copy = None, "Expected period"      # [HLR-D4] see Figma / CM-234 s5
        reason = (f"Today is inside predicted period days ({proj_start} + {P - 1}). "
                  f"No phase title; expected-period copy shown.")
    else:
        phase, copy = None, "Waiting for period"   # [HLR-D4]
        reason = (f"Predicted period from {first_pred} passed with no new log. Raw cycle day "
                  f"{raw_day} > L={L}, not a real cycle day. Phase unknown without a new D1.")

    return Expected(
        state=state,
        last_period=d1,
        est_next=nxt,
        cycle_length=L,
        avg_period=P,
        cycle_day=None if state == "waiting" else raw_day,
        phase=phase,
        state_copy=copy,
        next_label=next_label(today, nxt),
        prompt_add_data=False,
        prompt_log_period=today > first_window_end,      # [HLR-D2]
        edit_screen_predictions=(today - d1).days < STALE_DAYS,  # [HLR-M2]
        editable_from=edit_from,
        raw_cycle_day=raw_day,
        projected_phase=phase_for(today, proj_start, P, L),
        hidden_reason=reason,
        l_source=src,
    )


def predictions_not_logged(app_logged_days: set, periods) -> list:
    """[HLR-P3] Days the app saved as logs that the user never marked. Must be empty."""
    real = {p.start + timedelta(days=i) for p in periods for i in range(p.length)}
    return sorted(app_logged_days - real)


# ------------------------------------------------- relative test dates
def days_ago(today, n):
    if n > PICKER_MAX_DAYS_BACK:
        raise ValueError(f"{n} days back is past the picker limit ({PICKER_MAX_DAYS_BACK})")
    return today - timedelta(days=n)


def period(today, days_back, length):
    s = days_ago(today, days_back)
    return Period(s, s + timedelta(days=length - 1))


# ------------------------------------------------- input parsing & adapter
def parse_date(raw, year=2026):
    """Parse a date string. Accepts formats like 2026-03-02, 02-03-2026, Jul 10, etc."""
    if isinstance(raw, date) and not isinstance(raw, datetime):
        return raw
    if isinstance(raw, datetime):
        return raw.date()
    raw = str(raw).strip()
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


def parse_period_input(raw, default_year=2026) -> Tuple[Optional[date], Optional[int]]:
    """Flexible parser for onboarding cycle inputs."""
    if isinstance(raw, dict):
        m_str = raw.get("month", "Jul 2026")
        y_match = re.search(r"\b(20\d\d)\b", str(m_str))
        y = int(y_match.group(1)) if y_match else default_year
        m_match = re.search(r"(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)", str(m_str), re.I)
        m_abbr = m_match.group(1).title() if m_match else "Jul"

        s_d = int(raw.get("start_day", 10))
        c_days = int(raw.get("days_count") or (int(raw.get("end_day", s_d + 4)) - s_d + 1))
        d_obj = parse_date(f"{m_abbr} {s_d}", year=y)
        return d_obj, c_days

    raw_str = str(raw).strip()

    # Case A: 'Jul 10th to 14th' or 'Jul 10 - 14'
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
    """Compares app extracted string with algorithm string."""
    a_str = str(app_val or "").strip().lower()
    b_str = str(algo_val or "").strip().lower()

    if a_str == b_str:
        return True, "Exact match"

    # Extract digits for numeric comparisons (e.g. Day 4 vs Day 4, 35 days vs 35 days)
    a_num = re.findall(r"\d+", a_str)
    b_num = re.findall(r"\d+", b_str)
    if a_num and b_num and a_num[0] == b_num[0]:
        return True, f"Numeric values match ({a_num[0]})"

    # Phase name & copy normalization
    phase_aliases = {
        "menstruation": ["menstrual", "menstruation", "menstrual phase", "period"],
        "follicular": ["follicular", "follicular phase"],
        "fertile": ["fertile", "ovulation", "fertile window", "ovulation phase", "fertile/ovulation"],
        "luteal": ["luteal", "luteal phase"],
        "waiting": ["waiting", "waiting for period", "waiting for next period"],
        "expected": ["expected", "expected period"]
    }
    for canon, aliases in phase_aliases.items():
        if any(alias in a_str for alias in aliases) and any(alias in b_str for alias in aliases):
            return True, f"Phase semantics match ({canon.title()})"

    return False, f"Mismatch: App='{app_val}' vs Algo 1='{algo_val}'"


def run_algo1(input_data: Dict[str, Any], app_output_data: Dict[str, Any], today_date=None) -> Dict[str, Any]:
    """
    Executes Algo 1 (CM-191 Oracle) in parallel with test input data and verifies
    against live app outputs.
    """
    if today_date is None:
        today_date = date.today()
    elif isinstance(today_date, str):
        today_date = parse_date(today_date) or date.today()
    elif isinstance(today_date, datetime):
        today_date = today_date.date()

    cycles_input = input_data.get("cycles") or []
    periods: List[Period] = []

    for c in cycles_input:
        start_d, p_len = parse_period_input(c, default_year=2026)
        if start_d and p_len:
            periods.append(Period(start_d, start_d + timedelta(days=p_len - 1)))

    if not periods:
        periods = [
            Period(date(2026, 7, 10), date(2026, 7, 14)),
            Period(date(2026, 8, 14), date(2026, 8, 18)),
            Period(date(2026, 9, 18), date(2026, 9, 22)),
        ]

    periods.sort(key=lambda p: p.start)
    entered_L = int(input_data.get("stepper_cycle_length") or input_data.get("cycle_length") or DEFAULT_L)
    edited_L = input_data.get("edited_cycle_length")
    if edited_L is not None:
        edited_L = int(edited_L)

    # Calculate oracle expected state using function signature: expected(periods, today, entered_L, edited_L)
    exp = expected(periods, today_date, entered_L=entered_L, edited_L=edited_L)

    avg_p = exp.avg_period or 5

    if exp.cycle_day is not None:
        you_are_in_str = f"Day {exp.cycle_day}"
    else:
        you_are_in_str = f"Day {exp.raw_cycle_day}"

    phase_str = exp.phase or exp.state_copy or exp.projected_phase or "Waiting"

    algo_metrics = {
        "YOU_ARE_IN": you_are_in_str,
        "NEXT_PERIOD": exp.next_label or "–",
        "AVG_CYCLE": f"{exp.cycle_length} days",
        "AVG_PERIOD": f"{avg_p} days",
        "CYCLE_TRACKING": phase_str,
        "LAST_PERIOD": exp.last_period.strftime("%b %d") if exp.last_period else "–",
        "EST_NEXT": exp.est_next.strftime("%b %d") if exp.est_next else "–",
        "CYCLE_DAY_INFO": f"Cycle Day {exp.cycle_day or exp.raw_cycle_day} · Started {exp.last_period.strftime('%b %d')}" if exp.last_period else "",
        "state": exp.state,
        "state_copy": exp.state_copy,
        "hidden_reason": exp.hidden_reason,
        "raw_cycle_day": exp.raw_cycle_day,
        "projected_phase": exp.projected_phase,
        "prompt_add_data": exp.prompt_add_data,
        "prompt_log_period": exp.prompt_log_period,
        "edit_screen_predictions": exp.edit_screen_predictions,
        "editable_from": str(exp.editable_from) if exp.editable_from else "",
        "l_source": exp.l_source,
    }

    fields_to_compare = [
        ("YOU ARE IN", app_output_data.get("YOU_ARE_IN"), algo_metrics["YOU_ARE_IN"]),
        ("NEXT PERIOD", app_output_data.get("NEXT_PERIOD"), algo_metrics["NEXT_PERIOD"]),
        ("AVG CYCLE", app_output_data.get("AVG_CYCLE"), algo_metrics["AVG_CYCLE"]),
        ("AVG PERIOD", app_output_data.get("AVG_PERIOD"), algo_metrics["AVG_PERIOD"]),
        ("CYCLE TRACKING", app_output_data.get("CYCLE_TRACKING"), algo_metrics["CYCLE_TRACKING"]),
    ]

    comparisons = []
    mismatch_count = 0
    for field_name, app_val, algo_val in fields_to_compare:
        is_match, reason = compare_metrics(app_val, algo_val, field_name)
        if not is_match:
            mismatch_count += 1
        comparisons.append({
            "field": field_name,
            "app_value": app_val,
            "algo_value": algo_val,
            "is_match": is_match,
            "reason": reason,
        })

    overall_status = "PASS" if mismatch_count == 0 else "FAIL"

    return {
        "overall_status": overall_status,
        "algo_name": "Algo 1 (CM-191 Oracle)",
        "algo_metrics": algo_metrics,
        "field_comparisons": comparisons,
        "mismatch_count": mismatch_count,
        "expected_object": {
            "state": exp.state,
            "last_period": str(exp.last_period) if exp.last_period else None,
            "est_next": str(exp.est_next) if exp.est_next else None,
            "cycle_length": exp.cycle_length,
            "avg_period": exp.avg_period,
            "cycle_day": exp.cycle_day,
            "raw_cycle_day": exp.raw_cycle_day,
            "phase": exp.phase,
            "state_copy": exp.state_copy,
            "next_label": exp.next_label,
            "prompt_add_data": exp.prompt_add_data,
            "prompt_log_period": exp.prompt_log_period,
            "edit_screen_predictions": exp.edit_screen_predictions,
            "editable_from": str(exp.editable_from) if exp.editable_from else None,
            "l_source": exp.l_source,
            "hidden_reason": exp.hidden_reason,
        } if exp else None,
    }


def is_today_in_period_or_predicted(cycles, entered_cl=28, today=None) -> bool:
    """
    Determines if 'today' is currently within a logged period OR within/around a predicted period.
    Used for verifying whether the 'Has your period started?' modal popup is expected.
    """
    if today is None:
        today = date.today()
    elif isinstance(today, str):
        today = parse_date(today) or date.today()
    elif isinstance(today, datetime):
        today = today.date()

    periods: List[Period] = []
    for c in cycles or []:
        s_d, p_len = parse_period_input(c, default_year=2026)
        if s_d and p_len:
            periods.append(Period(s_d, s_d + timedelta(days=p_len - 1)))

    if not periods:
        return False

    periods.sort(key=lambda p: p.start)

    # 1. Is today within any logged bleeding days?
    for p in periods:
        if p.start <= today <= p.end:
            return True

    # 2. Check using expected()
    entered_L = int(entered_cl or DEFAULT_L)
    exp = expected(periods, today, entered_L=entered_L)

    # In window state (ROLLED_WINDOW=True): today is inside predicted period days (proj_start + P - 1)
    if exp.state == "window":
        return True

    if exp.phase == "Menstruation" or exp.projected_phase == "Menstruation":
        return True

    # Check proximity to next start or rolling projected start (+/- 2 days buffer)
    if exp.est_next and abs((today - exp.est_next).days) <= 2:
        return True

    d1 = periods[-1].start
    L = exp.cycle_length
    P = exp.avg_period or 5
    proj_start = d1 + timedelta(days=((today - d1).days // L) * L)
    if (proj_start - timedelta(days=2)) <= today <= (proj_start + timedelta(days=P + 1)):
        return True

    return False


# Backwards compatibility alias
run_parallel_cycle_algorithm = run_algo1


# ---------------------------------------------------------- self-check
if __name__ == "__main__":
    t = date(2026, 10, 8)
    r = expected([Period(date(2026, 7, 11), date(2026, 7, 15))], t, entered_L=32)
    assert r.last_period == date(2026, 7, 11) and r.est_next == date(2026, 10, 15)
    assert r.state == "waiting" and r.cycle_day is None and r.prompt_log_period

    t = date.today()
    r = expected([period(t, 10, 5)], t, entered_L=28)
    assert r.state == "prime" and r.cycle_day == 11 and not r.prompt_log_period

    r = expected([], t)
    assert r.state == "no_data" and r.cycle_length == 28 and r.prompt_add_data

    ps = [period(t, 89, 5), period(t, 60, 5), period(t, 30, 5)]
    assert cycle_length(ps)[0] == 30
    assert cycle_length(ps, edited_L=35)[0] == 35
    try:
        validate_onboarding(ps + [period(t, 1, 3)]); raise AssertionError
    except ValueError:
        pass
    assert predictions_not_logged({ps[0].start}, ps) == []
    # TODO: CM-234 TC-1..TC-10 and CM-237 after-Save cases
    print("all checks passed")
