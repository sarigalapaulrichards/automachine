"""
conftest.py - Pytest hooks and configuration for Curapod automated test suite.
Automatically captures the Present Date on every run and injects it into HTML reports and metadata.
"""

from datetime import datetime
import pytest


def pytest_html_report_title(report):
    """
    Sets the HTML report title to dynamically display the Present Date.
    """
    now = datetime.now()
    report.title = f"Curapod Test Report — Present Date: {now.strftime('%d-%b-%Y')}"


def pytest_html_results_summary(prefix, summary, postfix):
    """
    Adds a prominent Present Date banner at the top of the pytest-html report summary.
    """
    now = datetime.now()
    date_str = now.strftime("%d %B %Y (%A)")
    time_str = now.strftime("%H:%M:%S")
    banner_html = (
        f'<div style="background: #eaf1fb; border: 1px solid #c2e7ff; color: #174ea6; '
        f'padding: 12px 18px; border-radius: 8px; margin: 12px 0; font-size: 14px; font-weight: 600; '
        f'display: flex; align-items: center; gap: 8px; box-shadow: 0 1px 3px rgba(0,0,0,0.06);">'
        f'<span>📅 <strong>Present Date:</strong> {date_str}</span>'
        f'<span style="opacity: 0.5;">|</span>'
        f'<span>🕒 <strong>Run Time:</strong> {time_str}</span>'
        f'</div>'
    )
    prefix.extend([banner_html])


def pytest_metadata(metadata):
    """
    Injects the Present Date and Run Time into pytest Environment table metadata.
    """
    now = datetime.now()
    metadata["Present Date"] = now.strftime("%d-%b-%Y (%A)")
    metadata["Run Timestamp"] = now.strftime("%Y-%m-%d %H:%M:%S")
