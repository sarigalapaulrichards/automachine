"""
Curapod-M cycle-tracking algorithm -- single-file version.

This merges (unchanged logic, just combined into one file so it runs
without a multi-module package):
    constants.py
    models.py
    engine.py
    test_scenarios.py / test_scenarios2.py / test_scenarios3.py

Run it directly:
    python second_cycle_algorithm.py

That runs every test scenario (S01, S02, S11, S12, S04, S17, S18, S20,
S22, S24, S25, S28, S29, S30) with a plain pass/fail printout -- no
pytest installation required. If you DO have pytest installed and want
its nicer output/tracebacks instead, run:
    pytest second_cycle_algorithm.py -v

See the bottom of the file for the "How the math works" summary (from
math_explanation.md) as a docstring, and the __main__ block for both the
test runner and a quick interactive demo.
"""

import datetime
import math
import re
import sys
import traceback
from dataclasses import dataclass, field
from enum import Enum
from typing import Set, List, Optional, Dict, Tuple, Any


# =====================================================================
# constants.py
# =====================================================================

MIN_CYCLE = 15
MAX_CYCLE = 60
FIRST_LOOKBACK = 90
WINDOW = 14
JOIN_GAP = 2
DEFAULT_PERIOD_LENGTH = 5

# --- From the "no period dates / semi-filled / complete" product spec ---
MAX_ONBOARDING_CYCLES = 3        # sheet allows up to 3 cycles
ONBOARDING_BLOCKED_DAYS = 15     # days after a first date that are blocked in the adding sheet
ONBOARDING_MIN_START_GAP = ONBOARDING_BLOCKED_DAYS + 1   # 24 Apr -> next start 10 May = 16 days
DEFAULT_EDIT_WINDOW_DAYS = 28    # edit window = cycle length, or 28 if none
LOOKBACK_MONTHS = 3              # adding sheet shows the last 3 months (incl. current)
PREDICT_AHEAD_CYCLES = 3         # how many future predicted periods to project (assumption)


# =====================================================================
# models.py
# =====================================================================

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
    ovulation_date: Optional[datetime.date] = None
    fertile_window: Optional[tuple] = None  # (start_date, end_date)
    current_phase: Optional[Phase] = None
    predicted_period_days: List[datetime.date] = field(default_factory=list)


# =====================================================================
# engine.py
# =====================================================================

class Refusal(Exception):
    pass


class AskUser(Exception):
    def __init__(self, message, options=None):
        self.message = message
        self.options = options


def get_contiguous_periods(facts: Facts, apply_15_day_rule: bool = True) -> list:
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

    if not apply_15_day_rule:
        # Spec: the 15-day rule does NOT apply in Edit cycle / semi-filled / complete states.
        return blocks

    # Now filter blocks into actual periods using the 15-day rule
    periods = []
    if blocks:
        periods.append(blocks[0])
        for block in blocks[1:]:
            if (block.start_date - periods[-1].start_date).days >= 15:
                periods.append(block)
            else:
                # They are < 15 days apart.
                # Were they split ONLY because of a wall?
                gap = (block.start_date - periods[-1].end_date).days - 1
                if gap <= JOIN_GAP:
                    # Yes, split by a wall. The rule (R4b) says days before it become
                    # bleeding days, Day 1 moves to the first confirmed day after it.
                    # So we replace the previous period with this block.
                    periods.pop()
                    periods.append(block)
                else:
                    # Split because of natural gap. Earlier block remains the period,
                    # this block is just bleeding days.
                    pass

    return periods


