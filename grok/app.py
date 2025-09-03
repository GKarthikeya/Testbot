from flask import Flask, render_template, request, redirect, url_for
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import time
import re
import calendar
from datetime import datetime

app = Flask(__name__)

COLLEGE_LOGIN_URL = "https://samvidha.iare.ac.in/"
ATTENDANCE_URL = "https://samvidha.iare.ac.in/home?action=course_content"


# ---------------- Selenium Driver ----------------
def create_driver():
    chrome_options = Options()
    chrome_options.add_argument("--headless=new")  # Render needs headless
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    return driver


# ---------------- Attendance Calculation ----------------
def calculate_attendance_percentage(rows):
    result = {
        "subjects": {},
        "overall": {"present": 0, "absent": 0, "percentage": 0.0, "success": False, "status": ""}
    }

    current_course = None
    total_present = 0
    total_absent = 0

    for row in rows:
        text = row.text.strip().upper()
        if not text or text.startswith("S.NO") or "TOPICS COVERED" in text:
            continue

        # detect course line
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

    # subject-wise %
    for sub in result["subjects"].values():
        total = sub["present"] + sub["absent"]
        if total > 0:
            sub["percentage"] = round((sub["present"] / total) * 100, 2)
            if sub["percentage"] < 65:
                sub["status"] = "Shortage"
            elif sub["percentage"] < 75:
                sub["status"] = "Condonation"

    # overall %
    overall_total = total_present + total_absent
    if overall_total > 0:
        overall_percentage = round((total_present / overall_total) * 100, 2)
        status = ""
        if overall_percentage < 65:
            status = "Shortage"
        elif overall_percentage < 75:
            status = "Condonation"

        result["overall"] = {
            "present": total_present,
            "absent": total_absent,
            "percentage": overall_percentage,
            "status": status,
            "success": True
        }

    return result


# ---------------- Scraper Login ----------------
def login_and_get_attendance(username, password):
    driver = create_driver()
    try:
        driver.get(COLLEGE_LOGIN_URL)

        # wait for login fields
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "txt_uname"))
        )

        driver.find_element(By.ID, "txt_uname").send_keys(username)
        driver.find_element(By.ID, "txt_pwd").send_keys(password)
        driver.find_element(By.ID, "but_submit").click()

        time.sleep(3)

        # check invalid login
        if "Invalid username or password" in driver.page_source:
            return {"overall": {"success": False, "message": "Invalid username or password"}}

        driver.get(ATTENDANCE_URL)
        time.sleep(3)

        rows = driver.find_elements(By.TAG_NAME, "tr")
        return calculate_attendance_percentage(rows)

    except Exception as e:
        return {"overall": {"success": False, "message": str(e)}}
    finally:
        driver.quit()


# ---------------- Flask Routes ----------------
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        data = login_and_get_attendance(username, password)
        return render_template("attendance.html", data=data)

    # prepare month names + current month for dropdown
    month_names = {i: calendar.month_name[i] for i in range(1, 13)}
    current_month = datetime.now().month

    return render_template(
        "login.html",
        month_names=month_names,
        month=current_month
    )


@app.route("/")
def home():
    return redirect(url_for("login"))


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
