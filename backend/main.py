from contextlib import asynccontextmanager
from datetime import datetime, time as dt_time
from pathlib import Path
from typing import Optional
from zoneinfo import ZoneInfo
import asyncio
import json
import os
import re
import tempfile
import threading
import uuid

import pdfplumber
from fastapi import Depends, FastAPI, File, Form, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from twilio.rest import Client

from backend.auth.cognito_verifier import verify_cognito_token
from backend.doctor_search import search_nearby_doctors
from backend.parser import parse_lab_values
from backend.pipeline import run_analysis_pipeline


# =========================================================
# PATHS AND PERSISTENT APPOINTMENT STORAGE
# =========================================================
BASE_DIR = Path(__file__).resolve().parent.parent
UPLOAD_DIR = BASE_DIR / "uploaded_reports"
DATA_DIR = BASE_DIR / "backend" / "data"
APPOINTMENTS_FILE = DATA_DIR / "appointments.json"

UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
DATA_DIR.mkdir(parents=True, exist_ok=True)

DEFAULT_TIMEZONE = os.getenv("APP_TIMEZONE", "Asia/Kolkata")
DAY_REMINDER_HOUR = int(os.getenv("DAY_REMINDER_HOUR", "9"))
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_PHONE_NUMBER = os.getenv("TWILIO_PHONE_NUMBER")

appointments_lock = threading.Lock()
PATIENT_HISTORY_DB = {}


