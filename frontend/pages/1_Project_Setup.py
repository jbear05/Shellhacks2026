import streamlit as st
from data_loader import ProjectLoadError, load_uploaded_projects
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

if "files_a" not in st.session_state:
    st.session_state.files_a = []

if "files_b" not in st.session_state:
    st.session_state.files_b = []

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

with col2:
    utility_b = st.text_input(
        "Utility B",
        value=st.session_state.utility_b,
        placeholder="Example: Dominion Energy South Carolina"
    )

# Upload files
upload_panel = st.container(border=True)
upload_panel.subheader("2. Upload Project Documents")

col1, col2 = upload_panel.columns(2)

with col1:
    files_a = st.file_uploader(
        "Upload Utility A files",
        type=["pdf", "csv", "xlsx"],
        accept_multiple_files=True
    )

with col2:
    files_b = st.file_uploader(
        "Upload Utility B files",
        type=["pdf", "csv", "xlsx"],
        accept_multiple_files=True
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

# Save setup
if st.button("Save Project Setup", type="primary"):
    if not utility_a or not utility_b:
        st.error("Please enter both utility names.")

    elif utility_a.strip().lower() == utility_b.strip().lower():
        st.error("Utility A and Utility B must be different.")

    else:
        selected_files_a = (
            files_a or st.session_state.files_a
        )
        selected_files_b = (
            files_b or st.session_state.files_b
        )

        try:
            parsed_projects = load_uploaded_projects(
                selected_files_a or [],
                selected_files_b or [],
                utility_a.strip(),
                utility_b.strip(),
            )
        except ProjectLoadError as error:
            st.error(f"Project files could not be loaded:\n\n{error}")
        else:
            st.session_state.utility_a = utility_a.strip()
            st.session_state.utility_b = utility_b.strip()
            st.session_state.threshold_miles = threshold
            st.session_state.files_a = selected_files_a or []
            st.session_state.files_b = selected_files_b or []
            st.session_state.projects = parsed_projects

            st.success(
                f"Project setup saved. Loaded {len(parsed_projects)} project rows."
            )

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

    st.write(
        f"Utility A files uploaded: **{len(st.session_state.files_a)}**"
    )
    st.write(
        f"Utility B files uploaded: **{len(st.session_state.files_b)}**"
    )

    if st.button("Continue to Project Review"):
        st.switch_page("pages/2_Project_Review.py")