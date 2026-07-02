"""
Natura Resort - Admin Dashboard (Streamlit)

Run:
    streamlit run dashboard.py
"""

import hmac
import html
import os
import time
from datetime import date, datetime, timedelta, time as dt_time

import hashlib
import mysql.connector
import pandas as pd
import pytz
import streamlit as st
from dotenv import load_dotenv

load_dotenv()


def _read_secret(name: str, env_var: str) -> str:
    """Read secret from file (Docker secrets) or environment variable."""
    secret_path = f"/run/secrets/{name}"
    if os.path.exists(secret_path):
        with open(secret_path, "r") as f:
            return f.read().strip()
    return os.getenv(env_var, "")


# Config
st.set_page_config(
    page_title="Natura Resort",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Styles
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Fira+Sans:wght@300;400;500;600;700&family=Fira+Code:wght@400;500;600;700&display=swap');

:root {
  --bg:      #000000;
  --surface: #0A0A0A;
  --surface2:#111111;
  --border:  rgba(255, 255, 255, 0.14);
  --primary: #1E3A8A;
  --primary-light: #2563EB;
  --accent:  #16A34A;
  --accent-light: #4ADE80;
  --text:    #F8F9FA;
  --muted:   #9CA3AF;
  --danger:  #EF4444;
  --success: #52B788;
  --radius:  10px;
}

html, body, [class*="css"], #root, div[data-testid="stAppViewContainer"] {
  font-family: 'Fira Sans', sans-serif !important;
  background-color: #000000 !important;
  color: var(--text) !important;
  font-size: 14px;
}

h1, h2, h3, h4 {
  font-family: 'Fira Sans', sans-serif !important;
  color: #FFFFFF !important;
  font-weight: 600 !important;
  letter-spacing: -0.01em;
}

h1 { font-size: 1.8rem !important; }
h2 { font-size: 1.45rem !important; }
h3 { font-size: 1.15rem !important; }

p, li, span:not(.pill), label { color: var(--text) !important; }

# MainMenu, footer
header { background: transparent !important; }

.block-container {
  padding-top: 1.2rem !important;
  padding-bottom: 2rem !important;
  max-width: 1440px !important;
}

/* Sidebar */
div[data-testid="stSidebar"] {
  background: #050505 !important;
  border-right: 1px solid var(--border) !important;
  padding: 0 !important;
  margin: 0 !important;
  height: 100vh !important;
  height: 100dvh !important;
  max-height: 100vh !important;
  max-height: 100dvh !important;
  overflow-y: hidden !important;
  overflow-x: hidden !important;
  overscroll-behavior: none !important;
  touch-action: pan-y !important;
  scrollbar-width: none !important;
}
div[data-testid="stSidebar"] [data-testid="stSidebarUserContent"] {
  padding-top: 0 !important;
  margin-top: 0 !important;
  height: 100vh !important;
  height: 100dvh !important;
  max-height: 100vh !important;
  max-height: 100dvh !important;
  overflow: hidden !important;
  overflow-x: hidden !important;
  overscroll-behavior: none !important;
  touch-action: pan-y !important;
  display: flex !important;
  flex-direction: column !important;
  align-items: stretch !important;
  justify-content: flex-start !important;
  gap: 0 !important;
  min-width: 0 !important;
  scrollbar-width: none !important;
  padding-bottom: 0 !important;
  margin-bottom: 0 !important;
}
div[data-testid="stSidebar"] [data-testid="stSidebarContent"] {
  overflow: hidden !important;
  overflow-x: hidden !important;
  height: 100vh !important;
  height: 100dvh !important;
  max-height: 100vh !important;
  max-height: 100dvh !important;
  flex: 0 0 auto !important;
  overscroll-behavior: none !important;
  touch-action: pan-y !important;
  min-width: 0 !important;
  scrollbar-width: none !important;
  padding-bottom: 0 !important;
  margin-bottom: 0 !important;
  display: block !important;
}
div[data-testid="stSidebar"] > div {
  overflow: hidden !important;
  overflow-x: hidden !important;
  height: 100vh !important;
  height: 100dvh !important;
  max-height: 100vh !important;
  max-height: 100dvh !important;
  min-height: 0 !important;
  overscroll-behavior: none !important;
  touch-action: pan-y !important;
  min-width: 0 !important;
  scrollbar-width: none !important;
  padding: 0 !important;
  margin: 0 !important;
}
div[data-testid="stSidebar"] * {
  box-sizing: border-box;
  min-height: 0 !important;
}
div[data-testid="stSidebar"] [data-testid="stSidebarBrand"] {
  display: none !important;
  max-height: 0 !important;
  height: 0 !important;
  padding: 0 !important;
  margin: 0 !important;
  overflow: hidden !important;
}
div[data-testid="stSidebar"] h3 {
  color: #FFFFFF !important;
  font-size: 0.7rem !important;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  font-weight: 600;
  margin-top: 0.2rem !important;
  margin-bottom: 0.35rem !important;
}
div[data-testid="stSidebar"] .stButton {
  margin-top: 0 !important;
  margin-bottom: 0 !important;
}
div[data-testid="stSidebar"] .stDateInput,
div[data-testid="stSidebar"] .stSelectbox,
div[data-testid="stSidebar"] .stTextInput {
  margin-top: 0 !important;
  margin-bottom: 0.18rem !important;
  padding-top: 0 !important;
  padding-bottom: 0 !important;
}
div[data-testid="stSidebar"] .stMarkdown {
  margin-top: 0 !important;
  margin-bottom: 0 !important;
  padding-top: 0 !important;
  padding-bottom: 0 !important;
}
div[data-testid="stSidebar"] .stColumns {
  gap: 0 !important;
  margin-top: 0 !important;
  margin-bottom: 0 !important;
}
div[data-testid="stSidebar"] .stButton > button {
  background: #0A0A0A !important;
  color: #E5E7EB !important;
  border: 1px solid var(--border) !important;
  border-radius: 5px !important;
  font-size: 0.76rem !important;
  font-weight: 500 !important;
  padding: 0.22rem 0.35rem !important;
  transition: all 0.12s ease !important;
  margin-top: 0 !important;
  margin-bottom: 0 !important;
}
div[data-testid="stSidebar"] .stButton > button:hover {
  background: #111111 !important;
  border-color: var(--accent) !important;
  color: #FFFFFF !important;
}

/* Sidebar: compact form spacing, no line breaks */
div[data-testid="stSidebar"] .stDateInput,
div[data-testid="stSidebar"] .stSelectbox,
div[data-testid="stSidebar"] .stTextInput,
div[data-testid="stSidebar"] .stButton,
div[data-testid="stSidebar"] .stCaption,
div[data-testid="stSidebar"] .stMarkdown {
  margin-bottom: 0.22rem !important;
  line-height: 1.05 !important;
  max-width: 100% !important;
}
div[data-testid="stSidebar"] .stDateInput input,
div[data-testid="stSidebar"] .stSelectbox div[data-baseweb="select"],
div[data-testid="stSidebar"] .stTextInput input {
  font-size: 0.8rem !important;
  padding-top: 0.2rem !important;
  padding-bottom: 0.2rem !important;
  max-width: 100% !important;
}
div[data-testid="stSidebar"] .stDateInput label,
div[data-testid="stSidebar"] .stSelectbox label,
div[data-testid="stSidebar"] .stTextInput label {
  font-size: 0.75rem !important;
  margin-bottom: 0.05rem !important;
}
div[data-testid="stSidebar"] .stSelectbox div[data-baseweb="select"] > div {
  overflow: hidden !important;
  text-overflow: ellipsis !important;
  white-space: nowrap !important;
}

/* Nav active state is approximated via button style; keep consistent */

div[data-testid="stSidebar"] [data-testid="stForm"] {
  border: 1px solid var(--border) !important;
  border-radius: 8px !important;
  background: #0A0A0A !important;
  padding: 4px !important;
  margin-top: 0 !important;
  margin-bottom: 0 !important;
  min-height: 0 !important;
}
div[data-testid="stSidebar"] .stVerticalBlock {
  padding-top: 0 !important;
  padding-bottom: 0 !important;
  margin-top: 0 !important;
  margin-bottom: 0 !important;
  min-height: 0 !important;
}

div[data-testid="stSidebar"] .stAlert, 
div[data-testid="stSidebar"] div[data-testid="stStatusWidget"],
div[data-testid="stSidebar"] div[data-testid="stToast"] {
  background: #111111 !important;
  border: 1px solid var(--border) !important;
  color: #F8F9FA !important;
  margin-top: 0.35rem !important;
  margin-bottom: 0.35rem !important;
}

/* Header */
.header-logo {
  font-family: 'Fira Sans', sans-serif !important;
  font-weight: 700 !important;
  font-size: 1.35rem !important;
  color: #FFFFFF !important;
  letter-spacing: -0.02em;
}
.header-time {
  font-family: 'Fira Code', monospace !important;
  font-size: 0.8rem !important;
  color: var(--muted) !important;
  text-align: right;
  padding-top: 6px;
}

.sidebar-title {
  font-family: 'Fira Sans', sans-serif !important;
  font-weight: 700 !important;
  font-size: 1.7rem !important;
  color: #FFFFFF !important;
  margin-bottom: 8px;
}

hr.sidebar-hr {
  border: none;
  border-top: 1px solid #888888 !important;
  margin: 8px 0 10px 0 !important;
  opacity: 1 !important;
}
div[data-testid="metric-container"] {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 1rem 1.1rem 0.9rem;
  box-shadow: 0 1px 0 rgba(255,255,255,0.03) inset;
}
div[data-testid="metric-container"] [data-testid="stMetricValue"] {
  font-family: 'Fira Code', monospace !important;
  font-size: 1.4rem !important;
  color: #FFFFFF !important;
  font-weight: 600 !important;
}
div[data-testid="metric-container"] [data-testid="stMetricLabel"] {
  font-size: 0.75rem !important;
  color: var(--muted) !important;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  font-weight: 500;
}

