"""
Natura Resort — Admin Dashboard (Streamlit)

Run:
    streamlit run dashboard.py
"""

import hmac
import html
import os
from datetime import datetime, timedelta

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
    page_icon="🏨",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Styles
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Fraunces:wght@300;400;600&family=Inter:wght@300;400;500&display=swap');

:root {
  --bg:      #12261E;
  --surface: #1B382B;
  --border:  #295240;
  --accent:  #40916C;
  --accent2: #52B788;
  --soft:    #D8F3DC;
  --danger:  #E07A5F;
  --warn:    #F4A261;
  --text:    #F8F9FA;
  --muted:   #ADB5BD;
  --radius:  10px;
}

html, body, [class*="css"] {
  font-family: 'Inter', sans-serif !important;
  background-color: var(--bg) !important;
  color: var(--text) !important;
  font-size: 14px;
}

h1, h2, h3 {
  font-family: 'Fraunces', serif !important;
  color: #FFFFFF !important;
  font-weight: 400 !important;
}

p, li, span:not(.pill), label { color: var(--text) !important; }

# MainMenu, footer
header { background: transparent !important; }
.block-container { padding-top: 1.2rem !important; padding-bottom: 2rem !important; }

.stTabs [data-baseweb="tab-list"] { background: transparent !important; border-bottom: 1px solid var(--border) !important; }
.stTabs [data-baseweb="tab"] { color: var(--muted) !important; }
.stTabs [aria-selected="true"] { color: var(--text) !important; border-bottom: 2px solid var(--text) !important; }
div[data-baseweb="tab-highlight"] { display: none !important; }

div[data-testid="metric-container"] {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 1rem 1.1rem 0.9rem;
}

.stButton > button {
  background: var(--accent) !important;
  color: #fff !important;
  border: none !important;
  border-radius: 7px !important;
  font-size: 0.83rem !important;
  font-weight: 500 !important;
  padding: 0.4rem 1rem !important;
}
.stButton > button:hover { background: var(--accent2) !important; }

.stTextInput input, .stSelectbox div[data-baseweb="select"] > div,
.stDateInput input, .stNumberInput input, .stTextArea textarea,
div[role="radiogroup"] label {
  color: var(--text) !important;
}
.stTextInput input, .stSelectbox div[data-baseweb="select"] > div,
.stDateInput input, .stNumberInput input, .stTextArea textarea {
  background: var(--bg) !important;
  border: 1px solid var(--border) !important;
  border-radius: 7px !important;
}

.room-card {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 12px 14px;
  margin-bottom: 8px;
}

