# app.py

import streamlit as st
import pandas as pd
import sqlite3
from pathlib import Path
from datetime import datetime
import base64

# -------------------------
# CONFIG
# -------------------------

st.set_page_config(
    page_title="SJCET Feedback System",
    layout="wide",
)

BASE_DIR = Path(__file__).parent
STUDENTS_DIR = BASE_DIR / "students_list"
FACULTY_DIR = BASE_DIR / "faculty_list"
DB_PATH = BASE_DIR / "feedback.db"
LOGO_PATH = BASE_DIR / "sjcet_logo.png"

# -------------------------
# WHITE + MOBILE OPTIMIZED UI (ALL BLACK TEXT)
# -------------------------

white_mobile_css = """
<style>
/* Full white background */
.stApp {
    background: #ffffff !important;
}

/* Make basically everything black by default */
html, body,
[class*="st-"],
.stMarkdown, .stTextInput label, .stSelectbox label,
.stNumberInput label, .stDateInput label,
label, p, h1, h2, h3, h4, h5, h6, span {
    color: #000000 !important;
}

/* Hide sidebar fully */
section[data-testid="stSidebar"] {
    display: none !important;
}

/* Main content width - ideal for mobile + desktop */
.block-container {
    max-width: 700px;
    padding-top: 1.5rem !important;
    padding-bottom: 2rem !important;
    margin-left: auto;
    margin-right: auto;
}

/* Inputs white + black text */
input, textarea {
    background-color: #ffffff !important;
    color: #000000 !important;
    border: 1px solid #999999 !important;
}

/* Placeholder text also black (slightly softer) */
input::placeholder, textarea::placeholder {
    color: #000000 !important;
    opacity: 0.8 !important;
}

/* ---------- SELECT / DROPDOWN ---------- */

/* Closed select box */
[data-baseweb="select"] > div {
    background-color: #ffffff !important;
    color: #000000 !important;
    border: 1px solid #999999 !important;
}

/* Text inside select */
[data-baseweb="select"] * {
    color: #000000 !important;
}

/* Open dropdown panel background */
[data-baseweb="popover"],
[data-baseweb="select"] [role="listbox"] {
    background-color: #ffffff !important;
    color: #000000 !important;
}

/* Each option row */
[data-baseweb="select"] [role="option"] {
    background-color: #ffffff !important;
    color: #000000 !important;
}

/* Selected / hover option */
[data-baseweb="select"] [role="option"][aria-selected="true"],
[data-baseweb="select"] [role="option"]:hover {
    background-color: #e5e7eb !important;  /* light grey highlight */
}

/* ---------- FILE UPLOADER ---------- */

/* Drop zone background */
[data-testid="stFileUploaderDropzone"] {
    background-color: #ffffff !important;
    color: #000000 !important;
    border-radius: 8px !important;
    border: 1px solid #999999 !important;
}

/* Text & icon inside drop zone */
[data-testid="stFileUploaderDropzone"] * {
    color: #000000 !important;
}

/* Buttons full-width on mobile, clean */
.stButton>button {
    width: 100% !important;
    background-color: #f5f5f5 !important;
    color: #000000 !important;
    border-radius: 8px !important;
    border: 1px solid #999999 !important;
    padding: 0.55rem 1rem !important;
    font-weight: 600 !important;
}

/* Brown title */
.app-title {
    color: #8B4513 !important;
    font-weight: 800;
    font-size: 28px;
    text-align: center;
    margin-top: 10px;
    margin-bottom: 6px;
}

/* Red warning message */
.warning-dob {
    color: #d00000 !important;
    font-size: 16px;
    font-weight: 700;
    margin-top: 4px;
    margin-bottom: 20px;
}

/* Mobile text size */
@media (max-width: 768px) {
    .block-container {
        padding-left: 0.75rem !important;
        padding-right: 0.75rem !important;
    }
    .stButton>button,
    input,
    textarea,
    [data-baseweb="select"] > div {
        font-size: 16px !important;
    }
}
</style>
"""
st.markdown(white_mobile_css, unsafe_allow_html=True)


# -------------------------
# DATABASE SETUP
# -------------------------