def _load_appointments():
    if not APPOINTMENTS_FILE.exists():
        return []

    try:
        data = json.loads(APPOINTMENTS_FILE.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else []
    except Exception as exc:
        print(f"[Appointments] Could not read appointment file: {exc}")
        return []


def _save_appointments():
    with appointments_lock:
        temporary_file = APPOINTMENTS_FILE.with_suffix(".tmp")
        temporary_file.write_text(
            json.dumps(APPOINTMENTS_DB, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        temporary_file.replace(APPOINTMENTS_FILE)


APPOINTMENTS_DB = _load_appointments()

if not TWILIO_ACCOUNT_SID or not TWILIO_AUTH_TOKEN or not TWILIO_PHONE_NUMBER:
    print(
        "[Twilio] Missing TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, "
        "or TWILIO_PHONE_NUMBER in environment."
    )
    twilio_client = None
else:
    twilio_client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)


# =========================================================
# HELPERS
# =========================================================
def normalize_name(name: str):
    if not name:
        return "unknown"

    normalized = name.lower().strip()
    normalized = re.sub(r"[^a-z0-9 ]", "", normalized)
    normalized = re.sub(r"\s+", " ", normalized)
    return normalized or "unknown"


def make_patient_key(email: str, patient_name: str):
    return f"{email.lower().strip()}::{normalize_name(patient_name)}"


def validate_phone_number(phone_number: str):
    cleaned = phone_number.strip().replace(" ", "").replace("-", "")

    if not re.fullmatch(r"\+[1-9]\d{7,14}", cleaned):
        raise HTTPException(
            status_code=400,
            detail="Phone number must use E.164 format, for example +919876543210.",
        )

    return cleaned


def send_sms(phone_number: str, message: str):
    """Send one SMS using Twilio."""
    phone_number = validate_phone_number(phone_number)

    if twilio_client is None:
        raise RuntimeError(
            "Twilio is not configured. Add TWILIO_ACCOUNT_SID, "
            "TWILIO_AUTH_TOKEN, and TWILIO_PHONE_NUMBER to .env."
        )

    twilio_message = twilio_client.messages.create(
        body=message,
        from_=TWILIO_PHONE_NUMBER,
        to=phone_number,
    )

    print(
        f"[SMS] Sent to {phone_number}. "
        f"Message SID={twilio_message.sid}"
    )
    return {
        "sid": twilio_message.sid,
        "status": getattr(twilio_message, "status", None),
    }


def get_appointment_datetime(appointment: dict):
    timezone_name = appointment.get("timezone") or DEFAULT_TIMEZONE

    try:
        timezone = ZoneInfo(timezone_name)
    except Exception:
        timezone = ZoneInfo(DEFAULT_TIMEZONE)

    date_text = appointment["appointment_date"]
    time_text = appointment["appointment_time"]
    naive_datetime = datetime.strptime(
        f"{date_text} {time_text}",
        "%Y-%m-%d %H:%M",
    )

    return naive_datetime.replace(tzinfo=timezone)


def find_appointment(appointment_id: str):
    return next(
        (
            appointment
            for appointment in APPOINTMENTS_DB
            if appointment.get("id") == appointment_id
        ),
        None,
    )


async def check_appointment_reminders():
    """
    Check all future appointments and send:
    1. A reminder on the appointment day at/after 9 AM.
    2. A reminder when the appointment is within one hour.

    Reminder flags are persisted so the same SMS is not sent twice.
    """
    changed = False

    with appointments_lock:
        appointments_snapshot = [dict(item) for item in APPOINTMENTS_DB]

    for appointment in appointments_snapshot:
        if appointment.get("status") != "scheduled":
            continue

        try:
            appointment_datetime = get_appointment_datetime(appointment)
            now = datetime.now(appointment_datetime.tzinfo)
            seconds_until = (appointment_datetime - now).total_seconds()

            if seconds_until <= 0:
                continue

            doctor_name = appointment.get("doctor_name", "your doctor")
            hospital = appointment.get("hospital", "the clinic")
            display_time = appointment_datetime.strftime("%I:%M %p")
            display_date = appointment_datetime.strftime("%d %B %Y")
            phone_number = appointment["phone_number"]

            day_reminder_due = (
                appointment_datetime.date() == now.date()
                and now.time() >= dt_time(DAY_REMINDER_HOUR, 0)
                and not appointment.get("day_reminder_sent", False)
            )

            one_hour_reminder_due = (
                0 < seconds_until <= 3600
                and not appointment.get("one_hour_reminder_sent", False)
            )

            if day_reminder_due:
                day_message = (
                    "LabLens Appointment Reminder\n"
                    f"You have an appointment today with {doctor_name}.\n"
                    f"Time: {display_time}\n"
                    f"Location: {hospital}\n"
                    "Please carry your medical reports and current prescriptions."
                )

                await asyncio.to_thread(send_sms, phone_number, day_message)

                with appointments_lock:
                    live_appointment = find_appointment(appointment["id"])
                    if live_appointment:
                        live_appointment["day_reminder_sent"] = True
                        live_appointment["day_reminder_sent_at"] = now.isoformat()
                        changed = True

            if one_hour_reminder_due:
                hour_message = (
                    "LabLens Appointment Reminder\n"
                    f"Your appointment with {doctor_name} starts in about 1 hour.\n"
                    f"Time: {display_time}\n"
                    f"Location: {hospital}\n"
                    "Please leave on time and carry your reports."
                )

                await asyncio.to_thread(send_sms, phone_number, hour_message)

                with appointments_lock:
                    live_appointment = find_appointment(appointment["id"])
                    if live_appointment:
                        live_appointment["one_hour_reminder_sent"] = True
                        live_appointment["one_hour_reminder_sent_at"] = now.isoformat()
                        changed = True

        except Exception as exc:
            print(
                "[Appointments] Reminder check failed for "
                f"{appointment.get('id')}: {exc}"
            )

    if changed:
        _save_appointments()


async def appointment_reminder_loop():
    while True:
        try:
            await check_appointment_reminders()
        except Exception as exc:
            print(f"[Appointments] Reminder loop error: {exc}")

        await asyncio.sleep(30)


@asynccontextmanager
async def lifespan(app: FastAPI):
    reminder_task = asyncio.create_task(appointment_reminder_loop())
    print("[Appointments] Reminder scheduler started.")

    try:
        yield
    finally:
        reminder_task.cancel()
        try:
            await reminder_task
        except asyncio.CancelledError:
            pass
        print("[Appointments] Reminder scheduler stopped.")


app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount(
    "/uploaded_reports",
    StaticFiles(directory=str(UPLOAD_DIR)),
    name="uploaded_reports",
)


# =========================================================
# APPOINTMENT MODELS
# =========================================================
class AppointmentCreate(BaseModel):
    email: str
    patient_name: str
    phone_number: str
    doctor_name: str
    hospital: str
    appointment_date: str = Field(
        description="Appointment date in YYYY-MM-DD format"
    )
    appointment_time: str = Field(
        description="Appointment time in 24-hour HH:MM format"
    )
    specialty: Optional[str] = "General Physician"
    timezone: Optional[str] = DEFAULT_TIMEZONE


# =========================================================
# CORE ENDPOINTS
# =========================================================
@app.get("/")
def home():
    return {
        "status": "API running smoothly",
        "appointment_scheduler": "running",
        "saved_appointments": len(APPOINTMENTS_DB),
    }


@app.get("/api/patient/has-records")
async def check_patient_records(
    email: str,
    patient_name: str = Query(default=""),
):
    if not email:
        return {"success": True, "hasRecords": False}

    if patient_name:
        key = make_patient_key(email, patient_name)
        history = PATIENT_HISTORY_DB.get(key, [])
    else:
        history = [
            report
            for key, reports in PATIENT_HISTORY_DB.items()
            if key.startswith(email.lower().strip() + "::")
            for report in reports
        ]

    return {"success": True, "hasRecords": len(history) > 0}


@app.get("/api/patient/history")
async def get_patient_history(
    email: str,
    patient_name: str = Query(default=""),
):
    if not email:
        return {"success": True, "history": []}

    if patient_name:
        key = make_patient_key(email, patient_name)
        history = PATIENT_HISTORY_DB.get(key, [])
    else:
        history = [
            report
            for key, reports in PATIENT_HISTORY_DB.items()
            if key.startswith(email.lower().strip() + "::")
            for report in reports
        ]

    return {"success": True, "history": history}


# =========================================================
# APPOINTMENT ENDPOINTS
# =========================================================
@app.post("/api/appointments")
async def create_appointment(payload: AppointmentCreate):
    clean_email = payload.email.lower().strip()
    patient_name = payload.patient_name.strip() or "Unknown"
    phone_number = validate_phone_number(payload.phone_number)

    try:
        timezone = ZoneInfo(payload.timezone or DEFAULT_TIMEZONE)
    except Exception:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid timezone. Use {DEFAULT_TIMEZONE} for India.",
        )

    try:
        appointment_datetime = datetime.strptime(
            f"{payload.appointment_date} {payload.appointment_time}",
            "%Y-%m-%d %H:%M",
        ).replace(tzinfo=timezone)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail="Use appointment_date YYYY-MM-DD and appointment_time HH:MM.",
        )

    if appointment_datetime <= datetime.now(timezone):
        raise HTTPException(
            status_code=400,
            detail="Appointment date and time must be in the future.",
        )

    appointment = {
        "id": f"appointment_{uuid.uuid4().hex}",
        "email": clean_email,
        "patient_name": patient_name,
        "phone_number": phone_number,
        "doctor_name": payload.doctor_name.strip() or "Selected Doctor",
        "hospital": payload.hospital.strip() or "Clinic/Hospital",
        "appointment_date": payload.appointment_date,
        "appointment_time": payload.appointment_time,
        "specialty": payload.specialty or "General Physician",
        "timezone": payload.timezone or DEFAULT_TIMEZONE,
        "status": "scheduled",
        "day_reminder_sent": False,
        "one_hour_reminder_sent": False,
        "created_at": datetime.now(timezone).isoformat(),
    }

    with appointments_lock:
        APPOINTMENTS_DB.append(appointment)

    _save_appointments()

    confirmation_message = (
        "LabLens Appointment Saved\n"
        f"Doctor: {appointment['doctor_name']}\n"
        f"Date: {appointment_datetime.strftime('%d %B %Y')}\n"
        f"Time: {appointment_datetime.strftime('%I:%M %p')}\n"
        f"Location: {appointment['hospital']}\n"
        "We will remind you on the appointment day and about 1 hour before."
    )

    sms_sent = True
    sms_error = None

    try:
        await asyncio.to_thread(
            send_sms,
            phone_number,
            confirmation_message,
        )
    except Exception as exc:
        sms_sent = False
        sms_error = str(exc)
        print(f"[Appointments] Confirmation SMS failed: {exc}")

    return {
        "success": True,
        "appointment": appointment,
        "confirmation_sms_sent": sms_sent,
        "sms_error": sms_error,
    }


