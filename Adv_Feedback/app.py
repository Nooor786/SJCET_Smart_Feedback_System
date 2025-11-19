# app.py

import streamlit as st
import pandas as pd
import sqlite3
from pathlib import Path
from datetime import datetime
import base64

# ============================
# PAGE CONFIG
# ============================

st.set_page_config(
    page_title="SJCET Feedback System",
    layout="wide",
)

BASE_DIR = Path(__file__).parent
STUDENTS_DIR = BASE_DIR / "students_list"
FACULTY_DIR = BASE_DIR / "faculty_list"
DB_PATH = BASE_DIR / "feedback.db"
LOGO_PATH = BASE_DIR / "sjcet_logo.png"

# ============================
# FULL WHITE UI + MOBILE OPTIMIZED
# ============================

CSS = """
<style>

/* FULL WHITE APP */
.stApp {
    background: #ffffff !important;
}

/* REMOVE SIDEBAR COMPLETELY */
section[data-testid="stSidebar"] {
    display: none !important;
}

/* CENTER MAIN BLOCK */
.block-container {
    max-width: 700px !important;
    margin: auto !important;
    padding-top: 1.5rem !important;
}

/* MAKE ALL TEXT BLACK */
html, body, p, label, span,
h1, h2, h3, h4, h5, h6,
.stMarkdown, div, input, textarea,
[class*="st-"] {
    color: #000000 !important;
}

/* ---------------------------
   INPUT FIELDS
---------------------------- */
input, textarea {
    background: #ffffff !important;
    color: #000 !important;
    border: 1px solid #999 !important;
}
input::placeholder, textarea::placeholder {
    color: #000 !important;
    opacity: 0.8 !important;
}

/* ---------------------------
   SELECT BOXES (WHITE + ARROW BROWN)
---------------------------- */
[data-baseweb="select"] > div {
    background-color: #ffffff !important;
    border: 1px solid #999 !important;
    color: #000 !important;
}
[data-baseweb="select"] * {
    color: #000 !important;
}
/* ARROW BROWN */
[data-baseweb="select"] svg {
    color: #8B4513 !important;
    fill: #8B4513 !important;
}

/* Dropdown list white */
[data-baseweb="popover"],
div[role="listbox"] {
    background: #ffffff !important;
}
[role="option"] {
    background: #ffffff !important;
    color: #000000 !important;
}
[role="option"]:hover,
[role="option"][aria-selected="true"] {
    background: #e6e6e6 !important;
}

/* ---------------------------
   WHITE BUTTONS + BLACK TEXT
---------------------------- */
.stButton > button {
    width: 100% !important;
    background: #ffffff !important;
    color: #000 !important;
    border: 1px solid #999 !important;
    border-radius: 8px !important;
    padding: 10px !important;
    font-weight: 600 !important;
}
.stButton > button:hover {
    background: #e6e6e6 !important;
}

/* ---------------------------
   FIX: “Browse Files” BUTTON WHITE
---------------------------- */
[data-testid="stFileUploaderDropzone"] button,
button[data-baseweb="button"] {
    background: #ffffff !important;
    color: #000000 !important;
    border: 1px solid #999 !important;
    border-radius: 8px !important;
}
[data-testid="stFileUploaderDropzone"] button:hover,
button[data-baseweb="button"]:hover {
    background: #e5e5e5 !important;
}

/* FILE UPLOADER BACKGROUND */
[data-testid="stFileUploaderDropzone"] {
    background: #ffffff !important;
    border: 1px solid #999 !important;
    border-radius: 8px !important;
}
[data-testid="stFileUploaderDropzone"] * {
    color: #000 !important;
}

/* ---------------------------
   TABS (WHITE)
---------------------------- */
[data-baseweb="tab"] {
    background: #ffffff !important;
    color: #000 !important;
}

/* ---------------------------
   TITLE BROWN
---------------------------- */
.app-title {
    color: #8B4513 !important;
    font-size: 30px !important;
    font-weight: 900 !important;
    text-align: center;
    margin-top: 10px !important;
}

/* ---------------------------
   DOB WARNING RED
---------------------------- */
.warning-dob {
    color: #d00000 !important;
    font-size: 15px !important;
    font-weight: 700 !important;
    margin-top: 8px !important;
    margin-bottom: 20px !important;
    text-align: left;
}

/* MOBILE OPTIMIZATION */
@media (max-width: 768px) {
    .block-container {
        padding-left: 10px !important;
        padding-right: 10px !important;
    }
    input, textarea, select, .stButton > button {
        font-size: 16px !important;
    }
}

</style>
"""
st.markdown(CSS, unsafe_allow_html=True)