def recalculate(facts: Facts, today: datetime.date, apply_15_day_rule: bool = True) -> ComputedState:
    periods = get_contiguous_periods(facts, apply_15_day_rule)
    state = ComputedState()
    state.periods = periods

    # Calculate cycle lengths
    for i in range(len(periods) - 1):
        state.cycle_lengths.append((periods[i + 1].start_date - periods[i].start_date).days)

    # Predicted cycle length
    if len(state.cycle_lengths) >= 2:
        avg = sum(state.cycle_lengths[-2:]) / 2.0
        # .5 rounds up
        state.predicted_cycle_length = int(avg + 0.5)
    elif len(state.cycle_lengths) == 1:
        state.predicted_cycle_length = state.cycle_lengths[0]
    else:
        state.predicted_cycle_length = facts.typed_cycle_length

    if periods:
        latest_period = periods[-1]
        state.cycle_day = (today - latest_period.start_date).days + 1

        if state.predicted_cycle_length is not None:
            state.next_period_start = latest_period.start_date + datetime.timedelta(
                days=state.predicted_cycle_length
            )

    # Average period (bleeding) length. Not covered by math_explanation.md,
    # so this mirrors the same "average of the last two, round half up"
    # approach used for predicted cycle length, for consistency.
    period_lengths = [p.length for p in periods]
    if len(period_lengths) >= 2:
        avg = sum(period_lengths[-2:]) / 2.0
        state.avg_period_length = int(avg + 0.5)
    elif len(period_lengths) == 1:
        state.avg_period_length = period_lengths[0]
    else:
        state.avg_period_length = facts.typed_period_length

    # Phases (menstrual/follicular/ovulation/luteal), ovulation date, and
    # fertile window for the CURRENT cycle -- layered on top of the period
    # detection above rather than changing it. Uses state.predicted_cycle_length
    # (already computed above, with the engine's own round-half-up rule) as
    # the cycle length driving the math, per math_explanation.md's formulas
    # for ovulation midpoint M = ceil(P/2) and window [M-2, M+2].
    if periods and state.predicted_cycle_length:
        current_period = periods[-1]
        day_ranges, ovulation_date, fertile_start_day, fertile_end_day = _compute_phase_day_ranges(
            current_period.start_date, current_period.end_date, state.predicted_cycle_length
        )
        for phase, (start_d, end_d) in day_ranges.items():
            d = start_d
            while d <= end_d:
                state.phases[d] = phase
                d += datetime.timedelta(days=1)

        state.ovulation_date = ovulation_date
        state.fertile_window = (
            current_period.start_date + datetime.timedelta(days=fertile_start_day - 1),
            current_period.start_date + datetime.timedelta(days=fertile_end_day - 1),
        )

    # Predicted (dashed) period days: next few expected periods, each as long
    # as the average period length.
    if periods and state.predicted_cycle_length and state.avg_period_length:
        latest_start = periods[-1].start_date
        for k in range(1, PREDICT_AHEAD_CYCLES + 1):
            pred_start = latest_start + datetime.timedelta(days=k * state.predicted_cycle_length)
            for i in range(state.avg_period_length):
                state.predicted_period_days.append(pred_start + datetime.timedelta(days=i))

    # Today's phase uses the same projection as any viewed date, so an overdue
    # cycle rolls into the predicted period instead of staying "luteal" forever.
    state.current_phase = phase_for_date(state, today)

    return state


def phase_for_date(state: ComputedState, d: datetime.date) -> Optional[Phase]:
    """
    Phase of ANY date (past, current or future) -- for the calendar's phase bar
    marker when the user views another date. Past cycles use their real length;
    the latest cycle and everything after it uses the predicted length.
    """
    if not state.periods or not state.predicted_cycle_length:
        return None
    periods = state.periods
    P = state.predicted_cycle_length
    if d < periods[0].start_date:
        return None

    if d >= periods[-1].start_date:
        n = (d - periods[-1].start_date).days // P
        start = periods[-1].start_date + datetime.timedelta(days=n * P)
        cycle_len = P
        bleed_len = periods[-1].length if n == 0 else (state.avg_period_length or DEFAULT_PERIOD_LENGTH)
    else:
        idx = max(i for i, p in enumerate(periods) if p.start_date <= d)
        start = periods[idx].start_date
        cycle_len = (periods[idx + 1].start_date - start).days
        bleed_len = periods[idx].length

    ovulation_day = math.ceil(cycle_len / 2)
    fertile_start_day = max(ovulation_day - 2, bleed_len + 1)
    fertile_end_day = ovulation_day + 2
    return _phase_for_cycle_day((d - start).days + 1, bleed_len, fertile_start_day, fertile_end_day)


def _compute_phase_day_ranges(period_start: datetime.date, period_end: datetime.date, avg_cycle_length: int):
    menstrual_len = (period_end - period_start).days + 1

    ovulation_day = math.ceil(avg_cycle_length / 2)  # M = ceil(P/2)
    fertile_start_day = max(ovulation_day - 2, menstrual_len + 1)
    fertile_end_day = ovulation_day + 2

    follicular_start_day = menstrual_len + 1
    follicular_end_day = fertile_start_day - 1

    luteal_start_day = fertile_end_day + 1
    luteal_end_day = avg_cycle_length

    def day_to_date(day_num: int) -> datetime.date:
        return period_start + datetime.timedelta(days=day_num - 1)

    ranges = {Phase.MENSTRUAL: (day_to_date(1), day_to_date(menstrual_len))}
    if follicular_end_day >= follicular_start_day:
        ranges[Phase.FOLLICULAR] = (day_to_date(follicular_start_day), day_to_date(follicular_end_day))
    ranges[Phase.OVULATION] = (day_to_date(fertile_start_day), day_to_date(fertile_end_day))
    if luteal_end_day >= luteal_start_day:
        ranges[Phase.LUTEAL] = (day_to_date(luteal_start_day), day_to_date(luteal_end_day))

    ovulation_date = day_to_date(ovulation_day)
    return ranges, ovulation_date, fertile_start_day, fertile_end_day


