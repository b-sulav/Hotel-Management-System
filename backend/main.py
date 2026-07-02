import hmac
import os
import re
import uuid
import logging
import logging.config
from contextlib import asynccontextmanager
from decimal import Decimal
from datetime import date, datetime, time as dt_time
from typing import List, Self

import pytz
import mysql.connector
from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, field_validator, model_validator
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from db_connection import get_db_connection, get_db_pool

import threading

_request_id_ctx: threading.local = threading.local()


class _RequestIdFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = getattr(_request_id_ctx, "value", "-")
        return True


logger = logging.getLogger(__name__)

# Token
_ADMIN_TOKEN_PLACEHOLDER = "replace_with_a_strong_random_secret"


def _get_admin_token() -> str:
    """Read admin token from Docker secret file or environment."""
    secret_path = "/run/secrets/admin_token"
    if os.path.exists(secret_path):
        with open(secret_path, "r") as f:
            return f.read().strip()
    return os.getenv("ADMIN_SECRET_TOKEN", "")


_ADMIN_TOKEN = _get_admin_token()

if not _ADMIN_TOKEN or _ADMIN_TOKEN == _ADMIN_TOKEN_PLACEHOLDER:
    logger.warning(
        "ADMIN_SECRET_TOKEN is not configured or is the default placeholder; "
        "admin endpoints will be unavailable until a strong secret is set."
    )

# Timezone /
_NEPAL_TZ = pytz.timezone("Asia/Kathmandu")
CHECKOUT_TIME = dt_time(12, 0, 0)
CHECKOUT_TIME_DISPLAY = "12:00 PM NST"
CHECKIN_TIME = dt_time(12, 0, 1)
CHECKIN_TIME_DISPLAY = "2:00 PM NST"


def now_nepal() -> datetime:
    return datetime.now(_NEPAL_TZ)


def today_nepal() -> date:
    return now_nepal().date()


def is_past_checkout_time() -> bool:
    return now_nepal().time() >= CHECKOUT_TIME


def is_past_checkin_time() -> bool:
    return now_nepal().time() >= CHECKIN_TIME


# Lifecycle
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Natura Resort Booking API starting up.")
    # Initialize the
    get_db_pool()
    yield
    logger.info("Natura Resort Booking API shut down.")


_ENABLE_DOCS = os.getenv("ENABLE_API_DOCS", "").lower() == "true"

app = FastAPI(
    title="Natura Resort Booking API",
    version="2.0.0",
    docs_url="/docs" if _ENABLE_DOCS else None,
    redoc_url="/redoc" if _ENABLE_DOCS else None,
    lifespan=lifespan,
)

def _get_client_ip(request: Request) -> str:
    xff = request.headers.get("X-Forwarded-For")
    if xff:
        return xff.split(",")[0].strip()
    return request.client.host if request.client else "0.0.0.0"


# Limits
limiter = Limiter(key_func=_get_client_ip)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS
_allowed_origins_env = os.getenv(
    "ALLOWED_ORIGINS",
    "https://rosyohospitality.com.np,https://www.rosyohospitality.com.np",
)
allowed_origins = [o.strip() for o in _allowed_origins_env.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST"],  # restrict to only needed methods
    allow_headers=["Content-Type", "X-Admin-Token"],
)

# Security
_SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "Permissions-Policy": "geolocation=(), microphone=(), camera=()",
    "Strict-Transport-Security": "max-age=63072000; includeSubDomains; preload",
    "Content-Security-Policy": (
        "default-src 'self'; "
        "script-src 'self'; "
        "style-src 'self' https://fonts.googleapis.com; "
        "font-src 'self' https://fonts.gstatic.com; "
        "img-src 'self' data: https://images.unsplash.com https://upload.wikimedia.org; "
        "connect-src 'self';"
    ),
}
_SKIP_CSP_PATHS = {"/docs", "/redoc", "/openapi.json"}


@app.middleware("http")
async def request_lifecycle_middleware(request: Request, call_next):
    # Assign a
    req_id = str(uuid.uuid4())
    _request_id_ctx.value = req_id

    response = await call_next(request)

    response.headers["X-Request-Id"] = req_id
    for header, value in _SECURITY_HEADERS.items():
        if header == "Content-Security-Policy" and request.url.path in _SKIP_CSP_PATHS:
            continue
        response.headers[header] = value

    return response


# DB
def get_db():
    conn = get_db_connection()
    try:
        yield conn
    finally:
        try:
            conn.rollback()
        except Exception:
            pass
        try:
            conn.close()
        except Exception:
            pass


