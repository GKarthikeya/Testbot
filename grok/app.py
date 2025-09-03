from flask import Flask, render_template, request, redirect, url_for, session
from attendance_scraper import login_and_get_attendance


app = Flask(__name__)
app.secret_key = "supersecretkey"  # needed for session handling

@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        # Store in session (optional, if you want to reuse)
        session["username"] = username
        session["password"] = password

        # Call Selenium scraper
        data = login_and_get_attendance(username, password)

        if not data.get("overall", {}).get("success", False):
            return render_template("login.html", error="Invalid login or error fetching attendance.")

        return render_template("attendance.html", subjects=data["subjects"], overall=data["overall"])

    return render_template("login.html")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
