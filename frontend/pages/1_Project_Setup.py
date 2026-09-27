import pandas as pd
import streamlit as st
from frontend.data_loader import ProjectLoadError, load_uploaded_projects, prepare_projects
from frontend.pdf_import import parse_known_pdf
from frontend.project_data import DESC, GEORGIA, ROOT, load_demo_projects
from frontend.workspace import restore_bundle
from frontend.ui import render_shell

render_shell("Project Setup")
st.title("Project Setup")

@st.cache_data(show_spinner=False, max_entries=4)
def import_pdf(content):
    return parse_known_pdf(content)

mode = st.radio("Project source", ["Saved public plans", "Two source PDFs", "CSV / XLSX tables", "Saved snapshot"], horizontal=True)
loaded = None
try:
    if mode == "Saved public plans":
        st.write("Load the committed DESC and Georgia Power projects with saved endpoint evidence.")
        if st.button("Load public plans", type="primary"):
            loaded = load_demo_projects()
    elif mode == "Two source PDFs":
        st.write("Upload the organizer's DESC 2024–2028 project descriptions and Georgia Power 2025 IRP Volume 3 public PDF. Filenames may differ; contents must match the supplied plans.")
        a, b = st.columns(2)
        pdf_a = a.file_uploader("DESC source PDF", type=["pdf"])
        pdf_b = b.file_uploader("Georgia Power source PDF", type=["pdf"])
        st.caption("Uses the existing parsers and saved geocoding. Georgia's large PDF can take tens of seconds the first time; results are cached for reruns.")
        if st.button("Parse both PDFs", type="primary", disabled=not (pdf_a and pdf_b)):
            with st.status("Parsing source plans…", expanded=True) as progress:
                st.write("Reading DESC and joining endpoint evidence…")
                first = import_pdf(pdf_a.getvalue())
                st.write("Reading Georgia Power's transmission plan…")
                second = import_pdf(pdf_b.getvalue())
                loaded = prepare_projects(pd.concat([first, second], ignore_index=True))
                if set(loaded.Utility) != {DESC, GEORGIA}:
                    raise ProjectLoadError("Upload one DESC PDF and one Georgia Power PDF.")
                progress.update(label="Both plans are ready for review", state="complete")
    elif mode == "CSV / XLSX tables":
        st.write("Import one project table per utility. Required: Project ID and Project Name. Supply endpoints or Latitude/Longitude for mapping. Existing utility labels are preserved.")
        a, b = st.columns(2)
        fallback_a = a.text_input("Utility A (fills blank utility fields)", value=DESC)
        fallback_b = b.text_input("Utility B (fills blank utility fields)", value=GEORGIA)
        files_a = a.file_uploader("Utility A project tables", type=["csv", "xlsx"], accept_multiple_files=True)
        files_b = b.file_uploader("Utility B project tables", type=["csv", "xlsx"], accept_multiple_files=True)
        if st.button("Import project tables", type="primary", disabled=not (files_a and files_b)):
            loaded = load_uploaded_projects(files_a, files_b, fallback_a.strip(), fallback_b.strip())
    else:
        snapshot = st.file_uploader("Gridlock snapshot ZIP", type=["zip"])
        if st.button("Restore snapshot", type="primary", disabled=snapshot is None):
            loaded, settings = restore_bundle(snapshot.getvalue())
            st.session_state.update(settings)
    if loaded is not None:
        if loaded.empty or loaded.Utility.nunique() < 2:
            raise ProjectLoadError("Load projects from at least two distinct utilities.")
        st.session_state.projects = loaded
        utilities = list(loaded.Utility.unique())
        for key, index in (("utility_a", 0), ("utility_b", 1)):
            if st.session_state.get(key) not in utilities:
                st.session_state[key] = utilities[index]
        if st.session_state.utility_a == st.session_state.utility_b:
            st.session_state.utility_b = next(u for u in utilities if u != st.session_state.utility_a)
        st.session_state.pop("overlaps", None)
        st.success(f"Loaded {len(loaded)} projects. Source ownership and project IDs are preserved.")
except Exception as error:
    st.error(f"Import stopped: {error}")

if "projects" in st.session_state:
    st.subheader("Analysis settings")
    utilities = list(st.session_state.projects.Utility.unique())
    a, b = st.columns(2)
    a.selectbox("Compare utility", utilities, key="utility_a")
    b.selectbox("With utility", utilities, key="utility_b")
    st.number_input("Distance threshold (miles)", min_value=1.0, max_value=100.0, step=1.0, key="threshold_miles")
    st.caption("The challenge uses 25 miles. Larger values are exploratory.")
    if st.session_state.utility_a == st.session_state.utility_b:
        st.warning("Choose two different utilities.")
    elif st.button("Continue to Project Review"):
        st.switch_page(str(ROOT / "frontend/pages/2_Project_Review.py"))