def get_connection():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    return conn

def init_db():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS feedback_questions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            question_text TEXT NOT NULL,
            order_no INTEGER NOT NULL,
            is_active INTEGER NOT NULL DEFAULT 1
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS feedback (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_regd_no TEXT NOT NULL,
            branch_code TEXT NOT NULL,
            section TEXT,
            faculty_name TEXT NOT NULL,
            subject TEXT NOT NULL,
            department TEXT NOT NULL,
            q_scores TEXT NOT NULL,
            comments TEXT,
            created_at TEXT NOT NULL
        )
    """)

    conn.commit()

    cur.execute("SELECT COUNT(*) FROM feedback_questions")
    (count,) = cur.fetchone()

    if count == 0:
        default_qs = [
            "Teacher comes to the class in time",
            "Teacher teaches effectively",
            "Teacher speaks clearly and audibly",
            "Teacher plans lessons with clear objectives",
            "Teacher has good command on the subject",
            "Teacher writes and draws legibly",
            "Teacher asks questions to promote interaction and effective thinking",
            "Teacher encourages, compliments, and praises originality and creativity displayed by the students",
            "Teacher is courteous and impartial in dealing with the students",
            "Teacher covers the syllabus completely",
            "Teacher’s evaluation of exams, answer scripts, lab records, etc., is fair and impartial",
            "Teacher is prompt in valuing and returning the answer scripts and giving feedback",
            "Teacher offers assistance and counselling to needy students",
            "Teacher imparts practical knowledge related to the subject",
            "Overall rating of the Teacher",
        ]
        for i, q in enumerate(default_qs, start=1):
            cur.execute(
                "INSERT INTO feedback_questions (question_text, order_no, is_active) VALUES (?, ?, 1)",
                (q, i),
            )
        conn.commit()

    conn.close()

def get_questions():
    conn = get_connection()
    df = pd.read_sql_query(
        "SELECT id, question_text, order_no FROM feedback_questions WHERE is_active=1 ORDER BY order_no",
        conn
    )
    conn.close()
    return df

def save_feedback(student_regd_no, branch_code, section, faculty, subject, dept, scores, comments):
    conn = get_connection()
    cur = conn.cursor()

    score_str = ",".join(str(int(x)) for x in scores)

    cur.execute("""
        INSERT INTO feedback
        (student_regd_no, branch_code, section, faculty_name, subject, department, q_scores, comments, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (student_regd_no, branch_code, section, faculty, subject, dept, score_str, comments, datetime.now().isoformat()))

    conn.commit()
    conn.close()