# ============================
# DATABASE
# ============================

def get_connection():
    return sqlite3.connect(DB_PATH, check_same_thread=False)

def init_db():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS feedback_questions(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            question_text TEXT,
            order_no INTEGER,
            is_active INTEGER DEFAULT 1
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS feedback(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_regd_no TEXT,
            branch_code TEXT,
            section TEXT,
            faculty_name TEXT,
            subject TEXT,
            department TEXT,
            q_scores TEXT,
            comments TEXT,
            created_at TEXT
        )
    """)

    conn.commit()

    cur.execute("SELECT COUNT(*) FROM feedback_questions")
    (count,) = cur.fetchone()

    if count == 0:
        qs = [
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
        for i, q in enumerate(qs, start=1):
            cur.execute("INSERT INTO feedback_questions(question_text,order_no,is_active) VALUES (?,?,1)", (q, i))
        conn.commit()

    conn.close()

def get_questions():
    conn = get_connection()
    df = pd.read_sql("SELECT * FROM feedback_questions WHERE is_active=1 ORDER BY order_no", conn)
    conn.close()
    return df

def save_feedback(reg, branch, sec, fac, sub, dept, scores, comments):
    conn = get_connection()
    cur = conn.cursor()

    score_str = ",".join(str(s) for s in scores)

    cur.execute("""
        INSERT INTO feedback(student_regd_no,branch_code,section,faculty_name,
        subject,department,q_scores,comments,created_at)
        VALUES (?,?,?,?,?,?,?,?,?)
    """, (reg, branch, sec, fac, sub, dept, score_str, comments, datetime.now().isoformat()))

    conn.commit()
    conn.close()

def feedback_exists(reg, branch, sec, faculty, subject):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT COUNT(*) FROM feedback
        WHERE student_regd_no=? AND branch_code=? 
        AND IFNULL(section,'')=IFNULL(?, '')
        AND faculty_name=? AND subject=?
    """, (reg, branch, sec, faculty, subject))
    (count,) = cur.fetchone()
    conn.close()
    return count > 0

# ============================
# LOAD CSV
# ============================

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
            if p2.exists(): p = p2
            else: continue
        df = pd.read_csv(p)
        df["branch_code"] = branch
        df["section"] = sec
        df.rename(columns={"Regd. No.": "regd_no", "Name": "name", "DOB": "dob"}, inplace=True)
        df["regd_no"] = df["regd_no"].astype(str).str.upper()
        df["dob"] = df["dob"].astype(str)
        all_rows.append(df)
    return pd.concat(all_rows, ignore_index=True)

@st.cache_data
def load_faculty():
    all_rows = []
    for branch, sec, file in FACULTY_FILE_CONFIG:
        p = FACULTY_DIR / file
        if not p.exists():
            p2 = BASE_DIR / file
            if p2.exists(): p = p2
            else: continue
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

# ============================
# AUTH
# ============================

def authenticate_student(reg, dob, branch, sec):
    reg = reg.upper().strip()
    dob = dob.strip()

    data = students_df[
        (students_df["regd_no"] == reg) &
        (students_df["dob"] == dob) &
        (students_df["branch_code"] == branch)
    ]

    if branch == "II-CSE":
        data = data[data["section"] == sec]

    if data.empty:
        return None
    
    return data.iloc[0]

def authenticate_fixed_user(username, password, role):
    creds = {
        "HOD": ("hod", "hod123"),
        "Principal": ("principal", "principal123"),
        "Admin": ("admin", "admin123"),
    }
    u, p = creds[role]
    return username == u and password == p

# ============================
# HEADER
# ============================

def render_header():
    if LOGO_PATH.exists():
        b64 = base64.b64encode(LOGO_PATH.read_bytes()).decode()
        st.markdown(
            f"""
            <div style="text-align:center; margin-top:20px;">
                <img src="data:image/png;base64,{b64}" style="width:135px;margin-bottom:5px;" />
                <div class="app-title">SJCET Feedback System</div>
            </div>
            """,
            unsafe_allow_html=True
        )
    else:
        st.markdown('<div class="app-title">SJCET Feedback System</div>', unsafe_allow_html=True)

