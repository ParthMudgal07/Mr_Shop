import streamlit as st
from graph import app as graph_app

# ============================================================
# Page Configuration
# ============================================================
st.set_page_config(
    page_title="Mr.Shop • Direct",
    page_icon="🛍️",
    layout="centered",
    initial_sidebar_state="expanded"
)

# ============================================================
# Instagram DM Styling (CSS)
# ============================================================
st.markdown(
    """
    <style>
    /* Main background & base typography */
    .stApp {
        background-color: #000000;
        color: #f5f5f5;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    }

    /* Sidebar — ambient memory panel */
    [data-testid="stSidebar"] {
        background-color: #0a0a0a !important;
        border-right: 1px solid #262626;
    }
    [data-testid="stSidebar"] * {
        color: #f5f5f5;
    }
    .memory-card {
        background: #121212;
        border: 1px solid #262626;
        border-radius: 12px;
        padding: 12px 14px;
        margin-bottom: 12px;
    }
    .memory-label {
        font-size: 11px;
        letter-spacing: 0.06em;
        text-transform: uppercase;
        color: #8e8e8e;
        margin-bottom: 6px;
    }
    .memory-value {
        font-size: 14px;
        color: #f5f5f5;
        line-height: 1.45;
        word-break: break-word;
    }
    .memory-empty {
        color: #737373;
        font-style: italic;
    }

    /* Top IG direct header */
    .ig-header-container {
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 12px 18px;
        background: #121212;
        border: 1px solid #262626;
        border-radius: 16px;
        margin-bottom: 20px;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.4);
    }
    .ig-header-left {
        display: flex;
        align-items: center;
        gap: 14px;
    }
    .ig-avatar-wrapper {
        position: relative;
        width: 46px;
        height: 46px;
        border-radius: 50%;
        background: linear-gradient(45deg, #f09433 0%, #e6683c 25%, #dc2743 50%, #cc2366 75%, #bc1888 100%);
        padding: 2px;
        display: flex;
        align-items: center;
        justify-content: center;
    }
    .ig-avatar {
        width: 100%;
        height: 100%;
        border-radius: 50%;
        background: #1a1a1a;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 20px;
    }
    .ig-status-dot {
        position: absolute;
        bottom: 2px;
        right: 2px;
        width: 11px;
        height: 11px;
        background-color: #10b981;
        border: 2px solid #121212;
        border-radius: 50%;
    }
    .ig-header-title {
        display: flex;
        align-items: center;
        gap: 6px;
        font-size: 16px;
        font-weight: 600;
        color: #ffffff;
    }
    .ig-badge {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        background: #0095f6;
        color: white;
        border-radius: 50%;
        width: 14px;
        height: 14px;
        font-size: 9px;
        font-weight: bold;
    }
    .ig-header-sub {
        font-size: 12px;
        color: #8e8e8e;
    }

    /* Streamlit Chat Messages */
    [data-testid="stChatMessage"] {
        background-color: transparent !important;
        padding: 6px 0 !important;
    }

    /* User bubble (Instagram Gradient) */
    [data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-user"]) [data-testid="stChatMessageContent"] {
        background: linear-gradient(135deg, #5b51d8, #833ab4, #c13584, #e1306c);
        color: #ffffff;
        border-radius: 20px 20px 4px 20px;
        padding: 10px 16px;
        box-shadow: 0 2px 8px rgba(193, 53, 132, 0.25);
        max-width: 80%;
        margin-left: auto;
    }

    /* Assistant bubble (Instagram Neutral Dark) */
    [data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-assistant"]) [data-testid="stChatMessageContent"] {
        background: #262626;
        color: #f5f5f5;
        border: 1px solid #333333;
        border-radius: 20px 20px 20px 4px;
        padding: 10px 16px;
        max-width: 80%;
    }

    /* Chat input styling */
    [data-testid="stChatInput"] {
        border-radius: 24px;
        border: 1px solid #363636;
        background-color: #121212 !important;
    }
    [data-testid="stChatInput"] textarea {
        color: #ffffff !important;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# ============================================================
# Session State Initialization
# ============================================================
EMPTY_MEMORY = {
    "wardrobe": [],
    "preferences": {},
    "budget": None,
}

if "messages" not in st.session_state:
    st.session_state.messages = []

if "ambient_memory" not in st.session_state:
    st.session_state.ambient_memory = {
        "wardrobe": [],
        "preferences": {},
        "budget": None,
    }

if "last_memory_update" not in st.session_state:
    st.session_state.last_memory_update = {}

# ============================================================
# Sidebar — Ambient Memory
# ============================================================
memory = st.session_state.ambient_memory or EMPTY_MEMORY
wardrobe = memory.get("wardrobe") or []
preferences = memory.get("preferences") or {}
budget = memory.get("budget")
last_update = st.session_state.last_memory_update or {}

with st.sidebar:
    st.markdown("### Ambient Memory")
    st.caption("Live state — updates when you share new details.")

    wardrobe_html = (
        "<br>".join(f"• {item}" for item in wardrobe)
        if wardrobe
        else '<span class="memory-empty">No items yet</span>'
    )
    preferences_html = (
        "<br>".join(f"<b>{k}</b>: {v}" for k, v in preferences.items())
        if preferences
        else '<span class="memory-empty">No preferences yet</span>'
    )
    budget_html = (
        f"₹{budget}"
        if budget is not None
        else '<span class="memory-empty">Not set</span>'
    )

    st.markdown(
        f"""
        <div class="memory-card">
            <div class="memory-label">Wardrobe</div>
            <div class="memory-value">{wardrobe_html}</div>
        </div>
        <div class="memory-card">
            <div class="memory-label">Preferences</div>
            <div class="memory-value">{preferences_html}</div>
        </div>
        <div class="memory-card">
            <div class="memory-label">Budget</div>
            <div class="memory-value">{budget_html}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    with st.expander("Last memory update", expanded=bool(last_update)):
        if last_update:
            st.json(last_update)
        else:
            st.caption("No updates yet — tell Mr.Shop something about yourself.")

    st.markdown("##### Full ambient_memory")
    st.json(
        {
            "wardrobe": wardrobe,
            "preferences": preferences,
            "budget": budget,
        }
    )

# ============================================================
# Main Chat Header (Instagram DM Simulation)
# ============================================================
header_col1, header_col2 = st.columns([6, 1])

with header_col1:
    st.markdown(
        """
        <div class="ig-header-container">
            <div class="ig-header-left">
                <div class="ig-avatar-wrapper">
                    <div class="ig-avatar">🛍️</div>
                    <div class="ig-status-dot"></div>
                </div>
                <div>
                    <div class="ig-header-title">
                        mr.shop <span class="ig-badge">✓</span>
                    </div>
                    <div class="ig-header-sub">Mr.Shop • Active now</div>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

with header_col2:
    if st.button("🔄", help="Reset chat conversation"):
        st.session_state.messages = []
        st.session_state.ambient_memory = {
            "wardrobe": [],
            "preferences": {},
            "budget": None,
        }
        st.session_state.last_memory_update = {}
        st.rerun()

# ============================================================
# Render Message History
# ============================================================
if not st.session_state.messages:
    st.markdown(
        """
        <div style="text-align: center; color: #737373; padding: 40px 20px;">
            <div style="font-size: 38px; margin-bottom: 8px;">✨</div>
            <div style="font-size: 15px; font-weight: 500; color: #a8a8a8;">Message Mr.Shop on Direct</div>
            <div style="font-size: 12px; margin-top: 4px;">
                Ask for styling advice, wardrobe management, product finds, or stylist bookings.
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# ============================================================
# Chat Input & LangGraph Invocation Flow
# ============================================================
user_prompt = st.chat_input("Message...")

if user_prompt:
    st.session_state.messages.append({"role": "user", "content": user_prompt})
    with st.chat_message("user"):
        st.markdown(user_prompt)

    with st.chat_message("assistant"):
        with st.spinner("Seen • typing..."):
            try:
                graph_input = {
                    "messages": [user_prompt],
                    "intent": None,
                    "memory_update": {},
                    "ambient_memory": st.session_state.ambient_memory,
                    "response": None,
                }

                output_state = graph_app.invoke(graph_input)

                response_text = (
                    output_state.get("response")
                    or "Thanks for reaching out! Let me know what you'd like styling on."
                )
                updated_memory = output_state.get("ambient_memory")
                memory_update = output_state.get("memory_update") or {}

                # Persist merged ambient memory after every user turn
                if updated_memory and isinstance(updated_memory, dict):
                    st.session_state.ambient_memory = {
                        "wardrobe": list(updated_memory.get("wardrobe") or []),
                        "preferences": dict(updated_memory.get("preferences") or {}),
                        "budget": updated_memory.get("budget"),
                    }

                st.session_state.last_memory_update = (
                    memory_update if isinstance(memory_update, dict) else {}
                )

                st.markdown(response_text)
                st.session_state.messages.append(
                    {"role": "assistant", "content": response_text}
                )
                # Refresh sidebar so updated ambient memory shows immediately
                st.rerun()

            except Exception as e:
                error_msg = f"Sorry, I ran into an issue processing your request: {e}"
                st.error(error_msg)
                st.session_state.messages.append(
                    {"role": "assistant", "content": error_msg}
                )
