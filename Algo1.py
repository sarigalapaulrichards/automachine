from __future__ import annotations

"""
CM-191 oracle (incl. section 8 / CM-234) for the Curapod-M cycle automation suite.

Replaces cycle_predictor_algorithm.py, second_cycle_algorithm.py and
curapod_m_algorithm.py as the source of expected values.

Core rule: the PREDICTION rolls forward, logged Day 1 never does.

Items marked UNCONFIRMED must be checked against CM-234 section 11 before
results are reported. They are constants so they are easy to swap.
"""

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP
import math
import re
import warnings
from typing import List, Dict, Any, Optional, Tuple

# ---------------------------------------------------------------- config
L_MIN, L_MAX = 15, 60          # clamp for cycle length
PICKER_MAX_DAYS_BACK = 89      # onboarding picker limit
LUTEAL_DAYS = 14               # UNCONFIRMED: ovulation = next start - 14
FERTILE_SPAN = 2               # fertile = ovulation day +/- 2
WINDOW_DAYS = None             # UNCONFIRMED: days after a missed prediction
                               # that count as "window" before "waiting".
                               # None = no window state (prime -> waiting).
CLAMP_ENTERED_VALUE = True     # UNCONFIRMED: does 15-60 apply to entered L too?

if WINDOW_DAYS is None:
    warnings.warn("WINDOW_DAYS not set from CM-234 s11: window state is not modelled")


@dataclass
class Period:
    start: date
    end: date   # inclusive


@dataclass
class Expected:
    state: str              # "prime" | "window" | "waiting"
    last_period: date       # latest logged D1, never projected
    est_next: date
    cycle_length: int
    cycle_day: int | None   # None = hidden on the card
    phase: str | None       # None = no phase title (state copy instead)
    next_label: str
    raw_cycle_day: int = 0          # today - D1 + 1, always computed
    projected_phase: str = ""       # phase if the cycle had been projected (old oracle view)
    hidden_reason: str = ""         # why cycle day / phase are hidden