# Models
class AvailabilityRequest(BaseModel):
    checkin: date
    checkout: date

    @model_validator(mode="after")
    def dates_valid(self) -> Self:
        today = today_nepal()
        if self.checkin < today:
            raise ValueError("Check-in date cannot be in the past.")
        if self.checkout <= self.checkin:
            raise ValueError("Check-out must be after check-in.")
        if (self.checkout - self.checkin).days > 365:
            raise ValueError("Stay duration cannot exceed 365 nights.")
        return self


class GuestInfo(BaseModel):
    full_name: str
    email: str | None = None
    phone: str

    @field_validator("full_name")
    @classmethod
    def validate_full_name(cls, v: str) -> str:
        v = v.strip()
        if not v or len(v) > 100:
            raise ValueError("Full name must be between 1 and 100 characters.")
        return v

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str | None) -> str | None:
        if v is None:
            return None
        v = v.strip()
        if not v:
            return None
        if "@" not in v or "." not in v:
            raise ValueError("Invalid email format.")
        return v

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: str) -> str:
        v = v.strip()
        if not v or not re.match(r"^\+?[\d\s\-]{7,20}$", v):
            raise ValueError(
                "Invalid phone format. Use digits, spaces, hyphens, and an optional leading +."
            )
        return v


class ReservationRequest(BaseModel):
    checkin: date
    checkout: date
    room_type_ids: List[int]
    guest: GuestInfo

    @model_validator(mode="after")
    def dates_valid(self) -> Self:
        today = today_nepal()
        if self.checkin < today:
            raise ValueError("Check-in date cannot be in the past.")
        if self.checkout <= self.checkin:
            raise ValueError("Check-out must be after check-in.")
        if (self.checkout - self.checkin).days > 365:
            raise ValueError("Stay duration cannot exceed 365 nights.")
        return self

    @field_validator("room_type_ids")
    @classmethod
    def at_least_one_room(cls, v: List[int]) -> List[int]:
        if not v or len(v) > 10:
            raise ValueError("You must select between 1 and 10 rooms per reservation booking request.")
        if any((not isinstance(x, int) or x <= 0) for x in v):
            raise ValueError("Invalid room type selection.")
        return v