# ============================
# STUDENT LOGIN
# ============================

def student_login_panel():
    st.markdown("### Student Login")

    col1, col2 = st.columns(2)
    with col1:
        reg = st.text_input("Register Number")
        dob = st.text_input("Date of Birth (exact as in sheet)",
                            placeholder="e.g. 01/01/2005")
    with col2:
        branch = st.selectbox("Year & Branch", ["Select", "II-CSD", "II-CSE", "III-CSE", "III-CSD"])
        sec = None
        if branch == "II-CSE":
            sec = st.selectbox("Section (only for II-CSE)", ["A", "B", "C"])
        else:
            st.write("Section: Not required")

    # Red warning message
    st.markdown("""
        <div class="warning-dob">
        ⚠️ If login fails, try swapping day & month.
        <br>Example: <b>01/04/2005 → 04/01/2005</b>
        </div>
    """, unsafe_allow_html=True)

    st.write("")

    if st.button("Login as Student"):
        if branch == "Select" or not reg or not dob:
            st.error("Please fill all fields.")
            return None

        row = authenticate_student(reg, dob, branch, sec)
        if row is None:
            st.error("Invalid login. Check DOB format.")
            return None

        st.success("Login successful.")
        return {
            "name": row["name"],
            "regd_no": row["regd_no"],
            "branch_code": row["branch_code"],
            "section": row["section"]
        }

    return None

# ============================
# STUDENT DASHBOARD
# ============================

def student_dashboard(info):
    st.markdown(f"### Hi **{info['name']}**, please give your valuable feedback.")

    branch = info["branch_code"]
    sec = info["section"]

    fac = faculty_df[
        (faculty_df["branch_code"] == branch) &
        (faculty_df["section"].fillna("") == (sec or ""))
    ]

    st.write("### Faculty for your section:")
    st.dataframe(fac[["sno", "faculty_name", "subject", "department"]])

    if fac.empty:
        st.warning("No faculty found.")
        return

    fname = st.selectbox("Select Faculty", fac["faculty_name"].unique())
    r = fac[fac["faculty_name"] == fname].iloc[0]
    subject = r["subject"]
    dept = r["department"]

    if feedback_exists(info["regd_no"], branch, sec, fname, subject):
        st.info("Feedback already submitted for this faculty.")
        return

    st.write(f"**Faculty:** {fname}")
    st.write(f"**Subject:** {subject}")
    st.write(f"**Department:** {dept}")

    qs = get_questions()
    scores = []

    for _, q in qs.iterrows():
        s = st.slider(q["question_text"], 1, 10, 5)
        scores.append(s)

    comments = st.text_area("Additional suggestions (optional)")

    if st.button("Submit Feedback"):
        save_feedback(info["regd_no"], branch, sec, fname, subject, dept, scores, comments)
        st.success("Feedback submitted successfully!")

# ============================
# HOD / PRINCIPAL PANELS
# ============================

def section_selector():
    col1, col2 = st.columns(2)
    with col1:
        branch = st.selectbox("Select Branch", ["II-CSD", "II-CSE", "III-CSE", "III-CSD"])
    with col2:
        sec = st.selectbox("Select Section", ["A","B","C"]) if branch=="II-CSE" else None
    return branch, sec

def render_feedback_analysis(branch, sec):
    fac = faculty_df[
        (faculty_df["branch_code"] == branch) &
        (faculty_df["section"].fillna("") == (sec or ""))
    ]
    st.write("### Faculty List")
    st.dataframe(fac[["sno","faculty_name","subject","department"]])

    fb = get_feedback_for_section(branch, sec)
    if fb.empty:
        st.info("No feedback yet.")
        return

    qs = get_questions()
    nq = len(qs)

    labels = [f"Q{i}" for i in range(1, nq+1)]
    def expand(row):
        arr = [int(x) for x in row["q_scores"].split(",")]
        while len(arr) < nq: arr.append(None)
        return pd.Series(arr, index=labels)

    fb_exp = pd.concat([fb, fb.apply(expand, axis=1)], axis=1)

    results = []
    for _, f in fac.iterrows():
        df = fb_exp[
            (fb_exp["faculty_name"]==f["faculty_name"]) &
            (fb_exp["subject"]==f["subject"])
        ]
        if df.empty: continue

        out = {"Faculty": f["faculty_name"], "Subject": f["subject"], "Responses": len(df)}
        for i in range(1, nq+1):
            out[f"Q{i}_avg"] = round(df[f"Q{i}"].mean(), 2)
        results.append(out)

    st.dataframe(pd.DataFrame(results))