div[data-testid="stSidebar"] [data-testid="stForm"] {
    border: 1px solid var(--border) !important;
}
</style>
""", unsafe_allow_html=True)

# Constants
_NPL = pytz.timezone("Asia/Kathmandu")
_WALKIN_EMAIL = "walkin@natura-internal.local"   # sentinel; not a real address
_SEARCH_MAX_LEN = 100
_CHECKOUT_TIME = "12:00:00"


def now_npl() -> datetime:
    return datetime.now(_NPL)


# Auth
_DASH_PWD = _read_secret("dashboard_password", "DASHBOARD_PASSWORD")

if not _DASH_PWD:
    st.error("DASHBOARD_PASSWORD is not configured. Contact your system administrator.")
    st.stop()

with st.sidebar:
    st.markdown("### 🔐 Authentication")
    pwd = st.text_input("Admin Password", type="password")
    if not hmac.compare_digest(_DASH_PWD.encode(), pwd.encode()):
        st.warning("Please enter the correct admin password to access the dashboard.")
        st.stop()
    st.markdown("---")

# DB
@st.cache_resource
def get_pool():
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
        c.rollback()
        raise
    finally:
        cur.close()
        c.close()


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
        "<span style='font-family:Fraunces,serif;font-size:1.4rem;color:#D8F3DC;font-weight:600'>Natura Resort</span>",
        unsafe_allow_html=True,
    )
with col_time:
    st.markdown(
        f"<div style='text-align:right;font-size:0.8rem;color:#ADB5BD;padding-top:6px'>"
        f"{now_npl().strftime('%A, %d %B %Y  ·  %H:%M NST')}</div>",
        unsafe_allow_html=True,
    )

st.markdown("<div style='height:4px; margin-bottom: 20px;'></div>", unsafe_allow_html=True)

# Sidebar
with st.sidebar:
    st.markdown("### 🧭 Navigation")

    if st.button("📊 Dashboard", use_container_width=True):
        st.session_state.page = "Overview"; st.rerun()
    if st.button("📋 Reservations", use_container_width=True):
        st.session_state.page = "Reservations Table"; st.rerun()
    if st.button("👤 Guest Info", use_container_width=True):
        st.session_state.page = "Guest Info Table"; st.rerun()
    if st.button("🛏️ Rooms", use_container_width=True):
        st.session_state.page = "Rooms Table"; st.rerun()
    if st.button("⚙️ Settings", use_container_width=True):
        st.session_state.page = "Settings ⚙"; st.rerun()

    st.markdown("---")
    st.markdown("### ⚡ Fast Reservation")
    st.markdown(
        "<small style='color:#ADB5BD'>Instantly process an offline walk-in booking.</small>",
        unsafe_allow_html=True,
    )

    sb_today = now_npl().date()
    sb_ci = st.date_input("Check-In Date",  value=sb_today,                    min_value=sb_today,                    key="sb_fres_ci")
    sb_co = st.date_input("Check-Out Date", value=sb_today + timedelta(days=1), min_value=sb_today + timedelta(days=1), key="sb_fres_co")

    if sb_co <= sb_ci:
        st.error("Check-out must happen after check-in.")
    else:
        sb_rooms = run_q("""
            SELECT r.room_id, r.room_number, rt.type_name, r.status
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
        """, (sb_co, sb_ci))

        if sb_rooms:
            sb_room_map = {f"Room {rm['room_number']} — {rm['type_name']}": rm for rm in sb_rooms}
            sel_sb_room = st.selectbox("Select Available Room", list(sb_room_map.keys()), key="sb_fres_rm")
            target_room = sb_room_map[sel_sb_room]

            walkin_name  = st.text_input("Guest Name",  placeholder="Full name", key="sb_walkin_name")
            walkin_phone = st.text_input("Guest Phone", placeholder="+977 ...",  key="sb_walkin_phone")

            if st.button("⚡ Book Offline Reservation", use_container_width=True):
                walkin_name  = walkin_name.strip()
                walkin_phone = walkin_phone.strip()
                if not walkin_name or not walkin_phone:
                    st.error("Please provide guest name and phone number.")
                else:
                    res_status = "active" if sb_ci == sb_today else "pending"

                    def execute_walkin_booking(cur):
                        # Lock the
                        cur.execute(
                            "SELECT status FROM rooms WHERE room_id = %s FOR UPDATE",
                            (target_room["room_id"],),
                        )
                        rm_check = cur.fetchone()
                        if not rm_check or rm_check["status"] == "maintenance":
                            raise RuntimeError("Selected room was placed in maintenance during your selection. Please choose another.")

                        # Check for
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

                        # Upsert walk-in
                        # Name and
                        cur.execute("""
                            INSERT INTO guests (full_name, email, phone)
                            VALUES (%s, %s, %s)
                            ON DUPLICATE KEY UPDATE
                                guest_id  = LAST_INSERT_ID(guest_id),
                                full_name = VALUES(full_name),
                                phone     = VALUES(phone)
                        """, (walkin_name, _WALKIN_EMAIL, walkin_phone))
                        gid = cur.lastrowid

                        cur.execute("""
                            INSERT INTO reservations
                                (room_id, guest_id, check_in_date, check_out_date, checkout_time, reservation_status)
                            VALUES (%s, %s, %s, %s, %s, %s)
                        """, (target_room["room_id"], gid, sb_ci, sb_co, _CHECKOUT_TIME, res_status))

                        if res_status == "active":
                            cur.execute(
                                "UPDATE rooms SET status = 'occupied' WHERE room_id = %s",
                                (target_room["room_id"],),
                            )

                    try:
                        run_transaction(execute_walkin_booking)
                        st.toast(f"Room {target_room['room_number']} booked successfully!", icon="🟢")
                        st.rerun()
                    except RuntimeError as e:
                        st.error(str(e))
                    except Exception:
                        st.error("Booking failed due to an unexpected error. Please try again.")
        else:
            st.warning("No rooms available for these dates.")

# Page
if st.session_state.page == "Overview":
    st.markdown("## 📊 Overview")

    rooms_all = run_q("SELECT status FROM rooms")
    avail = sum(1 for r in rooms_all if r["status"] == "available")
    occ   = sum(1 for r in rooms_all if r["status"] == "occupied")
    maint = sum(1 for r in rooms_all if r["status"] == "maintenance")

    today = now_npl().date()
    checkins_today = (run_q(
        "SELECT COUNT(*) AS n FROM reservations WHERE check_in_date = %s AND reservation_status = 'pending'",
        (today,), "one",
    ) or {}).get("n", 0)

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Rooms Occupied",        f"{occ} Rooms")
    c2.metric("Rooms Available",       f"{avail} Vacant")
    c3.metric("Under Maintenance",     f"{maint} Locked")
    c4.metric("Arrivals Expected Today", f"{checkins_today} Check-ins")

    st.markdown("<div style='height:20px'></div>", unsafe_allow_html=True)
    left, right = st.columns([1.6, 1])

    with left:
        st.markdown(
            "<p style='font-size:0.78rem;letter-spacing:0.07em;text-transform:uppercase;"
            "color:#ADB5BD;margin-bottom:8px'>Live Property Room Grid</p>",
            unsafe_allow_html=True,
        )
        room_grid = run_q("""
            SELECT r.room_number, rt.type_name, r.status,
                   g.full_name AS guest_name,
                   res.check_in_date, res.check_out_date
            FROM rooms r
            JOIN room_types rt ON r.room_type_id = rt.room_type_id
            LEFT JOIN reservations res
                   ON res.room_id = r.room_id AND res.reservation_status = 'active'
            LEFT JOIN guests g ON g.guest_id = res.guest_id
            ORDER BY r.room_number
        """)
        cols = st.columns(4)
        STATUS_DOT = {"available": "#52B788", "occupied": "#E07A5F", "maintenance": "#F4A261"}
        for i, rm in enumerate(room_grid):
            dot = STATUS_DOT.get(rm["status"], "#aaa")
            if rm["guest_name"]:
                guest_clean = html.escape(rm["guest_name"])
                guest_html = (
                    f"<div style='font-size:0.77rem;color:#F8F9FA;margin-top:3px'>{guest_clean}</div>"
                    f"<div style='font-size:0.7rem;color:#ADB5BD'>"
                    f"{rm['check_in_date']} → {rm['check_out_date']}</div>"
                )
            else:
                guest_html = "<div style='font-size:0.75rem;color:#ADB5BD;margin-top:3px'>✨ Vacant / Ready</div>"

            with cols[i % 4]:
                st.markdown(f"""
                <div class='room-card'>
                  <div style='display:flex;justify-content:space-between;align-items:center'>
                    <span style='font-weight:500;font-size:0.88rem'>Room {rm['room_number']}</span>
                    <span style='width:8px;height:8px;background:{dot};border-radius:50%;display:inline-block'></span>
                  </div>
                  <div style='font-size:0.72rem;color:#ADB5BD;margin-top:1px'>{html.escape(rm['type_name'])}</div>
                  {guest_html}
                </div>
                """, unsafe_allow_html=True)

    with right:
        st.markdown(
            "<p style='font-size:0.78rem;letter-spacing:0.07em;text-transform:uppercase;"
            "color:#ADB5BD;margin-bottom:8px'>Upcoming Arrivals</p>",
            unsafe_allow_html=True,
        )
        arrivals = run_q("""
            SELECT g.full_name, r.room_number, res.check_in_date, res.check_out_date
            FROM reservations res
            JOIN guests g ON g.guest_id = res.guest_id
            JOIN rooms   r ON r.room_id  = res.room_id
            WHERE res.check_in_date >= %s AND res.reservation_status = 'pending'
            ORDER BY res.check_in_date ASC LIMIT 5
        """, (today,))

        if arrivals:
            for a in arrivals:
                nights = (a["check_out_date"] - a["check_in_date"]).days
                st.markdown(f"""
                <div style='padding:10px;background:var(--surface);border-radius:6px;
                            margin-bottom:8px;border-left:4px solid var(--accent)'>
                    <div style='font-weight:500'>{html.escape(a['full_name'])}</div>
                    <div style='font-size:0.75rem;color:#ADB5BD'>
                        Room {a['room_number']} · Arriving: {a['check_in_date']} ({nights} Nights)
                    </div>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.markdown(
                "<p style='color:#ADB5BD;font-size:0.85rem'>No upcoming check-ins scheduled.</p>",
                unsafe_allow_html=True,
            )

