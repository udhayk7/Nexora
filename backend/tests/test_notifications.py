from datetime import datetime, timedelta, timezone
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.application import ApplicationInterview, JobApplication
from app.models.notification import Notification
from app.models.user import User
from app.services.notification_service import NotificationService
from app.tasks.reminder_tasks import process_scheduled_reminders_task


def create_user_and_token(
    client: TestClient, email: str = "notify_user@example.com"
) -> tuple[dict[str, str], str]:
    """Helper to register and authenticate a test user."""
    client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "Password123!",
            "full_name": "Notify User",
        },
    )
    login_res = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "Password123!"},
    )
    token = login_res.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}, email


def test_notification_creation_and_retrieval(client: TestClient, db_session: Session) -> None:
    headers, email = create_user_and_token(client, "test_notif_create@example.com")
    user = db_session.query(User).filter(User.email == email).first()
    assert user is not None

    # Create notifications via service
    n1 = NotificationService.create_notification(
        db=db_session,
        user_id=user.id,
        notification_type="system",
        title="Welcome to Nexora",
        message="Your account is set up and ready.",
        action_url="/dashboard",
    )
    assert n1 is not None

    n2 = NotificationService.create_notification(
        db=db_session,
        user_id=user.id,
        notification_type="job_freshness_update",
        title="Job Listing Verified",
        message="A saved job has been rechecked.",
        action_url="/dashboard/jobs",
    )
    assert n2 is not None

    # Retrieve via API
    res = client.get("/api/v1/notifications", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["total"] == 2
    assert data["unread_count"] == 2
    assert len(data["items"]) == 2

    # Check unread count endpoint
    unread_res = client.get("/api/v1/notifications/unread-count", headers=headers)
    assert unread_res.status_code == 200
    assert unread_res.json()["unread_count"] == 2


def test_read_and_read_all_operations(client: TestClient, db_session: Session) -> None:
    headers, email = create_user_and_token(client, "test_read_ops@example.com")
    user = db_session.query(User).filter(User.email == email).first()
    assert user is not None

    n1 = NotificationService.create_notification(
        db=db_session,
        user_id=user.id,
        notification_type="task_completion",
        title="Resume Parsed",
        message="Your resume was parsed successfully.",
    )
    n2 = NotificationService.create_notification(
        db=db_session,
        user_id=user.id,
        notification_type="system",
        title="Security Alert",
        message="New session logged in.",
    )
    assert n1 is not None and n2 is not None

    # Mark single as read
    patch_res = client.patch(f"/api/v1/notifications/{n1.id}/read", headers=headers)
    assert patch_res.status_code == 200
    assert patch_res.json()["is_read"] is True
    assert patch_res.json()["read_at"] is not None

    # Unread count should now be 1
    unread_res = client.get("/api/v1/notifications/unread-count", headers=headers)
    assert unread_res.json()["unread_count"] == 1

    # Mark all as read
    read_all_res = client.post("/api/v1/notifications/read-all", headers=headers)
    assert read_all_res.status_code == 200
    assert read_all_res.json()["updated_count"] == 1

    # Unread count should now be 0
    unread_res2 = client.get("/api/v1/notifications/unread-count", headers=headers)
    assert unread_res2.json()["unread_count"] == 0


def test_user_isolation(client: TestClient, db_session: Session) -> None:
    headers_a, email_a = create_user_and_token(client, "user_a_notify@example.com")
    headers_b, email_b = create_user_and_token(client, "user_b_notify@example.com")

    user_a = db_session.query(User).filter(User.email == email_a).first()
    assert user_a is not None

    notif_a = NotificationService.create_notification(
        db=db_session,
        user_id=user_a.id,
        notification_type="system",
        title="User A Only",
        message="Secret notification for A",
    )
    assert notif_a is not None

    # User B lists notifications
    res_b = client.get("/api/v1/notifications", headers=headers_b)
    assert res_b.json()["total"] == 0

    # User B cannot mark User A's notification as read
    patch_res = client.patch(f"/api/v1/notifications/{notif_a.id}/read", headers=headers_b)
    assert patch_res.status_code == 404

    # User B cannot delete User A's notification
    del_res = client.delete(f"/api/v1/notifications/{notif_a.id}", headers=headers_b)
    assert del_res.status_code == 404


def test_preference_get_and_update(client: TestClient) -> None:
    headers, _ = create_user_and_token(client, "pref_user@example.com")

    # Get default preferences
    res = client.get("/api/v1/notifications/preferences", headers=headers)
    assert res.status_code == 200
    pref = res.json()
    assert pref["enable_in_app"] is True
    assert pref["preferred_timezone"] == "UTC"
    assert pref["interview_reminder_24h"] is True
    assert pref["interview_reminder_1h"] is True

    # Update preferences
    update_res = client.put(
        "/api/v1/notifications/preferences",
        json={
            "enable_interview_reminders": False,
            "preferred_timezone": "America/New_York",
            "interview_reminder_1h": False,
        },
        headers=headers,
    )
    assert update_res.status_code == 200
    updated = update_res.json()
    assert updated["enable_interview_reminders"] is False
    assert updated["preferred_timezone"] == "America/New_York"
    assert updated["interview_reminder_1h"] is False

    # Invalid timezone returns 400
    bad_tz_res = client.put(
        "/api/v1/notifications/preferences",
        json={"preferred_timezone": "Mars/Olympus_Mons"},
        headers=headers,
    )
    assert bad_tz_res.status_code == 400


def test_disabling_category_prevents_future_notifications(
    client: TestClient, db_session: Session
) -> None:
    headers, email = create_user_and_token(client, "disable_cat@example.com")
    user = db_session.query(User).filter(User.email == email).first()
    assert user is not None

    # Disable deadline reminders
    client.put(
        "/api/v1/notifications/preferences",
        json={"enable_deadline_reminders": False},
        headers=headers,
    )

    # Attempt to create deadline notification
    notif = NotificationService.create_notification(
        db=db_session,
        user_id=user.id,
        notification_type="application_deadline",
        title="Deadline",
        message="This should be skipped.",
    )
    assert notif is None

    # Notifications list should remain empty
    res = client.get("/api/v1/notifications", headers=headers)
    assert res.json()["total"] == 0


def test_reminder_scheduling_and_intervals(client: TestClient, db_session: Session) -> None:
    headers, email = create_user_and_token(client, "reminder_sched@example.com")
    user = db_session.query(User).filter(User.email == email).first()
    assert user is not None

    # Configure timezone
    client.put(
        "/api/v1/notifications/preferences",
        json={"preferred_timezone": "America/New_York"},
        headers=headers,
    )

    now = datetime.now(timezone.utc)

    # Create an application
    app = JobApplication(
        user_id=user.id,
        title="Backend Engineer",
        company_name="Stripe",
        status="interview",
        application_channel="official_portal",
        deadline_at=now + timedelta(hours=12),
        next_follow_up_at=now + timedelta(hours=8),
    )
    db_session.add(app)
    db_session.commit()

    # Create an interview scheduled in 24 hours (within 24h window [22h, 24h15m])
    iv = ApplicationInterview(
        application_id=app.id,
        user_id=user.id,
        round_number=2,
        interview_type="technical",
        title="Systems & Coding Round",
        scheduled_at=now + timedelta(hours=24),
        duration_minutes=60,
        status="scheduled",
    )
    db_session.add(iv)
    db_session.commit()

    # Trigger process reminders
    proc_res = client.post("/api/v1/notifications/process-reminders", headers=headers)
    assert proc_res.status_code == 200
    res_data = proc_res.json()
    assert res_data["reminders_created"] >= 2  # Interview 24h + Deadline + Follow-up

    # Check notification contents
    notifs_res = client.get("/api/v1/notifications", headers=headers)
    notifs = notifs_res.json()["items"]
    types = [n["notification_type"] for n in notifs]
    assert "interview_reminder" in types
    assert "application_deadline" in types
    assert "application_follow_up" in types

    # Verify timezone citation in message
    iv_notif = next(n for n in notifs if n["notification_type"] == "interview_reminder")
    assert "America/New_York" in iv_notif["message"]


def test_duplicate_prevention_idempotency(client: TestClient, db_session: Session) -> None:
    headers, email = create_user_and_token(client, "idemp_test@example.com")
    user = db_session.query(User).filter(User.email == email).first()
    assert user is not None

    now = datetime.now(timezone.utc)
    app = JobApplication(
        user_id=user.id,
        title="Full Stack Engineer",
        company_name="Linear",
        status="interview",
        application_channel="official_portal",
    )
    db_session.add(app)
    db_session.commit()

    iv = ApplicationInterview(
        application_id=app.id,
        user_id=user.id,
        round_number=1,
        interview_type="technical",
        title="Initial Screen",
        scheduled_at=now + timedelta(hours=24),
        status="scheduled",
    )
    db_session.add(iv)
    db_session.commit()

    # First run creates notification
    res1 = client.post("/api/v1/notifications/process-reminders", headers=headers)
    assert res1.json()["reminders_created"] == 1

    # Second run immediately following must NOT create duplicates
    res2 = client.post("/api/v1/notifications/process-reminders", headers=headers)
    assert res2.json()["reminders_created"] == 0

    # Total notifications must remain exactly 1
    list_res = client.get("/api/v1/notifications", headers=headers)
    assert list_res.json()["total"] == 1


def test_cancelled_and_completed_event_exclusions(client: TestClient, db_session: Session) -> None:
    headers, email = create_user_and_token(client, "exclusions_test@example.com")
    user = db_session.query(User).filter(User.email == email).first()
    assert user is not None

    now = datetime.now(timezone.utc)

    # Cancelled Application
    rej_app = JobApplication(
        user_id=user.id,
        title="Frontend Dev",
        company_name="Old Corp",
        status="rejected",
        application_channel="official_portal",
        deadline_at=now + timedelta(hours=5),
        next_follow_up_at=now + timedelta(hours=5),
    )
    # Cancelled Interview
    active_app = JobApplication(
        user_id=user.id,
        title="DevOps Engineer",
        company_name="Cloud Corp",
        status="applied",
        application_channel="official_portal",
    )
    db_session.add_all([rej_app, active_app])
    db_session.commit()

    cancelled_iv = ApplicationInterview(
        application_id=active_app.id,
        user_id=user.id,
        round_number=1,
        interview_type="technical",
        title="Screen",
        scheduled_at=now + timedelta(hours=3),
        status="cancelled",
    )
    completed_iv = ApplicationInterview(
        application_id=active_app.id,
        user_id=user.id,
        round_number=2,
        interview_type="technical",
        title="Final",
        scheduled_at=now + timedelta(hours=3),
        status="completed",
        outcome="passed",
    )
    db_session.add_all([cancelled_iv, completed_iv])
    db_session.commit()

    # Process reminders
    proc_res = client.post("/api/v1/notifications/process-reminders", headers=headers)
    assert proc_res.status_code == 200
    assert proc_res.json()["reminders_created"] == 0

    list_res = client.get("/api/v1/notifications", headers=headers)
    assert list_res.json()["total"] == 0


def test_delete_notification(client: TestClient, db_session: Session) -> None:
    headers, email = create_user_and_token(client, "del_notif@example.com")
    user = db_session.query(User).filter(User.email == email).first()
    assert user is not None

    n = NotificationService.create_notification(
        db=db_session,
        user_id=user.id,
        notification_type="system",
        title="To Delete",
        message="Will be deleted soon.",
    )
    assert n is not None

    del_res = client.delete(f"/api/v1/notifications/{n.id}", headers=headers)
    assert del_res.status_code == 200

    # Ensure removed
    list_res = client.get("/api/v1/notifications", headers=headers)
    assert list_res.json()["total"] == 0


def test_celery_task_execution() -> None:
    """Test Celery reminder task runs directly without error."""
    result = process_scheduled_reminders_task.apply()
    assert result.status == "SUCCESS"
    data = result.result
    assert data["status"] == "success"
    assert "reminders_created" in data


def test_event_30_minutes_away_does_not_trigger_24h_reminder(
    client: TestClient, db_session: Session
) -> None:
    """An event 30 minutes away must trigger 1h reminder but NEVER 24h reminder."""
    headers, email = create_user_and_token(client, "thirty_min@example.com")
    user = db_session.query(User).filter(User.email == email).first()
    assert user is not None

    now = datetime.now(timezone.utc)
    app = JobApplication(
        user_id=user.id,
        title="Backend Engineer",
        company_name="Cloudflare",
        status="interview",
        application_channel="official_portal",
    )
    db_session.add(app)
    db_session.commit()

    # Interview 30 minutes away
    iv = ApplicationInterview(
        application_id=app.id,
        user_id=user.id,
        round_number=1,
        interview_type="technical",
        title="Technical Screen",
        scheduled_at=now + timedelta(minutes=30),
        status="scheduled",
    )
    # Assessment 30 minutes away
    assessment = ApplicationInterview(
        application_id=app.id,
        user_id=user.id,
        round_number=2,
        interview_type="take_home",
        title="Coding Assessment",
        scheduled_at=now + timedelta(minutes=30),
        status="scheduled",
    )
    db_session.add_all([iv, assessment])
    db_session.commit()

    # Process reminders
    proc_res = client.post("/api/v1/notifications/process-reminders", headers=headers)
    assert proc_res.status_code == 200

    notifs = db_session.query(Notification).filter(Notification.user_id == user.id).all()
    # Exactly two 1h reminders created (one for interview, one for assessment)
    assert len(notifs) == 2

    idempotency_keys = [n.idempotency_key for n in notifs]
    # Verify 1h keys are present
    assert f"reminder:interview_reminder:1h:{iv.id}" in idempotency_keys
    assert f"reminder:assessment_reminder:1h:{assessment.id}" in idempotency_keys

    # Crucial assertion: 24h reminder keys must NEVER be generated for 30m events
    assert f"reminder:interview_reminder:24h:{iv.id}" not in idempotency_keys
    assert f"reminder:assessment_reminder:24h:{assessment.id}" not in idempotency_keys

    for n in notifs:
        assert n.metadata_json.get("interval") == "1h"


def test_event_24_hours_away_triggers_only_24h_reminder(
    client: TestClient, db_session: Session
) -> None:
    """An event ~24 hours away triggers only the 24-hour reminder, not the 1-hour."""
    headers, email = create_user_and_token(client, "twenty_four_hr@example.com")
    user = db_session.query(User).filter(User.email == email).first()
    assert user is not None

    now = datetime.now(timezone.utc)
    app = JobApplication(
        user_id=user.id,
        title="Systems Engineer",
        company_name="Datadog",
        status="interview",
        application_channel="official_portal",
    )
    db_session.add(app)
    db_session.commit()

    # Interview exactly 24 hours away
    iv = ApplicationInterview(
        application_id=app.id,
        user_id=user.id,
        round_number=1,
        interview_type="technical",
        title="Architecture Discussion",
        scheduled_at=now + timedelta(hours=24),
        status="scheduled",
    )
    db_session.add(iv)
    db_session.commit()

    proc_res = client.post("/api/v1/notifications/process-reminders", headers=headers)
    assert proc_res.status_code == 200

    notifs = db_session.query(Notification).filter(Notification.user_id == user.id).all()
    assert len(notifs) == 1

    notif = notifs[0]
    assert notif.idempotency_key == f"reminder:interview_reminder:24h:{iv.id}"
    assert notif.metadata_json.get("interval") == "24h"
    assert "Upcoming Interview" in notif.title


def test_event_1_hour_away_triggers_only_1h_reminder(
    client: TestClient, db_session: Session
) -> None:
    """An event ~1 hour away triggers only the 1-hour reminder."""
    headers, email = create_user_and_token(client, "one_hr@example.com")
    user = db_session.query(User).filter(User.email == email).first()
    assert user is not None

    now = datetime.now(timezone.utc)
    app = JobApplication(
        user_id=user.id,
        title="Platform Engineer",
        company_name="Figma",
        status="interview",
        application_channel="official_portal",
    )
    db_session.add(app)
    db_session.commit()

    # Interview 55 minutes away
    iv = ApplicationInterview(
        application_id=app.id,
        user_id=user.id,
        round_number=1,
        interview_type="technical",
        title="Pair Programming",
        scheduled_at=now + timedelta(minutes=55),
        status="scheduled",
    )
    db_session.add(iv)
    db_session.commit()

    proc_res = client.post("/api/v1/notifications/process-reminders", headers=headers)
    assert proc_res.status_code == 200

    notifs = db_session.query(Notification).filter(Notification.user_id == user.id).all()
    assert len(notifs) == 1

    notif = notifs[0]
    assert notif.idempotency_key == f"reminder:interview_reminder:1h:{iv.id}"
    assert notif.metadata_json.get("interval") == "1h"
    assert "less than an hour" in notif.message


def test_missed_execution_recovery(client: TestClient, db_session: Session) -> None:
    """Ensure missed executions within the grace period are recovered properly."""
    headers, email = create_user_and_token(client, "recovery_test@example.com")
    user = db_session.query(User).filter(User.email == email).first()
    assert user is not None

    now = datetime.now(timezone.utc)
    app = JobApplication(
        user_id=user.id,
        title="Infrastructure Lead",
        company_name="Vercel",
        status="interview",
        application_channel="official_portal",
    )
    db_session.add(app)
    db_session.commit()

    # Worker was offline when the 24h mark hit; now it's 22.5 hours away (within 2h grace window)
    iv_24h_missed = ApplicationInterview(
        application_id=app.id,
        user_id=user.id,
        round_number=1,
        interview_type="technical",
        title="Tech Screen",
        scheduled_at=now + timedelta(hours=22, minutes=30),
        status="scheduled",
    )
    # Worker was offline when 1h mark hit; now it's 20 minutes away (within 1h grace window)
    iv_1h_missed = ApplicationInterview(
        application_id=app.id,
        user_id=user.id,
        round_number=2,
        interview_type="behavioral",
        title="Manager Chat",
        scheduled_at=now + timedelta(minutes=20),
        status="scheduled",
    )
    db_session.add_all([iv_24h_missed, iv_1h_missed])
    db_session.commit()

    proc_res = client.post("/api/v1/notifications/process-reminders", headers=headers)
    assert proc_res.status_code == 200

    notifs = db_session.query(Notification).filter(Notification.user_id == user.id).all()
    assert len(notifs) == 2

    idemp_keys = [n.idempotency_key for n in notifs]
    assert f"reminder:interview_reminder:24h:{iv_24h_missed.id}" in idemp_keys
    assert f"reminder:interview_reminder:1h:{iv_1h_missed.id}" in idemp_keys


def test_events_started_or_completed_do_not_receive_reminders(
    client: TestClient, db_session: Session
) -> None:
    """Events in the past (delta <= 0) or completed/cancelled must not receive reminders."""
    headers, email = create_user_and_token(client, "past_events@example.com")
    user = db_session.query(User).filter(User.email == email).first()
    assert user is not None

    now = datetime.now(timezone.utc)
    app = JobApplication(
        user_id=user.id,
        title="Data Engineer",
        company_name="Snowflake",
        status="interview",
        application_channel="official_portal",
    )
    db_session.add(app)
    db_session.commit()

    # Event started 5 minutes ago
    past_iv = ApplicationInterview(
        application_id=app.id,
        user_id=user.id,
        round_number=1,
        interview_type="technical",
        title="Past Interview",
        scheduled_at=now - timedelta(minutes=5),
        status="scheduled",
    )
    # Event cancelled
    cancelled_iv = ApplicationInterview(
        application_id=app.id,
        user_id=user.id,
        round_number=2,
        interview_type="technical",
        title="Cancelled Interview",
        scheduled_at=now + timedelta(hours=24),
        status="cancelled",
    )
    # Event completed
    completed_iv = ApplicationInterview(
        application_id=app.id,
        user_id=user.id,
        round_number=3,
        interview_type="technical",
        title="Completed Interview",
        scheduled_at=now + timedelta(minutes=45),
        status="completed",
        outcome="passed",
    )
    db_session.add_all([past_iv, cancelled_iv, completed_iv])
    db_session.commit()

    proc_res = client.post("/api/v1/notifications/process-reminders", headers=headers)
    assert proc_res.status_code == 200
    assert proc_res.json()["reminders_created"] == 0

    notifs = db_session.query(Notification).filter(Notification.user_id == user.id).all()
    assert len(notifs) == 0


def test_concurrent_execution_idempotency(client: TestClient, db_session: Session) -> None:
    """Idempotency keys and DB constraints gracefully prevent duplicate inserts."""
    _, email = create_user_and_token(client, "concurrent_test@example.com")
    user = db_session.query(User).filter(User.email == email).first()
    assert user is not None

    test_key = f"concurrent-test-key-{uuid4()}"

    # First attempt: successfully creates record
    notif1, created1 = NotificationService.create_notification_record(
        db=db_session,
        user_id=user.id,
        notification_type="system",
        title="Test Title",
        message="Test Message",
        idempotency_key=test_key,
    )
    assert created1 is True
    assert notif1 is not None

    # Second attempt (simulating concurrent worker or retry): returns existing record
    notif2, created2 = NotificationService.create_notification_record(
        db=db_session,
        user_id=user.id,
        notification_type="system",
        title="Test Title",
        message="Test Message",
        idempotency_key=test_key,
    )
    assert created2 is False
    assert notif2.id == notif1.id

    # Database count must be exactly 1
    count = db_session.query(Notification).filter(Notification.idempotency_key == test_key).count()
    assert count == 1