def hod_panel():
    st.markdown("### HOD Dashboard")
    b, s = section_selector()
    render_feedback_analysis(b, s)

def principal_panel():
    st.markdown("### Principal Dashboard")
    b, s = section_selector()
    render_feedback_analysis(b, s)

# ============================
# ADMIN PANEL
# ============================

def admin_panel():
    st.markdown("### Admin Panel")

    tab1, tab2, tab3 = st.tabs(["Uploads", "Edit Questions", "Reset"])

    with tab1:
        st.write("#### Upload Students CSV")
        stu_file = st.file_uploader("Upload Students CSV")
        stu_name = st.text_input("Save as (e.g. S_IV-CSE_A.csv)")
        if st.button("Save Students CSV"):
            if stu_file and stu_name:
                with open(STUDENTS_DIR / stu_name, "wb") as f:
                    f.write(stu_file.getbuffer())
                st.success("Saved.")
            else:
                st.error("Provide file & name.")

        st.write("#### Upload Faculty CSV")
        fac_file = st.file_uploader("Upload Faculty CSV")
        fac_name = st.text_input("Save as (e.g. F_IV-CSE_A.csv)")
        if st.button("Save Faculty CSV"):
            if fac_file and fac_name:
                with open(FACULTY_DIR / fac_name, "wb") as f:
                    f.write(fac_file.getbuffer())
                st.success("Saved.")
            else:
                st.error("Provide file & name.")

    with tab2:
        st.write("#### Edit Questions")
        qs = get_questions()
        txt = "\n".join(qs["question_text"])
        new = st.text_area("Edit Questions (one per line)", value=txt, height=300)
        if st.button("Save Questions"):
            arr = [x.strip() for x in new.split("\n") if x.strip()]
            conn = get_connection()
            cur = conn.cursor()
            cur.execute("DELETE FROM feedback_questions")
            for i, q in enumerate(arr,1):
                cur.execute("INSERT INTO feedback_questions(question_text,order_no,is_active) VALUES (?,?,1)", (q,i))
            conn.commit()
            conn.close()
            st.success("Saved.")

    with tab3:
        st.write("#### Raw Feedback")
        conn = get_connection()
        df = pd.read_sql("SELECT * FROM feedback", conn)
        conn.close()
        st.dataframe(df)
        if st.button("RESET ALL FEEDBACK"):
            conn = get_connection()
            conn.execute("DELETE FROM feedback")
            conn.commit()
            conn.close()
            st.warning("All feedback cleared.")

# ============================
# LOGIN SCREEN
# ============================

def login_screen():
    render_header()

    st.markdown("### Login")

    role = st.selectbox("Select Role", ["Student", "HOD", "Principal", "Admin"])

    if role == "Student":
        info = student_login_panel()
        if info:
            st.session_state["auth_role"] = "Student"
            st.session_state["student_info"] = info
            st.rerun()
    else:
        st.markdown(f"### {role} Login")
        u = st.text_input("Username")
        p = st.text_input("Password", type="password")
        if st.button(f"Login as {role}"):
            if authenticate_fixed_user(u, p, role):
                st.session_state["auth_role"] = role
                st.rerun()
            else:
                st.error("Invalid credentials.")

# ============================
# MAIN
# ============================

def main():
    init_db()

    if "auth_role" not in st.session_state:
        st.session_state["auth_role"] = None

    if st.session_state["auth_role"] is None:
        login_screen()
    else:
        render_header()

        if st.button("Logout"):
            st.session_state["auth_role"] = None
            st.session_state.pop("student_info", None)
            st.rerun()

        role = st.session_state["auth_role"]
        if role == "Student":
            student_dashboard(st.session_state["student_info"])
        elif role == "HOD":
            hod_panel()
        elif role == "Principal":
            principal_panel()
        elif role == "Admin":
            admin_panel()

if __name__ == "__main__":
    main()
