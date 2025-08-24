# app.py
from flask import Flask, render_template, request
from collections import defaultdict
from datetime import datetime
import calendar
import re
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
import time

app = Flask(__name__)

COLLEGE_LOGIN_URL = "https://samvidha.iare.ac.in/"
ATTENDANCE_URL = "https://samvidha.iare.ac.in/home?action=course_content"

# ------------------- SCRAPER FUNCTION -------------------
def get_raw_attendance_text(username, password):
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")

    driver = webdriver.Chrome(
        service=Service(ChromeDriverManager().install()),
        options=options
    )

    try:
        driver.get(COLLEGE_LOGIN_URL)
        time.sleep(2)
        driver.find_element(By.ID, "txt_uname").send_keys(username)
        driver.find_element(By.ID, "txt_pwd").send_keys(password)
        driver.find_element(By.ID, "but_submit").click()
        time.sleep(3)

        driver.get(ATTENDANCE_URL)
        time.sleep(3)

        rows = driver.find_elements(By.TAG_NAME, "tr")
        lines = []
        for row in rows:
            text = row.text.strip()
            if text:
                # Replace multiple spaces with a tab to mimic raw_text format
                lines.append(re.sub(r"\s{2,}", "\t", text))
        return "\n".join(lines)
    finally:
        driver.quit()

# ------------------- PARSE ATTENDANCE -------------------
def parse_attendance(raw_text):
    attendance = []
    for line in raw_text.splitlines():
        parts = line.split("\t")
        if len(parts) < 4:
            continue
        date_str = parts[0].strip()
        status = parts[3].strip().upper()

        try:
            date_obj = datetime.strptime(date_str, "%d %b, %Y")
            iso_date = date_obj.strftime("%Y-%m-%d")
            attendance.append({"date": iso_date, "status": status})
        except:
            continue
    return attendance

# ------------------- FLASK ROUTE -------------------
@app.route("/", methods=["GET", "POST"])
def calendar_view():
    raw_text = ""
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        raw_text = get_raw_attendance_text(username, password)

    attendance_data = parse_attendance(raw_text)

    # Group statuses by date
    daily_status = defaultdict(list)
    for entry in attendance_data:
        daily_status[entry["date"]].append(entry["status"])

    # Final mark for each day
    day_marks = {}
    for d, statuses in daily_status.items():
        date_obj = datetime.strptime(d, "%Y-%m-%d")
        weekday = date_obj.weekday()  # Mon=0..Sun=6

        present_count = statuses.count("PRESENT")
        absent_count = statuses.count("ABSENT")

        if absent_count > 0:
            day_marks[d] = "absent"
        else:
            if weekday == 5:  # Saturday
                day_marks[d] = "full" if present_count >= 6 else "not_enough"
            elif weekday < 5:  # Mon–Fri
                day_marks[d] = "full" if present_count >= 5 else "not_enough"
            else:
                day_marks[d] = "empty"

    # Example calendar month
    year, month = 2025, 8
    first_weekday, num_days = calendar.monthrange(year, month)

    return render_template(
        "calendar.html",
        year=year,
        month=month,
        first_weekday=first_weekday,
        num_days=num_days,
        day_marks=day_marks,
    )

if __name__ == "__main__":
    app.run(debug=True)
