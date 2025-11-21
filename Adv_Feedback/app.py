# ============================================================
#                    SJCET FEEDBACK SYSTEM
#               Fully White UI + Mobile Optimized
# ============================================================

import streamlit as st
import pandas as pd
import sqlite3
from pathlib import Path
from datetime import datetime
import base64

import plotly.express as px
import plotly.graph_objects as go

# -----------------------------
# PAGE CONFIG
# -----------------------------
st.set_page_config(
    page_title="SJCET Feedback System",
    layout="wide",
)

BASE_DIR = Path(__file__).parent
STUDENTS_DIR = BASE_DIR / "students_list"
FACULTY_DIR = BASE_DIR / "faculty_list"
DB_PATH = BASE_DIR / "feedback.db"
LOGO_PATH = BASE_DIR / "sjcet_logo.png"

# -----------------------------
# WHITE UI + MOBILE CSS
# -----------------------------
CSS = """
<style>

.stApp { background: white !important; }

/* No Sidebar */
section[data-testid="stSidebar"] {
    display: none !important;
}

/* Center container */
.block-container {
    max-width: 700px !important;
    margin: auto !important;
}

/* Make all text black */
html, body, p, label, span, div, input, textarea, select,
h1, h2, h3, h4, h5, h6 {
    color: black !important;
}

/* Inputs */
input, textarea {
    background: white !important;
    border: 1px solid #999 !important;
}

/* Placeholder text */
input::placeholder, textarea::placeholder {
    color: black !important;
    opacity: 0.7 !important;
}

/* Select boxes */
[data-baseweb="select"] > div {
    background: white !important;
    border: 1px solid #999 !important;
    color: black !important;
}
[data-baseweb="select"] svg {
    color: #8B4513 !important;   /* brown arrow */
}

/* Dropdown menu white */
[data-baseweb="popover"], [role="listbox"] {
    background: white !important;
}
[role="option"] {
    color: black !important;
}

/* Buttons white */
.stButton > button {
    width: 100% !important;
    background: white !important;
    color: black !important;
    border: 1px solid #999 !important;
    padding: 10px;
    border-radius: 8px;
    font-weight: 600;
}
.stButton > button:hover {
    background: #e6e6e6 !important;
}

/* File Uploader */
[data-testid="stFileUploaderDropzone"] {
    background: white !important;
    border: 1px solid #999 !important;
    color: black !important;
}
[data-testid="stFileUploaderDropzone"] button {
    background: white !important;
    color: black !important;
    border: 1px solid #999 !important;
}

/* Title style */
.app-title {
    font-size: 32px !important;
    font-weight: 900;
    text-align: center;
    color: #8B4513 !important;
}

/* Red DOB warning */
.warning-dob {
    color: #d00000 !important;
    font-size: 16px;
    font-weight: 700;
}

/* Mobile */
@media (max-width: 768px) {
    input, textarea, select, .stButton > button {
        font-size: 17px !important;
    }
}
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)

# -----------------------------
# DATABASE
# -----------------------------
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
            "Teacher encourages creativity",
            "Teacher is courteous and impartial",
            "Teacher completes syllabus",
            "Teacher evaluates fairly",
            "Teacher returns scripts promptly",
            "Teacher helps needy students",
            "Teacher gives practical knowledge",
            "Overall rating of the Teacher",
        ]
        for i, q in enumerate(qs, 1):
            cur.execute(
                "INSERT INTO feedback_questions(question_text, order_no) VALUES(?,?)",
                (q, i),
            )
        conn.commit()

    conn.close()

def get_questions():
    conn = get_connection()
    df = pd.read_sql("SELECT * FROM feedback_questions ORDER BY order_no", conn)
    conn.close()
    return df

def save_feedback(reg, branch, sec, fac, sub, dept, scores, comments):
    conn = get_connection()
    cur = conn.cursor()
    s = ",".join(str(x) for x in scores)

    cur.execute("""
        INSERT INTO feedback(student_regd_no,branch_code,section,
        faculty_name,subject,department,q_scores,comments,created_at)
        VALUES (?,?,?,?,?,?,?,?,?)
    """, (reg, branch, sec, fac, sub, dept, s, comments, datetime.now().isoformat()))

    conn.commit()
    conn.close()

def feedback_exists(reg, branch, sec, fac, sub):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT COUNT(*) FROM feedback
        WHERE student_regd_no=? AND branch_code=?
        AND IFNULL(section,'') = IFNULL(?, '')
        AND faculty_name=? AND subject=?
    """, (reg, branch, sec, fac, sub))
    (count,) = cur.fetchone()
    conn.close()
    return count > 0