@app.get("/api/appointments")
async def get_appointments(
    email: str = Query(...),
    patient_name: str = Query(default=""),
):
    clean_email = email.lower().strip()
    normalized_patient = normalize_name(patient_name) if patient_name else None

    appointments = [
        appointment
        for appointment in APPOINTMENTS_DB
        if appointment.get("email") == clean_email
        and (
            normalized_patient is None
            or normalize_name(appointment.get("patient_name", ""))
            == normalized_patient
        )
    ]

    appointments.sort(
        key=lambda item: (
            item.get("appointment_date", ""),
            item.get("appointment_time", ""),
        )
    )

    return {"success": True, "appointments": appointments}


@app.patch("/api/appointments/{appointment_id}/cancel")
async def cancel_appointment(
    appointment_id: str,
    email: str = Query(...),
):
    clean_email = email.lower().strip()

    with appointments_lock:
        appointment = find_appointment(appointment_id)

        if not appointment or appointment.get("email") != clean_email:
            raise HTTPException(
                status_code=404,
                detail="Appointment not found.",
            )

        appointment["status"] = "cancelled"
        appointment["cancelled_at"] = datetime.now(
            ZoneInfo(appointment.get("timezone", DEFAULT_TIMEZONE))
        ).isoformat()

    _save_appointments()

    return {
        "success": True,
        "appointment": appointment,
    }


