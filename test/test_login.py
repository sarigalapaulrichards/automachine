"""
test_login.py
Basic Appium test template for Curapod app (com.litemed.curapod.app)

Location: D:\\automachine\\tests\\test_login.py

Run with:
    pytest tests/test_login.py -v --html=reports/report.html

NOTE: The resource-ids below (loginButton, usernameField, etc.) are PLACEHOLDERS.
Replace them with the real resource-ids you find using Appium Inspector.
"""

import os
import pytest
from appium import webdriver
from appium.options.android import UiAutomator2Options
from appium.webdriver.common.appiumby import AppiumBy


# ---------- CONFIG ----------

DEVICE_UDID = "9b010059305330363400b96220f7c0"   # your phone's device ID from `adb devices`
APP_PACKAGE = "com.litemed.curapod.app"
APP_ACTIVITY = ".MainActivity"

SCREENSHOTS_DIR = os.path.join(os.path.dirname(__file__), "..", "screenshots")


# ---------- SETUP / TEARDOWN ----------

@pytest.fixture
def driver():
    """
    Starts an Appium session before the test, and closes it after.
    """
    options = UiAutomator2Options()
    options.platform_name = "Android"
    options.automation_name = "UiAutomator2"
    options.udid = DEVICE_UDID
    options.app_package = APP_PACKAGE
    options.app_activity = APP_ACTIVITY
    options.no_reset = True   # don't wipe app data between runs

    driver = webdriver.Remote("http://127.0.0.1:4723", options=options)
    driver.implicitly_wait(10)  # wait up to 10s for elements to appear

    yield driver   # test runs here

    driver.quit()  # runs after the test, pass or fail


# ---------- HELPER ----------

def save_failure_screenshot(driver, name="fail_screenshot"):
    """
    Saves a screenshot to the screenshots/ folder if a test fails.
    """
    os.makedirs(SCREENSHOTS_DIR, exist_ok=True)
    path = os.path.join(SCREENSHOTS_DIR, f"{name}.png")
    driver.save_screenshot(path)
    print(f"Screenshot saved to: {path}")


# ---------- TEST ----------

def test_login(driver):
    """
    Basic login test.
    REPLACE the resource-ids below with real ones from Appium Inspector.
    """
    try:
        # Example: find username field and type into it
        username_field = driver.find_element(
            AppiumBy.ID, f"{APP_PACKAGE}:id/usernameField"
        )
        username_field.send_keys("testuser")

        # Example: find password field and type into it
        password_field = driver.find_element(
            AppiumBy.ID, f"{APP_PACKAGE}:id/passwordField"
        )
        password_field.send_keys("testpassword")

        # Example: find and click login button
        login_button = driver.find_element(
            AppiumBy.ID, f"{APP_PACKAGE}:id/loginButton"
        )
        login_button.click()

        # Example: check for something that only appears after successful login
        home_screen_element = driver.find_element(
            AppiumBy.ID, f"{APP_PACKAGE}:id/homeScreenTitle"
        )

        assert home_screen_element.is_displayed(), "Home screen did not load after login"

        print("PASS: Login successful")

    except Exception as e:
        save_failure_screenshot(driver, name="test_login_fail")
        print(f"FAIL: {e}")
        raise  # re-raise so pytest marks this test as failed