def feedback_exists(student, branch, section, faculty, subject):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT COUNT(*) FROM feedback
        WHERE student_regd_no=? AND branch_code=? 
          AND ifnull(section,'') = ifnull(?, '')
          AND faculty_name=? AND subject=?
    """, (student, branch, section, faculty, subject))

    (count,) = cur.fetchone()
    conn.close()

    return count > 0

def get_feedback_for_section(branch, section):
    conn = get_connection()
    df = pd.read_sql_query("""
        SELECT * FROM feedback 
        WHERE branch_code=? AND ifnull(section,'') = ifnull(?, '')
    """, conn, params=(branch, section))
    conn.close()
    return df

# -------------------------
# LOAD DATA
# -------------------------

STUDENT_FILE_CONFIG = [
    ("II-CSD", None, "S_II-CSD.csv"),
    ("II-CSE", "A", "S_II-CSE_A.csv"),
    ("II-CSE", "B", "S_II-CSE_B.csv"),
    ("II-CSE", "C", "S_II-CSE_C.csv"),
    ("III-CSE", None, "S_III-CSE.csv"),
    ("III-CSD", None, "S_lll-CSD.csv"),
]

FACULTY_FILE_CONFIG = [
    ("II-CSD", None, "F_II-CSD.csv"),
    ("II-CSE", "A", "F_II-CSE_A.csv"),
    ("II-CSE", "B", "F_II-CSE_B.csv"),
    ("II-CSE", "C", "F_II-CSE_C.csv"),
    ("III-CSE", None, "F_III-CSE.csv"),
    ("III-CSD", None, "F_lll-CSD.csv"),
]

@st.cache_data
def load_students():
    all_rows = []
    for branch, sec, file in STUDENT_FILE_CONFIG:
        p = STUDENTS_DIR / file
        if not p.exists():
            p2 = BASE_DIR / file
            if p2.exists():
                p = p2
            else:
                continue
        df = pd.read_csv(p)
        df["branch_code"] = branch
        df["section"] = sec
        df.rename(columns={
            "Regd. No.": "regd_no",
            "Name": "name",
            "DOB": "dob",
        }, inplace=True)
        df["regd_no"] = df["regd_no"].astype(str).str.strip().str.upper()
        df["dob"] = df["dob"].astype(str).str.strip()
        all_rows.append(df)
    return pd.concat(all_rows, ignore_index=True)

@st.cache_data
def load_faculty():
    all_rows = []
    for branch, sec, file in FACULTY_FILE_CONFIG:
        p = FACULTY_DIR / file
        if not p.exists():
            p2 = BASE_DIR / file
            if p2.exists():
                p = p2
            else:
                continue
        df = pd.read_csv(p, encoding="latin1")
        df["branch_code"] = branch
        df["section"] = sec
        df.rename(columns={
            "S.No": "sno",
            "Faculty Name": "faculty_name",
            "Subject (Full Form)": "subject",
            "Department": "department"
        }, inplace=True)
        all_rows.append(df)
    return pd.concat(all_rows, ignore_index=True)

students_df = load_students()
faculty_df = load_faculty()

# -------------------------
# AUTH
# -------------------------

def authenticate_student(reg, dob, branch, sec):
    reg = reg.strip().upper()
    dob = dob.strip()
    sub = students_df[
        (students_df["regd_no"] == reg) &
        (students_df["dob"] == dob) &
        (students_df["branch_code"] == branch)
    ]
    if branch == "II-CSE":
        sub = sub[sub["section"] == sec]
    if sub.empty:
        return None
    return sub.iloc[0]

def authenticate_fixed(username, password, role):
    creds = {
        "HOD": ("hod", "hod123"),
        "Principal": ("principal", "principal123"),
        "Admin": ("admin", "admin123"),
    }
    u, p = creds[role]
    return username == u and password == p

# -------------------------
# HEADER
# -------------------------

def render_header():
    if LOGO_PATH.exists():
        logo_b64 = base64.b64encode(LOGO_PATH.read_bytes()).decode()
        st.markdown(
            f"""
            <div style="text-align:center; padding-top: 24px; padding-bottom: 8px;">
                <img src="data:image/png;base64,{logo_b64}" 
                     style="width:130px; margin-bottom:6px;" />
                <h1 class="app-title">SJCET Feedback System</h1>
            </div>
            """, unsafe_allow_html=True
        )
    else:
        st.markdown('<h1 class="app-title" style="padding-top:24px;">SJCET Feedback System</h1>', unsafe_allow_html=True)

# -------------------------
# STUDENT LOGIN
# -------------------------

def student_login_panel():
    st.markdown("## 🔐 Student Login")

    col1, col2 = st.columns(2)
    with col1:
        reg = st.text_input("Register Number")
        dob = st.text_input("Date of Birth (exact as in sheet)", placeholder="e.g. 01/01/2005")
    with col2:
        branch = st.selectbox("Year & Branch", ["Select", "II-CSD", "II-CSE", "III-CSE", "III-CSD"])
        sec = None
        if branch == "II-CSE":
            sec = st.selectbox("Section (only for II-CSE)", ["A", "B", "C"])
        else:
            st.write("Section: Not required")

    # Red warning
    st.markdown(
        """
        <div class="warning-dob">
        ⚠️ If login fails, try swapping the day and month.
        <br>Example: <b>01/04/2005 → 04/01/2005</b>
        </div>
        """, unsafe_allow_html=True
    )

    st.write("")
    st.write("")

    if st.button("Login as Student"):
        if branch == "Select" or not reg or not dob:
            st.error("Fill all fields.")
            return None
        row = authenticate_student(reg, dob, branch, sec)
        if row is None:
            st.error("Invalid login. Check DOB or branch/section.")
            return None
        st.success("Login successful.")
        return {
            "name": row["name"],
            "regd_no": row["regd_no"],
            "branch_code": row["branch_code"],
            "section": row["section"],
        }
    return None

# -------------------------
# STUDENT DASHBOARD
# -------------------------

def student_dashboard(info):
    st.markdown("## Student Feedback Panel")
    st.write(f"### Hi **{info['name']}**, please give genuine feedback.")

    branch = info["branch_code"]
    sec = info["section"]

    fac = faculty_df[
        (faculty_df["branch_code"] == branch) &
        (faculty_df["section"].fillna("") == (sec or ""))
    ]

    st.write("### Faculty for your Section:")
    st.dataframe(fac[["sno", "faculty_name", "subject", "department"]])

    if fac.empty:
        st.warning("No faculty found. Contact admin.")
        return

    fname = st.selectbox("Select Faculty", fac["faculty_name"].unique())
    row = fac[fac["faculty_name"] == fname].iloc[0]
    subj = row["subject"]
    dept = row["department"]

    st.write(f"**Faculty:** {fname}")
    st.write(f"**Subject:** {subj}")
    st.write(f"**Department:** {dept}")

    if feedback_exists(info["regd_no"], branch, sec, fname, subj):
        st.info("You already submitted feedback for this faculty.")
        return

    questions = get_questions()
    scores = []

    st.write("#### Rate on a scale of 1 to 10:")
    for _, q in questions.iterrows():
        s = st.slider(q["question_text"], 1, 10, 5, key=f"q_{q['id']}")
        scores.append(s)

    comments = st.text_area("Additional suggestions (optional)")

    if st.button("Submit Feedback"):
        save_feedback(
            info["regd_no"], branch, sec, fname, subj, dept,
            scores, comments
        )
        st.success("Feedback submitted!")

# -------------------------
# HOD / PRINCIPAL
# -------------------------

def section_selector():
    c1, c2 = st.columns(2)
    with c1:
        branch = st.selectbox("Branch", ["II-CSD", "II-CSE", "III-CSE", "III-CSD"])
    with c2:
        sec = st.selectbox("Section", ["A", "B", "C"]) if branch=="II-CSE" else None
    return branch, sec

def render_feedback_analysis(branch, sec):
    fac = faculty_df[
        (faculty_df["branch_code"] == branch) &
        (faculty_df["section"].fillna("") == (sec or ""))
    ]

    if fac.empty:
        st.warning("No faculty found.")
        return

    st.dataframe(fac[["sno","faculty_name","subject","department"]])

    fb = get_feedback_for_section(branch, sec)
    if fb.empty:
        st.info("No feedback yet.")
        return

    questions = get_questions()
    nq = len(questions)
    labels = [f"Q{i}" for i in range(1, nq+1)]

    def expand(r):
        parts = [int(x) for x in str(r["q_scores"]).split(",")]
        if len(parts) < nq:
            parts += [None] * (nq - len(parts))
        return pd.Series(parts[:nq], index=labels)

    expanded = fb.apply(expand, axis=1)
    full = pd.concat([fb, expanded], axis=1)

    results = []
    for _, f in fac.iterrows():
        ff = full[(full["faculty_name"]==f["faculty_name"]) & (full["subject"]==f["subject"])]
        if ff.empty:
            continue
        row = {
            "Faculty": f["faculty_name"],
            "Subject": f["subject"],
            "Responses": len(ff)
        }
        for i in range(1, nq+1):
            row[f"Q{i}_avg"] = round(ff[f"Q{i}"].mean(), 2)
        results.append(row)

    if not results:
        st.info("No data.")
        return

    df = pd.DataFrame(results)
    st.dataframe(df)

    st.write("### Question-wise Average")
    qavg = {}
    for i, (_, qr) in enumerate(questions.iterrows(), 1):
        col = f"Q{i}_avg"
        if col in df.columns:
            qavg[qr["question_text"]] = df[col].mean()
    st.bar_chart(pd.DataFrame({"avg": qavg}).T)

def hod_panel():
    st.markdown("## HOD Dashboard")
    b, s = section_selector()
    render_feedback_analysis(b, s)

def principal_panel():
    st.markdown("## Principal Dashboard")
    b, s = section_selector()
    render_feedback_analysis(b, s)

# -------------------------
# ADMIN PANEL
# -------------------------

def admin_panel():
    st.markdown("## Admin Panel")
    tab1, tab2, tab3 = st.tabs(["Uploads", "Edit Questions", "Reset"])

    with tab1:
        st.write("#### Upload CSV Files")

        stu_file = st.file_uploader("Upload Students CSV")
        stu_name = st.text_input("Save students file as (S_IV-CSE_A.csv)")
        if st.button("Save Students CSV"):
            if stu_file and stu_name:
                with open(STUDENTS_DIR / stu_name, "wb") as f:
                    f.write(stu_file.getbuffer())
                st.success("Saved.")
            else:
                st.error("Select file and name.")

        fac_file = st.file_uploader("Upload Faculty CSV")
        fac_name = st.text_input("Save faculty file as (F_IV-CSE_A.csv)")
        if st.button("Save Faculty CSV"):
            if fac_file and fac_name:
                with open(FACULTY_DIR / fac_name, "wb") as f:
                    f.write(fac_file.getbuffer())
                st.success("Saved.")
            else:
                st.error("Select file and name.")

    with tab2:
        st.write("#### Edit Questions")
        qs = get_questions()
        txt = "\n".join(qs["question_text"])
        newtxt = st.text_area("One question per line:", value=txt, height=300)
        if st.button("Save Questions"):
            lines = [x.strip() for x in newtxt.split("\n") if x.strip()]
            if not lines:
                st.error("Cannot be empty.")
            else:
                conn = get_connection()
                cur = conn.cursor()
                cur.execute("DELETE FROM feedback_questions")
                for i, q in enumerate(lines, 1):
                    cur.execute(
                        "INSERT INTO feedback_questions (question_text, order_no, is_active) VALUES (?, ?, 1)",
                        (q, i)
                    )
                conn.commit()
                conn.close()
                st.success("Updated.")

    with tab3:
        st.write("#### Reset Feedback")
        conn = get_connection()
        fb = pd.read_sql_query("SELECT * FROM feedback", conn)
        conn.close()
        st.write(f"Total records: {len(fb)}")
        st.dataframe(fb)
        if st.button("RESET ALL FEEDBACK"):
            conn = get_connection()
            cur = conn.cursor()
            cur.execute("DELETE FROM feedback")
            conn.commit()
            conn.close()
            st.warning("All feedback deleted.")

# -------------------------
# LOGIN SCREEN
# -------------------------

def login_screen():
    render_header()

    st.markdown("## 🔐 Login")

    role = st.selectbox("Select Role", ["Student", "HOD", "Principal", "Admin"])

    if role == "Student":
        info = student_login_panel()
        if info:
            st.session_state["auth_role"] = "Student"
            st.session_state["student_info"] = info
            st.rerun()
    else:
        st.markdown(f"## {role} Login")
        u = st.text_input("Username")
        p = st.text_input("Password", type="password")
        if st.button(f"Login as {role}"):
            if authenticate_fixed(u, p, role):
                st.session_state["auth_role"] = role
                st.rerun()
            else:
                st.error("Invalid credentials.")

# -------------------------
# MAIN
# -------------------------

def main():
    init_db()

    if "auth_role" not in st.session_state:
        st.session_state["auth_role"] = None

    if st.session_state["auth_role"] is None:
        login_screen()
    else:
        render_header()

        st.write("")
        if st.button("Logout"):
            st.session_state["auth_role"] = None
            st.session_state.pop("student_info", None)
            st.rerun()

        role = st.session_state["auth_role"]

        if role == "Student":
            info = st.session_state.get("student_info")
            if not info:
                st.session_state["auth_role"] = None
                st.rerun()
            student_dashboard(info)
        elif role == "HOD":
            hod_panel()
        elif role == "Principal":
            principal_panel()
        elif role == "Admin":
            admin_panel()

if __name__ == "__main__":
    main()
