from flask import Flask, render_template, request, redirect, url_for
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import time
import datetime
import calendar

app = Flask(__name__)

# -------------------------
# Configure Selenium
# -------------------------
def get_driver():
    chrome_options = Options()
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    return driver

# -------------------------
# Routes
# -------------------------
@app.route("/", methods=["GET"])
def home():
    # Entry page (your student login form)
    return render_template("login.html")

@app.route("/attendance", methods=["POST"])
def attendance():
    username = request.form.get("username")
    password = request.form.get("password")

    if not username or not password:
        return render_template("login.html", message="Please enter username and password.")

    try:
        driver = get_driver()
        driver.get("https://samvidha.iare.ac.in/")  # login page

        # Fill login form (adjust selectors as per actual HTML)
        driver.find_element(By.NAME, "username").send_keys(username)
        driver.find_element(By.NAME, "password").send_keys(password)
        driver.find_element(By.ID, "btnLogin").click()
        time.sleep(3)

        # Check login success
        if "Invalid username or password" in driver.page_source:
            driver.quit()
            return render_template("login.html", message="Invalid username or password.")

        # -------------------------
        # Example: Fetch attendance data
        # -------------------------
        driver.get("https://samvidha.iare.ac.in/attendance")  
        time.sleep(3)

        # Parse attendance (this part depends on actual table structure)
        subjects_table = []
        rows = driver.find_elements(By.CSS_SELECTOR, "table tbody tr")
        for idx, row in enumerate(rows, start=1):
            cols = row.find_elements(By.TAG_NAME, "td")
            if len(cols) >= 5:
                code = cols[0].text
                name = cols[1].text
                present = cols[2].text
                absent = cols[3].text
                percent = cols[4].text
                subjects_table.append([idx, code, name, present, absent, percent])

        driver.quit()

        # Calendar data (placeholder — build with real logic)
        today = datetime.date.today()
        year, month = today.year, today.month
        cal = calendar.Calendar(firstweekday=6)
        matrix = list(cal.monthdatescalendar(year, month))

        data = {
            "subjects_table": subjects_table,
            "streak": {"current": 0, "longest": 0},
            "matrix": matrix,
            "calendar_map": {},  # Fill with presence/absence info
        }

        return render_template(
            "attendance.html",
            data=data,
            month=month,
            year=year,
            month_name=calendar.month_name[month],
            today=today,
        )

    except Exception as e:
        return render_template("login.html", message=f"Error: {str(e)}")

# -------------------------
# Run (local)
# -------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