# Checkout
def run_auto_checkout(cursor) -> int:
    """
    Mark overdue reservations as completed and synchronise room statuses.
    Returns the total number of reservations completed.
    """
    now = now_nepal()
    today = now.date()
    checkout_now = now.time()

    cursor.execute(
        "UPDATE reservations SET reservation_status = 'completed', checkout_time = %s "
        "WHERE check_out_date < %s AND reservation_status IN ('pending', 'active')",
        (checkout_now, today),
    )
    past_due = cursor.rowcount

    today_checkouts = 0
    print(f"[turnover:backend] now={now}, today={today}, past_due={past_due}, today_checkouts={today_checkouts}")
    if is_past_checkout_time():
        cursor.execute(
            "UPDATE reservations SET reservation_status = 'completed', checkout_time = %s "
            "WHERE check_out_date = %s AND reservation_status = 'active'",
            (checkout_now, today),
        )
        today_checkouts = cursor.rowcount

        # Turnover: completed rooms go to occupied if same-day pending/active exists, else available
        cursor.execute("""
            UPDATE rooms r
            LEFT JOIN reservations res ON res.room_id = r.room_id
                AND res.reservation_status IN ('pending', 'active')
                AND res.check_in_date <= %s
                AND res.check_out_date >= %s
            SET r.status = CASE WHEN res.room_id IS NOT NULL THEN 'occupied' ELSE 'available' END
        """, (today, today))
        print(f"[turnover:backend] room sync updated={cursor.rowcount}")

        # Activate pending reservations that now have an occupied room
        cursor.execute("""
            UPDATE reservations res
            JOIN rooms r ON r.room_id = res.room_id
            SET res.reservation_status = 'active'
            WHERE res.reservation_status = 'pending'
              AND res.check_in_date <= %s
              AND r.status = 'occupied'
        """, (today,))

    # At 2PM, activate any remaining pending reservations for rooms already occupied
    if is_past_checkin_time():
        cursor.execute(
            """
                UPDATE reservations r JOIN rooms rm ON rm.room_id = r.room_id
                SET r.reservation_status = 'active', rm.status = 'occupied'
                WHERE r.check_in_date = %s AND r.reservation_status = 'pending'
                  AND rm.status = 'occupied'
                """,
            (today,),
        )

    total_completed = past_due + today_checkouts

    # Cleanup rooms with no active/pending reservations
    cursor.execute(
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

    return total_completed




def run_archive_old(cursor, days: int = 90) -> dict:
    """
    Move completed/cancelled reservations older than `days` days
    into reservation_archives as compressed JSON snapshots.
    Returns counts.
    """
    from datetime import timedelta
    import json

    cutoff = today_nepal() - timedelta(days=days)

    cursor.execute("""
        SELECT r.reservation_id, r.room_id, r.guest_id, r.guest_name,
               r.check_in_date, r.check_out_date, r.checkout_time,
               r.reservation_status, r.created_at, r.updated_at,
               g.full_name AS guest_full_name, g.email AS guest_email, g.phone AS guest_phone, g.created_at AS guest_created,
               rm.room_number, rt.type_name AS room_type, rt.price AS room_price, rt.capacity AS room_capacity
        FROM reservations r
        JOIN guests g ON g.guest_id = r.guest_id
        JOIN rooms rm ON rm.room_id = r.room_id
        JOIN room_types rt ON rt.room_type_id = rm.room_type_id
        WHERE r.reservation_status IN ('completed', 'cancelled')
          AND r.check_out_date < %s
        ORDER BY r.check_out_date ASC
        LIMIT 5000
    """, (cutoff,))

    rows = cursor.fetchall()
    archived = 0
    deleted = 0

    for row in rows:
        reservation_json = {
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
        }
        guest_snapshot = {
            "guest_id": row["guest_id"],
            "full_name": row["guest_full_name"],
            "email": row["guest_email"],
            "phone": row["guest_phone"],
            "created_at": str(row["guest_created"]),
        }
        room_snapshot = {
            "room_id": row["room_id"],
            "room_number": row["room_number"],
            "room_type": row["room_type"],
            "room_price": float(row["room_price"]) if row["room_price"] else 0.0,
            "room_capacity": row["room_capacity"],
        }
        cursor.execute("""
            INSERT INTO reservation_archives (reservation_data, guest_snapshot, room_snapshot, archive_reason)
            VALUES (%s, %s, %s, %s)
        """, (
            json.dumps(reservation_json, ensure_ascii=False),
            json.dumps(guest_snapshot, ensure_ascii=False),
            json.dumps(room_snapshot, ensure_ascii=False),
            "completed_aged" if row["reservation_status"] == "completed" else "cancelled_aged",
        ))
        archived += 1
        cursor.execute("DELETE FROM reservations WHERE reservation_id = %s", (row["reservation_id"],))
        deleted += 1

    return {"archived": archived, "deleted": deleted, "cutoff_days": days}

def find_all_available_rooms(
    cursor, checkin: date, checkout: date, lock_for_update: bool = False
) -> list:
    query = """
        SELECT r.room_id, r.room_number, r.room_type_id, rt.type_name, rt.price, rt.capacity
        FROM rooms r
        JOIN room_types rt ON r.room_type_id = rt.room_type_id
        WHERE r.status != 'maintenance'
          AND NOT EXISTS (
              SELECT 1 FROM reservations res
              WHERE res.room_id = r.room_id
                AND res.reservation_status IN ('pending', 'active')
                AND res.check_in_date < %s AND res.check_out_date > %s
          )
        ORDER BY rt.price ASC, r.room_number ASC
    """
    if lock_for_update:
        query += " FOR UPDATE"
    cursor.execute(query, (checkout, checkin))
    return cursor.fetchall()




# =====================
# Admin archive route
# =====================
@app.post("/api/admin/archive-old")
@limiter.limit("10/minute")
async def admin_archive_old(request: Request, db=Depends(get_db)):
    provided = request.headers.get("X-Admin-Token", "")
    if not _verify_admin_token(provided):
        raise HTTPException(status_code=403, detail="Forbidden.")

    cursor = db.cursor(dictionary=True)
    try:
        import json as _json
        body_bytes = await request.body()
        body = _json.loads(body_bytes.decode() or "{}")
        days = int(body.get("days", 90))
        if not (1 <= days <= 3650):
            raise HTTPException(status_code=422, detail="Days must be between 1 and 3650.")

        result = run_archive_old(cursor, days=days)
        db.commit()
        logger.info(
            "Admin archive: archived=%d deleted=%d cutoff=%dd",
            result["archived"], result["deleted"], days,
        )
        return {"status": "ok", **result}
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        logger.error("Admin archive error: %s", e)
        raise HTTPException(status_code=500, detail="Archive processing error.")
    finally:
        cursor.close()

# =====================
# Stats / monitoring
# =====================
@app.get("/api/admin/stats")
@limiter.limit("30/minute")
def admin_stats(request: Request, db=Depends(get_db)):
    provided = request.headers.get("X-Admin-Token", "")
    if not _verify_admin_token(provided):
        raise HTTPException(status_code=403, detail="Forbidden.")

    from datetime import timedelta

    cursor = db.cursor(dictionary=True)
    try:
        cursor.execute("""
            SELECT
                (SELECT COUNT(*) FROM reservations)                         AS live_reservations,
                (SELECT COUNT(*) FROM guests)                               AS total_guests,
                (SELECT COUNT(*) FROM reservations
                 WHERE reservation_status IN ('pending','active'))         AS active_reservations,
                (SELECT COUNT(*) FROM reservations
                 WHERE reservation_status IN ('completed','cancelled'))    AS closed_reservations,
                (SELECT COUNT(*) FROM reservation_archives)                 AS archived_reservations,
                (SELECT COALESCE(SUM(CHAR_LENGTH(reservation_data)), 0)
                 FROM reservation_archives)                                AS archive_bytes,
                (SELECT COALESCE(SUM(
                    CHAR_LENGTH(guest_name) +
                    CHAR_LENGTH(COALESCE(email, '')) +
                    CHAR_LENGTH(phone)
                ), 0) FROM reservations)                                    AS live_guest_bytes_approx
        """)
        stats = cursor.fetchone()

        cursor.execute("""
            SELECT COUNT(*) AS cnt
            FROM reservations
            WHERE reservation_status IN ('completed', 'cancelled')
              AND check_out_date < %s
        """, (today_nepal() - timedelta(days=60),))
        row = cursor.fetchone()
        suggestion = "archive" if row and row.get("cnt", 0) > 500 else "ok"

        return {"status": "ok", "stats": stats, "suggestion": suggestion}
    finally:
        cursor.close()

def _verify_admin_token(provided: str) -> bool:
    """Constant-time comparison to prevent timing attacks."""
    token = _ADMIN_TOKEN
    if not token or token == _ADMIN_TOKEN_PLACEHOLDER:
        return False
    return hmac.compare_digest(token.encode(), provided.encode())


# Routes
@app.get("/api/health")
def health_check(db=Depends(get_db)):
    cursor = db.cursor()
    try:
        cursor.execute("SELECT 1")
        cursor.fetchone()
        return {
            "status": "ok",
            "database": "connected",
            "server_time_nst": now_nepal().strftime("%Y-%m-%d %H:%M:%S %Z"),
        }
    except Exception as e:
        logger.error("Health check DB failure: %s", e)
        raise HTTPException(status_code=503, detail="Service temporarily unavailable.")
    finally:
        cursor.close()


@app.post("/api/admin/run-checkout")
@limiter.limit("10/minute")
def admin_run_checkout(request: Request, db=Depends(get_db)):
    provided = request.headers.get("X-Admin-Token", "")
    if not _verify_admin_token(provided):
        raise HTTPException(status_code=403, detail="Forbidden.")

    cursor = db.cursor(dictionary=True)
    try:
        completed = run_auto_checkout(cursor)
        db.commit()
        logger.info("Admin checkout triggered; %d reservation(s) completed.", completed)
        return {
            "status": "ok",
            "reservations_completed": completed,
            "server_time_nst": now_nepal().strftime("%Y-%m-%d %H:%M:%S %Z"),
        }
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        logger.error("Admin checkout error: %s", e)
        raise HTTPException(status_code=500, detail="Checkout processing error.")
    finally:
        cursor.close()


@app.post("/api/check-availability")
@limiter.limit("30/minute")
def check_availability(request: Request, req: AvailabilityRequest, db=Depends(get_db)):
    cursor = db.cursor(dictionary=True)
    try:
        rooms = find_all_available_rooms(cursor, req.checkin, req.checkout)
        inventory: dict = {}
        for r in rooms:
            tid = r["room_type_id"]
            if tid not in inventory:
                inventory[tid] = {
                    "room_type_id": tid,
                    "type_name": r["type_name"],
                    "capacity": r["capacity"],
                    "price": float(r["price"]),
                    "available_count": 0,
                }
            inventory[tid]["available_count"] += 1

        return {"checkout_time": CHECKOUT_TIME_DISPLAY, "inventory": list(inventory.values())}
    except Exception as e:
        logger.error("Error fetching availability: %s", e)
        raise HTTPException(status_code=500, detail="Internal processing fault occurred.")
    finally:
        cursor.close()


@app.post("/api/reserve")
@limiter.limit("5/minute")
def create_reservation(request: Request, req: ReservationRequest, db=Depends(get_db)):
    cursor = db.cursor(dictionary=True)
    try:
        # REPEATABLE READ
        db.start_transaction(isolation_level="REPEATABLE READ")

        # Validate all
        unique_type_ids = sorted(set(req.room_type_ids))
        if not unique_type_ids:
            raise HTTPException(status_code=422, detail="No room types specified.")

        placeholders = ",".join(["%s"] * len(unique_type_ids))
        cursor.execute(
            f"SELECT room_type_id FROM room_types WHERE room_type_id IN ({placeholders})",
            tuple(unique_type_ids),
        )
        valid_ids = {r["room_type_id"] for r in cursor.fetchall()}
        if len(valid_ids) != len(unique_type_ids):
            raise HTTPException(status_code=422, detail="Invalid room type selection.")

        # Lock available
        available_rooms = find_all_available_rooms(
            cursor, req.checkin, req.checkout, lock_for_update=True
        )
        rooms_by_type: dict[int, list] = {}
        for rm in available_rooms:
            rooms_by_type.setdefault(rm["room_type_id"], []).append(rm)

        assigned_rooms: list = []
        for requested_type_id in req.room_type_ids:
            pool = rooms_by_type.get(requested_type_id)
            if pool:
                assigned_rooms.append(pool.pop(0))
            else:
                raise HTTPException(
                    status_code=409,
                    detail="Selected inventory profile no longer available for these dates.",
                )

        # Upsert guest
        cursor.execute(
            """
            INSERT INTO guests (full_name, email, phone)
            VALUES (%s, %s, %s)
            ON DUPLICATE KEY UPDATE
                guest_id = LAST_INSERT_ID(guest_id)
            """,
            (req.guest.full_name, req.guest.email, req.guest.phone),
        )
        guest_id = cursor.lastrowid

        # Guard against
        cursor.execute(
            """
            SELECT reservation_id FROM reservations
            WHERE guest_id = %s AND reservation_status IN ('pending', 'active')
              AND check_in_date < %s AND check_out_date > %s LIMIT 1
            """,
            (guest_id, req.checkout, req.checkin),
        )
        if cursor.fetchone():
            raise HTTPException(
                status_code=409,
                detail="An active booking already covers this window for this customer account.",
            )

        reservation_ids, room_numbers = [], []
        nights = (req.checkout - req.checkin).days
        total_price = Decimal("0.00")
        today = today_nepal()

        for room in assigned_rooms:
            # Final in-transaction overlap guard with row locking
            cursor.execute(
                """
                SELECT 1 FROM reservations
                WHERE room_id = %s
                  AND reservation_status IN ('pending', 'active')
                  AND check_in_date < %s AND check_out_date > %s
                FOR UPDATE
                """,
                (room["room_id"], req.checkout, req.checkin),
            )
            if cursor.fetchone():
                raise HTTPException(
                    status_code=409,
                    detail=f"Room {room['room_number']} was just booked by another request for these dates.",
                )

            if req.checkin == today:
                initial_status = "active" if now_nepal().time() >= CHECKIN_TIME else "pending"
            else:
                initial_status = "pending"
            cursor.execute(
                "INSERT INTO reservations "
                "(room_id, guest_id, guest_name, check_in_date, check_out_date, checkout_time, reservation_status) "
                "VALUES (%s, %s, %s, %s, %s, %s, %s)",
                (
                    room["room_id"],
                    guest_id,
                    req.guest.full_name,
                    req.checkin,
                    req.checkout,
                    CHECKOUT_TIME,
                    initial_status,
                ),
            )
            reservation_ids.append(cursor.lastrowid)
            room_numbers.append(str(room["room_number"]))
            total_price += Decimal(str(room["price"])) * nights

            if initial_status == "active":
                cursor.execute(
                    "UPDATE rooms SET status = 'occupied' WHERE room_id = %s",
                    (room["room_id"],),
                )

        db.commit()
        logger.info(
            "Reservation created: guest_id=%d rooms=%s checkin=%s checkout=%s total=%.2f",
            guest_id,
            room_numbers,
            req.checkin,
            req.checkout,
            float(total_price),
        )
        return {
            "reservation_ids": reservation_ids,
            "room_number": ", ".join(room_numbers),
            "checkin": str(req.checkin),
            "checkout": str(req.checkout),
            "nights": nights,
            "total_price": float(total_price),
            "message": f"Booking confirmed! Rooms {', '.join(room_numbers)} locked.",
        }
    except mysql.connector.Error as sql_err:
        db.rollback()
        logger.error("Database error during reservation: %s", sql_err)
        raise HTTPException(status_code=500, detail="A database error occurred. Please try again.")
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        logger.error("Unexpected error during reservation: %s", e)
        raise HTTPException(status_code=500, detail="An unexpected error occurred. Please try again.")
    finally:
        cursor.close()