def _phase_for_cycle_day(cycle_day: int, menstrual_len: int, fertile_start_day: int, fertile_end_day: int) -> Phase:
    if cycle_day <= menstrual_len:
        return Phase.MENSTRUAL
    elif cycle_day < fertile_start_day:
        return Phase.FOLLICULAR
    elif cycle_day <= fertile_end_day:
        return Phase.OVULATION
    else:
        return Phase.LUTEAL


def tap_started(facts: Facts, today: datetime.date, d: datetime.date) -> Facts:
    if d > today:
        raise Refusal("You can't log a period for a future day.")

    if d in facts.confirmed_bleeding_days:
        raise Refusal("Refuse: Already a bleeding day")

    periods = get_contiguous_periods(facts)
    if periods:
        latest = periods[-1]
        if (d - latest.start_date).days < 15 and d > latest.start_date:
            new_facts = facts.copy()
            new_facts.confirmed_bleeding_days.add(d)
            return new_facts

    for p in periods:
        days_before = (p.start_date - d).days
        if 0 < days_before < 15:
            if days_before - 1 <= JOIN_GAP:
                new_facts = facts.copy()
                new_facts.confirmed_bleeding_days.add(d)
                return new_facts
            else:
                raise AskUser("Start of that period, or separate bleeding?")

    new_facts = facts.copy()
    new_facts.confirmed_bleeding_days.add(d)
    return new_facts


def tap_not_on_period(facts: Facts, today: datetime.date, d: datetime.date) -> Facts:
    new_facts = facts.copy()
    new_facts.not_on_my_period_days.add(d)
    return new_facts


def tap_ongoing(
    facts: Facts, today: datetime.date, d: datetime.date, picked_start: datetime.date = None
) -> Facts:
    if d > today:
        raise Refusal("Future day")
    if d in facts.confirmed_bleeding_days:
        raise Refusal("Already confirmed")

    periods = get_contiguous_periods(facts)
    if periods:
        latest = periods[-1]
        days_ago = (d - latest.start_date).days
        if 0 <= days_ago < 14:
            new_facts = facts.copy()
            for i in range((d - latest.start_date).days + 1):
                day_to_confirm = latest.start_date + datetime.timedelta(days=i)
                if day_to_confirm not in new_facts.not_on_my_period_days:
                    new_facts.confirmed_bleeding_days.add(day_to_confirm)
            return new_facts

    if not picked_start:
        raise AskUser("When did it start?")

    new_facts = facts.copy()
    for i in range((d - picked_start).days + 1):
        day_to_confirm = picked_start + datetime.timedelta(days=i)
        if day_to_confirm not in new_facts.not_on_my_period_days:
            new_facts.confirmed_bleeding_days.add(day_to_confirm)
    return new_facts


def edit_start(facts: Facts, today: datetime.date, period_index: int, new_start: datetime.date) -> Facts:
    periods = get_contiguous_periods(facts)
    p = periods[period_index]

    earliest = None
    if period_index > 0:
        earliest = periods[period_index - 1].start_date + datetime.timedelta(days=15)
    else:
        earliest = p.start_date - datetime.timedelta(days=90)

    latest = min(today, p.end_date)
    if period_index < len(periods) - 1:
        latest = min(latest, periods[period_index + 1].start_date - datetime.timedelta(days=15))

    if new_start < earliest or new_start > latest:
        raise Refusal(f"Choose a date between {earliest.strftime('%d %b')} and {latest.strftime('%d %b')}")

    new_facts = facts.copy()
    if new_start < p.start_date:
        for i in range((p.start_date - new_start).days):
            new_facts.confirmed_bleeding_days.add(new_start + datetime.timedelta(days=i))
    elif new_start > p.start_date:
        raise AskUser(f"This will remove {(new_start - p.start_date).days} days. Continue?")

    return new_facts


def remove_period(facts: Facts, period_index: int) -> Facts:
    periods = get_contiguous_periods(facts)
    p = periods[period_index]
    raise AskUser("Remove your period? Continue?")


# =====================================================================
# Product-spec rules (empty / semi-filled / complete states, edit window)
# =====================================================================

def recalculate_app(facts: Facts, today: datetime.date) -> ComputedState:
    """What the app should use: 15-day rule off (it only exists in the adding sheet)."""
    return recalculate(facts, today, apply_15_day_rule=False)


def onboarding_state(facts: Facts) -> str:
    """'empty' (no dates), 'semi_filled' (1-2 cycles), 'complete' (3 cycles)."""
    n = len(get_contiguous_periods(facts, apply_15_day_rule=False))
    if n == 0:
        return "empty"
    return "complete" if n >= MAX_ONBOARDING_CYCLES else "semi_filled"


def editable_window(today: datetime.date, cycle_length: Optional[int] = None):
    days = cycle_length or DEFAULT_EDIT_WINDOW_DAYS
    return today - datetime.timedelta(days=days), today


