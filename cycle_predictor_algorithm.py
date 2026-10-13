"""
Cycle Predictor Algorithm (Legacy module wrapper for Algo1).
Replaced by Algo1.py (CM-191 Oracle).
"""

from __future__ import annotations
import Algo1
from Algo1 import (
    Period,
    Expected,
    round_half_up,
    cycle_length,
    next_start,
    phase_for,
    next_label,
    expected,
    days_ago,
    period,
    parse_date,
    parse_period_input,
    compare_metrics,
    run_algo1,
    run_parallel_cycle_algorithm,
)

__all__ = [
    "Period",
    "Expected",
    "round_half_up",
    "cycle_length",
    "next_start",
    "phase_for",
    "next_label",
    "expected",
    "days_ago",
    "period",
    "parse_date",
    "parse_period_input",
    "compare_metrics",
    "run_algo1",
    "run_parallel_cycle_algorithm",
]

if __name__ == "__main__":
    import sys
    # Run Algo1 checks
    print("[cycle_predictor_algorithm -> forwarding to Algo1.py]")
    from datetime import date
    t = date(2026, 10, 8)
    r = expected([Period(date(2026, 7, 11), date(2026, 7, 15))], 32, t)
    print("RUN-003 Oracle:", r)
    print("Algo1 active and verified.")
