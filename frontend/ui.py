import streamlit as st


WORKFLOW = [
    ("Project Setup", "📍"),
    ("Project Review", "📋"),
    ("Location Verification", "🗺️"),
    ("Overlap Results", "🔗"),
    ("Export Results", "📤"),
]


SHELL_CSS = """
<style>
    .stApp {
        background-color: #0B132B;
        font-family: 'Aeonik', sans-serif;
        color: #fff3d0;
    }

    .block-container {
        max-width: 1320px;
        padding-top: 1.5rem;
        padding-bottom: 3.5rem;
    }

    [data-testid="stSidebar"] {
        background-color: #1C2541;
        border-right: 1px solid rgba(91, 192, 190, 0.25);
    }

    [data-testid="stSidebar"] * {
        color: #fff3d0 !important;
    }

    .workspace-header {
        display: flex;
        align-items: flex-end;
        justify-content: space-between;
        gap: 2rem;
        margin-bottom: 1.6rem;
        padding-bottom: 1rem;
        border-bottom: 2px solid rgba(91, 192, 190, 0.55);
    }

    .workspace-kicker {
        margin: 0 0 0.35rem;
        color: #5BC0BE;
        font-size: 0.7rem;
        font-weight: 700;
        letter-spacing: 0.14em;
        text-transform: uppercase;
    }

    .workspace-name {
        margin: 0;
        color: #fff3d0;
        font-size: 1.25rem;
        font-weight: 600;
    }

    .workspace-context {
        margin: 0;
        color: rgba(255, 243, 208, 0.68);
        font-size: 0.8rem;
        text-align: right;
        letter-spacing: 0.04em;
    }

    div[data-testid="stVerticalBlockBorderWrapper"] {
        border-color: rgba(255, 243, 208, 0.14);
        border-radius: 2px;
        background: rgba(28, 37, 65, 0.22);
    }

    div[data-testid="stMetric"] {
        min-height: 5.2rem;
        padding: 0.85rem 1rem;
        border: 1px solid rgba(255, 243, 208, 0.12);
        border-radius: 2px;
        background: rgba(28, 37, 65, 0.42);
    }

    div[data-testid="stDataEditor"],
    div[data-testid="stDataFrame"] {
        overflow: hidden;
        border: 1px solid rgba(255, 243, 208, 0.13);
        border-radius: 2px;
        background-color: #0C0A3E;
    }

    div[data-testid="stFileUploader"] section {
        border: 1px dashed rgba(91, 192, 190, 0.42);
        border-radius: 2px;
        background: rgba(28, 37, 65, 0.28);
    }

    .stButton > button {
        border: 1px solid rgba(91, 192, 190, 0.6);
        border-radius: 2px;
        background-color: #5BC0BE;
        color: #0B132B;
        font-weight: 700;
        padding: 0.56rem 1rem;
    }

    .stButton > button:hover {
        border-color: rgba(255, 243, 208, 0.5);
        background-color: rgba(91, 192, 190, 0.9);
    }

    .stInfo,
    .stWarning,
    .stSuccess,
    .stError,
    .stExpander {
        border-radius: 2px;
        border: 1px solid rgba(255, 243, 208, 0.12);
        background-color: rgba(28, 37, 65, 0.42);
        color: #fff3d0;
    }

    .stInfo {
        border-left: 3px solid #5BC0BE;
    }

    .stWarning {
        border-left: 3px solid #5BC0BE;
    }

    .stSuccess {
        border-left: 3px solid #5BC0BE;
    }

    .stExpander > div {
        border: 1px solid rgba(255, 243, 208, 0.12);
        border-radius: 2px;
        background-color: rgba(28, 37, 65, 0.35);
    }

    h1 {
        font-family: 'Aeonik', sans-serif;
        font-weight: 700;
        color: #fff3d0;
        letter-spacing: -0.02em;
        border-bottom: 2px solid #5BC0BE;
        padding-bottom: 0.5rem;
        margin-bottom: 1.5rem;
    }

    h2, h3 {
        font-family: 'Aeonik', sans-serif;
        font-weight: 500;
        color: #fff3d0;
    }

    [data-testid="stMetricValue"] {
        font-family: 'Aeonik', sans-serif;
        font-size: 2.2rem;
        color: #5BC0BE;
        font-weight: 700;
    }

    [data-testid="stMetricLabel"] {
        color: #fff3d0;
        opacity: 0.8;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        font-size: 0.85rem;
    }

    @media (max-width: 700px) {
        .workspace-header {
            align-items: flex-start;
            flex-direction: column;
            gap: 0.4rem;
        }

        .workspace-context {
            text-align: left;
        }
    }
</style>
"""


def render_shell(page_title):
    """Render a consistent visual header without changing page navigation."""
    current_step = next(
        (index for index, (title, _) in enumerate(WORKFLOW, start=1) if title == page_title),
        0,
    )
    context = f"Step {current_step} of {len(WORKFLOW)} · {page_title}" if current_step else "Public plans · Shared opportunities"

    st.markdown(SHELL_CSS, unsafe_allow_html=True)
    st.markdown(
        f"""
        <div class="workspace-header">
            <div>
                <p class="workspace-kicker">ShellHacks 2026</p>
                <p class="workspace-name">Gridlock</p>
            </div>
            <p class="workspace-context">{context}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
