# Curapod-M Mobile Automation Test Suite

Automated mobile end-to-end testing suite for Curapod-M using Appium (UIAutomator2), Pytest, and Python.

## Overview

This repository automates the full Curapod-M mobile testing workflows, including:
- **Onboarding & Authentication**: Login, Terms acceptance, Profile information setup, physical metrics (Height/Weight), and account onboarding.
- **Cycle & Pain Tracking**: Calendar date selection, cycle length stepper verification, pain pattern selection, and pain relief sessions.
- **Cross-Validation Algorithms**: Three-way parallel algorithm verification comparing live mobile application behavior against first and second cycle prediction algorithms.
- **Reporting & History**: Interactive reporting via `report_manager.py` and test run management.

## Project Structure

```text
├── cycle_predictor_algorithm.py      # Cycle prediction algorithm implementation
├── second_cycle_algorithm.py         # Secondary cycle comparison algorithm
├── report_manager.py                 # Test report generation and history tracking
├── run_excel_suite.py                # Excel data-driven test runner
├── run_oneplus.py                    # Device-specific test runner for OnePlus
├── run_parallel_phones.py            # Multi-device parallel test runner
├── requirements.txt                  # Python dependencies
├── test/
│   ├── test_pain_tracking.py         # Core pain tracking test suite
│   ├── test_pain_tracking_oneplus.py # OnePlus targeted test suite
│   ├── test_login.py                 # Login and authentication tests
│   └── verify_three_way.py           # Verification script for 3-way cycle matching
└── .gitignore                        # Git ignore rules for test dumps & environments
```

## Setup & Prerequisites

1. **Python 3.9+**
2. **Appium 2.x** with `uiautomator2` driver installed.
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Running Tests

Run the test suite via Pytest:
```bash
pytest test/test_pain_tracking.py -v -s
```

Run data-driven suite via Excel:
```bash
python run_excel_suite.py
```
