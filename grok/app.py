from flask import Flask, render_template, request
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
import os, re, time, calendar
from datetime import datetime, date, timedelta

COLLEGE_LOGIN_URL = "https://samvidha.iare.ac.in/"
ATTENDANCE_URL = "https://samvidha.iare.ac.in/home?action=course_content"

app = Flask(__name__)


def create_driver():
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")

    return webdriver.Chrome(
        service=Service(os.environ.get("CHROMEDRIVER_PATH", "/usr/local/bin/chromedriver")),
        options=chrome_options,
    )


def _try_date(s: str):
    """Return datetime.date if s matches '23 Aug, 2025', else None."""
    s = s.strip()
    try:
        return datetime.strptime(s, "%d %b, %Y").date()
    except Exception:
        return None


def scrape_rows_for_calendar_and_subjects(rows):
    """
    Parses table rows to:
      1) build per-subject present/absent counts
      2) build day->list[status] map for calendar
    Returns {subjects: {...}, calendar_map: {date: [PRESENT/ABSENT,...]}}
    """
    subjects = {}
    calendar_map = {}
    current_course = None

    # This regex detects a course header row (like 'AECD20 - Control Systems')
    header_rx = re.compile(r"^(A[A-Z]+\d+)\s*[-:\s]+\s*(.+)$", re.I)

    for tr in rows:
        text = tr.text.strip()
        if not text:
            continue

        # Check if it's a course header row
        m = header_rx.match(text)
        if m:
            code, name = m.group(1).upper(), m.group(2).strip()
            current_course = code
            if code not in subjects:
                subjects[code] = {"name": name, "present": 0, "absent": 0}
            continue

        # Try read as a data row via <td>
        tds = tr.find_elements(By.TAG_NAME, "td")
        if len(tds) >= 5:
            date_cell = tds[1].text
            status_cell = tds[4].text
            d = _try_date(date_cell)
            if d:
                status = status_cell.strip().upper()
                # --------- count repeated periods as separate ----------
                if current_course:
                    if status == "PRESENT":
                        subjects[current_course]["present"] += 1
                    elif status == "ABSENT":
                        subjects[current_course]["absent"] += 1

                calendar_map.setdefault(d, []).append(status)
            continue

        # Fallback: extremely defensive parse (tab/space split)
        parts = re.split(r"\s{2,}|\t", text)
        if len(parts) >= 5:
            d = _try_date(parts[1])
            status = parts[4].strip().upper()
            if d:
                if current_course:
                    if status == "PRESENT":
                        subjects[current_course]["present"] += 1
                    elif status == "ABSENT":
                        subjects[current_course]["absent"] += 1
                calendar_map.setdefault(d, []).append(status)

    # Add percentages
    for sub in subjects.values():
        total = sub["present"] + sub["absent"]
        sub["percentage"] = round((sub["present"] / total) * 100, 2) if total else 0.0

    return {"subjects": subjects, "calendar_map": calendar_map}


def login_and_get_attendance(username, password):
    driver = create_driver()
    try:
        driver.get(COLLEGE_LOGIN_URL)
        time.sleep(2)

        driver.find_element(By.ID, "txt_uname").send_keys(username)
        driver.find_element(By.ID, "txt_pwd").send_keys(password)
        driver.find_element(By.ID, "but_submit").click()
        time.sleep(3)

        if driver.current_url == COLLEGE_LOGIN_URL:
            return {"ok": False, "msg": "ERROR occurred: Please check username or password."}

        driver.get(ATTENDANCE_URL)
        time.sleep(3)
        rows = driver.find_elements(By.TAG_NAME, "tr")
        parsed = scrape_rows_for_calendar_and_subjects(rows)
        return {"ok": True, **parsed}

    except Exception as e:
        return {"ok": False, "msg": f"Error: {e}"}
    finally:
        driver.quit()


def month_matrix(year: int, month: int):
    """Return list of weeks; each week is list of 7 date objects (Sunday-first)."""
    cal = calendar.Calendar(firstweekday=6)  # Sunday start
    weeks = []
    week = []
    for d in cal.itermonthdates(year, month):
        if len(week) == 0 and d.weekday() != 6 and d.month == month:
            # fill leading days from previous month
            pass
        week.append(d)
        if len(week) == 7:
            weeks.append(week)
            week = []
    if week:
        weeks.append(week)
    return weeks


def day_status_for_calendar(day, calendar_map):
    """
    Returns one of: 'empty', 'all_present', 'absent'
    'all_present' only if there is >=1 class AND every entry is PRESENT
    """
    statuses = calendar_map.get(day, [])
    if not statuses:
        return "empty"
    return "all_present" if all(s == "PRESENT" for s in statuses) else "absent"


def streaks(calendar_map):
    """
    Compute current and longest streak of 'all_present' days over the available range.
    Only calendar days that exist in calendar_map are considered (days with no classes are neutral).
    """
    if not calendar_map:
        return {"current": 0, "longest": 0}

    days_sorted = sorted(calendar_map.keys())
    longest = 0
    current = 0
    prev_day = None

    for d in days_sorted:
        is_green = day_status_for_calendar(d, calendar_map) == "all_present"
        if prev_day and (d - prev_day).days == 1:
            current = current + 1 if is_green else 0
        else:
            current = 1 if is_green else 0
        longest = max(longest, current)
        prev_day = d

    # current streak up to today
    today = date.today()
    # if last tracked day is not today, but today is class-less, we still keep the streak as of last tracked day
    return {"current": current if prev_day else 0, "longest": longest}


@app.route("/", methods=["GET", "POST"])
def home():
    data = None
    msg = None

    # Default month/year = today's
    today = date.today()
    year = int(request.form.get("year", today.year))
    month = int(request.form.get("month", today.month))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()
        if username and password:
            result = login_and_get_attendance(username, password)
            if not result.get("ok"):
                msg = result.get("msg", "Unknown error")
            else:
                subjects = result["subjects"]
                calendar_map = result["calendar_map"]

                # Recenter to the latest month that has data if user didn't change
                if calendar_map and request.form.get("month") is None:
                    last_day = max(calendar_map.keys())
                    year, month = last_day.year, last_day.month

                # Build a month matrix for template
                matrix = month_matrix(year, month)

                # Table rows for subjects
                subject_rows = []
                i = 1
                for code, sub in subjects.items():
                    subject_rows.append(
                        [i, code, sub["name"], sub["present"], sub["absent"], f'{sub["percentage"]}%']
                    )
                    i += 1

                data = {
                    "subjects_table": subject_rows,
                    "calendar_map": calendar_map,
                    "matrix": matrix,
                    "streak": streaks(calendar_map),
                }
        else:
            msg = "Enter username & password."

    # Month options for the dropdown
    month_names = list(calendar.month_name)
    return render_template(
        "index.html",
        month=month,
        year=year,
        month_name=calendar.month_name[month],
        month_names=month_names,
        message=msg,
        data=data,
        today=date.today(),
    )


if __name__ == "__main__":
    app.run(debug=True)
