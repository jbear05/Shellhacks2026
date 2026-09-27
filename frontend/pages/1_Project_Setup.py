import streamlit as st
from ai_parser_jobs import ParseInput, clear_job, get_job, projects_from_job, start_job
from ui import render_shell

st.set_page_config(
    page_title="Project Setup",
    page_icon="📍",
    layout="wide"
)

render_shell("Project Setup")

st.title("Project Setup")
st.write(
    "Choose the two utilities you want to compare and upload their project documents."
)

# Initialize session state
if "utility_a" not in st.session_state:
    st.session_state.utility_a = ""

if "utility_b" not in st.session_state:
    st.session_state.utility_b = ""

if "threshold_miles" not in st.session_state:
    st.session_state.threshold_miles = 25.0

if "state_a" not in st.session_state:
    st.session_state.state_a = ""

if "state_b" not in st.session_state:
    st.session_state.state_b = ""

if "parser_job_id" not in st.session_state:
    st.session_state.parser_job_id = ""

# Utility inputs
utility_panel = st.container(border=True)
utility_panel.subheader("1. Select Utilities")

col1, col2 = utility_panel.columns(2)

with col1:
    utility_a = st.text_input(
        "Utility A",
        value=st.session_state.utility_a,
        placeholder="Example: Georgia Power"
    )
    state_a = st.text_input(
        "Utility A state",
        value=st.session_state.state_a,
        placeholder="Example: Georgia"
    )

with col2:
    utility_b = st.text_input(
        "Utility B",
        value=st.session_state.utility_b,
        placeholder="Example: Dominion Energy South Carolina"
    )
    state_b = st.text_input(
        "Utility B state",
        value=st.session_state.state_b,
        placeholder="Example: South Carolina"
    )

# Upload files
upload_panel = st.container(border=True)
upload_panel.subheader("2. Upload Project Documents")

col1, col2 = upload_panel.columns(2)

with col1:
    file_a = st.file_uploader(
        "Upload Utility A PDF",
        type=["pdf"],
        accept_multiple_files=False,
    )

with col2:
    file_b = st.file_uploader(
        "Upload Utility B PDF",
        type=["pdf"],
        accept_multiple_files=False,
    )

# Analysis settings
settings_panel = st.container(border=True)
settings_panel.subheader("3. Analysis Settings")

threshold = settings_panel.number_input(
    "Overlap distance threshold in miles",
    min_value=1.0,
    max_value=100.0,
    value=st.session_state.threshold_miles,
    step=1.0
)

settings_panel.caption(
    "Projects within this distance of each other will be included in the overlap table."
)

run_button = st.button("Run AI parser", type="primary")
if run_button:
    if not utility_a or not utility_b:
        st.error("Please enter both utility names.")
    elif utility_a.strip().lower() == utility_b.strip().lower():
        st.error("Utility A and Utility B must be different.")
    elif not state_a or not state_b:
        st.error("Please enter both utility states.")
    elif file_a is None or file_b is None:
        st.error("Please upload one PDF for each utility.")
    else:
        st.session_state.utility_a = utility_a.strip()
        st.session_state.utility_b = utility_b.strip()
        st.session_state.state_a = state_a.strip()
        st.session_state.state_b = state_b.strip()
        st.session_state.threshold_miles = threshold
        st.session_state.parser_job_id = start_job(
            [
                ParseInput(
                    utility=utility_a.strip(),
                    state=state_a.strip(),
                    filename=file_a.name,
                    content=file_a.getvalue(),
                ),
                ParseInput(
                    utility=utility_b.strip(),
                    state=state_b.strip(),
                    filename=file_b.name,
                    content=file_b.getvalue(),
                ),
            ]
        )

job_id = st.session_state.get("parser_job_id", "")
if job_id:
    job = get_job(job_id)
    if job is None:
        st.warning("Parser job state was cleared. Start a new parse run.")
        st.session_state.parser_job_id = ""
    elif job["status"] == "running":
        st.info(job.get("message", "Parsing in progress."))
        st.progress(min(100, int(job.get("progress", 0.0))) / 100)
        st.caption("Parsing runs asynchronously. Click refresh to update status.")
        st.button("Refresh parser status")
    elif job["status"] == "failed":
        st.error(f"AI parser failed: {job.get('error', 'Unknown error')}")
        if st.button("Clear failed run"):
            clear_job(job_id)
            st.session_state.parser_job_id = ""
            st.rerun()
    elif job["status"] == "completed":
        st.session_state.projects = projects_from_job(job)
        st.success(
            f"AI parser finished. Loaded {job.get('row_count', len(st.session_state.projects))} project rows."
        )
        st.download_button(
            label="Download generated CSV",
            data=job.get("projects_csv", b""),
            file_name=f"{st.session_state.utility_a}_{st.session_state.utility_b}_projects.csv".replace(" ", "_"),
            mime="text/csv",
        )
        if st.button("Continue to Project Review"):
            st.switch_page("pages/2_Project_Review.py")

# Display current setup
if st.session_state.utility_a and st.session_state.utility_b:
    st.divider()
    st.subheader("Current Project Setup")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("Utility A", st.session_state.utility_a)

    with col2:
        st.metric("Utility B", st.session_state.utility_b)

    with col3:
        st.metric(
            "Overlap Threshold",
            f"{st.session_state.threshold_miles:.0f} miles"
        )