/* Buttons */
.stButton > button {
  background: var(--accent) !important;
  color: #FFFFFF !important;
  border: none !important;
  border-radius: 8px !important;
  font-size: 0.85rem !important;
  font-weight: 600 !important;
  padding: 0.45rem 1.1rem !important;
  transition: background 0.2s ease, transform 0.15s ease !important;
  letter-spacing: 0.01em;
}
.stButton > button:hover {
  background: var(--accent-light) !important;
  transform: translateY(-1px);
}

/* Force form submit buttons green */
[data-testid="stFormSubmitButton"] button,
form[data-testid="stForm"] button[type="submit"] {
  background: var(--accent) !important;
  color: #FFFFFF !important;
  border: none !important;
}

/* Sidebar: compact form spacing, no line breaks */
div[data-testid="stSidebar"] .stDateInput,
div[data-testid="stSidebar"] .stSelectbox,
div[data-testid="stSidebar"] .stTextInput,
div[data-testid="stSidebar"] .stButton,
div[data-testid="stSidebar"] .stCaption,
div[data-testid="stSidebar"] .stMarkdown {
  margin-bottom: 0.18rem !important;
  line-height: 1.05 !important;
}
div[data-testid="stSidebar"] .stDateInput input,
div[data-testid="stSidebar"] .stSelectbox div[data-baseweb="select"],
div[data-testid="stSidebar"] .stTextInput input {
  font-size: 0.8rem !important;
  padding-top: 0.2rem !important;
  padding-bottom: 0.2rem !important;
}
div[data-testid="stSidebar"] .stDateInput label,
div[data-testid="stSidebar"] .stSelectbox label,
div[data-testid="stSidebar"] .stTextInput label {
  font-size: 0.75rem !important;
  margin-bottom: 0.05rem !important;
}

/* Inputs */
.stTextInput input, .stSelectbox div[data-baseweb="select"] > div,
.stDateInput input, .stNumberInput input, .stTextArea textarea,
div[role="radiogroup"] label {
  color: var(--text) !important;
}
.stTextInput input, .stSelectbox div[data-baseweb="select"] > div,
.stDateInput input, .stNumberInput input, .stTextArea textarea {
  background: #000000 !important;
  border: 1px solid var(--border) !important;
  border-radius: 8px !important;
}
.stTextInput input:not([type="password"]):focus, .stSelectbox div[data-baseweb="select"] > div:focus,
.stDateInput input:focus, .stNumberInput input:focus, .stTextArea textarea:focus {
  border-color: var(--primary) !important;
  box-shadow: 0 0 0 2px rgba(30,58,138,0.35) !important;
}

/* Room cards */
.room-card {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 12px 14px;
  margin-bottom: 8px;
  transition: border-color 0.2s ease;
}
.room-card:hover {
  border-color: rgba(255,255,255,0.28);
}

/* Tabs */
.stTabs [data-baseweb="tab-list"] { background: transparent !important; border-bottom: 1px solid var(--border) !important; }
.stTabs [data-baseweb="tab"] { color: var(--muted) !important; font-size: 1.05rem !important; font-weight: 500 !important; padding: 0.6rem 1rem !important; }
.stTabs [aria-selected="true"] { color: var(--accent-light) !important; border-bottom: 2px solid var(--accent) !important; font-size: 1.15rem !important; font-weight: 600 !important; }
div[data-baseweb="tab-highlight"] { display: none !important; }

/* Alerts / toasts */
.stAlert, div[data-testid="stStatusWidget"], div[data-testid="stToast"] {
  background: #111111 !important;
  border: 1px solid var(--border) !important;
  color: #F8F9FA !important;
  border-radius: 10px !important;
}

/* Dataframes */
div[data-testid="stDataFrame"] {
  border: 1px solid var(--border) !important;
  border-radius: var(--radius) !important;
  overflow: hidden !important;
}

/* Misc utility */
.muted { color: var(--muted) !important; }
.section-label {
  font-size: 0.78rem !important;
  letter-spacing: 0.07em;
  text-transform: uppercase;
  color: var(--muted) !important;
  margin-bottom: 10px;
}

/* Reduced motion */
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after {
    animation-duration: 0.01ms !important;
    transition-duration: 0.01ms !important;
  }
}

/* Hide sidebar collapse toggle arrow/button entirely */
[data-testid="collapsedControl"],
[data-testid="stSidebarCollapseButton"] {
  display: none !important;
}

/* Sidebar: fit in one screen and do not scroll */
[data-testid="stSidebar"] {
  max-height: 100vh !important;
  overflow-y: hidden !important;
}

