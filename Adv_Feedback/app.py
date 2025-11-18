# app.py

import streamlit as st
import pandas as pd
import sqlite3
from pathlib import Path
from datetime import datetime
import base64

# -------------------------
# CONFIG & PATHS
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
# GLOBAL CSS (single theme, mobile-friendly, no sidebar)
# -------------------------

app_css = """
<style>
/* Hide Streamlit sidebar entirely */
div[data-testid="stSidebar"] {
    display: none !important;
}

/* Center main content, nice width for mobile + desktop */
.block-container {
    max-width: 1100px;
    padding-top: 1.5rem;
    padding-bottom: 2.5rem;
    margin-left: auto;
    margin-right: auto;
}

/* Background: teal gradient like your reference app */
.stApp {
    background: radial-gradient(circle at top,
        #014451 0%,
        #012b36 40%,
        #02141d 80%);
    color: #f9fafb;
}

/* Simple login / content card with white background */
.login-card {
    background: #ffffff;
    color: #111827;
    border-radius: 20px;
    padding: 26px 26px 30px 26px;
    box-shadow: 0 22px 70px rgba(0,0,0,0.60);
    margin-top: 16px;
}

/* Header title style */
.app-title {
    text-align: center;
    font-weight: 700;
    font-size: 32px;
    letter-spacing: 0.03em;
    margin: 10px 0 0 0;
}

/* Small helper text */
.helper-text {
    font-size: 0.85rem;
    color: #6b7280;
    margin-top: 6px;
}

/* Tables rounded a bit */
[data-testid="stDataFrame"], .stTable {
    border-radius: 0.75rem;
    overflow: hidden;
}

/* Button full width on small screens */
@media (max-width: 768px) {
    button[kind="primary"] {
        width: 100% !important;
    }
}
</style>
"""
st.markdown(app_css, unsafe_allow_html=True)

# -------------------------
# DATABASE SETUP
# -------------------------

def get_connection():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    return conn

def init_db():
    conn = get_connection()
    cur = conn.cursor()

    # Feedback questions table
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS feedback_questions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            question_text TEXT NOT NULL,
            order_no INTEGER NOT NULL,
            is_active INTEGER NOT NULL DEFAULT 1
        )
        """
    )

    # Feedback table
    cur.execute(
        """
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
        """
    )

    conn.commit()

    # Insert default questions if none
    cur.execute("SELECT COUNT(*) FROM feedback_questions")
    (count,) = cur.fetchone()
    if count == 0:
        default_questions = [
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
        for i, q in enumerate(default_questions, start=1):
            cur.execute(
                "INSERT INTO feedback_questions (question_text, order_no, is_active) VALUES (?, ?, ?)",
                (q, i, 1),
            )
        conn.commit()

    conn.close()

def get_questions():
    conn = get_connection()
    df = pd.read_sql_query(
        "SELECT id, question_text, order_no FROM feedback_questions WHERE is_active = 1 ORDER BY order_no ASC",
        conn,
    )
    conn.close()
    return df

def save_feedback(student_regd_no, branch_code, section, faculty_name, subject, department, scores_list, comments):
    conn = get_connection()
    cur = conn.cursor()
    scores_str = ",".join(str(int(x)) for x in scores_list)
    cur.execute(
        """
        INSERT INTO feedback
        (student_regd_no, branch_code, section, faculty_name, subject, department, q_scores, comments, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            student_regd_no,
            branch_code,
            section,
            faculty_name,
            subject,
            department,
            scores_str,
            comments,
            datetime.now().isoformat(timespec="seconds"),
        ),
    )
    conn.commit()
    conn.close()