# Page
elif st.session_state.page == "Reservations Table":
    st.markdown("## 📋 Reservations")

    fc1, fc2 = st.columns([1, 2])
    with fc1:
        f_status = st.selectbox("Filter Status", ["All", "pending", "active", "completed", "cancelled"])
    with fc2:
        f_search = st.text_input("🔍 Search by Guest Name...", placeholder="Type name here...", max_chars=_SEARCH_MAX_LEN)

    sql = """
        SELECT res.reservation_id, res.room_id, g.full_name, r.room_number, rt.type_name,
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
        conds.append("g.full_name LIKE %s")
        params.append(f"%{f_search[:_SEARCH_MAX_LEN]}%")

    if conds:
        sql += " WHERE " + " AND ".join(conds)
    sql += " ORDER BY res.check_in_date DESC"

    reservations = run_q(sql, params)

    if reservations:
        df = pd.DataFrame(reservations)
        df["total_cost"] = df.apply(
            lambda row: f"NPR {float(row['price']) * int(row['nights']):,.2f}", axis=1
        )
        st.dataframe(
            df[["reservation_id", "full_name", "room_number", "type_name",
                "check_in_date", "check_out_date", "nights", "total_cost", "reservation_status"]
            ].rename(columns={
                "reservation_id":     "ID",
                "full_name":          "Guest Name",
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

        st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)
        st.markdown("### ❌ Cancel Reservation")
        st.markdown(
            "<p style='color:var(--muted);font-size:0.85rem;margin-top:-8px'>"
            "Cancelling a pending or active reservation marks it as cancelled and "
            "immediately releases the room back to available inventory.</p>",
            unsafe_allow_html=True,
        )

        # Only pending/active
        cancellable = [r for r in reservations if r["reservation_status"] in ("pending", "active")]

        if cancellable:
            cancel_map = {
                f"#{r['reservation_id']} — Room {r['room_number']} · {r['full_name']} "
                f"({r['check_in_date']} → {r['check_out_date']})": r
                for r in cancellable
            }

            ca, cb = st.columns([3, 1])
            with ca:
                sel_label = st.selectbox(
                    "Select reservation to cancel",
                    list(cancel_map.keys()),
                    key="cancel_res_select",
                )
            with cb:
                st.markdown("<div style='height:28px'></div>", unsafe_allow_html=True)
                cancel_clicked = st.button(
                    "Cancel Reservation",
                    use_container_width=True,
                    key="cancel_res_btn",
                )

            target_res = cancel_map[sel_label]

            # Confirmation gate
            if cancel_clicked:
                if st.session_state.get("cancel_confirm_id") == target_res["reservation_id"]:
                    # Second click
                    def do_cancel(cur):
                        # Re-fetch status
                        cur.execute(
                            "SELECT reservation_status, room_id FROM reservations "
                            "WHERE reservation_id = %s FOR UPDATE",
                            (target_res["reservation_id"],),
                        )
                        row = cur.fetchone()
                        if not row:
                            raise RuntimeError("Reservation not found.")
                        if row["reservation_status"] not in ("pending", "active"):
                            raise RuntimeError(
                                f"Reservation is already '{row['reservation_status']}' and cannot be cancelled."
                            )

                        cur.execute(
                            "UPDATE reservations SET reservation_status = 'cancelled' "
                            "WHERE reservation_id = %s",
                            (target_res["reservation_id"],),
                        )

                        # Release the
                        cur.execute(
                            """
                            SELECT 1 FROM reservations
                            WHERE room_id = %s
                              AND reservation_status IN ('pending', 'active')
                              AND reservation_id != %s
                            LIMIT 1
                            """,
                            (row["room_id"], target_res["reservation_id"]),
                        )
                        still_booked = cur.fetchone()
                        if not still_booked:
                            cur.execute(
                                "UPDATE rooms SET status = 'available' WHERE room_id = %s",
                                (row["room_id"],),
                            )

                    try:
                        run_transaction(do_cancel)
                        st.session_state.pop("cancel_confirm_id", None)
                        st.toast(
                            f"Reservation #{target_res['reservation_id']} cancelled — "
                            f"Room {target_res['room_number']} is now available.",
                            icon="🟢",
                        )
                        st.rerun()
                    except RuntimeError as e:
                        st.error(str(e))
                        st.session_state.pop("cancel_confirm_id", None)
                    except Exception:
                        st.error("Cancellation failed due to an unexpected error. Please try again.")
                        st.session_state.pop("cancel_confirm_id", None)
                else:
                    # First click
                    st.session_state["cancel_confirm_id"] = target_res["reservation_id"]
                    st.warning(
                        f"⚠️ Are you sure you want to cancel reservation "
                        f"**#{target_res['reservation_id']}** for **{html.escape(target_res['full_name'])}** "
                        f"in Room **{target_res['room_number']}**? "
                        f"Click **Cancel Reservation** again to confirm."
                    )
            elif st.session_state.get("cancel_confirm_id") and \
                    st.session_state["cancel_confirm_id"] != target_res["reservation_id"]:
                # User switched
                st.session_state.pop("cancel_confirm_id", None)
        else:
            st.info("No pending or active reservations available to cancel.")
    else:
        st.info("No records match your search criteria.")

# Page
elif st.session_state.page == "Guest Info Table":
    st.markdown("## 👤 Guest Info")
    search_g = st.text_input(
        "🔍 Search Directory...",
        placeholder="Type name, phone, or email...",
        max_chars=_SEARCH_MAX_LEN,
    )

    # Select explicit
    base_cols = "SELECT guest_id, full_name, email, phone FROM guests"
    if search_g:
        term = f"%{search_g[:_SEARCH_MAX_LEN]}%"
        guests = run_q(
            base_cols + " WHERE full_name LIKE %s OR email LIKE %s OR phone LIKE %s ORDER BY full_name",
            (term, term, term),
        )
    else:
        guests = run_q(base_cols + " ORDER BY full_name")

    if guests:
        st.dataframe(
            pd.DataFrame(guests).rename(columns={
                "guest_id":  "Guest ID",
                "full_name": "Full Name",
                "email":     "Email Address",
                "phone":     "Phone Number",
            }),
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.info("No guest profiles found.")

# Page
elif st.session_state.page == "Rooms Table":
    st.markdown("## 🛏️ Live Room Inventory")

    f_rm_status = st.selectbox("Filter Status", ["All", "available", "occupied", "maintenance"])
    room_full = run_q("""
        SELECT r.room_id, r.room_number, rt.type_name, r.status, rt.price, rt.capacity
        FROM rooms r
        JOIN room_types rt ON r.room_type_id = rt.room_type_id
        ORDER BY r.room_number
    """)
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
elif st.session_state.page == "Settings ⚙":
    st.markdown("## ⚙️ Settings")

    tab_rooms, tab_types = st.tabs(["🛏️ Manage Rooms", "🏷️ Manage Room Types"])

    with tab_rooms:
        st.markdown("### Physical Room Inventory Updates")
        c_add, c_edit, c_del = st.columns(3)

        with c_add:
            with st.expander("➕ Add New Room", expanded=False):
                with st.form("add_room_form"):
                    new_rm_num  = st.text_input("Room Number (Unique)", placeholder="e.g., 105", max_chars=20)
                    rt_choices  = run_q("SELECT room_type_id, type_name FROM room_types")
                    rt_map      = {r["type_name"]: r["room_type_id"] for r in rt_choices} if rt_choices else {}
                    new_rm_type = st.selectbox("Assign Category", list(rt_map.keys()) if rt_map else ["— Setup Types First —"])
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
            with st.expander("✏️ Edit Room", expanded=False):
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
            with st.expander("❌ Delete Room", expanded=False):
                all_rooms_list2 = run_q("SELECT room_id, room_number FROM rooms ORDER BY room_number")
                if all_rooms_list2:
                    rm_del_map = {f"Room {r['room_number']}": r["room_id"] for r in all_rooms_list2}
                    sel_del_rm = st.selectbox("Select Room to Remove", list(rm_del_map.keys()))

                    st.warning("⚠️ Ensure this room has no active reservations before deleting.")
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

    with tab_types:
        st.markdown("### Room Category & Pricing")
        c_tadd, c_tedit, c_tdel = st.columns(3)

        with c_tadd:
            with st.expander("➕ Add New Room Type", expanded=False):
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
            with st.expander("✏️ Edit Category", expanded=False):
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
            with st.expander("❌ Delete Category", expanded=False):
                all_types_list2 = run_q("SELECT room_type_id, type_name FROM room_types ORDER BY type_name")
                if all_types_list2:
                    type_del_map  = {t["type_name"]: t["room_type_id"] for t in all_types_list2}
                    sel_del_type  = st.selectbox("Select Category to Delete", list(type_del_map.keys()))

                    st.warning("⚠️ All rooms assigned to this category must be reassigned or deleted first.")
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