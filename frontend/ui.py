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
    .block-container {
        max-width: 1320px;
        padding-top: 1.5rem;
        padding-bottom: 3.5rem;
    }

    .workspace-header {
        display: flex;
        align-items: end;
        justify-content: space-between;
        gap: 2rem;
        margin-bottom: 1.6rem;
        padding-bottom: 1rem;
        border-bottom: 1px solid rgba(255, 243, 208, 0.14);
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
        color: rgba(255, 243, 208, 0.6);
        font-size: 0.8rem;
        text-align: right;
    }

    div[data-testid="stVerticalBlockBorderWrapper"] {
        border-color: rgba(255, 243, 208, 0.16);
        border-radius: 0.35rem;
        background: rgba(28, 37, 65, 0.22);
    }

    div[data-testid="stMetric"] {
        min-height: 5.2rem;
        padding: 0.85rem 1rem;
        border: 1px solid rgba(255, 243, 208, 0.13);
        border-radius: 0.35rem;
        background: rgba(28, 37, 65, 0.38);
    }

    div[data-testid="stDataEditor"],
    div[data-testid="stDataFrame"] {
        overflow: hidden;
        border: 1px solid rgba(255, 243, 208, 0.13);
        border-radius: 0.35rem;
    }

    div[data-testid="stFileUploader"] section {
        border: 1px dashed rgba(91, 192, 190, 0.42);
        border-radius: 0.35rem;
        background: rgba(28, 37, 65, 0.28);
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