def feedback_exists(student_regd_no, branch_code, section, faculty_name, subject):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT COUNT(*) FROM feedback
        WHERE student_regd_no = ?
          AND branch_code = ?
          AND ifnull(section, '') = ifnull(?, '')
          AND faculty_name = ?
          AND subject = ?
        """,
        (student_regd_no, branch_code, section, faculty_name, subject),
    )
    (count,) = cur.fetchone()
    conn.close()
    return count > 0

def get_feedback_for_section(branch_code, section):
    conn = get_connection()
    query = """
        SELECT * FROM feedback
        WHERE branch_code = ?
          AND ifnull(section, '') = ifnull(?, '')
    """
    df = pd.read_sql_query(query, conn, params=(branch_code, section))
    conn.close()
    return df

# -------------------------
# LOAD CSV DATA (cached)
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
    for branch_code, section, filename in STUDENT_FILE_CONFIG:
        local_path = STUDENTS_DIR / filename
        if not local_path.exists():
            alt_path = BASE_DIR / filename
            if alt_path.exists():
                local_path = alt_path
            else:
                continue

        df = pd.read_csv(local_path)
        df["branch_code"] = branch_code
        df["section"] = section

        df = df.rename(
            columns={
                "Regd. No.": "regd_no",
                "Name": "name",
                "DOB": "dob",
                "Year & Br.": "year_branch",
                "Parent Ph.-1": "parent_phone",
                "Student Ph.1": "student_phone",
                "email ID": "email",
                "Father Name": "father_name",
            }
        )
        all_rows.append(df)

    if not all_rows:
        return pd.DataFrame()

    students_df = pd.concat(all_rows, ignore_index=True)
    students_df["dob"] = students_df["dob"].astype(str).str.strip()
    students_df["regd_no"] = students_df["regd_no"].astype(str).str.strip().str.upper()
    return students_df

@st.cache_data
def load_faculty():
    all_rows = []
    for branch_code, section, filename in FACULTY_FILE_CONFIG:
        local_path = FACULTY_DIR / filename
        if not local_path.exists():
            alt_path = BASE_DIR / filename
            if alt_path.exists():
                local_path = alt_path
            else:
                continue

        df = pd.read_csv(local_path, encoding="latin1")
        df["branch_code"] = branch_code
        df["section"] = section
        df = df.rename(
            columns={
                "S.No": "sno",
                "Faculty Name": "faculty_name",
                "Subject (Full Form)": "subject",
                "Department": "department",
            }
        )
        all_rows.append(df)

    if not all_rows:
        return pd.DataFrame()

    fac_df = pd.concat(all_rows, ignore_index=True)
    return fac_df

students_df = load_students()
faculty_df = load_faculty()

# -------------------------
# AUTH HELPERS
# -------------------------

def authenticate_student(regd_no, dob, branch_code, section):
    if students_df.empty:
        return None

    regd_no = str(regd_no).strip().upper()
    dob_str = str(dob).strip()

    subset = students_df[
        (students_df["regd_no"] == regd_no)
        & (students_df["dob"] == dob_str)
        & (students_df["branch_code"] == branch_code)
    ]
    if branch_code == "II-CSE":
        subset = subset[subset["section"] == section]

    if subset.empty:
        return None
    return subset.iloc[0]

def authenticate_fixed_user(username, password, role):
    creds = {
        "HOD": ("hod", "hod123"),
        "Principal": ("principal", "principal123"),
        "Admin": ("admin", "admin123"),
    }
    u, p = creds[role]
    return username == u and password == p

# -------------------------
# STUDENT UI
# -------------------------

def student_login_panel():
    st.subheader("Student Login")

    col1, col2 = st.columns(2)
    with col1:
        regd_no = st.text_input("Register Number")
        dob = st.text_input(
            "Date of Birth (exact as in sheet)",
            placeholder="e.g. 01/01/2005",
        )
    with col2:
        branch_choice = st.selectbox(
            "Year & Branch",
            ["Select", "II-CSD", "II-CSE", "III-CSE", "III-CSD"],
            index=0,
        )

        section_choice = None
        if branch_choice == "II-CSE":
            section_choice = st.selectbox("Section (only for II-CSE)", ["A", "B", "C"])
        else:
            st.write("Section: Not required for this branch")

    # Suggestion message BEFORE login button
    # Warning message:
        st.markdown(
                """
                <div style="
                    color: #ff0000;
                    font-size: 18px;
                    font-weight: 600;
                    margin-top: 8px;
                    margin-bottom: 18px;
                ">
                    ⚠️ If login fails, try swapping the day and month in your date of birth.
                    <br>For example: <b>01/04/2005 → 04/01/2005</b>.
                </div>
                """,
                unsafe_allow_html=True
            )
            
            # Add space before the button:
            st.write("")
            st.write("")

    if st.button("Login as Student"):
        if not regd_no or not dob or branch_choice == "Select":
            st.error("Please fill Register Number, Date of Birth and Year & Branch.")
            return None

        student_row = authenticate_student(regd_no, dob, branch_choice, section_choice)
        if student_row is None:
            st.error("Invalid credentials or wrong branch/section.")
            return None

        st.success("Login successful.")
        return {
            "regd_no": student_row["regd_no"],
            "name": student_row["name"],
            "branch_code": student_row["branch_code"],
            "section": student_row["section"],
        }

    return None

def student_dashboard(student_info):
    st.subheader("Student Feedback Panel")

    student_name = student_info["name"]
    regd_no = student_info["regd_no"]
    branch_code = student_info["branch_code"]
    section = student_info["section"]

    st.markdown(
        f"### Hi **{student_name}**, please give your genuine and valuable feedback to improve the quality of education."
    )

    fac_subset = faculty_df[
        (faculty_df["branch_code"] == branch_code)
        & (faculty_df["section"].fillna("") == (section or "").strip())
    ]
    st.write("### Faculty for your Section:")
    st.dataframe(fac_subset[["sno", "faculty_name", "subject", "department"]])

    if fac_subset.empty:
        st.warning("No faculty data found for your section. Please contact admin.")
        return

    st.write("### Select Faculty to Give Feedback")

    faculty_names = fac_subset["faculty_name"].unique().tolist()
    selected_faculty = st.selectbox(
        "Search / select faculty name",
        faculty_names,
    )

    if not selected_faculty:
        return

    fac_row = fac_subset[fac_subset["faculty_name"] == selected_faculty].iloc[0]
    subject = fac_row["subject"]
    department = fac_row["department"]

    st.markdown(f"**Faculty Name:** {selected_faculty}")
    st.markdown(f"**Subject:** {subject}")
    st.markdown(f"**Department:** {department}")

    if feedback_exists(regd_no, branch_code, section, selected_faculty, subject):
        st.info("You have already submitted feedback for this faculty.")
        return

    questions_df = get_questions()
    scores = []

    st.write("#### Please rate the following on a scale of 1 to 10:")
    for _, row in questions_df.iterrows():
        q_text = row["question_text"]
        score = st.slider(
            q_text,
            min_value=1,
            max_value=10,
            value=5,
            key=f"q_{row['id']}",
        )
        scores.append(score)

    comments = st.text_area(
        "Any additional insights, suggestions or feedback (optional)",
        placeholder="Write your feedback in English...",
    )

    if st.button("Submit Feedback"):
        save_feedback(
            student_regd_no=regd_no,
            branch_code=branch_code,
            section=section,
            faculty_name=selected_faculty,
            subject=subject,
            department=department,
            scores_list=scores,
            comments=comments,
        )
        st.success(
            "Thank you! Your feedback has been submitted successfully. You cannot submit again for this faculty."
        )

# -------------------------
# HOD / PRINCIPAL UI
# -------------------------

def section_selector():
    col1, col2 = st.columns(2)
    with col1:
        branch_choice = st.selectbox(
            "Year & Branch",
            ["II-CSD", "II-CSE", "III-CSE", "III-CSD"],
        )
    with col2:
        if branch_choice == "II-CSE":
            section_choice = st.selectbox("Section", ["A", "B", "C"])
        else:
            section_choice = None
            st.write("Section: Not required for this branch")
    return branch_choice, section_choice

def render_feedback_analysis(branch_code, section):
    fac_subset = faculty_df[
        (faculty_df["branch_code"] == branch_code)
        & (faculty_df["section"].fillna("") == (section or "").strip())
    ]

    if fac_subset.empty:
        st.warning("No faculty data found for this branch/section.")
        return

    st.write("### Faculty in this Branch / Section")
    st.dataframe(fac_subset[["sno", "faculty_name", "subject", "department"]])

    fb_df = get_feedback_for_section(branch_code, section)
    if fb_df.empty:
        st.info("No feedback submitted yet for this branch/section.")
        return

    st.write("### Aggregated Feedback (All Students)")

    questions_df = get_questions()
    num_q = len(questions_df)
    q_labels = [f"Q{i}" for i in range(1, num_q + 1)]

    def expand_scores(row):
        parts = str(row["q_scores"]).split(",")
        parts = [int(x) for x in parts]
        if len(parts) < num_q:
            parts = parts + [None] * (num_q - len(parts))
        return pd.Series(parts[:num_q], index=q_labels)

    scores_expanded = fb_df.apply(expand_scores, axis=1)
    fb_full = pd.concat([fb_df, scores_expanded], axis=1)

    results = []
    for _, fac in fac_subset.iterrows():
        f_name = fac["faculty_name"]
        subj = fac["subject"]
        fac_fb = fb_full[
            (fb_full["faculty_name"] == f_name) & (fb_full["subject"] == subj)
        ]
        if fac_fb.empty:
            continue

        row_result = {
            "Faculty Name": f_name,
            "Subject": subj,
            "Department": fac["department"],
            "Responses": len(fac_fb),
        }
        for i, (_, q_row) in enumerate(questions_df.iterrows(), start=1):
            avg_score = fac_fb[f"Q{i}"].mean()
            row_result[f"Q{i}_avg"] = round(avg_score, 2)
        results.append(row_result)

    if not results:
        st.info("No feedback entries found for listed faculty.")
        return

    res_df = pd.DataFrame(results)
    st.dataframe(res_df)

    st.write("### Question-wise Average (Section Level)")
    q_avg_data = {}
    for i, (_, qrow) in enumerate(questions_df.iterrows(), start=1):
        col_name = f"Q{i}_avg"
        if col_name in res_df.columns:
            q_avg_data[qrow["question_text"]] = res_df[col_name].mean()

    q_avg_df = pd.DataFrame(
        {"Question": list(q_avg_data.keys()), "Average Score": list(q_avg_data.values())}
    )
    st.dataframe(q_avg_df)

    st.write("#### Visual: Question-wise Average (Bar Chart)")
    st.bar_chart(q_avg_df.set_index("Question"))

    st.write("#### Visual: Overall Average per Faculty")
    fac_overall = []
    for _, row in res_df.iterrows():
        q_cols = [c for c in res_df.columns if c.startswith("Q") and c.endswith("_avg")]
        overall_avg = row[q_cols].mean()
        fac_overall.append(
            {"Faculty": f"{row['Faculty Name']} ({row['Subject']})", "Overall Avg": overall_avg}
        )
    fac_overall_df = pd.DataFrame(fac_overall)
    st.bar_chart(fac_overall_df.set_index("Faculty"))

def hod_panel():
    st.subheader("HOD Dashboard")
    branch_code, section = section_selector()
    render_feedback_analysis(branch_code, section)

def principal_panel():
    st.subheader("Principal Dashboard")
    branch_code, section = section_selector()
    render_feedback_analysis(branch_code, section)

# -------------------------
# ADMIN UI
# -------------------------

def admin_panel():
    st.subheader("Admin Panel")

    tab1, tab2, tab3 = st.tabs(
        ["Departments & Uploads", "Edit Questions", "Reset / View Raw Feedback"]
    )

    with tab1:
        st.markdown("#### Upload New Student / Faculty Lists (CSV)")
        st.write("Current departments (for info): CSE, CSD, ME, CE, CAI, ECE, EEE")
        st.write("Years: I, II, III, IV | Sections: A, B, C, D (optional)")

        st.markdown("##### Upload Students List (CSV)")
        stu_file = st.file_uploader(
            "Upload students_list CSV", type=["csv"], key="stu_upload"
        )
        stu_target_name = st.text_input(
            "Save as file name (e.g. S_IV-CSE_A.csv)", key="stu_name"
        )

        if st.button("Save Students CSV"):
            if stu_file and stu_target_name:
                save_path = STUDENTS_DIR / stu_target_name
                with open(save_path, "wb") as f:
                    f.write(stu_file.getbuffer())
                st.success(f"Saved students file as {save_path}")
            else:
                st.error("Please select a file and enter target file name.")

        st.markdown("##### Upload Faculty List (CSV)")
        fac_file = st.file_uploader(
            "Upload faculty_list CSV", type=["csv"], key="fac_upload"
        )
        fac_target_name = st.text_input(
            "Save as file name (e.g. F_IV-CSE_A.csv)", key="fac_name"
        )

        if st.button("Save Faculty CSV"):
            if fac_file and fac_target_name:
                save_path = FACULTY_DIR / fac_target_name
                with open(save_path, "wb") as f:
                    f.write(fac_file.getbuffer())
                st.success(f"Saved faculty file as {save_path}")
            else:
                st.error("Please select a file and enter target file name.")

    with tab2:
        st.subheader("Edit Feedback Questions")

        questions_df = get_questions().sort_values("order_no")
        current_text = "\n".join(questions_df["question_text"].tolist())
        new_text = st.text_area(
            "Edit questions (one per line in order):",
            value=current_text,
            height=300,
        )

        if st.button("Save Questions"):
            lines = [l.strip() for l in new_text.split("\n") if l.strip()]
            if not lines:
                st.error("At least one question is required.")
            else:
                conn = get_connection()
                cur = conn.cursor()
                cur.execute("DELETE FROM feedback_questions")
                for i, q in enumerate(lines, start=1):
                    cur.execute(
                        "INSERT INTO feedback_questions (question_text, order_no, is_active) VALUES (?, ?, ?)",
                        (q, i, 1),
                    )
                conn.commit()
                conn.close()
                st.success(
                    "Questions updated successfully. (Reload page to see effect everywhere)"
                )

    with tab3:
        st.subheader("Raw Feedback & Reset Options")
        conn = get_connection()
        fb_df = pd.read_sql_query("SELECT * FROM feedback", conn)
        conn.close()

        st.write(f"Total feedback records: {len(fb_df)}")
        st.dataframe(fb_df)

        if st.button("Reset All Feedback (Dangerous)"):
            conn = get_connection()
            cur = conn.cursor()
            cur.execute("DELETE FROM feedback")
            conn.commit()
            conn.close()
            st.warning(
                "All feedback records deleted. (Students can now give feedback again.)"
            )

# -------------------------
# HEADER (logo + title)
# -------------------------

def render_header():
    if LOGO_PATH.exists():
        logo_bytes = LOGO_PATH.read_bytes()
        logo_b64 = base64.b64encode(logo_bytes).decode("utf-8")

        st.markdown(
            f"""
            <div style="
                width: 100%;
                display: flex;
                flex-direction: column;
                justify-content: center;
                align-items: center;
                padding-top: 18px;
                padding-bottom: 10px;
            ">
                <img src="data:image/png;base64,{logo_b64}"
                     style="
                        width: 120px;
                        max-width: 70%;
                        height: auto;
                        border-radius: 16px;
                        margin-bottom: 8px;
                     " />
                <div class="app-title">SJCET Feedback System</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        st.markdown('<h1 class="app-title">SJCET Feedback System</h1>', unsafe_allow_html=True)

