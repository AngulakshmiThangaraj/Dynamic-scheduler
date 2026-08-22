import pytest
from datetime import datetime, timedelta
from fastapi.testclient import TestClient
from backend.main import app
from backend.database.schema import SessionLocal, Base, engine, User, Conflict
from backend.database.seed import seed_database
from backend.services.scheduling_engine import SchedulingEngine

client = TestClient(app)

def get_next_weekday_str():
    dt = datetime.now()
    while dt.weekday() >= 5:  # 5=Sat, 6=Sun
        dt += timedelta(days=1)
    return dt.strftime("%Y-%m-%d")

@pytest.fixture(scope="module", autouse=True)
def setup_test_database():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    seed_database()
    db = SessionLocal()
    yield db
    db.close()

def test_user_auth_and_roles(setup_test_database):
    response = client.post("/api/auth/login", json={
        "email": "admin@company.com",
        "password": "admin123"
    })
    assert response.status_code == 200, response.text
    data = response.json()
    assert "access_token" in data
    assert data["user"]["role"] == "ADMIN"

def test_event_crud_and_conflict_detection(setup_test_database):
    login_res = client.post("/api/auth/login", json={
        "email": "organizer@company.com",
        "password": "org123"
    }).json()
    assert "access_token" in login_res, login_res
    headers = {"Authorization": f"Bearer {login_res['access_token']}"}

    weekday_str = get_next_weekday_str()

    ev_a = client.post("/api/events", headers=headers, json={
        "title": "Strategy Meeting A",
        "description": "Primary meeting",
        "date": weekday_str,
        "start_time": "15:30",
        "end_time": "16:30",
        "duration": 60,
        "priority": "HIGH",
        "buffer_time": 0,
        "participants": [{"user_id": login_res["user"]["id"]}]
    })
    assert ev_a.status_code == 200, ev_a.text
    assert ev_a.json()["status"] == "SCHEDULED"

    ev_b = client.post("/api/events", headers=headers, json={
        "title": "Strategy Meeting B",
        "description": "Conflicting meeting",
        "date": weekday_str,
        "start_time": "16:00",
        "end_time": "17:00",
        "duration": 60,
        "priority": "HIGH",
        "participants": [{"user_id": login_res["user"]["id"]}]
    })
    assert ev_b.status_code == 200, ev_b.text
    b_json = ev_b.json()
    assert b_json["status"] == "CONFLICTED"
    assert len(b_json["conflicts"]) > 0
    assert any(c["type"] == "PARTICIPANT_CONFLICT" for c in b_json["conflicts"])

def test_smart_optimizer_scoring(setup_test_database):
    db = setup_test_database
    engine = SchedulingEngine(db)

    user = db.query(User).filter(User.role == "ORGANIZER").first()
    assert user is not None
    weekday_str = get_next_weekday_str()

    recommendations = engine.optimize_schedule(
        event_id=None,
        date_str=weekday_str,
        duration=60,
        participant_ids=[user.id],
        preferred_time="10:00"
    )

    assert len(recommendations) > 0
    best_slot = recommendations[0]
    assert "score" in best_slot
    assert best_slot["score"] > 50.0
    assert "reasons" in best_slot

def test_what_if_simulation(setup_test_database):
    db = setup_test_database
    engine = SchedulingEngine(db)

    user = db.query(User).first()
    assert user is not None
    weekday_str = get_next_weekday_str()

    sim = engine.simulate_schedule_change(
        event_id=None,
        proposed_date=weekday_str,
        proposed_start="09:00",
        proposed_end="10:00",
        proposed_participant_ids=[user.id]
    )

    assert sim["success"] is True
    assert "compatibilityScore" in sim

def test_automatic_resolution_and_cascading(setup_test_database):
    db = setup_test_database
    engine = SchedulingEngine(db)

    conflict = db.query(Conflict).filter(Conflict.is_resolved == False).first()
    if conflict:
        admin = db.query(User).filter(User.role == "ADMIN").first()
        res = engine.resolve_conflict_auto(conflict.id, admin.id)
        assert res["success"] is True
        assert "resolvedSlot" in res