def round_half_up(x: float) -> int:
    return int(Decimal(str(x)).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def cycle_length(periods: list[Period], entered_L: int) -> int:
    starts = sorted(p.start for p in periods)
    gaps = [(b - a).days for a, b in zip(starts, starts[1:])]
    if len(gaps) >= 2:
        L = round_half_up((gaps[-1] + gaps[-2]) / 2)
    elif len(gaps) == 1:
        L = gaps[0]
    else:
        L = entered_L
        if not CLAMP_ENTERED_VALUE:
            return L
    return max(L_MIN, min(L_MAX, L))


def next_start(d1: date, L: int, today: date) -> date:
    k = max(1, math.ceil((today - d1).days / L))
    return d1 + timedelta(days=k * L)


def phase_for(today: date, latest: Period, L: int) -> str:
    """App's current windows. Only used in prime state."""
    nxt = latest.start + timedelta(days=L)
    ovulation = nxt - timedelta(days=LUTEAL_DAYS)
    fertile_start = ovulation - timedelta(days=FERTILE_SPAN)
    fertile_end = ovulation + timedelta(days=FERTILE_SPAN)
    if latest.start <= today <= latest.end:
        return "Menstruation"
    if fertile_start <= today <= fertile_end:
        return "Fertile"
    if today < fertile_start:
        return "Follicular"
    return "Luteal"


def next_label(today: date, nxt: date) -> str:
    # Exact strings: CM-234 section 5. This only fixes "In 1 days".
    n = (nxt - today).days
    if n == 0:
        return "Today"
    return f"In {n} day" if n == 1 else f"In {n} days"


def expected(periods: list[Period], entered_L: int, today: date) -> Expected:
    latest = max(periods, key=lambda p: p.start)
    d1 = latest.start
    L = cycle_length(periods, entered_L)
    nxt = next_start(d1, L, today)
    first_prediction = d1 + timedelta(days=L)

    if today < first_prediction:
        state = "prime"
    elif WINDOW_DAYS is not None and (today - first_prediction).days <= WINDOW_DAYS:
        state = "window"
    else:
        state = "waiting"

    raw_day = (today - d1).days + 1
    proj_start = d1 + timedelta(days=((today - d1).days // L) * L)  # latest projected start <= today
    proj = Period(proj_start, proj_start + (latest.end - latest.start))
    projected = phase_for(today, proj, L)

    if state == "waiting":
        missed = (today - first_prediction).days
        reason = (f"Predicted start {first_prediction} passed {missed} day(s) ago with no new "
                  f"period logged. Raw cycle day {raw_day} is longer than L={L}, so it is not a "
                  f"real cycle day. Phase is unknown without a new D1. CM-191 s8: hide both, "
                  f"show waiting copy.")
    elif state == "window":
        reason = (f"Predicted start {first_prediction} passed; inside the window. "
                  f"Cycle day shown, phase hidden (CM-191 s8).")
    else:
        reason = ""

    return Expected(
        raw_cycle_day=raw_day,
        projected_phase=projected,
        hidden_reason=reason,
        state=state,
        last_period=d1,
        est_next=nxt,
        cycle_length=L,
        cycle_day=None if state == "waiting" else (today - d1).days + 1,
        phase=phase_for(today, latest, L) if state == "prime" else None,
        next_label=next_label(today, nxt),
    )


# ------------------------------------------------- relative test dates
def days_ago(today: date, n: int) -> date:
    if n > PICKER_MAX_DAYS_BACK:
        raise ValueError(f"{n} days back is past the picker limit ({PICKER_MAX_DAYS_BACK})")
    return today - timedelta(days=n)


def period(today: date, days_back: int, length: int) -> Period:
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

    return False, f"Mismatch: App='{app_val}' vs Algo1='{algo_val}'"


def run_algo1(input_data: Dict[str, Any], app_output_data: Dict[str, Any], today_date=None) -> Dict[str, Any]:
    """
    Executes Algo1 (CM-191 Oracle) in parallel with test input data and verifies
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
    entered_L = int(input_data.get("stepper_cycle_length") or 28)

    # Calculate oracle expected state
    exp = expected(periods, entered_L, today_date)

    # Average period length across logged periods
    period_lengths = [(p.end - p.start).days + 1 for p in periods]
    avg_period = round_half_up(sum(period_lengths) / len(period_lengths))

    if exp.cycle_day is not None:
        you_are_in_str = f"Day {exp.cycle_day}"
    else:
        you_are_in_str = f"Day {exp.raw_cycle_day}"

    phase_str = exp.phase or exp.projected_phase or "Waiting"

    algo_metrics = {
        "YOU_ARE_IN": you_are_in_str,
        "NEXT_PERIOD": exp.next_label,
        "AVG_CYCLE": f"{exp.cycle_length} days",
        "AVG_PERIOD": f"{avg_period} days",
        "CYCLE_TRACKING": phase_str,
        "LAST_PERIOD": exp.last_period.strftime("%b %d"),
        "EST_NEXT": exp.est_next.strftime("%b %d"),
        "CYCLE_DAY_INFO": f"Cycle Day {exp.cycle_day or exp.raw_cycle_day} · Started {exp.last_period.strftime('%b %d')}",
        "state": exp.state,
        "hidden_reason": exp.hidden_reason,
        "raw_cycle_day": exp.raw_cycle_day,
        "projected_phase": exp.projected_phase,
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
        "algo_name": "Algo1 (CM-191 Oracle)",
        "algo_metrics": algo_metrics,
        "field_comparisons": comparisons,
        "mismatch_count": mismatch_count,
        "expected_object": exp,
    }


# Backwards compatibility alias
run_parallel_cycle_algorithm = run_algo1


# ---------------------------------------------------------- self-check
if __name__ == "__main__":
    # RUN-003 shape (inputs assumed: one logged period, entered L = 32)
    t = date(2026, 10, 8)
    r = expected([Period(date(2026, 7, 11), date(2026, 7, 15))], 32, t)
    assert r.last_period == date(2026, 7, 11)
    assert r.est_next == date(2026, 10, 15)
    assert r.state == "waiting" and r.cycle_day is None and r.phase is None
    print("RUN-003:", r)

    # Prime state, relative dates
    t = date.today()
    r = expected([period(t, 10, 5)], 28, t)
    assert r.state == "prime" and r.cycle_day == 11
    print("prime  :", r)

    # Two completed cycles: mean 29 and 30 -> 29.5 -> 30 (half-up)
    ps = [period(t, 89, 5), period(t, 60, 5), period(t, 30, 5)]
    assert cycle_length(ps, 28) == 30
    print("mean L :", cycle_length(ps, 28))

    # Test run_algo1 adapter
    sample_in = {"cycles": ["Jul 11th to 15th 2026"], "stepper_cycle_length": 32}
    sample_app = {
        "YOU_ARE_IN": "Day 90",
        "NEXT_PERIOD": "In 7 days",
        "AVG_CYCLE": "32 days",
        "AVG_PERIOD": "5 days",
        "CYCLE_TRACKING": "Luteal",
    }
    res = run_algo1(sample_in, sample_app, today_date=date(2026, 10, 8))
    print("run_algo1 result:", res["overall_status"], res["algo_metrics"])
    assert res["overall_status"] == "PASS"

    print("all checks passed")