/* Mobile: hide sidebar so only dashboard is visible */
@media (max-width: 768px) {
  [data-testid="stSidebar"] {
    display: none !important;
  }
  [data-testid="stAppViewContainer"] {
    margin-left: 0 !important;
    padding-left: 0 !important;
  }
}
</style>
""", unsafe_allow_html=True)

# Constants
_NPL = pytz.timezone("Asia/Kathmandu")
_SEARCH_MAX_LEN = 100
_CHECKOUT_TIME = dt_time(12, 0, 0)
_CHECKIN_TIME = dt_time(12, 0, 1)


def now_npl() -> datetime:
    return datetime.now(_NPL)


# Auth
_DASH_PWD = _read_secret("dashboard_password", "DASHBOARD_PASSWORD")

if not _DASH_PWD:
    st.error("DASHBOARD_PASSWORD is not configured. Contact your system administrator.")
    st.stop()

_DASH_AUTH_SECRET = os.getenv("DASHBOARD_AUTH_SECRET", "") or _DASH_PWD
_DASH_AUTH_TTL = 12 * 60 * 60  # 12 hours


def _create_dashboard_auth_token(secret: str) -> str:
    expiry = int(time.time()) + _DASH_AUTH_TTL
    msg = f"{expiry}".encode("utf-8")
    sig = hmac.new(secret.encode("utf-8"), msg, hashlib.sha256).hexdigest()
    return f"{expiry}.{sig}"


def _verify_dashboard_auth_token(secret: str, token: str) -> bool:
    try:
        parts = token.split(".", 1)
        if len(parts) != 2:
            return False
        expiry_str, sig = parts
        expiry = int(expiry_str)
        if time.time() > expiry:
            return False
        msg = f"{expiry}".encode("utf-8")
        expected = hmac.new(secret.encode("utf-8"), msg, hashlib.sha256).hexdigest()
        return hmac.compare_digest(sig, expected)
    except Exception:
        return False


if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

try:
    raw_token = st.query_params.get("auth", "")
    if raw_token and _verify_dashboard_auth_token(_DASH_AUTH_SECRET, raw_token):
        st.session_state.authenticated = True
        st.markdown(
            "<script>"
            "try { if (window.history.replaceState) { window.history.replaceState({}, '', window.location.pathname); } } catch (e) {}"
            "</script>",
            unsafe_allow_html=True,
        )
except Exception:
    pass

# Login wrapper
if not st.session_state.authenticated:
    st.markdown("""
    <style>
    html, body {
        overflow: hidden !important;
        margin: 0 !important;
        padding: 0 !important;
        height: 100vh !important;
        width: 100vw !important;
        background: #000000 !important;
    }
    html, body, [class*="css"], #root, div[data-testid="stAppViewContainer"] {
        background-color: #000000 !important;
        color: #F8F9FA !important;
    }
    .login-brand {
        text-align: center;
        margin-bottom: 34px;
    }
    .login-brand h1 {
        font-family: 'Fira Sans', sans-serif !important;
        font-weight: 700 !important;
        font-size: 3rem !important;
        letter-spacing: 0.03em;
        margin: 0;
        color: #FFFFFF !important;
    }
    .login-brand p {
        color: #B0B8C0 !important;
        font-size: 1.05rem !important;
        margin-top: 10px !important;
        letter-spacing: 0.04em;
        text-transform: uppercase;
    }
    .login-footer {
        text-align: center;
        margin-top: 26px;
        font-size: 0.9rem !important;
        color: #6B7280 !important;
    }
    .login-footer strong {
        color: #9CA3AF !important;
        font-weight: 500;
    }
    [data-testid="stColumn"]:nth-of-type(2) .stContainer {
        background: rgba(12, 12, 12, 0.98);
        border: 1px solid rgba(255, 255, 255, 0.10);
        border-radius: 28px;
        padding: 68px 42px 52px;
        max-width: 460px;
        box-shadow: 0 30px 70px rgba(0,0,0,0.95), 0 0 0 1px rgba(255,255,255,0.04) inset;
        margin-top: -25vh;
    }
    form[data-testid="stForm"] {
        border: 1px solid rgba(255,255,255,0.08) !important;
        border-radius: 18px !important;
        padding: 24px !important;
        background: rgba(18,18,18,0.8) !important;
    }
    /* Force password input: hide any red/hidden border, show white only on focus */
    form[data-testid="stForm"] .stTextInput,
    form[data-testid="stForm"] .stTextInput > div,
    form[data-testid="stForm"] .stTextInput > div > div,
    form[data-testid="stForm"] .stTextInput [data-baseweb="input"],
    form[data-testid="stForm"] .stTextInput [data-baseweb="input"] > div,
    form[data-testid="stForm"] .stTextInput input[type="password"],
    form[data-testid="stForm"] .stTextInput [data-baseweb="input"] input {
        height: 60px !important;
        min-height: 60px !important;
        max-height: 60px !important;
        box-sizing: border-box !important;
        border: 0px solid transparent !important;
        border-style: hidden !important;
        background: #000000 !important;
        color: #F8F9FA !important;
        border-radius: 10px !important;
        padding: 18px 20px !important;
        font-size: 1.05rem !important;
        outline: none !important;
        outline-color: transparent !important;
        box-shadow: none !important;
        transition: none !important;
    }
    form[data-testid="stForm"] .stTextInput:focus-within input[type="password"],
    form[data-testid="stForm"] .stTextInput:focus-within [data-baseweb="input"],
    form[data-testid="stForm"] input[type="password"]:focus,
    form[data-testid="stForm"] input[type="password"]:focus-visible {
        border: 2px solid #FFFFFF !important;
        border-color: #FFFFFF !important;
        outline: none !important;
        outline-color: transparent !important;
        box-shadow: none !important;
        transition: none !important;
    }
    .stButton > button {
        background: #16A34A !important;
        color: #FFFFFF !important;
        border: none !important;
        border-radius: 10px !important;
        font-size: 1rem !important;
        font-weight: 600 !important;
        padding: 0.8rem 1.1rem !important;
        letter-spacing: 0.04em;
        transition: transform 0.15s ease, background 0.15s ease !important;
    }
    .stButton > button:hover {
        background: #4ADE80 !important;
        color: #000000 !important;
        transform: translateY(-1px);
    }

    /* Suppress Streamlit form-submit hints/tooltips on login */
    [data-testid="stTooltip"] { display: none !important; }
    [role="tooltip"] { display: none !important; }
    .stTextInput [class*="e1kt9bl72"] { display: none !important; }
    .stTextInput [class*="epumps80"] { display: none !important; }
    </style>
    <script>
    (function() {
      function removePressEnterHints() {
        var walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
        var node;
        var found = false;
        while (node = walker.nextNode()) {
          if (node.textContent.trim().toLowerCase().indexOf('press enter') !== -1) {
            var parent = node.parentElement;
            if (parent) {
              parent.style.display = 'none';
              found = true;
            }
          }
        }
        if (found) console.log('Removed press-enter hints via JS');
      }
      function observeAndRemove() {
        removePressEnterHints();
        if (window._pressEnterObserver) window._pressEnterObserver.disconnect();
        window._pressEnterObserver = new MutationObserver(function() {
          removePressEnterHints();
        });
        window._pressEnterObserver.observe(document.body, { childList: true, subtree: true });
      }
      if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', observeAndRemove);
      } else {
        observeAndRemove();
      }
    })();
    </script>
    """, unsafe_allow_html=True)
    st.markdown('<div style="height: 10vh;"></div>', unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 3, 1])
    with col2:
            st.markdown("""
            <div class="login-brand">
                <br>
                <h1>Natura Resort</h1>
                <br>
                <p>Admin Dashboard</p>
            </div>
            """, unsafe_allow_html=True)
            with st.form("login_form", clear_on_submit=True):
                col_a, col_b, col_c = st.columns([1, 2, 1])
                with col_b:
                    pwd = st.text_input(
                        label="Password",
                        type="password",
                        placeholder="Enter admin password",
                        label_visibility="collapsed",
                    )
                    submitted = st.form_submit_button("Sign In", use_container_width=True, type="primary")
                    if submitted:
                        if hmac.compare_digest(_DASH_PWD.encode(), pwd.encode()):
                            st.session_state.authenticated = True
                            st.markdown(
                                "<script>"
                                "try { if (window.history.replaceState) { window.history.replaceState({}, '', window.location.pathname + '?dashboard_auth=1'); } } catch (e) {}"
                                "</script>",
                                unsafe_allow_html=True,
                            )
                            st.rerun()
                        else:
                            st.error("Incorrect password. Please try again.")
            st.markdown("""
            <style>
            login-form-check-fix::part(root) {
              display: none !important;
            }

            /* Suppress Streamlit form QA / accessibility checker overlays on login form */
            [data-testid="stAlert"]:has(> div > div > *:is(p, span)[data-testid="stAlertContent"]),
            form[data-testid="stForm"] ~ div[role="alert"],
            form[data-testid="stForm"] + div[role="alert"],
            div[role="alert"] > div > div > p {
              display: none !important;
            }

            /* Suppress the inline Streamlit form-submit hints/tooltips on login */
            [data-testid="stTooltip"] { display: none !important; }
            [role="tooltip"] { display: none !important; }
            .stTextInput [class*="e1kt9bl72"] { display: none !important; }
            .stTextInput [class*="epumps80"] { display: none !important; }

            /* Hide injected alert banners/tooltips that contain submit-button warnings */
            form[data-testid="stForm"] ~ div[role="status"],
            form[data-testid="stForm"] + div[role="status"],
            form[data-testid="stForm"] ~ div[role="alert"] {
              display: none !important;
            }
            </style>
            <script>
            (function() {
              "use strict";
              var formSelector = 'form[data-testid="stForm"]';

              function hideBadAlerts(node) {
                var walker = document.createTreeWalker(
                  node || document.body,
                  NodeFilter.SHOW_ELEMENT
                );
                var el;
                var removed = 0;
                while ((el = walker.nextNode())) {
                  try {
                    var text = (el.textContent || '').trim();
                    if (
                      text.indexOf('submit button') !== -1 ||
                      text.indexOf('user interactions will never be sent') !== -1
                    ) {
                      el.style.setProperty('display', 'none', 'important');
                      el.setAttribute('aria-hidden', 'true');
                      removed++;
                    }
                  } catch (e) {}
                }
                return removed;
              }

              function run() {
                hideBadAlerts();
                var form = document.querySelector(formSelector);
                if (!form) return;
                if (form._loginFormFix) return;
                form._loginFormFix = true;

                form.addEventListener('keydown', function(e) {
                  if (e.key === 'Enter' && e.target.tagName !== 'TEXTAREA') {
                    e.preventDefault();
                    e.stopPropagation();
                    var btn = form.querySelector('button[type="submit"]');
                    if (btn) btn.click();
                  }
                });

                var observer = new MutationObserver(function() {
                  hideBadAlerts();
                });
                try {
                  observer.observe(form.parentElement || document.body, {
                    childList: true,
                    subtree: true
                  });
                } catch (e) {}
              }

              if (document.readyState === 'loading') {
                document.addEventListener('DOMContentLoaded', run);
              } else {
                run();
              }
            })();
            </script>
            """, unsafe_allow_html=True)
            st.markdown("""
            <div class="login-footer">
                <strong>Restricted Access</strong> - Authorized personnel only
            </div>
            """, unsafe_allow_html=True)
    st.stop()

# DB
@st.cache_resource
def get_pool() -> mysql.connector.pooling.MySQLConnectionPool:
    # Force the secret to be re-read every time so container restarts with new secrets work reliably.
    host = os.getenv("DB_HOST", "localhost")
    user = os.getenv("DB_USER")
    password = _read_secret("db_app_password", "DB_PASSWORD")
    db = os.getenv("DB_NAME")

    missing = [n for n, v in [("DB_USER", user), ("DB_PASSWORD", password), ("DB_NAME", db)] if not v]
    if missing:
        raise ValueError(f"Missing required DB environment variable(s): {', '.join(missing)}")

    if user == "root":
        raise ValueError(
            "DB_USER=root is not permitted. Create a least-privilege MySQL user and "
            "update DB_USER. The 'resort_app' user should be used in production."
        )

    try:
        pool_size = max(1, min(32, int(os.getenv("DB_POOL_SIZE", "5"))))
    except ValueError:
        pool_size = 5

    return mysql.connector.pooling.MySQLConnectionPool(
        pool_name="dash_pool",
        pool_size=pool_size,
        pool_reset_session=True,
        host=host,
        port=int(os.getenv("DB_PORT", "3306")),
        user=user,
        password=password,
        database=db,
        autocommit=False,
        charset="utf8mb4",
        collation="utf8mb4_unicode_ci",
        connection_timeout=10,
    )


def _conn():
    try:
        return get_pool().get_connection()
    except Exception as e:
        st.error("Could not connect to the database. Please try again later.")
        st.stop()


def run_q(sql: str, params: tuple = (), fetch: str = "all"):
    """Execute a read-only query and return results. Always cleans up."""
    c = _conn()
    cur = c.cursor(dictionary=True)
    try:
        cur.execute(sql, params)
        return cur.fetchall() if fetch == "all" else cur.fetchone()
    except mysql.connector.Error as err:
        st.error(f"Database query failed: {err}")
        return [] if fetch == "all" else None
    finally:
        cur.close()
        try:
            c.rollback()
        except Exception:
            pass
        c.close()


def run_write(sql: str, params: tuple = ()):
    """Execute a single write statement inside its own transaction."""
    c = _conn()
    cur = c.cursor()
    try:
        cur.execute(sql, params)
        c.commit()
        return cur.lastrowid or cur.rowcount
    except mysql.connector.Error:
        c.rollback()
        # Re-raise as
        # without leaking
        raise RuntimeError("Database write failed. Please try again.")
    finally:
        cur.close()
        c.close()


def run_transaction(callback):
    """Run callback(cursor) inside a REPEATABLE READ transaction."""
    c = _conn()
    cur = c.cursor(dictionary=True)
    try:
        c.start_transaction(isolation_level="REPEATABLE READ")
        result = callback(cur)
        c.commit()
        return result
    except Exception:
        try:
            c.rollback()
        except Exception:
            pass
        raise
    finally:
        cur.close()
        c.close()


def apply_checkout_statuses():
    now = now_npl()
    today = now.date()

    if now.time() >= _CHECKOUT_TIME:
        def _turnover(cur):
            print(f"[turnover:overview] now={now}, today={today}")
            # Complete overdue and today's checkouts
            cur.execute(
                """
                UPDATE reservations
                SET reservation_status = 'completed', checkout_time = %s
                WHERE check_out_date < %s AND reservation_status IN ('pending', 'active')
                """,
                (now.time(), today),
            )
            print(f"[turnover:overview] completed past_due={cur.rowcount}")

            if now.time() >= _CHECKOUT_TIME:
                cur.execute(
                    """
                    UPDATE reservations
                    SET reservation_status = 'completed', checkout_time = %s
                    WHERE check_out_date = %s AND reservation_status = 'active'
                    """,
                    (now.time(), today),
                )
                print(f"[turnover:overview] completed today_active={cur.rowcount}")

            # Turnover: completed rooms go to occupied if same-day pending/active exists, else available
            cur.execute("""
                UPDATE rooms r
                LEFT JOIN reservations res ON res.room_id = r.room_id
                    AND res.reservation_status IN ('pending', 'active')
                    AND res.check_in_date <= %s
                    AND res.check_out_date >= %s
                SET r.status = CASE WHEN res.room_id IS NOT NULL THEN 'occupied' ELSE 'available' END
            """, (today, today))
            print(f"[turnover:overview] room sync updated={cur.rowcount}")

            # Activate pending reservations that now have an occupied room
            cur.execute("""
                UPDATE reservations res
                JOIN rooms r ON r.room_id = res.room_id
                SET res.reservation_status = 'active'
                WHERE res.reservation_status = 'pending'
                  AND res.check_in_date <= %s
                  AND r.status = 'occupied'
            """, (today,))

            # At 2PM, activate any remaining pending reservations for rooms already occupied
            if now.time() >= _CHECKIN_TIME:
                cur.execute(
                    """
                    UPDATE reservations r JOIN rooms rm ON rm.room_id = r.room_id
                    SET r.reservation_status = 'active', rm.status = 'occupied'
                    WHERE r.check_in_date = %s AND r.reservation_status = 'pending'
                      AND rm.status = 'occupied'
                    """,
                    (today,),
                )

            # Cleanup rooms with no active/pending reservations
            cur.execute(
                """
                UPDATE rooms r
                SET r.status = 'available'
                WHERE r.status IN ('available', 'maintenance')
                  AND NOT EXISTS (
                      SELECT 1 FROM reservations res
                      WHERE res.room_id = r.room_id
                        AND res.reservation_status IN ('pending', 'active')
                  )
                """
            )

        run_transaction(_turnover)


def free_room_if_empty(cur, room_id: int):
    cur.execute(
        """
        SELECT 1 FROM reservations
        WHERE room_id = %s AND reservation_status IN ('pending','active')
        LIMIT 1
        """,
        (room_id,),
    )
    if not cur.fetchone():
        cur.execute(
            "UPDATE rooms SET status = 'available' WHERE room_id = %s AND status = 'occupied'",
            (room_id,),
        )


# Watcher
def db_fingerprint():
    try:
        row = run_q("""
            SELECT
                (SELECT COUNT(*) FROM reservations)  AS r_count,
                (SELECT COUNT(*) FROM rooms)          AS rm_count,
                (SELECT COUNT(*) FROM guests)         AS g_count,
                (SELECT COALESCE(MAX(reservation_id), 0) FROM reservations) AS r_max,
                (SELECT COALESCE(MAX(room_id),        0) FROM rooms)        AS rm_max
        """, fetch="one")
        return (row["r_count"], row["rm_count"], row["g_count"], row["r_max"], row["rm_max"])
    except Exception:
        return None


if "db_fp" not in st.session_state:
    st.session_state.db_fp = db_fingerprint()

if "page" not in st.session_state:
    st.session_state.page = "Overview"


@st.fragment(run_every=5)
def _db_watcher():
    current_fp = db_fingerprint()
    if current_fp is not None and current_fp != st.session_state.db_fp:
        st.session_state.db_fp = current_fp
        st.rerun()


_db_watcher()

# Header
col_logo, col_time = st.columns([1, 1])
with col_logo:
    st.markdown(
        "<span class='header-logo'>Natura Resort</span>",
        unsafe_allow_html=True,
    )
with col_time:
    st.markdown(
        f"<div class='header-time'>"
        f"{now_npl().strftime('%A, %d %B %Y  %H:%M NST')}</div>",
        unsafe_allow_html=True,
    )

st.markdown("<div style='height:4px; margin-bottom: 20px;'></div>", unsafe_allow_html=True)

# Sidebar
with st.sidebar:
    if st.button("Dashboard", use_container_width=True):
        st.session_state.page = "Overview"; st.rerun()
    if st.button("Reservations", use_container_width=True):
        st.session_state.page = "Reservations Table"; st.rerun()
    if st.button("Guest Info", use_container_width=True):
        st.session_state.page = "Guest Info Table"; st.rerun()
    if st.button("Rooms", use_container_width=True):
        st.session_state.page = "Rooms Table"; st.rerun()
    if st.button("Settings", use_container_width=True):
        st.session_state.page = "Settings"; st.rerun()

    st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)
    st.markdown("<div class='sidebar-title'>Fast Reservation</div>", unsafe_allow_html=True)
    st.markdown("<hr class='sidebar-hr'/>", unsafe_allow_html=True)

    sb_today = now_npl().date()

    if "sb_fres_room_id" not in st.session_state:
        st.session_state.sb_fres_room_id = None

    def _sync_checkout_to_checkin():
        ci = st.session_state.get("sb_fres_ci", sb_today)
        co = st.session_state.get("sb_fres_co")
        if co is None or co <= ci:
            st.session_state["sb_fres_co"] = ci + timedelta(days=1)

    def _available_rooms(ci, co):
        return run_q("""
            SELECT r.room_id, r.room_number, rt.type_name
            FROM rooms r
            JOIN room_types rt ON r.room_type_id = rt.room_type_id
            WHERE r.status != 'maintenance'
            AND NOT EXISTS (
                SELECT 1 FROM reservations res
                WHERE res.room_id = r.room_id
                  AND res.reservation_status IN ('pending', 'active')
                  AND res.check_in_date < %s AND res.check_out_date > %s
            )
            ORDER BY r.room_number
        """, (co, ci))

    # Room selector
    _ci_val = st.session_state.get("sb_fres_ci", sb_today)
    _co_val = st.session_state.get("sb_fres_co", sb_today + timedelta(days=1))

    if _co_val <= _ci_val:
        st.session_state["sb_fres_co"] = _ci_val + timedelta(days=1)
        _co_val = _ci_val + timedelta(days=1)

    _date_err = _co_val <= _ci_val
    _rooms = _available_rooms(_ci_val, _co_val) if not _date_err else []
    _room_ids = [r["room_id"] for r in _rooms]
    if st.session_state.sb_fres_room_id not in _room_ids:
        st.session_state.sb_fres_room_id = None

    if _rooms:
        opts = {f"Room {r['room_number']} — {r['type_name']}": r for r in _rooms}
        sel = st.selectbox(
            "Room",
            list(opts.keys()),
            index=list(opts.keys()).index(next((k for k, v in opts.items() if v["room_id"] == st.session_state.sb_fres_room_id), list(opts.keys())[0])) if st.session_state.sb_fres_room_id else 0,
            key="sb_fres_rm",
            placeholder="Select a room",
        )
        st.session_state.sb_fres_room_id = opts[sel]["room_id"] if sel else None
        target_room = opts[sel] if sel else None
    else:
        st.selectbox("Room", [], disabled=True, key="sb_fres_rm", placeholder="No options to select")
        target_room = None

    # Dates
    date_col1, date_col2 = st.columns(2)
    with date_col1:
        sb_ci = st.date_input(
            "Check-in",
            value=sb_today,
            min_value=sb_today,
            key="sb_fres_ci",
            on_change=_sync_checkout_to_checkin,
        )
    with date_col2:
        sb_co_min = sb_ci + timedelta(days=1)
        sb_co = st.date_input(
            "Check-out",
            value=sb_co_min,
            min_value=sb_co_min,
            key="sb_fres_co",
        )

    date_error = sb_co <= sb_ci

    # Guest
    walkin_name  = st.text_input("Guest name",  placeholder="Full name", key="sb_walkin_name")
    walkin_phone = st.text_input("Guest phone", key="sb_walkin_phone")

    can_book = bool(target_room and not date_error and walkin_name.strip() and walkin_phone.strip())
    if st.button("Book", use_container_width=True, disabled=not can_book, key="sb_book_btn", type="primary"):
        if not target_room:
            st.error("No rooms available for the selected dates.")
        elif not walkin_name.strip() or not walkin_phone.strip():
            st.error("Please provide guest name and phone number.")
        else:
            if sb_ci == sb_today:
                res_status = "active" if now_npl().time() >= _CHECKIN_TIME else "pending"
            else:
                res_status = "pending"

            def execute_walkin_booking(cur):
                cur.execute(
                    "SELECT status FROM rooms WHERE room_id = %s FOR UPDATE",
                    (target_room["room_id"],),
                )
                rm_check = cur.fetchone()
                if not rm_check or rm_check["status"] == "maintenance":
                    raise RuntimeError("Selected room was placed in maintenance during your selection. Please choose another.")

                cur.execute("""
                    SELECT 1 FROM reservations
                    WHERE room_id = %s
                      AND reservation_status IN ('pending', 'active')
                      AND check_in_date < %s
                      AND check_out_date > %s
                    FOR UPDATE
                """, (target_room["room_id"], sb_co, sb_ci))
                if cur.fetchone():
                    raise RuntimeError("This room was just reserved by another session. Please refresh and try again.")

                walkin_email = "walkin@natura.com"
                cur.execute("""
                    INSERT INTO guests (full_name, email, phone)
                    VALUES (%s, %s, %s)
                    ON DUPLICATE KEY UPDATE
                        guest_id = LAST_INSERT_ID(guest_id)
                """, (walkin_name.strip(), walkin_email, walkin_phone.strip()))
                gid = cur.lastrowid

                cur.execute("""
                    INSERT INTO reservations
                        (room_id, guest_id, guest_name, check_in_date, check_out_date, checkout_time, reservation_status)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """, (target_room["room_id"], gid, walkin_name.strip(), sb_ci, sb_co, _CHECKOUT_TIME, res_status))

                if res_status == "active":
                    cur.execute(
                        "UPDATE rooms SET status = 'occupied' WHERE room_id = %s",
                        (target_room["room_id"],),
                    )

            try:
                run_transaction(execute_walkin_booking)
                st.toast(f"Room {target_room['room_number']} booked successfully!", icon="✅")
                st.session_state.sb_fres_room_id = None
            except RuntimeError as e:
                st.error(str(e))
            except Exception as e:
                st.error(f"Booking failed: {e}")
            else:
                st.rerun()

apply_checkout_statuses()

# Page
if st.session_state.page == "Overview":
    today = now_npl().date()

    rooms_all = run_q("""
        SELECT r.room_id, r.room_number, r.status, rt.type_name
        FROM rooms r
        JOIN room_types rt ON r.room_type_id = rt.room_type_id
        ORDER BY r.room_number
    """)

    reservation_map = {}
    for row in run_q("""
        SELECT res.room_id, res.reservation_status, res.check_in_date, res.check_out_date,
               COALESCE(res.guest_name, g.full_name) AS guest_name
        FROM reservations res
        JOIN guests g ON g.guest_id = res.guest_id
        WHERE res.reservation_status IN ('pending', 'active')
          AND res.check_in_date <= %s
          AND res.check_out_date >= %s
    """, (today, today)):
        reservation_map[row["room_id"]] = row

    for room in rooms_all:
        res = reservation_map.get(room["room_id"])
        if room["status"] == "maintenance":
            room["effective_status"] = "maintenance"
        elif res:
            room["effective_status"] = "occupied"
            room["guest_name"] = res.get("guest_name") or ""
            room["check_in_date"] = res.get("check_in_date")
            room["check_out_date"] = res.get("check_out_date")
        else:
            room["effective_status"] = room["status"]
            room["guest_name"] = ""
            room["check_in_date"] = None
            room["check_out_date"] = None

    avail = sum(1 for r in rooms_all if r["effective_status"] == "available")
    occ   = sum(1 for r in rooms_all if r["effective_status"] == "occupied")
    maint = sum(1 for r in rooms_all if r["effective_status"] == "maintenance")

    checkins_today = sum(
        1 for r in rooms_all
        if r.get("check_in_date") == today and r["effective_status"] == "occupied"
    )

    room_type_map = {}
    for room in rooms_all:
        rt = room["type_name"]
        if rt not in room_type_map:
            room_type_map[rt] = {"type_name": rt, "total": 0, "available": 0}
        room_type_map[rt]["total"] += 1
        if room["effective_status"] == "available":
            room_type_map[rt]["available"] += 1

    room_types = []
    for rt_name in ["Super Deluxe (Single)", "Super Deluxe (Twin)", "Super Deluxe (Triple)", "Single", "Twin", "Double", "Triple"]:
        if rt_name in room_type_map:
            room_types.append(room_type_map[rt_name])
    for rt_name, rt_info in room_type_map.items():
        if rt_name not in ["Super Deluxe (Single)", "Super Deluxe (Twin)", "Super Deluxe (Triple)", "Single", "Twin", "Double", "Triple"]:
            room_types.append(rt_info)

    c1, c2, c3 = st.columns(3, gap="small")
    c1.metric("Rooms Occupied", f"{occ} Rooms")
    c2.metric("Rooms Available", f"{avail} Vacant")
    c3.metric("Under Maintenance", f"{maint} Locked")

    sd_single = next((rt for rt in room_types if rt["type_name"] == "Super Deluxe (Single)"), None)
    sd_twin = next((rt for rt in room_types if rt["type_name"] == "Super Deluxe (Twin)"), None)
    sd_triple = next((rt for rt in room_types if rt["type_name"] == "Super Deluxe (Triple)"), None)

    d1, d2, d3 = st.columns(3, gap="small")
    d1.metric("Super Deluxe (Single) Available", f"{int(sd_single['available'] if sd_single else 0)} / {int(sd_single['total'] if sd_single else 0)}")
    d2.metric("Super Deluxe (Twin) Available", f"{int(sd_twin['available'] if sd_twin else 0)} / {int(sd_twin['total'] if sd_twin else 0)}")
    d3.metric("Super Deluxe (Triple) Available", f"{int(sd_triple['available'] if sd_triple else 0)} / {int(sd_triple['total'] if sd_triple else 0)}")

    st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)

    STATUS_CARD = {
        "available": {"bg": "#052E16", "border": "#16A34A", "text": "#4ADE80", "label": "Vacant / Ready"},
        "occupied":  {"bg": "#3B0D0D", "border": "#EF4444", "text": "#FCA5A5", "label": "Occupied"},
        "maintenance": {"bg": "#3B2E05", "border": "#D4A017", "text": "#FDE68A", "label": "Maintenance"},
    }
    white = "#FFFFFF"
    card_cols = st.columns(4)
    for i, rm in enumerate(rooms_all):
        style = STATUS_CARD.get(rm["effective_status"], {
            "bg": "var(--surface2)", "border": "var(--border)", "text": "var(--text)", "label": rm.get("effective_status") or rm.get("status", "")
        })
        guest_clean = html.escape(rm.get("guest_name") or "")
        guest_row = (
            f"<div style='font-size:0.75rem;color:{style['text']};margin-top:1px'>{guest_clean}</div>"
            f"<div style='font-size:0.68rem;color:{style['text']};opacity:0.8'>"
            f"{rm['check_in_date']} -> {rm['check_out_date']}</div>"
            if guest_clean else f"<div style='font-size:0.8rem;color:{style['text']};margin-top:1px'>{style['label']}</div>"
        )
        with card_cols[i % 4]:
            st.markdown(f"""
            <div class='room-card' style='background:{style['bg']};border:1px solid {style['border']};border-radius:12px;padding:10px 12px;min-height:88px;'>
              <div style='font-weight:600;font-size:0.95rem;color:{white}'>Room {html.escape(str(rm['room_number']))}</div>
              <div style='font-size:0.75rem;color:{white};opacity:0.92;margin-top:1px'>{html.escape(rm['type_name'])}</div>
              <div style='margin-top:6px;border-top:1px solid rgba(255,255,255,0.06);padding-top:5px;'>
                {guest_row}
              </div>
            </div>
            """, unsafe_allow_html=True)

# Page
elif st.session_state.page == "Reservations Table":
    st.markdown("## Reservations")

    fc1, fc2 = st.columns([1, 2])
    with fc1:
        f_status = st.selectbox("Filter Status", ["All", "pending", "active", "completed", "cancelled"])
    with fc2:
        f_search = st.text_input("Search by Guest Name...", placeholder="Type name here...", max_chars=_SEARCH_MAX_LEN)

    sql = """
        SELECT res.reservation_id, res.room_id, COALESCE(res.guest_name, g.full_name) AS guest_name, r.room_number, rt.type_name,
               res.check_in_date, res.check_out_date, res.reservation_status,
               DATEDIFF(res.check_out_date, res.check_in_date) AS nights, rt.price
        FROM reservations res
        JOIN guests    g  ON g.guest_id    = res.guest_id
        JOIN rooms     r  ON r.room_id     = res.room_id
        JOIN room_types rt ON rt.room_type_id = r.room_type_id
    """
    conds, params = [], []
    if f_status != "All":
        conds.append("res.reservation_status = %s")
        params.append(f_status)
    if f_search:
        conds.append("(res.guest_name LIKE %s OR g.full_name LIKE %s)")
        params.extend([f"%{f_search[:_SEARCH_MAX_LEN]}%", f"%{f_search[:_SEARCH_MAX_LEN]}%"])

    if conds:
        sql += " WHERE " + " AND ".join(conds)
    sql += " ORDER BY res.check_in_date ASC"

    reservations = run_q(sql, params)

    if reservations:
        df = pd.DataFrame(reservations)
        df["total_cost"] = df.apply(
            lambda row: f"NPR {float(row['price']) * int(row['nights']):,.2f}", axis=1
        )
        st.dataframe(
            df[["reservation_id", "guest_name", "room_number", "type_name",
                "check_in_date", "check_out_date", "nights", "total_cost", "reservation_status"]
            ].rename(columns={
                "reservation_id":     "ID",
                "guest_name":         "Guest Name",
                "room_number":        "Room",
                "type_name":          "Room Type",
                "check_in_date":      "Check-In",
                "check_out_date":     "Check-Out",
                "nights":             "Nights",
                "total_cost":         "Total Price",
                "reservation_status": "Status",
            }),
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.info("No records match your search criteria.")

# Page
elif st.session_state.page == "Guest Info Table":
    st.markdown("## Guest Info")
    search_g = st.text_input(
        "Search Directory...",
        placeholder="Type name, phone, or email...",
        max_chars=_SEARCH_MAX_LEN,
    )

    # Select explicit
    base_cols = (
        "SELECT g.guest_id, g.full_name, g.email, g.phone, "
        "GROUP_CONCAT(DISTINCT r.room_number ORDER BY res.check_in_date SEPARATOR ', ') AS room_numbers "
        "FROM guests g "
        "LEFT JOIN reservations res ON res.guest_id = g.guest_id "
        "LEFT JOIN rooms r ON r.room_id = res.room_id "
        "GROUP BY g.guest_id, g.full_name, g.email, g.phone"
    )
    if search_g:
        term = f"%{search_g[:_SEARCH_MAX_LEN]}%"
        guests = run_q(
            base_cols + " WHERE full_name LIKE %s OR email LIKE %s OR phone LIKE %s ORDER BY full_name",
            (term, term, term),
        )
    else:
        guests = run_q(base_cols + " ORDER BY full_name")

    if guests:
        df_guests = pd.DataFrame(guests)
        if "room_numbers" not in df_guests.columns:
            df_guests["room_numbers"] = ""
        st.dataframe(
            df_guests.rename(columns={
                "guest_id":    "Guest ID",
                "full_name":   "Full Name",
                "email":       "Email Address",
                "phone":       "Phone Number",
                "room_numbers":"Room Number",
            }),
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.info("No guest profiles found.")

# Page
elif st.session_state.page == "Rooms Table":
    st.markdown("## Live Room Inventory")

    f_rm_status = st.selectbox("Filter Status", ["All", "available", "occupied", "maintenance"])
    today = now_npl().date()
    room_full = run_q("""
        SELECT
            r.room_id,
            r.room_number,
            rt.type_name,
            CASE
                WHEN r.status = 'maintenance' THEN 'maintenance'
                WHEN EXISTS (
                    SELECT 1 FROM reservations res
                    WHERE res.room_id = r.room_id
                      AND res.reservation_status IN ('pending', 'active')
                      AND res.check_in_date <= %s
                      AND res.check_out_date >= %s
                ) THEN 'occupied'
                ELSE r.status
            END AS status,
            rt.price,
            rt.capacity
        FROM rooms r
        JOIN room_types rt ON r.room_type_id = rt.room_type_id
        ORDER BY r.room_number
    """, (today, today))
    if f_rm_status != "All":
        room_full = [r for r in room_full if r["status"] == f_rm_status]

    if room_full:
        df_rooms = pd.DataFrame(room_full)
        df_rooms["price"] = df_rooms["price"].apply(lambda x: f"NPR {float(x):,.2f}")
        st.dataframe(
            df_rooms[["room_id", "room_number", "type_name", "capacity", "price", "status"]].rename(columns={
                "room_id":     "System ID",
                "room_number": "Room Number",
                "type_name":   "Category",
                "capacity":    "Capacity",
                "price":       "Rate/Night",
                "status":      "Current Status",
            }),
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.info("No matching rooms found.")

# Page
elif st.session_state.page == "Settings":
    st.markdown("## Settings")

    tab_rooms, tab_types, tab_res, tab_guests, tab_archive = st.tabs(["Manage Rooms", "Manage Room Types", "Manage Reservations", "Manage Guests", "Archive & Storage"])

    with tab_rooms:
        st.markdown("### Physical Room Inventory Updates")
        c_add, c_edit, c_del = st.columns(3)

        with c_add:
            with st.expander("Add New Room", expanded=False):
                with st.form("add_room_form"):
                    new_rm_num  = st.text_input("Room Number (Unique)", placeholder="e.g., 105", max_chars=20)
                    rt_choices  = run_q("SELECT room_type_id, type_name FROM room_types")
                    rt_map      = {r["type_name"]: r["room_type_id"] for r in rt_choices} if rt_choices else {}
                    new_rm_type = st.selectbox("Assign Category", list(rt_map.keys()) if rt_map else ["- Setup Types First -"])
                    new_rm_stat = st.selectbox("Initial Status", ["available", "occupied", "maintenance"])

                    if st.form_submit_button("Create Room"):
                        if not new_rm_num.strip() or not rt_map:
                            st.error("Room number and a valid category are required.")
                        else:
                            try:
                                run_write(
                                    "INSERT INTO rooms (room_number, room_type_id, status) VALUES (%s, %s, %s)",
                                    (new_rm_num.strip(), rt_map[new_rm_type], new_rm_stat),
                                )
                                st.success(f"Room {html.escape(new_rm_num.strip())} added.")
                                st.rerun()
                            except RuntimeError as e:
                                st.error(str(e))

        with c_edit:
            with st.expander("Edit Room", expanded=False):
                all_rooms_list = run_q("SELECT room_id, room_number, room_type_id, status FROM rooms ORDER BY room_number")
                if all_rooms_list:
                    rm_edit_map  = {f"Room {r['room_number']}": r for r in all_rooms_list}
                    sel_edit_rm  = st.selectbox("Select Room", list(rm_edit_map.keys()))
                    tgt_edit_rm  = rm_edit_map[sel_edit_rm]

                    with st.form("edit_room_form"):
                        chg_rm_num  = st.text_input("Room Number", value=str(tgt_edit_rm["room_number"]), max_chars=20)
                        rt_choices2 = run_q("SELECT room_type_id, type_name FROM room_types")
                        rt_map2     = {r["type_name"]: r["room_type_id"] for r in rt_choices2} if rt_choices2 else {}
                        current_type_name = next((k for k, v in rt_map2.items() if v == tgt_edit_rm["room_type_id"]), None)
                        chg_rm_type = st.selectbox(
                            "Category",
                            list(rt_map2.keys()),
                            index=list(rt_map2.keys()).index(current_type_name) if current_type_name else 0,
                        )
                        status_list = ["available", "occupied", "maintenance"]
                        chg_rm_stat = st.selectbox(
                            "Status", status_list,
                            index=status_list.index(tgt_edit_rm["status"]),
                        )

                        if st.form_submit_button("Save Changes"):
                            try:
                                rowcount = run_write("""
                                    UPDATE rooms SET room_number=%s, room_type_id=%s, status=%s
                                    WHERE room_id=%s
                                    AND NOT EXISTS (
                                        SELECT 1 FROM reservations
                                        WHERE room_id=%s AND reservation_status IN ('pending','active')
                                    )
                                """, (chg_rm_num.strip(), rt_map2[chg_rm_type], chg_rm_stat,
                                      tgt_edit_rm["room_id"], tgt_edit_rm["room_id"]))
                                if rowcount == 0:
                                    st.error("Cannot modify: room has an active reservation, or it no longer exists.")
                                else:
                                    st.success("Room updated.")
                                    st.rerun()
                            except RuntimeError as e:
                                st.error(str(e))
                else:
                    st.info("No rooms to edit.")

        with c_del:
            with st.expander("Delete Room", expanded=False):
                all_rooms_list2 = run_q("SELECT room_id, room_number FROM rooms ORDER BY room_number")
                if all_rooms_list2:
                    rm_del_map = {f"Room {r['room_number']}": r["room_id"] for r in all_rooms_list2}
                    sel_del_rm = st.selectbox("Select Room to Remove", list(rm_del_map.keys()))

                    st.warning("Ensure this room has no active reservations before deleting.")
                    if st.button("Permanently Delete Room", use_container_width=True):
                        any_hist = run_q(
                            "SELECT 1 FROM reservations WHERE room_id = %s LIMIT 1",
                            (rm_del_map[sel_del_rm],), fetch="one",
                        )
                        if any_hist:
                            st.error("Cannot delete: reservation history exists. Set the room to Maintenance status instead.")
                        else:
                            try:
                                run_write("DELETE FROM rooms WHERE room_id = %s", (rm_del_map[sel_del_rm],))
                                st.success("Room removed from inventory.")
                                st.rerun()
                            except RuntimeError as e:
                                st.error(str(e))
                else:
                    st.info("No rooms found.")

    with tab_res:
        st.markdown("### Reservation Management")
        c_radd, c_redit, c_rdel = st.columns(3)

        today_dt = now_npl().date()

        def _overlaps(room_id, checkin, checkout, exclude_res_id=None):
            sql = """
                SELECT 1 FROM reservations
                WHERE room_id = %s
                  AND reservation_status IN ('pending', 'active')
                  AND check_in_date < %s
                  AND check_out_date > %s
            """
            params = [room_id, checkout, checkin]
            if exclude_res_id:
                sql += " AND reservation_id != %s"
                params.append(exclude_res_id)
            rows = run_q(sql, tuple(params))
            return bool(rows)

        with c_radd:
            with st.expander("Add New Reservation", expanded=False):
                with st.form("add_reservation_form"):
                    guest_opts = {g["full_name"]: g["guest_id"] for g in run_q("SELECT guest_id, full_name FROM guests ORDER BY full_name")}
                    room_opts = {r["room_number"]: r["room_id"] for r in run_q("SELECT room_id, room_number FROM rooms ORDER BY room_number")}
                    if not guest_opts or not room_opts:
                        st.info("Guests and rooms must exist before creating a reservation.")
                    else:
                        new_res_guest = st.selectbox("Guest", list(guest_opts.keys()))
                        new_res_room = st.selectbox("Room", list(room_opts.keys()))
                        ci, co = st.columns(2)
                        with ci:
                            new_ci = st.date_input("Check-In", value=today_dt)
                        with co:
                            new_co_min = new_ci + timedelta(days=1)
                            new_co = st.date_input("Check-Out", value=new_co_min, min_value=new_co_min)
                        new_status = st.selectbox("Status", ["pending", "active", "cancelled"])

                        if st.form_submit_button("Create Reservation"):
                            if _overlaps(room_opts[new_res_room], new_ci, new_co):
                                st.error("Selected room is already booked for the chosen dates.")
                            else:
                                try:
                                    run_write(
                                        """
                                        INSERT INTO reservations
                                            (guest_id, guest_name, room_id, check_in_date, check_out_date, checkout_time, reservation_status, created_at, updated_at)
                                        VALUES (%s, %s, %s, %s, %s, %s, %s, NOW(), NOW())
                                        """,
                                        (
                                            guest_opts[new_res_guest],
                                            new_res_guest,
                                            room_opts[new_res_room],
                                            new_ci,
                                            new_co,
                                            _CHECKOUT_TIME,
                                            new_status,
                                        ),
                                    )
                                    if new_status == 'active':
                                        run_write(
                                            "UPDATE rooms SET status = 'occupied' WHERE room_id = %s",
                                            (room_opts[new_res_room],),
                                        )
                                    st.success(f"Reservation created for {new_res_guest} in Room {new_res_room}.")
                                    st.rerun()
                                except RuntimeError as e:
                                    st.error(str(e))

        with c_redit:
            with st.expander("Edit Reservation", expanded=False):
                all_res = run_q("""
                    SELECT res.reservation_id, COALESCE(res.guest_name, g.full_name) AS guest_name, r.room_number,
                           res.check_in_date, res.check_out_date, res.reservation_status,
                           res.room_id
                    FROM reservations res
                    JOIN guests g ON g.guest_id = res.guest_id
                    JOIN rooms r ON r.room_id = res.room_id
                    ORDER BY res.reservation_id DESC
                """)
                if all_res:
                    res_edit_map = {
                        f"#{r['reservation_id']} - Room {r['room_number']} | {r['guest_name']} "
                        f"({r['check_in_date']} -> {r['check_out_date']}) [{r['reservation_status']}]": r
                        for r in all_res
                    }
                    sel_edit_res = st.selectbox("Select Reservation", list(res_edit_map.keys()), key="edit_res_select")
                    tgt_edit_res = res_edit_map[sel_edit_res]

                    rm_opts = {r["room_number"]: r["room_id"] for r in run_q("SELECT room_id, room_number FROM rooms ORDER BY room_number")}
                    g_opts = {g["full_name"]: g["guest_id"] for g in run_q("SELECT guest_id, full_name FROM guests ORDER BY full_name")}
                    status_opts = ["pending", "active", "completed", "cancelled"]

                    with st.form("edit_reservation_form"):
                        edit_guest_name = st.selectbox(
                            "Guest",
                            list(g_opts.keys()),
                            index=list(g_opts.keys()).index(tgt_edit_res["guest_name"]) if tgt_edit_res["guest_name"] in g_opts else 0
                        )
                        edit_room_num = st.selectbox("Room", list(rm_opts.keys()), index=list(rm_opts.keys()).index(tgt_edit_res["room_number"]) if tgt_edit_res["room_number"] in rm_opts else 0)
                        edit_status = st.selectbox("Status", status_opts, index=status_opts.index(tgt_edit_res["reservation_status"]) if tgt_edit_res["reservation_status"] in status_opts else 0)
                        eci, eco = st.columns(2)
                        with eci:
                            edit_ci = st.date_input("Check-In", value=tgt_edit_res["check_in_date"])
                        with eco:
                            edit_co_min = edit_ci + timedelta(days=1)
                            edit_co = st.date_input("Check-Out", value=tgt_edit_res["check_out_date"], min_value=edit_co_min)

                        if st.form_submit_button("Save Changes"):
                            if _overlaps(rm_opts[edit_room_num], edit_ci, edit_co, exclude_res_id=tgt_edit_res["reservation_id"]):
                                st.error("Selected room overlaps an existing reservation for the chosen dates.")
                            else:
                                try:
                                    def _update(cur):
                                        cur.execute(
                                            """
                                            UPDATE reservations
                                            SET guest_id=%s, guest_name=%s, room_id=%s, check_in_date=%s, check_out_date=%s, reservation_status=%s
                                            WHERE reservation_id=%s
                                            """,
                                            (
                                                g_opts[edit_guest_name],
                                                edit_guest_name,
                                                rm_opts[edit_room_num],
                                                edit_ci,
                                                edit_co,
                                                edit_status,
                                                tgt_edit_res["reservation_id"],
                                            ),
                                        )
                                        cur.execute(
                                            "UPDATE rooms SET status = 'occupied' WHERE room_id = %s",
                                            (rm_opts[edit_room_num],),
                                        )
                                    run_transaction(_update)
                                    st.success("Reservation updated.")
                                    st.rerun()
                                except RuntimeError as e:
                                    st.error(str(e))
                else:
                    st.info("No reservations to edit.")

        with c_rdel:
            with st.expander("Delete Reservation", expanded=False):
                all_res_list2 = run_q("""
                    SELECT res.reservation_id, COALESCE(res.guest_name, g.full_name) AS guest_name, r.room_number,
                           res.check_in_date, res.check_out_date, res.reservation_status,
                           res.room_id
                    FROM reservations res
                    JOIN guests g ON g.guest_id = res.guest_id
                    JOIN rooms r ON r.room_id = res.room_id
                    ORDER BY res.reservation_id DESC
                """)
                if all_res_list2:
                    res_del_map = {
                        f"#{r['reservation_id']} - Room {r['room_number']} | {r['guest_name']} "
                        f"({r['check_in_date']} -> {r['check_out_date']}) [{r['reservation_status']}]": r
                        for r in all_res_list2
                    }
                    sel_del_res = st.selectbox("Select Reservation to Remove", list(res_del_map.keys()), key="del_res_select")
                    tgt_del_res = res_del_map[sel_del_res]

                    st.warning("This will permanently delete the selected reservation.")
                    if st.button("Permanently Delete Reservation", use_container_width=True, key="mg_del_res_btn"):
                        if st.session_state.get("mg_del_res_confirm_id") == tgt_del_res["reservation_id"]:
                            def do_mg_delete_res(cur):
                                cur.execute("DELETE FROM reservations WHERE reservation_id = %s", (tgt_del_res["reservation_id"],))
                                free_room_if_empty(cur, tgt_del_res["room_id"])

                            try:
                                run_transaction(do_mg_delete_res)
                                st.session_state.pop("mg_del_res_confirm_id", None)
                                st.toast(f"Reservation #{tgt_del_res['reservation_id']} permanently deleted.")
                                st.rerun()
                            except RuntimeError as e:
                                st.error(str(e))
                                st.session_state.pop("mg_del_res_confirm_id", None)
                            except Exception:
                                st.error("Deletion failed due to an unexpected error. Please try again.")
                                st.session_state.pop("mg_del_res_confirm_id", None)
                        else:
                            st.session_state["mg_del_res_confirm_id"] = tgt_del_res["reservation_id"]
                            st.warning(
                                "Are you sure you want to permanently delete reservation "
                                f"**#{tgt_del_res['reservation_id']}** for **{html.escape(tgt_del_res['guest_name'])}** "
                                f"in Room **{tgt_del_res['room_number']}**? "
                                "This cannot be undone. Click **Permanently Delete Reservation** again to confirm."
                            )
                else:
                    st.info("No reservations found.")

    with tab_types:
        st.markdown("### Room Category & Pricing")
        c_tadd, c_tedit, c_tdel = st.columns(3)

        with c_tadd:
            with st.expander("Add New Room Type", expanded=False):
                with st.form("add_type_form"):
                    nt_name = st.text_input("Category Name", placeholder="e.g., Deluxe Forest Suite", max_chars=100)
                    nt_cap  = st.number_input("Max Capacity (Guests)", min_value=1, value=2)
                    nt_prc  = st.number_input("Base Rate per Night (NPR)", min_value=0.0, value=5000.0, step=500.0)

                    if st.form_submit_button("Add Category"):
                        if not nt_name.strip():
                            st.error("Category name is required.")
                        else:
                            try:
                                run_write(
                                    "INSERT INTO room_types (type_name, capacity, price) VALUES (%s, %s, %s)",
                                    (nt_name.strip(), int(nt_cap), float(nt_prc)),
                                )
                                st.success(f"Category '{html.escape(nt_name.strip())}' added.")
                                st.rerun()
                            except RuntimeError as e:
                                st.error(str(e))

        with c_tedit:
            with st.expander("Edit Category", expanded=False):
                all_types_list = run_q("SELECT room_type_id, type_name, capacity, price FROM room_types ORDER BY type_name")
                if all_types_list:
                    type_edit_map  = {t["type_name"]: t for t in all_types_list}
                    sel_edit_type  = st.selectbox("Select Category", list(type_edit_map.keys()))
                    tgt_edit_type  = type_edit_map[sel_edit_type]

                    with st.form("edit_type_form"):
                        chg_t_name = st.text_input("Name",     value=tgt_edit_type["type_name"], max_chars=100)
                        chg_t_cap  = st.number_input("Max Capacity", min_value=1, value=int(tgt_edit_type["capacity"]))
                        chg_t_prc  = st.number_input("Rate per Night", min_value=0.0, value=float(tgt_edit_type["price"]), step=500.0)

                        if st.form_submit_button("Save Changes"):
                            try:
                                run_write(
                                    "UPDATE room_types SET type_name=%s, capacity=%s, price=%s WHERE room_type_id=%s",
                                    (chg_t_name.strip(), int(chg_t_cap), float(chg_t_prc), tgt_edit_type["room_type_id"]),
                                )
                                st.success("Category updated.")
                                st.rerun()
                            except RuntimeError as e:
                                st.error(str(e))
                else:
                    st.info("No categories exist yet.")

        with c_tdel:
            with st.expander("Delete Category", expanded=False):
                all_types_list2 = run_q("SELECT room_type_id, type_name FROM room_types ORDER BY type_name")
                if all_types_list2:
                    type_del_map  = {t["type_name"]: t["room_type_id"] for t in all_types_list2}
                    sel_del_type  = st.selectbox("Select Category to Delete", list(type_del_map.keys()))

                    st.warning("All rooms assigned to this category must be reassigned or deleted first.")
                    if st.button("Delete Category", use_container_width=True):
                        in_use = run_q(
                            "SELECT 1 FROM rooms WHERE room_type_id = %s LIMIT 1",
                            (type_del_map[sel_del_type],), fetch="one",
                        )
                        if in_use:
                            st.error("Cannot delete: rooms are assigned to this category. Reassign or delete them first.")
                        else:
                            try:
                                run_write(
                                    "DELETE FROM room_types WHERE room_type_id = %s",
                                    (type_del_map[sel_del_type],),
                                )
                                st.success("Category deleted.")
                                st.rerun()
                            except RuntimeError as e:
                                st.error(str(e))
                else:
                    st.info("No categories found.")

    with tab_guests:
        st.markdown("### Guest Profile Management")
        c_gadd, c_gedit, c_gdel = st.columns(3)

        with c_gadd:
            with st.expander("Add New Guest", expanded=False):
                with st.form("add_guest_form"):
                    new_name = st.text_input("Full Name", placeholder="Guest full name", max_chars=100)
                    new_email = st.text_input("Email", placeholder="email@example.com", max_chars=120)
                    new_phone = st.text_input("Phone", placeholder="+977-98xxxxxxx", max_chars=20)

                    if st.form_submit_button("Create Guest"):
                        if not new_name.strip():
                            st.error("Guest name is required.")
                        else:
                            try:
                                run_write(
                                    "INSERT INTO guests (full_name, email, phone) VALUES (%s, %s, %s)",
                                    (new_name.strip(), new_email.strip() or None, new_phone.strip() or None),
                                )
                                st.success(f"Guest '{html.escape(new_name.strip())}' added.")
                                st.rerun()
                            except RuntimeError as e:
                                st.error(str(e))

        with c_gedit:
            with st.expander("Edit Guest", expanded=False):
                all_guests_list = run_q("SELECT guest_id, full_name, email, phone FROM guests ORDER BY full_name")
                if all_guests_list:
                    guest_edit_map = {g["full_name"]: g for g in all_guests_list}
                    sel_edit_guest = st.selectbox("Select Guest", list(guest_edit_map.keys()))
                    tgt_edit_guest = guest_edit_map[sel_edit_guest]

                    with st.form("edit_guest_form"):
                        chg_name = st.text_input("Full Name", value=tgt_edit_guest["full_name"], max_chars=100)
                        chg_email = st.text_input("Email", value=tgt_edit_guest.get("email") or "", max_chars=120)
                        chg_phone = st.text_input("Phone", value=tgt_edit_guest.get("phone") or "", max_chars=20)

                        if st.form_submit_button("Save Changes"):
                            try:
                                run_write(
                                    "UPDATE guests SET full_name=%s, email=%s, phone=%s WHERE guest_id=%s",
                                    (chg_name.strip(), chg_email.strip() or None, chg_phone.strip() or None, tgt_edit_guest["guest_id"]),
                                )
                                st.success("Guest profile updated.")
                                st.rerun()
                            except RuntimeError as e:
                                st.error(str(e))
                else:
                    st.info("No guests to edit.")

        with c_gdel:
            with st.expander("Delete Guest", expanded=False):
                all_guests_list2 = run_q(
                    """
                    SELECT g.guest_id, g.full_name,
                           GROUP_CONCAT(r.room_number ORDER BY res.check_in_date SEPARATOR ', ') AS room_numbers
                    FROM guests g
                    LEFT JOIN reservations res ON res.guest_id = g.guest_id AND res.reservation_status IN ('pending','active')
                    LEFT JOIN rooms r ON r.room_id = res.room_id
                    GROUP BY g.guest_id, g.full_name
                    ORDER BY g.full_name
                    """
                )
                if all_guests_list2:
                    guest_del_map = {f"{g['full_name']} - {html.escape(str(g.get('room_numbers') or ''))}": g["guest_id"] for g in all_guests_list2}
                    sel_del_guest = st.selectbox("Select Guest to Remove", list(guest_del_map.keys()))

                    st.warning("This will also end any active/pending reservations for this guest.")
                    if st.button("Permanently Delete Guest", use_container_width=True):
                        if st.session_state.get("mg_del_guest_confirm_id") == guest_del_map[sel_del_guest]:
                            def do_mg_delete_guest(cur):
                                cur.execute(
                                    "SELECT reservation_id, room_id FROM reservations "
                                    "WHERE guest_id = %s AND reservation_status IN ('pending','active')",
                                    (guest_del_map[sel_del_guest],),
                                )
                                related = cur.fetchall()
                                for rel in related:
                                    cur.execute("DELETE FROM reservations WHERE reservation_id = %s", (rel["reservation_id"],))
                                    free_room_if_empty(cur, rel["room_id"])
                                cur.execute("DELETE FROM guests WHERE guest_id = %s", (guest_del_map[sel_del_guest],))

                            try:
                                run_transaction(do_mg_delete_guest)
                                st.session_state.pop("mg_del_guest_confirm_id", None)
                                st.toast("Guest profile permanently deleted.")
                                st.rerun()
                            except RuntimeError as e:
                                st.error(str(e))
                                st.session_state.pop("mg_del_guest_confirm_id", None)
                            except Exception:
                                st.error("Guest deletion failed due to an unexpected error. Please try again.")
                                st.session_state.pop("mg_del_guest_confirm_id", None)
                        else:
                            st.session_state["mg_del_guest_confirm_id"] = guest_del_map[sel_del_guest]
                            st.warning(
                                "Are you sure you want to permanently delete this guest profile? "
                                "This cannot be undone. Click **Permanently Delete Guest** again to confirm."
                            )
                else:
                    st.info("No guests found.")

    with tab_archive:
        st.markdown("### Archive & Storage Management")
        st.caption("Archived reservations are stored as compressed JSON to save disk space while keeping full history accessible.")

        stats_row = run_q("""
            SELECT
                (SELECT COUNT(*) FROM reservations)                         AS live_reservations,
                (SELECT COUNT(*) FROM guests)                               AS total_guests,
                (SELECT COUNT(*) FROM reservations
                 WHERE reservation_status IN ('completed','cancelled'))    AS closed_reservations,
                (SELECT COUNT(*) FROM reservation_archives)                 AS archived_reservations,
                (SELECT COALESCE(SUM(CHAR_LENGTH(reservation_data)), 0)
                 FROM reservation_archives)                                AS archive_bytes
        """, fetch="one")

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Live Reservations", stats_row.get("live_reservations", 0) if stats_row else 0)
        m2.metric("Closed Reservations", stats_row.get("closed_reservations", 0) if stats_row else 0)
        m3.metric("Archived Records", stats_row.get("archived_reservations", 0) if stats_row else 0)
        mb = stats_row.get("archive_bytes", 0) if stats_row else 0
        m4.metric("Archive Size", f"{mb/1024/1024:.1f} MB" if mb > 1024*1024 else f"{mb/1024:.1f} KB")

        st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)
        st.markdown("#### Automatic Archiving")
        arc_col1, arc_col2 = st.columns([2, 1])
        with arc_col1:
            archive_days = st.number_input(
                "Archive reservations older than (days)",
                min_value=30, max_value=3650, value=90, step=30,
                help="Completed/cancelled reservations with check-out older than this will be moved to archive."
            )
        with arc_col2:
            st.markdown("<div style='height:26px'></div>", unsafe_allow_html=True)
            if st.button("Run Archive Now", use_container_width=True, type="primary"):
                with st.spinner("Archiving old reservations..."):
                    try:
                        def _run_archive(cur):
                            from datetime import timedelta
                            import json as _json
                            cutoff = date.today() - timedelta(days=int(archive_days))
                            cur.execute("""
                                SELECT r.reservation_id, r.room_id, r.guest_id, r.guest_name,
                                       r.check_in_date, r.check_out_date, r.checkout_time,
                                       r.reservation_status, r.created_at, r.updated_at,
                                       g.full_name AS guest_full_name, g.email AS guest_email, g.phone AS guest_phone, g.created_at AS guest_created,
                                       rm.room_number, rt.type_name AS room_type, rt.price AS room_price, rt.capacity AS room_capacity
                                FROM reservations r
                                JOIN guests g ON g.guest_id = r.guest_id
                                JOIN rooms rm ON rm.room_id = r.room_id
                                JOIN room_types rt ON rt.room_type_id = rm.room_type_id
                                WHERE r.reservation_status IN ('completed','cancelled')
                                  AND r.check_out_date < %s
                                ORDER BY r.check_out_date ASC
                                LIMIT 5000
                            """, (cutoff,))
                            rows = cur.fetchall()
                            archived = 0
                            for row in rows:
                                cur.execute("""
                                    INSERT INTO reservation_archives (reservation_data, guest_snapshot, room_snapshot, archive_reason)
                                    VALUES (%s, %s, %s, %s)
                                """, (
                                    _json.dumps({
                                        "reservation_id": row["reservation_id"],
                                        "room_id": row["room_id"],
                                        "guest_id": row["guest_id"],
                                        "guest_name": row["guest_name"],
                                        "check_in_date": str(row["check_in_date"]),
                                        "check_out_date": str(row["check_out_date"]),
                                        "checkout_time": str(row["checkout_time"]) if row["checkout_time"] else None,
                                        "reservation_status": row["reservation_status"],
                                        "created_at": str(row["created_at"]),
                                        "updated_at": str(row["updated_at"]),
                                    }, ensure_ascii=False),
                                    _json.dumps({
                                        "guest_id": row["guest_id"],
                                        "full_name": row["guest_full_name"],
                                        "email": row["guest_email"],
                                        "phone": row["guest_phone"],
                                        "created_at": str(row["guest_created"]),
                                    }, ensure_ascii=False),
                                    _json.dumps({
                                        "room_id": row["room_id"],
                                        "room_number": row["room_number"],
                                        "room_type": row["room_type"],
                                        "room_price": float(row["room_price"]) if row["room_price"] else 0.0,
                                        "room_capacity": row["room_capacity"],
                                    }, ensure_ascii=False),
                                    "completed_aged" if row["reservation_status"] == "completed" else "cancelled_aged",
                                ))
                                cur.execute("DELETE FROM reservations WHERE reservation_id = %s", (row["reservation_id"],))
                                archived += 1
                            return archived
                        count = run_transaction(_run_archive)
                        st.toast(f"Archived {count} old reservations.", icon="✅")
                        st.rerun()
                    except RuntimeError as e:
                        st.error(str(e))
                    except Exception as e:
                        st.error(f"Archive failed: {e}")

        st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)
        st.markdown("#### Recent Archive Log")
        recent_archives = run_q("""
            SELECT archive_id, reservation_data, guest_snapshot, room_snapshot, archived_at, archive_reason
            FROM reservation_archives
            ORDER BY archived_at DESC
            LIMIT 20
        """)
        if recent_archives:
            df_arc = pd.DataFrame(recent_archives)
            df_arc["reservation_id"] = df_arc["reservation_data"].apply(lambda x: x.get("reservation_id", "") if isinstance(x, dict) else "")
            df_arc["guest_name"] = df_arc["guest_snapshot"].apply(lambda x: x.get("full_name", "") if isinstance(x, dict) else "")
            df_arc["room_number"] = df_arc["room_snapshot"].apply(lambda x: x.get("room_number", "") if isinstance(x, dict) else "")
            df_arc["archived_at"] = df_arc["archived_at"].apply(lambda x: str(x) if x else "")
            st.dataframe(
                df_arc[["archive_id", "reservation_id", "guest_name", "room_number", "archived_at", "archive_reason"]].rename(columns={
                    "archive_id": "ID", "reservation_id": "Res ID", "guest_name": "Guest",
                    "room_number": "Room", "archived_at": "Archived At", "archive_reason": "Reason"
                }),
                use_container_width=True, hide_index=True
            )
        else:
            st.info("No archived records yet.")

    st.markdown("---")