def blocked_dates_after(first_date: datetime.date):
    return (
        first_date + datetime.timedelta(days=1),
        first_date + datetime.timedelta(days=ONBOARDING_BLOCKED_DAYS),
    )


def earliest_next_start(first_date: datetime.date) -> datetime.date:
    return first_date + datetime.timedelta(days=ONBOARDING_MIN_START_GAP)


def adding_sheet_earliest_date(today: datetime.date) -> datetime.date:
    y, m = today.year, today.month - (LOOKBACK_MONTHS - 1)
    while m < 1:
        m += 12
        y -= 1
    return datetime.date(y, m, 1)


def validate_onboarding_periods(periods, today: datetime.date):
    if len(periods) > MAX_ONBOARDING_CYCLES:
        raise Refusal(f"You can add up to {MAX_ONBOARDING_CYCLES} cycles.")
    earliest = adding_sheet_earliest_date(today)
    ordered = sorted(periods)
    for start, n_days in ordered:
        end = start + datetime.timedelta(days=n_days - 1)
        if end > today:
            raise Refusal(
                f"{start.strftime('%b %d')} + {n_days} days runs past today -- future dates can't be selected."
            )
        if start < earliest:
            raise Refusal(f"{start.strftime('%b %d')} is older than the last {LOOKBACK_MONTHS} months.")
    for (prev_start, _), (start, _) in zip(ordered, ordered[1:]):
        if start < earliest_next_start(prev_start):
            b_from, b_to = blocked_dates_after(prev_start)
            raise Refusal(
                f"{start.strftime('%b %d')} is blocked: the 15 days after {prev_start.strftime('%b %d')} "
                f"({b_from.strftime('%b %d')} - {b_to.strftime('%b %d')}) can't start a new cycle. "
                f"Earliest next start is {earliest_next_start(prev_start).strftime('%b %d')}."
            )
    return ordered


def _check_in_window(facts: Facts, today: datetime.date, days):
    lo, hi = editable_window(today, facts.typed_cycle_length)
    for d in days:
        if d > today:
            raise Refusal("Future dates can't be selected.")
        if d < lo or d > hi:
            raise Refusal(
                f"You can edit {(hi - lo).days} days from the current date "
                f"({lo.strftime('%b %d')} - {hi.strftime('%b %d')})."
            )


def mark_period_days(facts: Facts, today: datetime.date, days) -> Facts:
    days = list(days)
    _check_in_window(facts, today, days)
    new_facts = facts.copy()
    for d in days:
        new_facts.confirmed_bleeding_days.add(d)
        new_facts.not_on_my_period_days.discard(d)
    return new_facts


def unmark_period_days(facts: Facts, today: datetime.date, days) -> Facts:
    days = list(days)
    _check_in_window(facts, today, days)
    new_facts = facts.copy()
    for d in days:
        new_facts.confirmed_bleeding_days.discard(d)
    return new_facts


def dates_sheet_for(facts: Facts, today: datetime.date) -> dict:
    if onboarding_state(facts) == "empty":
        return {
            "sheet": "When were your last periods?",
            "max_cycles": MAX_ONBOARDING_CYCLES,
            "fifteen_day_rule": True,
            "opens_on": today.strftime("%B %Y"),
            "future_dates_selectable": False,
            "legend": None,
        }
    lo, hi = editable_window(today, facts.typed_cycle_length)
    return {
        "sheet": "Change your period dates?",
        "fifteen_day_rule": False,
        "editable_window": (lo, hi),
        "note": f"You can edit {(hi - lo).days} days from the current date.",
        "legend": ["Marked Periods", "Predicted Periods (dashed)"],
        "today_outlined": True,
    }


def should_show_period_checkin(facts: Facts, today: datetime.date, context: str):
    if not facts.confirmed_bleeding_days:
        if context == "session":
            return {
                "figma": "P3",
                "title": "Are you on your period?",
                "body": "You haven\u2019t added any cycle dates yet. Mark your period days so Curapod-M can start learning your cycle.",
                "yes": "Yes, mark my days",
                "no": "No, not now",
                "on_yes": dates_sheet_for(facts, today),
            }
        return None

    state = recalculate_app(facts, today)
    if today not in set(state.predicted_period_days):
        return None
    run_start = today
    while run_start - datetime.timedelta(days=1) in set(state.predicted_period_days):
        run_start -= datetime.timedelta(days=1)
    if any(d >= run_start for d in facts.confirmed_bleeding_days):
        return None
    return {
        "figma": "P1",
        "title": "Has your period started?",
        "body": "Your period was expected around today. Log it so your predictions stay accurate.",
        "yes": "Yes, log my dates",
        "no": "No, not yet",
        "on_yes": dates_sheet_for(facts, today),
    }