def get_feedback_for_section(branch, section):
    conn = get_connection()
    df = pd.read_sql_query("""
        SELECT * FROM feedback
        WHERE branch_code=?
        AND IFNULL(section,'') = IFNULL(?, '')
    """, conn, params=(branch, section))
    conn.close()
    return df

# -----------------------------
# LOAD CSV
# -----------------------------
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
    rows = []
    for b, s, f in STUDENT_FILE_CONFIG:
        p = STUDENTS_DIR / f
        if not p.exists():
            continue
        df = pd.read_csv(p)
        df["branch_code"] = b
        df["section"] = s
        df.rename(columns={"Regd. No.": "regd_no", "Name": "name", "DOB": "dob"}, inplace=True)
        df["regd_no"] = df["regd_no"].astype(str).str.upper()
        df["dob"] = df["dob"].astype(str)
        rows.append(df)
    return pd.concat(rows, ignore_index=True)

@st.cache_data
def load_faculty():
    rows = []
    for b, s, f in FACULTY_FILE_CONFIG:
        p = FACULTY_DIR / f
        if not p.exists():
            continue
        df = pd.read_csv(p, encoding="latin1")
        df["branch_code"] = b
        df["section"] = s
        df.rename(columns={
            "S.No": "sno",
            "Faculty Name": "faculty_name",
            "Subject (Full Form)": "subject",
            "Department": "department"
        }, inplace=True)
        rows.append(df)
    return pd.concat(rows, ignore_index=True)

students_df = load_students()
faculty_df = load_faculty()

# -----------------------------
# AUTH
# -----------------------------
def authenticate_student(reg, dob, branch, sec):
    reg = reg.strip().upper()
    dob = dob.strip()

    d = students_df[
        (students_df["regd_no"] == reg) &
        (students_df["dob"] == dob) &
        (students_df["branch_code"] == branch)
    ]

    if branch == "II-CSE":
        d = d[d["section"] == sec]

    if d.empty:
        return None
    return d.iloc[0]

def auth_user(username, password, role):
    creds = {
        "HOD": ("hod", "hod123"),
        "Principal": ("principal", "principal123"),
        "Admin": ("admin", "admin123"),
    }
    return (username, password) == creds[role]

# -----------------------------
# HEADER
# -----------------------------
def render_header():
    if LOGO_PATH.exists():
        b64 = base64.b64encode(LOGO_PATH.read_bytes()).decode()
        st.markdown(
            f"""
            <div style="text-align:center;margin-top:18px;margin-bottom:5px;">
                <img src="data:image/png;base64,{b64}"
                     style="width:140px;margin-bottom:10px;" />
                <div class="app-title">SJCET Feedback System</div>
            </div>
            """,
            unsafe_allow_html=True
        )
    else:
        st.markdown('<div class="app-title">SJCET Feedback System</div>', unsafe_allow_html=True)

# -----------------------------
# STUDENT LOGIN
# -----------------------------
def student_login_panel():
    st.markdown("### Student Login")

    col1, col2 = st.columns(2)
    with col1:
        reg = st.text_input("Register Number")
        dob = st.text_input("Date of Birth (exact as in sheet)", placeholder="e.g. 01/01/2005")
    with col2:
        branch = st.selectbox("Year & Branch", ["Select", "II-CSD", "II-CSE", "III-CSE", "III-CSD"])
        sec = st.selectbox("Section", ["A","B","C"]) if branch=="II-CSE" else None

    st.markdown("""
        <div class="warning-dob">
        ⚠️ If login fails, try swapping day & month (01/04/2005 → 04/01/2005)
        </div>
    """, unsafe_allow_html=True)

    if st.button("Login as Student"):
        if branch == "Select":
            st.error("Please select branch.")
            return None
        user = authenticate_student(reg, dob, branch, sec)
        if user is None:
            st.error("Invalid Register Number / DOB / Section")
            return None
        st.success("Login successful.")
        return {
            "name": user["name"],
            "regd_no": user["regd_no"],
            "branch_code": user["branch_code"],
            "section": user["section"]
        }

    return None

