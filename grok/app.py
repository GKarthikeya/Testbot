from flask import Flask, render_template, request, redirect
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
import os, time

app = Flask(__name__)

COLLEGE_LOGIN_URL = "https://example.com/login"  # Replace with real URL
ATTENDANCE_URL = "https://example.com/attendance"  # Replace with real URL

def calculate_attendance_percentage(rows):
    # Dummy logic, replace with real one
    data = []
    for row in rows[1:]:
        cols = row.find_elements(By.TAG_NAME, "td")
        if cols:
            subject = cols[0].text
            attended = int(cols[1].text)
            total = int(cols[2].text)
            percentage = round((attended / total) * 100, 2) if total else 0
            data.append((subject, attended, total, percentage))
    return data

def get_attendance_data(username, password):
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")

    chrome_bin = os.environ.get("GOOGLE_CHROME_BIN", "/usr/bin/google-chrome")
    if not os.path.exists(chrome_bin):
        raise RuntimeError("Chrome binary not found at GOOGLE_CHROME_BIN or /usr/bin/google-chrome")
    options.binary_location = chrome_bin

    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

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
        return calculate_attendance_percentage(rows)
    finally:
        driver.quit()

@app.route("/", methods=["GET"])
def home():
    return render_template("login.html")

@app.route("/attendance", methods=["POST"])
def show_attendance():
    username = request.form.get("username")
    password = request.form.get("password")
    try:
        data = get_attendance_data(username, password)
        return render_template("attendance.html", data=data)
    except Exception as e:
        return f"Error: {e}. Check your credentials or Chrome setup."

if __name__ == "__main__":
    app.run(debug=True)
