from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import re

COLLEGE_LOGIN_URL = "https://samvidha.iare.ac.in/"
ATTENDANCE_URL = "https://samvidha.iare.ac.in/home?action=course_content"


def create_driver():
    chrome_options = Options()
    chrome_options.add_argument("--headless=new")  # Render requires headless
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    return driver


def calculate_attendance_percentage(rows):
    result = {
        "subjects": {},
        "overall": {
            "present": 0,
            "absent": 0,
            "percentage": 0.0,
            "status": "",
            "success": False,
            "message": ""
        }
    }

    current_course = None
    total_present = 0
    total_absent = 0

    for row in rows:
        text = row.text.strip().upper()
        if not text or text.startswith("S.NO") or "TOPICS COVERED" in text:
            continue

        # More flexible regex for course codes
        course_match = re.match(r"^([A-Z0-9]+)\s*[-:\s]+\s*(.+)$", text)
        if course_match:
            current_course = course_match.group(1)
            course_name = course_match.group(2).strip()
            result["subjects"][current_course] = {
                "name": course_name,
                "present": 0,
                "absent": 0,
                "percentage": 0.0,
                "status": ""
            }
            continue

        if current_course:
            present_count = text.count("PRESENT")
            absent_count = text.count("ABSENT")
            result["subjects"][current_course]["present"] += present_count
            result["subjects"][current_course]["absent"] += absent_count
            total_present += present_count
            total_absent += absent_count

    # Subject-wise percentage + status
    for sub in result["subjects"].values():
        total = sub["present"] + sub["absent"]
        if total > 0:
            sub["percentage"] = round((sub["present"] / total) * 100, 2)
            if sub["percentage"] < 65:
                sub["status"] = "Shortage"
            elif sub["percentage"] < 75:
                sub["status"] = "Condonation"
            else:
                sub["status"] = "OK"

    # Overall percentage + status
    overall_total = total_present + total_absent
    if overall_total > 0:
        overall_percentage = round((total_present / overall_total) * 100, 2)
        status = ""
        if overall_percentage < 65:
            status = "Shortage"
        elif overall_percentage < 75:
            status = "Condonation"
        else:
            status = "OK"

        result["overall"] = {
            "present": total_present,
            "absent": total_absent,
            "percentage": overall_percentage,
            "status": status,
            "success": True,
            "message": f"Overall Attendance: {overall_percentage}%"
        }

    return result


def login_and_get_attendance(username, password):
    driver = create_driver()
    try:
        driver.get(COLLEGE_LOGIN_URL)

        # Wait for login form
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "txt_uname"))
        )

        driver.find_element(By.ID, "txt_uname").send_keys(username)
        driver.find_element(By.ID, "txt_pwd").send_keys(password)
        driver.find_element(By.ID, "but_submit").click()

        # Wait after login
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )

        # Check for invalid login
        if "Invalid username or password" in driver.page_source:
            return {
                "overall": {
                    "success": False,
                    "message": "Invalid username or password"
                }
            }

        # Go to attendance page
        driver.get(ATTENDANCE_URL)
        WebDriverWait(driver, 10).until(
            EC.presence_of_all_elements_located((By.TAG_NAME, "tr"))
        )

        rows = driver.find_elements(By.TAG_NAME, "tr")
        return calculate_attendance_percentage(rows)

    except Exception as e:
        return {
            "overall": {
                "success": False,
                "message": f"Error: {str(e)}"
            }
        }
    finally:
        driver.quit()