# -----------------------------
# STUDENT DASHBOARD
# -----------------------------
def student_dashboard(info):
    st.markdown(f"### Hi **{info['name']}**, please give your valuable feedback.")

    branch = info["branch_code"]
    sec = info["section"]

    f = faculty_df[
        (faculty_df["branch_code"] == branch) &
        (faculty_df["section"].fillna("") == (sec or ""))
    ]
    st.write("### Faculty for your section")
    st.dataframe(f[["sno","faculty_name","subject","department"]])

    fname = st.selectbox("Select Faculty", f["faculty_name"].unique())
    row = f[f["faculty_name"] == fname].iloc[0]
    subject = row["subject"]
    dept = row["department"]

    if feedback_exists(info["regd_no"], branch, sec, fname, subject):
        st.info("Feedback already submitted.")
        return

    qs = get_questions()
    scores = []
    for _, q in qs.iterrows():
        sc = st.slider(q["question_text"], 1, 10, 5)
        scores.append(sc)

    comments = st.text_area("Additional suggestions (optional)")

    if st.button("Submit Feedback"):
        save_feedback(info["regd_no"], branch, sec, fname, subject, dept, scores, comments)
        st.success("Thank you! Feedback recorded.")

# -----------------------------
# HELPER: EMOJI MAPPING
# -----------------------------
def score_to_emoji(avg):
    if avg is None:
        return "❔"
    try:
        v = float(avg)
    except:
        return "❔"
    if v >= 8:
        return "😍"
    elif v >= 6:
        return "🙂"
    elif v >= 4:
        return "😐"
    else:
        return "😣"

# -----------------------------
# HOD / PRINCIPAL HELPERS
# -----------------------------
def section_selector():
    col1, col2 = st.columns(2)
    with col1:
        branch = st.selectbox("Select Branch", ["II-CSD","II-CSE","III-CSE","III-CSD"])
    with col2:
        sec = st.selectbox("Select Section", ["A","B","C"]) if branch=="II-CSE" else None
    return branch, sec