# =========================================================
# REPORT ANALYSIS
# =========================================================
@app.post("/analyze-report")
async def analyze_report(
    file: UploadFile = File(...),
    email: str = Form(...),
    city: str = Form(default="Delhi"),
):
    print("\n--- [START] Incoming Analysis Request ---")
    print(f"Target Account Email: {email}")
    print(f"File Received: {file.filename}")

    temporary_path = None

    try:
        file_bytes = await file.read()

        if not file_bytes:
            raise HTTPException(status_code=400, detail="Uploaded file is empty.")

        report_id = f"report_{uuid.uuid4().hex}"
        original_filename = file.filename or "lab-report.pdf"
        safe_filename = re.sub(r"[^a-zA-Z0-9_.-]", "_", original_filename)
        saved_filename = f"{report_id}_{safe_filename}"
        saved_path = UPLOAD_DIR / saved_filename

        saved_path.write_bytes(file_bytes)
        report_url = f"/uploaded_reports/{saved_filename}"

        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temporary:
            temporary.write(file_bytes)
            temporary_path = temporary.name

        text_parts = []

        with pdfplumber.open(temporary_path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text_parts.append(page_text)

        text = "\n".join(text_parts).strip()

        if not text:
            raise HTTPException(
                status_code=400,
                detail="No readable text was found in the PDF.",
            )

        parsed = parse_lab_values(text)

        if not parsed:
            raise HTTPException(
                status_code=400,
                detail="Could not parse lab report.",
            )

        patient_name = parsed.get("patient_name", "Unknown")
        report_date = parsed.get("report_date", "Unknown")
        tests = parsed.get("tests", [])

        try:
            result = run_analysis_pipeline(parsed)
        except Exception as ai_error:
            print(f"[AI Core] Pipeline error: {ai_error}")

            normal_count = sum(
                1 for test in tests if test.get("status") == "NORMAL"
            )
            abnormal_count = sum(
                1
                for test in tests
                if test.get("status") in {"HIGH", "LOW", "CRITICAL"}
            )

            result = {
                "status": "partial_success",
                "total_tests": len(tests),
                "normal_count": normal_count,
                "abnormal_count": abnormal_count,
                "summary": (
                    "Report values were extracted, but the detailed "
                    "AI explanation could not complete."
                ),
                "specialist": {
                    "primary_specialist": "General Physician"
                },
                "parsed_report": parsed,
            }

        specialist = result.get("specialist", {}) or {}
        primary_specialist = specialist.get(
            "primary_specialist",
            "General Physician",
        )

        try:
            result["nearby_doctors"] = search_nearby_doctors(
                primary_specialist,
                city,
            )
        except Exception as doctor_error:
            print(f"[Doctor Search] Error: {doctor_error}")
            result["nearby_doctors"] = []

        result["id"] = report_id
        result["analyzed_at"] = datetime.now(
            ZoneInfo(DEFAULT_TIMEZONE)
        ).isoformat()
        result["file_name"] = original_filename
        result["report_url"] = report_url
        result["patient_name"] = patient_name
        result["report_date"] = report_date
        result["parsed_report"] = parsed

        clean_email = email.lower().strip()
        patient_key = make_patient_key(clean_email, patient_name)
        PATIENT_HISTORY_DB.setdefault(patient_key, []).insert(0, result)

        return result

    except HTTPException:
        raise
    except Exception as exc:
        print(f"[Analyze Report] Critical error: {exc}")
        raise HTTPException(status_code=500, detail=str(exc))
    finally:
        if temporary_path and os.path.exists(temporary_path):
            try:
                os.remove(temporary_path)
            except OSError:
                pass


@app.get("/api/dashboard")
def get_patient_dashboard(
    current_user: dict = Depends(verify_cognito_token),
):
    user_id = current_user.get("sub")
    email = current_user.get("email")

    return {
        "status": "Authorized",
        "message": f"Welcome to your secure AI health desk, {email}!",
        "aws_cognito_user_id": user_id,
    }


@app.get("/api/patient/report/text-summary")
async def get_text_summary(
    email: str = Query(...),
    report_id: str = Query(...),
    patient_name: str = Query(default=""),
):
    clean_email = email.lower().strip()

    if patient_name:
        key = make_patient_key(clean_email, patient_name)
        user_history = PATIENT_HISTORY_DB.get(key, [])
    else:
        user_history = [
            report
            for key, reports in PATIENT_HISTORY_DB.items()
            if key.startswith(clean_email + "::")
            for report in reports
        ]

    report = next(
        (
            record
            for record in user_history
            if record.get("id") == report_id
        ),
        None,
    )

    if not report:
        raise HTTPException(
            status_code=404,
            detail="Requested lab report not found.",
        )

    status_flag = str(report.get("status", "NORMAL")).upper()
    briefing_summary = report.get(
        "summary",
        "Your tested health metrics have been processed.",
    )
    specialist = report.get("specialist", {}) or {}
    recommended_doctor = specialist.get(
        "primary_specialist",
        "General Physician",
    )

    if any(
        word in status_flag
        for word in ["CRITICAL", "HIGH", "ABNORMAL", "ALERT"]
    ):
        greeting = (
            "Your latest report has been processed, and some values "
            "need attention."
        )
        next_step = (
            f"The system recommends consulting a {recommended_doctor} "
            "for formal review."
        )
    else:
        greeting = (
            "Your latest report has been analyzed, and the extracted "
            "values appear stable."
        )
        next_step = (
            f"For routine tracking, you may consult a "
            f"{recommended_doctor}."
        )

    return {
        "success": True,
        "summary_text": (
            f"{greeting} {briefing_summary} {next_step}"
        ),
    }
