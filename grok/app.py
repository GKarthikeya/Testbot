from flask import Flask, render_template, request, jsonify

app = Flask(__name__)

# ---------------- Home ----------------
@app.route("/")
def index():
    return render_template("index.html")

# ---------------- Lab Page ----------------
@app.route("/lab")
def lab():
    return render_template("lab.html")

# ---------------- Lab Subjects ----------------
@app.route("/get_lab_subjects", methods=["POST"])
def get_lab_subjects_route():
    """API endpoint to fetch lab subjects based on course/semester."""
    data = request.json
    semester = data.get("semester", "5")  # fallback to 5th sem
    
    # Dummy subjects - replace with scraped ones
    lab_subjects = {
        "5": ["Microprocessors Lab", "Control Systems Lab", "High Speed Comm Lab"],
        "6": ["VLSI Lab", "Embedded Systems Lab"],
    }
    return jsonify({"subjects": lab_subjects.get(semester, [])})

# ---------------- Lab Dates ----------------
@app.route("/get_lab_dates", methods=["POST"])
def get_lab_dates_route():
    """API endpoint to fetch available lab dates for a subject."""
    data = request.json
    subject = data.get("subject")

    # Dummy dates (replace with scraped ones)
    dummy_dates = {
        "Microprocessors Lab": ["2025-09-01", "2025-09-08", "2025-09-15"],
        "Control Systems Lab": ["2025-09-02", "2025-09-09"],
        "High Speed Comm Lab": ["2025-09-03", "2025-09-10"],
    }
    return jsonify({"dates": dummy_dates.get(subject, [])})

# ---------------- Experiment Titles ----------------
@app.route("/get_experiment_title", methods=["POST"])
def get_experiment_title_route():
    """API endpoint to fetch experiment titles for a subject + date."""
    data = request.json
    subject = data.get("subject")
    date = data.get("date")

    # Dummy experiments (replace with scraped ones)
    dummy_experiments = {
        ("Microprocessors Lab", "2025-09-01"): ["8086 Basics", "ALP with MOV Instructions"],
        ("Microprocessors Lab", "2025-09-08"): ["String Reversal", "Bubble Sort"],
        ("Control Systems Lab", "2025-09-02"): ["Root Locus", "Bode Plot"],
    }

    return jsonify({"experiments": dummy_experiments.get((subject, date), [])})


# ---------------- Run ----------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)