def render_feedback_analysis(branch, sec, view_mode):
    # Faculty list for this section
    f = faculty_df[
        (faculty_df["branch_code"] == branch) &
        (faculty_df["section"].fillna("") == (sec or ""))
    ]

    st.write("### Faculty in this Branch & Section")
    st.dataframe(f[["sno", "faculty_name", "subject", "department"]])

    fb = get_feedback_for_section(branch, sec)
    if fb.empty:
        st.info("No feedback submitted yet for this branch/section.")
        return

    qs = get_questions()
    nq = len(qs)

    # Expand q_scores to Q1..Qn columns
    labels = [f"Q{i}" for i in range(1, nq+1)]
    def exp(row):
        arr = [int(x) for x in str(row["q_scores"]).split(",")]
        while len(arr) < nq:
            arr.append(None)
        return pd.Series(arr, index=labels)

    fb_full = pd.concat([fb, fb.apply(exp, axis=1)], axis=1)

    # Build faculty summary table (per-faculty averages)
    summary_rows = []
    for _, prof in f.iterrows():
        d = fb_full[
            (fb_full["faculty_name"] == prof["faculty_name"]) &
            (fb_full["subject"] == prof["subject"])
        ]
        if d.empty:
            continue

        row = {
            "Faculty": prof["faculty_name"],
            "Subject": prof["subject"],
            "Department": prof["department"],
            "Responses": len(d),
        }
        q_avgs = []
        for i in range(1, nq+1):
            col_q = f"Q{i}"
            avg_i = d[col_q].mean()
            row[f"Q{i}_avg"] = round(avg_i, 2)
            q_avgs.append(avg_i)
        overall = sum(q_avgs) / len(q_avgs) if q_avgs else 0
        row["Overall Avg"] = round(overall, 2)
        row["Overall %"] = round((overall / 10) * 100, 1)  # percentage
        row["Emoji"] = score_to_emoji(overall)
        summary_rows.append(row)

    if not summary_rows:
        st.info("No feedback entries matching the listed faculty.")
        return

    fac_summary_df = pd.DataFrame(summary_rows)

    # Question-wise average (section level)
    q_rows = []
    for i, (_, qrow) in enumerate(qs.iterrows(), start=1):
        col = f"Q{i}_avg"
        if col in fac_summary_df.columns:
            q_rows.append({
                "Question": qrow["question_text"],
                "Average Score": fac_summary_df[col].mean()
            })
    q_avg_df = pd.DataFrame(q_rows)

    # Faculty overall rating table
    fac_overall_df = fac_summary_df[["Faculty","Subject","Department","Responses","Overall Avg","Overall %","Emoji"]].copy()

    # ---------------- VIEW SWITCHING ----------------
    if view_mode == "Faculty summary (table + emojis)":
        st.write("### Faculty-wise Summary 😍🙂😐😣")
        st.dataframe(fac_summary_df)

    elif view_mode == "Question-wise average (table)":
        st.write("### Question-wise Average (Section Level)")
        st.dataframe(q_avg_df)

    elif view_mode == "Overall faculty rating (horizontal bar)":
        st.write("### Overall Faculty Rating (Horizontal Bar)")
        if not fac_overall_df.empty:
            chart_df = fac_overall_df.sort_values("Overall Avg", ascending=True)
            chart_df["Label"] = chart_df["Faculty"] + " (" + chart_df["Emoji"] + ")"
            fig = px.bar(
                chart_df,
                x="Overall Avg",
                y="Label",
                orientation="h",
                text="Overall Avg",
            )
            fig.update_layout(
                xaxis_title="Average Rating (1–10)",
                yaxis_title="Faculty",
                margin=dict(l=10,r=10,t=30,b=10),
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No faculty overall data available to plot.")

    elif view_mode == "3D faculty rating matrix":
        st.write("### 3D Surface – Faculty vs Questions")
        # Build Z matrix :: faculties x questions
        fac_names = fac_summary_df["Faculty"].tolist()
        q_names = [f"Q{i}" for i in range(1, nq+1)]
        z = []
        for _, r in fac_summary_df.iterrows():
            row_vals = []
            for i in range(1, nq+1):
                row_vals.append(r.get(f"Q{i}_avg", 0))
            z.append(row_vals)

        if z:
            fig = go.Figure(
                data=[
                    go.Surface(
                        z=z,
                        x=list(range(1, nq+1)),
                        y=list(range(1, len(fac_names)+1)),
                        colorscale="Viridis",
                    )
                ]
            )
            fig.update_layout(
                scene=dict(
                    xaxis_title="Question Index",
                    yaxis_title="Faculty Index",
                    zaxis_title="Average Score",
                    xaxis=dict(
                        tickmode="array",
                        tickvals=list(range(1, nq+1)),
                    ),
                ),
                margin=dict(l=10, r=10, t=30, b=10),
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Not enough data for 3D visualization.")

    elif view_mode == "Overall faculty percentage (pie chart)":
        st.write("### Overall Faculty Feedback Percentage (Pie)")
        if not fac_overall_df.empty:
            fig = px.pie(
                fac_overall_df,
                names="Faculty",
                values="Overall %", 
                hover_data=["Subject","Department"],
                hole=0.3,
            )
            fig.update_traces(textinfo="percent+label")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No faculty percentage data to display.")

    elif view_mode == "Top & Bottom 3 Faculty":
        st.write("### Top & Bottom 3 Faculty (by Overall Avg)")
        df_sorted = fac_overall_df.sort_values("Overall Avg", ascending=False)

        top3 = df_sorted.head(3)
        bottom3 = df_sorted.tail(3)

        st.write("#### 🏆 Top 3 Faculty")
        st.dataframe(top3)

        st.write("#### ⚠️ Bottom 3 Faculty")
        st.dataframe(bottom3)

    elif view_mode == "Raw feedback records (no student IDs)":
        st.write("### Raw Feedback Entries (Student Info Hidden)")
        fb_copy = fb.copy()
        # Remove student register number from display for privacy
        if "student_regd_no" in fb_copy.columns:
            fb_copy = fb_copy.drop(columns=["student_regd_no"])
        st.dataframe(fb_copy)

# -----------------------------
# HOD PANEL
# -----------------------------
def hod_panel():
    st.markdown("### HOD Dashboard")
    branch, sec = section_selector()

    view_mode = st.selectbox(
        "Select Feedback View",
        [
            "Faculty summary (table + emojis)",
            "Question-wise average (table)",
            "Overall faculty rating (horizontal bar)",
            "3D faculty rating matrix",
            "Overall faculty percentage (pie chart)",
            "Top & Bottom 3 Faculty",
            "Raw feedback records (no student IDs)",
        ]
    )

    render_feedback_analysis(branch, sec, view_mode)

# -----------------------------
# PRINCIPAL PANEL
# -----------------------------
def principal_panel():
    st.markdown("### Principal Dashboard")
    branch, sec = section_selector()

    view_mode = st.selectbox(
        "Select Feedback View",
        [
            "Faculty summary (table + emojis)",
            "Question-wise average (table)",
            "Overall faculty rating (horizontal bar)",
            "3D faculty rating matrix",
            "Overall faculty percentage (pie chart)",
            "Top & Bottom 3 Faculty",
            "Raw feedback records (no student IDs)",
        ]
    )

    render_feedback_analysis(branch, sec, view_mode)

# -----------------------------
# ADMIN PANEL
# -----------------------------
def admin_panel():
    st.markdown("### Admin Panel")
    tabs = st.tabs(["Uploads", "Edit Questions", "Reset"])

    # UPLOADS
    with tabs[0]:
        st.write("#### Upload Students CSV")
        f1 = st.file_uploader("Upload Students CSV")
        name1 = st.text_input("Save as filename (e.g. S_IV-CSE_A.csv)")
        if st.button("Save Students CSV"):
            if f1 and name1:
                with open(STUDENTS_DIR / name1, "wb") as f:
                    f.write(f1.getbuffer())
                st.success("Saved.")
            else:
                st.error("Select file & enter name.")

        st.write("#### Upload Faculty CSV")
        f2 = st.file_uploader("Upload Faculty CSV")
        name2 = st.text_input("Save as filename (e.g. F_IV-CSE_A.csv)")
        if st.button("Save Faculty CSV"):
            if f2 and name2:
                with open(FACULTY_DIR / name2, "wb") as f:
                    f.write(f2.getbuffer())
                st.success("Saved.")
            else:
                st.error("Select file & enter name.")

    # EDIT QUESTIONS
    with tabs[1]:
        st.write("#### Edit Feedback Questions")
        qs = get_questions()
        t = "\n".join(qs["question_text"])
        new = st.text_area("One question per line", value=t, height=300)
        if st.button("Save Questions"):
            arr = [x.strip() for x in new.split("\n") if x.strip()]
            conn = get_connection()
            c = conn.cursor()
            c.execute("DELETE FROM feedback_questions")
            for i, q in enumerate(arr, 1):
                c.execute("INSERT INTO feedback_questions(question_text, order_no) VALUES(?,?)", (q, i))
            conn.commit()
            conn.close()
            st.success("Updated!")

    # RESET
    with tabs[2]:
        st.write("#### Raw Feedback")
        conn = get_connection()
        df = pd.read_sql("SELECT * FROM feedback", conn)
        conn.close()
        # Hide student_regd_no here as well for safety
        if "student_regd_no" in df.columns:
            df = df.drop(columns=["student_regd_no"])
        st.dataframe(df)

        if st.button("RESET ALL FEEDBACK"):
            conn = get_connection()
            conn.execute("DELETE FROM feedback")
            conn.commit()
            conn.close()
            st.warning("All feedback cleared!")

# -----------------------------
# LOGIN SCREEN
# -----------------------------
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
            if auth_user(u, p, role):
                st.session_state["auth_role"] = role
                st.rerun()
            else:
                st.error("Invalid username or password.")

# -----------------------------
# MAIN
# -----------------------------
def main():
    init_db()

    if "auth_role" not in st.session_state:
        st.session_state["auth_role"] = None

    if st.session_state["auth_role"] is None:
        login_screen()
        return

    render_header()

    if st.button("Logout"):
        st.session_state["auth_role"] = None
        st.session_state.pop("student_info", None)
        st.rerun()

    role = st.session_state["auth_role"]

    if role == "Student":
        student_info = st.session_state.get("student_info")
        if not student_info:
            st.session_state["auth_role"] = None
            st.rerun()
        student_dashboard(student_info)

    elif role == "HOD":
        hod_panel()

    elif role == "Principal":
        principal_panel()

    elif role == "Admin":
        admin_panel()

if __name__ == "__main__":
    main()