# -------------------------
# LOGIN SCREEN (roles on main page)
# -------------------------

def login_screen():
    render_header()

    st.subheader("🔐 Login")

    role_choice = st.selectbox(
        "Select Role",
        ["Student", "HOD", "Principal", "Admin"],
        index=0,
    )

    if role_choice == "Student":
        student_info = student_login_panel()
        if student_info:
            st.session_state["auth_role"] = "Student"
            st.session_state["student_info"] = student_info
            st.rerun()
    else:
        st.subheader(f"{role_choice} Login")
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        if st.button(f"Login as {role_choice}"):
            if authenticate_fixed_user(username, password, role_choice):
                st.session_state["auth_role"] = role_choice
                st.success("Login successful.")
                st.rerun()
            else:
                st.error("Invalid username or password.")

# -------------------------
# MAIN APP
# -------------------------

def main():
    init_db()

    if "auth_role" not in st.session_state:
        st.session_state["auth_role"] = None

    if st.session_state["auth_role"] is None:
        login_screen()
    else:
        # Logged-in views
        render_header()

        role = st.session_state["auth_role"]

        # Logout button on top-right
        col1, col2 = st.columns([3, 1])
        with col2:
            if st.button("Logout"):
                st.session_state["auth_role"] = None
                st.session_state.pop("student_info", None)
                st.rerun()

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