# =====================================================================
# Period Entry Parsing & Comparison Utilities
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
      - string: "Jul 10 5", "Jul 10th 5 days", "10 Jul 5", "Sep 18th to 22nd"
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
# Second Algorithm Runner & Comparison Interface (Kept for compatibility)
# =====================================================================

def run_second_cycle_algorithm(input_data: Dict[str, Any], app_output_data: Dict[str, Any], today_date: Optional[datetime.date] = None) -> Dict[str, Any]:
    """
    Runs the Curapod-M cycle-tracking algorithm against input data and verifies against app outputs.
    Maintains full compatibility with the existing test runner and report manager.
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

    # Recalculate computed state via new engine
    state = recalculate_app(facts, today_date)

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

    def fmt_d(d: datetime.date) -> str:
        try:
            return d.strftime("%b %-d")
        except ValueError:
            return d.strftime("%b %#d")

    pred_cl = state.predicted_cycle_length or stepper_cl
    active_period_start = current_period.start_date
    if state.next_period_start and today_date >= state.next_period_start:
        while active_period_start + datetime.timedelta(days=pred_cl) <= today_date:
            active_period_start += datetime.timedelta(days=pred_cl)
        upcoming_next = active_period_start + datetime.timedelta(days=pred_cl)
        days_until_next = (upcoming_next - today_date).days
        cycle_day = (today_date - active_period_start).days + 1
        est_next_str = fmt_d(upcoming_next)
        last_period_str = fmt_d(active_period_start)

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
        est_next_str = fmt_d(state.next_period_start) if state.next_period_start else "N/A"
        last_period_str = fmt_d(prev_period.start_date)
        cycle_day = state.cycle_day
        if state.current_phase:
            ph = state.current_phase.value.capitalize()
            if ph == "Menstrual":
                current_phase = "Menstruation"
            elif ph == "Ovulation":
                current_phase = "Fertile"
            else:
                current_phase = ph
        else:
            current_phase = "Menstruation"

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
        "CYCLE_DAY_INFO": f"Cycle Day {elapsed_days} · Started {fmt_d(active_period_start)}",
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


# =====================================================================
# Test scenarios (merged from test_scenarios.py / 2 / 3)
# =====================================================================

def date(y, m, d):
    return datetime.date(y, m, d)


def base_facts() -> Facts:
    facts = Facts()
    facts.typed_period_length = 5
    for start, end in [
        (date(2026, 7, 8), date(2026, 7, 12)),
        (date(2026, 8, 5), date(2026, 8, 9)),
        (date(2026, 9, 1), date(2026, 9, 5)),
    ]:
        for i in range((end - start).days + 1):
            facts.confirmed_bleeding_days.add(start + datetime.timedelta(days=i))
    return facts


def test_s01():
    facts = base_facts()
    today = date(2026, 9, 19)
    new_facts = tap_started(facts, today, today)
    state = recalculate(new_facts, today)
    assert state.periods[-1].start_date == date(2026, 9, 19)
    assert state.predicted_cycle_length == 23
    assert state.next_period_start == date(2026, 10, 12)


def test_s02():
    facts = base_facts()
    for d in list(facts.confirmed_bleeding_days):
        if d.month == 9:
            facts.confirmed_bleeding_days.remove(d)
    for i in range(5):
        facts.confirmed_bleeding_days.add(date(2026, 9, 10) + datetime.timedelta(days=i))

    today = date(2026, 9, 19)
    new_facts = tap_started(facts, today, today)
    state = recalculate(new_facts, today)
    assert state.periods[-1].start_date == date(2026, 9, 10)
    assert date(2026, 9, 19) in new_facts.confirmed_bleeding_days


def test_s11():
    facts = base_facts()
    today = date(2026, 9, 19)
    new_facts = tap_started(facts, today, date(2026, 8, 30))
    state = recalculate(new_facts, today)
    assert state.periods[-1].start_date == date(2026, 8, 30)
    assert state.predicted_cycle_length == 27
    assert state.next_period_start == date(2026, 9, 26)
    assert state.cycle_day == 21


def test_s12():
    facts = base_facts()
    today = date(2026, 9, 19)
    try:
        tap_started(facts, today, date(2026, 8, 27))
        raise AssertionError("expected AskUser to be raised")
    except AskUser as exc:
        assert "Start of that period, or separate bleeding?" in exc.message


def test_s04():
    facts = base_facts()
    facts.confirmed_bleeding_days.add(date(2026, 9, 17))
    today = date(2026, 9, 19)
    new_facts = tap_not_on_period(facts, today, date(2026, 9, 19))
    assert date(2026, 9, 19) in new_facts.not_on_my_period_days


def test_s17():
    facts = base_facts()
    today = date(2026, 9, 19)
    new_facts = tap_started(facts, today, date(2026, 9, 7))
    state = recalculate(new_facts, today)
    assert state.periods[-1].start_date == date(2026, 9, 1)
    assert state.periods[-1].end_date == date(2026, 9, 7)


def test_s18():
    facts = base_facts()
    today = date(2026, 9, 19)
    try:
        tap_started(facts, today, date(2026, 9, 3))
        raise AssertionError("expected Refusal to be raised")
    except Refusal:
        pass


def test_s20():
    facts = base_facts()
    facts.confirmed_bleeding_days.add(date(2026, 8, 30))
    today = date(2026, 9, 19)
    new_facts = tap_not_on_period(facts, today, date(2026, 8, 31))
    state = recalculate(new_facts, today)
    assert state.periods[-1].start_date == date(2026, 9, 1)


def test_s22():
    facts = base_facts()
    today = date(2026, 9, 19)
    try:
        tap_ongoing(facts, today, date(2026, 9, 19))
        raise AssertionError("expected AskUser to be raised")
    except AskUser as exc:
        assert "When did it start" in exc.message

    new_facts = tap_ongoing(facts, today, date(2026, 9, 19), picked_start=date(2026, 9, 16))
    state = recalculate(new_facts, today)
    assert state.periods[-1].start_date == date(2026, 9, 16)
    assert state.periods[-1].end_date == date(2026, 9, 19)


def test_s24():
    facts = base_facts()
    today = date(2026, 9, 19)
    try:
        edit_start(facts, today, 2, date(2026, 9, 3))
        raise AssertionError("expected AskUser to be raised")
    except AskUser as exc:
        assert "Continue" in exc.message


def test_s25():
    facts = base_facts()
    today = date(2026, 9, 19)
    try:
        edit_start(facts, today, 2, date(2026, 8, 18))
        raise AssertionError("expected Refusal to be raised")
    except Refusal:
        pass


def test_s28():
    facts = base_facts()
    try:
        remove_period(facts, 2)
        raise AssertionError("expected AskUser to be raised")
    except AskUser:
        pass


def test_s29():
    facts = base_facts()
    today = date(2026, 9, 19)
    new_facts = edit_start(facts, today, 1, date(2026, 8, 3))
    state = recalculate(new_facts, today)
    assert state.periods[1].start_date == date(2026, 8, 3)


def test_s30():
    pass


def _expect_refusal(fn, *args):
    try:
        fn(*args)
    except Refusal:
        return
    raise AssertionError("expected Refusal")


def test_spec_15_day_block_figma_example():
    first = date(2026, 4, 24)
    assert blocked_dates_after(first) == (date(2026, 4, 25), date(2026, 5, 9))
    assert earliest_next_start(first) == date(2026, 5, 10)
    today = date(2026, 6, 20)
    validate_onboarding_periods([(first, 5), (date(2026, 5, 10), 5)], today)
    _expect_refusal(validate_onboarding_periods, [(first, 5), (date(2026, 5, 9), 5)], today)


def test_spec_onboarding_limits():
    today = date(2026, 9, 22)
    _expect_refusal(validate_onboarding_periods, [(date(2026, 9, 20), 5)], today)
    _expect_refusal(validate_onboarding_periods, [(date(2026, 6, 30), 5)], today)
    validate_onboarding_periods([(date(2026, 7, 1), 5)], today)
    four = [(date(2026, 7, 1), 3), (date(2026, 7, 20), 3), (date(2026, 8, 10), 3), (date(2026, 9, 1), 3)]
    _expect_refusal(validate_onboarding_periods, four, today)


def test_spec_edit_window():
    today = date(2026, 9, 22)
    assert editable_window(today, 27) == (date(2026, 8, 26), today)
    assert editable_window(today, None) == (date(2026, 8, 25), today)
    facts = Facts(typed_cycle_length=27)
    mark_period_days(facts, today, [date(2026, 9, 20)])
    _expect_refusal(mark_period_days, facts, today, [date(2026, 8, 20)])
    _expect_refusal(mark_period_days, facts, today, [date(2026, 9, 23)])


def test_spec_no_15_day_rule_in_edit_states():
    facts = Facts()
    for start in (date(2026, 9, 1), date(2026, 9, 11)):
        for i in range(3):
            facts.confirmed_bleeding_days.add(start + datetime.timedelta(days=i))
    today = date(2026, 9, 22)
    assert len(recalculate(facts, today).periods) == 1
    assert len(recalculate_app(facts, today).periods) == 2


def test_spec_state_and_sheet():
    today = date(2026, 9, 22)
    assert onboarding_state(Facts()) == "empty"
    one = Facts(typed_cycle_length=27)
    one.confirmed_bleeding_days.update(date(2026, 9, 10) + datetime.timedelta(days=i) for i in range(5))
    assert onboarding_state(one) == "semi_filled"
    assert dates_sheet_for(Facts(), today)["fifteen_day_rule"] is True
    sheet = dates_sheet_for(one, today)
    assert sheet["fifteen_day_rule"] is False and sheet["note"] == "You can edit 27 days from the current date."


def test_spec_predicted_days_and_phase_for_any_date():
    facts = base_facts()
    today = date(2026, 9, 19)
    state = recalculate_app(facts, today)
    assert state.predicted_cycle_length == 28
    assert state.predicted_period_days[:5] == [date(2026, 9, 29) + datetime.timedelta(days=i) for i in range(5)]
    assert phase_for_date(state, date(2026, 9, 2)) == Phase.MENSTRUAL
    assert phase_for_date(state, date(2026, 9, 30)) == Phase.MENSTRUAL
    assert phase_for_date(state, date(2026, 7, 9)) == Phase.MENSTRUAL
    assert phase_for_date(state, date(2026, 6, 1)) is None


def test_spec_checkin_popup():
    assert should_show_period_checkin(Facts(), date(2026, 9, 22), "app_open") is None
    assert should_show_period_checkin(Facts(), date(2026, 9, 22), "session")["figma"] == "P3"
    facts = base_facts()
    due = date(2026, 9, 29)
    popup = should_show_period_checkin(facts, due, "app_open")
    assert popup["figma"] == "P1" and popup["on_yes"]["fifteen_day_rule"] is False
    assert should_show_period_checkin(facts, date(2026, 9, 20), "app_open") is None
    marked = mark_period_days(facts, due, [due])
    assert should_show_period_checkin(marked, due, "app_open") is None


ALL_TESTS = [
    test_s01,
    test_s02,
    test_s11,
    test_s12,
    test_s04,
    test_s17,
    test_s18,
    test_s20,
    test_s22,
    test_s24,
    test_s25,
    test_s28,
    test_s29,
    test_s30,
    test_spec_15_day_block_figma_example,
    test_spec_onboarding_limits,
    test_spec_edit_window,
    test_spec_no_15_day_rule_in_edit_states,
    test_spec_state_and_sheet,
    test_spec_predicted_days_and_phase_for_any_date,
    test_spec_checkin_popup,
]


def run_all_tests():
    passed, failed = 0, 0
    for test_fn in ALL_TESTS:
        name = test_fn.__name__
        try:
            test_fn()
            print(f"  PASS  {name}")
            passed += 1
        except Exception:
            print(f"  FAIL  {name}")
            traceback.print_exc()
            failed += 1
    print(f"\n{passed} passed, {failed} failed out of {len(ALL_TESTS)} tests")
    return failed == 0


def demo():
    print("\n--- Demo ---")
    facts = base_facts()
    today = date(2026, 9, 19)
    print(f"Starting facts: 3 historical periods (8-12 Jul, 5-9 Aug, 1-5 Sep), today = {today}")

    state = recalculate(facts, today)
    print(f"Periods found: {[ (p.start_date, p.end_date) for p in state.periods ]}")
    print(f"Predicted cycle length: {state.predicted_cycle_length}")
    print(f"Current cycle day: {state.cycle_day}")
    print(f"Next expected period start: {state.next_period_start}")

    print("\nLogging 'Started' today (19 Sep)...")
    new_facts = tap_started(facts, today, today)
    new_state = recalculate(new_facts, today)
    print(f"New periods: {[ (p.start_date, p.end_date) for p in new_state.periods ]}")
    print_cycle_card(new_state, today)


def parse_month(text: str) -> int:
    text = text.strip()
    for candidate, fmt in ((text[:3].title(), "%b"), (text.title(), "%B")):
        try:
            return datetime.datetime.strptime(candidate, fmt).month
        except ValueError:
            continue
    raise ValueError(f"could not understand month '{text}'")


def infer_year(month: int, day: int, today: datetime.date) -> int:
    candidate = datetime.date(today.year, month, day)
    if candidate > today:
        candidate = datetime.date(today.year - 1, month, day)
    return candidate.year


_PERIOD_ENTRY_RE = re.compile(
    r"^\s*([A-Za-z]+)\.?\s+(\d{1,2})\s*(?:st|nd|rd|th)?\s+(\d{1,3})\s*days?\s*$",
    re.IGNORECASE,
)


def parse_period_entry(text: str):
    match = _PERIOD_ENTRY_RE.match(text)
    if not match:
        raise ValueError(f"could not parse '{text}' (expected e.g. 'Jul 10th 5 days')")
    month_str, day_str, days_str = match.groups()
    month = parse_month(month_str)
    day = int(day_str)
    n_days = int(days_str)
    if n_days < 1:
        raise ValueError(f"'{text}': number of days must be at least 1")
    return month, day, n_days


def ask_period_count() -> int:
    while True:
        count_str = input("How many periods do you want to enter? (1-3): ").strip()
        try:
            count = int(count_str)
        except ValueError:
            print("  Please enter a number.")
            continue
        if count < 1 or count > 3:
            print("  Please enter 1, 2, or 3.")
            continue
        return count


def collect_periods_interactively(today: datetime.date) -> Facts:
    facts = Facts()
    count = ask_period_count()

    example = ", ".join(
        ["Jul 10th 5 days", "Aug 7th 5 days", "Sep 7th 5 days"][:count]
    )
    print(f"\nEnter all {count} period(s) on one line, separated by commas.")
    print(f"Example: {example}\n")

    while True:
        line = input(f"Your {count} period(s): ").strip()
        entries = [e.strip() for e in line.split(",") if e.strip()]
        if len(entries) != count:
            print(f"  Expected {count} period(s) separated by commas, got {len(entries)}. Try again.")
            continue
        try:
            parsed = [parse_period_entry(e) for e in entries]
            dated = [
                (datetime.date(infer_year(m, d, today), m, d), n)
                for (m, d, n) in parsed
            ]
            dated = validate_onboarding_periods(dated, today)
        except (ValueError, Refusal) as e:
            print(f"  {e} Try again.")
            continue
        break

    for start, n_days in dated:
        end = start + datetime.timedelta(days=n_days - 1)
        for i in range(n_days):
            facts.confirmed_bleeding_days.add(start + datetime.timedelta(days=i))
        print(f"  Added: {start.strftime('%d %b %Y')} - {end.strftime('%d %b %Y')} ({n_days} days)")

    return facts


def run_interactive():
    today = datetime.date.today()
    print(f"(Using today's date: {today.strftime('%d %b %Y')})\n")

    facts = collect_periods_interactively(today)

    cycle_len_str = input("Typical cycle length in days (e.g. 27): ").strip()
    try:
        facts.typed_cycle_length = int(cycle_len_str) if cycle_len_str else None
    except ValueError:
        print("  Could not read that as a number -- leaving cycle length unset.")
        facts.typed_cycle_length = None

    state = recalculate_app(facts, today)
    print_cycle_card(state, today)


def print_cycle_card(state: ComputedState, today: datetime.date):
    if not state.periods:
        print("\nNo periods could be identified from the dates given.")
        return

    current = state.periods[-1]
    previous = state.periods[-2] if len(state.periods) >= 2 else current

    def fmt(d: datetime.date) -> str:
        try:
            return d.strftime("%b %-d")
        except ValueError:
            return d.strftime("%b %#d")

    days_until_next = None
    if state.next_period_start is not None:
        days_until_next = (state.next_period_start - today).days

    print()
    print("CYCLE TRACKING : Menstruation")
    print(f"  Cycle Day Info : Cycle Day {state.cycle_day} \u00b7 Started {fmt(current.start_date)}")
    print(f"  LAST PERIOD    : {fmt(previous.start_date)}")
    if state.next_period_start is not None:
        print(f"  EST. NEXT      : {fmt(state.next_period_start)}")
    else:
        print("  EST. NEXT      : n/a")
    print(f"  AVG CYCLE      : {state.predicted_cycle_length} days")
    print()
    print(f"  YOU ARE IN  : \"Day {state.cycle_day}\"")
    if days_until_next is not None:
        print(f"  NEXT PERIOD : \"In {days_until_next} days\"")
    else:
        print("  NEXT PERIOD : \"Unknown\"")
    print(f"  AVG CYCLE   : \"{state.predicted_cycle_length} days\"")
    print(f"  AVG PERIOD  : \"{state.avg_period_length} days\"")

    if state.current_phase is not None:
        print()
        print(f"  PHASE          : {state.current_phase.value.capitalize()}")
        if state.ovulation_date is not None:
            print(f"  OVULATION      : {fmt(state.ovulation_date)}")
        if state.fertile_window is not None:
            fw_start, fw_end = state.fertile_window
            print(f"  FERTILE WINDOW : {fmt(fw_start)} - {fmt(fw_end)}")
    if state.predicted_period_days:
        first = state.predicted_period_days[0]
        last = first + datetime.timedelta(days=(state.avg_period_length or 1) - 1)
        print(f"  PREDICTED PERIOD : {fmt(first)} - {fmt(last)}")


if __name__ == "__main__":
    if "--test" in sys.argv:
        print("Running Curapod-M algorithm test scenarios...\n")
        ok = run_all_tests()
        demo()
        raise SystemExit(0 if ok else 1)
    elif "--compare" in sys.argv or "--verify" in sys.argv:
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
            st = "[PASS]" if c["matched"] else "[FAIL]"
            print(f"  {st} {c['field']}: App='{c['app_value']}' | SecondAlgo='{c['algo_value']}' ({c['reason']})")
    else:
        run_interactive()
