import pytest
from app import create_app, db
from app.models import Assessment, CompetencyFramework, Course, Department, Enrollment, Institution, JobRole, Question, Role, RoleSkillRequirement, ScenarioLab, Skill, User, UserSkill


class TestConfig:
    TESTING = True
    SECRET_KEY = "test"
    JWT_SECRET_KEY = "test"
    SQLALCHEMY_DATABASE_URI = "sqlite://"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    CORS_ORIGINS = ["http://localhost:5173"]


@pytest.fixture()
def client():
    app = create_app(TestConfig)
    with app.app_context():
        db.create_all()
        learner_role = Role(name="Employee/Learner", description="Learner")
        trainer_role = Role(name="Trainer", description="Trainer")
        institution = Institution(name="Test MoES Institution", code="TMI", location="Delhi")
        db.session.add_all([learner_role, trainer_role, institution]); db.session.flush()
        department = Department(name="Forecasting", institution=institution)
        job = JobRole(title="Test Forecaster", domain="Weather", description="Forecasts")
        db.session.add_all([department, job]); db.session.flush()
        learner = User(name="Test Learner", email="learner@test.in", employee_id="T-1", role=learner_role, institution=institution, department=department, job_role=job); learner.set_password("Demo@123")
        trainer = User(name="Test Trainer", email="trainer@test.in", employee_id="T-2", role=trainer_role, institution=institution, department=department, job_role=job); trainer.set_password("Demo@123")
        skill = Skill(name="Test Radar", domain="Weather", description="Test skill", importance=5)
        db.session.add_all([learner, trainer, skill]); db.session.flush()
        framework = CompetencyFramework(name="Test framework", job_role=job)
        db.session.add(framework); db.session.flush()
        db.session.add_all([RoleSkillRequirement(framework=framework, skill=skill, required_level=4, criticality="critical"), UserSkill(user=learner, skill=skill, level=2, verified=False)])
        course = Course(title="Test course", description="A relevant test course", domain="Weather", level="Foundation", duration_hours=2, skill_ids=[skill.id], trainer=trainer)
        db.session.add(course); db.session.flush(); db.session.add(Enrollment(user=learner, course=course, progress=20))
        assessment = Assessment(course=course, title="Test knowledge check", minutes=10, pass_score=70)
        db.session.add(assessment); db.session.flush()
        db.session.add(Question(assessment=assessment, prompt="What is the approved action?", options=["Document evidence", "Ignore the guide"], correct_answer="Document evidence"))
        db.session.add(ScenarioLab(title="Test response", domain="Weather", situation="Choose.", competency_ids=[skill.id], decisions=[{"id":"safe", "label":"Safe", "score":100, "consequence":"Good", "explanation":"Correct", "improvement":"Continue"}]))
        db.session.commit()
        yield app.test_client()
        db.session.remove(); db.drop_all()


def login(client, email="learner@test.in"):
    response = client.post("/api/auth/login", json={"email": email, "password": "Demo@123"})
    return {"Authorization": f"Bearer {response.get_json()['accessToken']}"}


def test_login_and_role_scoped_dashboard(client):
    response = client.post("/api/auth/login", json={"email": "learner@test.in", "password": "Demo@123"})
    assert response.status_code == 200
    dashboard = client.get("/api/dashboard", headers=login(client))
    assert dashboard.status_code == 200
    assert dashboard.get_json()["metrics"]["activeCourses"] == 1


def test_skill_gap_explains_calculation(client):
    # The analysis workspace loads this read-only resource with GET.
    response = client.get("/api/skills/analyze", headers=login(client))
    assert response.status_code == 200
    body = response.get_json()
    assert body["analysis"]["gapScore"] == 40
    assert body["recommendations"][0]["skill"] == "Test Radar"
    assert "advisory" in body["disclaimer"]


def test_course_progress_and_certificate_path(client):
    response = client.post("/api/courses/1/progress", headers=login(client), json={"progress": 100})
    assert response.status_code == 200
    assert response.get_json()["status"] == "completed"


def test_evidence_review_requires_authorized_role(client):
    response = client.post("/api/evidence/99/review", headers=login(client), json={"decision": "approved"})
    assert response.status_code == 403


def test_employee_onboarding_and_assessment_path(client):
    options = client.get("/api/onboarding/options").get_json()
    registration = client.post("/api/auth/register", json={"fullName": "New Employee", "officialEmail": "new.employee@test.in", "password": "Demo@123", "role": "Employee/New Trainee"})
    assert registration.status_code == 201
    headers = {"Authorization": f"Bearer {registration.get_json()['accessToken']}"}
    profile = client.put("/api/onboarding", headers=headers, json={
        "fullName": "New Employee", "employeeId": "T-3", "institutionId": options["institutions"][0]["id"],
        "departmentId": options["departments"][0]["id"], "jobRoleId": options["jobRoles"][0]["id"],
        "designation": "Forecasting Officer", "workLocation": "Delhi", "employmentType": "New trainee",
        "availableTimes": {"days": ["Tuesday"], "time": "16:00–18:00"}, "hoursPerWeek": 4,
        "skills": [{"skillId": options["skills"][0]["id"], "level": 2}],
    })
    assert profile.status_code == 200 and profile.get_json()["onboardingComplete"] is True
    assert client.get("/api/skill-gaps", headers=headers).status_code == 200
    assert client.get("/api/learning-plan", headers=headers).status_code == 200
    assessment = client.get("/api/assessments", headers=headers).get_json()["assessments"][0]
    answer = assessment["questions"][0]
    attempt = client.post(f"/api/assessments/{assessment['id']}/attempt", headers=headers, json={"answers": {str(answer["id"]): "Document evidence"}})
    assert attempt.status_code == 200 and attempt.get_json()["passed"] is True


def test_employee_can_type_a_new_department_and_job_role(client):
    options = client.get("/api/onboarding/options").get_json()
    registration = client.post("/api/auth/register", json={"fullName": "Digital Employee", "officialEmail": "digital.employee@test.in", "password": "Demo@123", "role": "Employee/New Trainee"})
    headers = {"Authorization": f"Bearer {registration.get_json()['accessToken']}"}
    profile = client.put("/api/onboarding", headers=headers, json={
        "fullName": "Digital Employee", "employeeId": "T-4", "institutionName": "Digital Innovation Centre",
        "departmentName": "Digital Transformation Lab", "jobRoleName": "Frontend Developer",
        "designation": "Junior Frontend Developer", "workLocation": "Chennai",
        "availableTimes": {"days": ["Friday"], "time": "12:00–14:00"},
        "skills": [{"skillId": -1203, "name": "React Development", "domain": "Software Development", "level": 3}],
    })
    assert profile.status_code == 200 and profile.get_json()["onboardingComplete"] is True
    me = client.get("/api/me", headers=headers).get_json()
    assert me["institution"] == "Digital Innovation Centre"
    assert me["department"] == "Digital Transformation Lab"
    assert me["jobRole"] == "Frontend Developer"
    saved_skills = client.get("/api/onboarding", headers=headers).get_json()["skills"]
    assert any(item["name"] == "React Development" and item["level"] == 3 for item in saved_skills)
    evidence = client.post("/api/evidence", headers=headers, json={"skillName": "Accessibility review", "skillDomain": "Software Development", "title": "Keyboard accessibility review", "type": "practical task"})
    assert evidence.status_code == 201
    mentors = client.get("/api/mentors", headers=headers).get_json()
    assert mentors["roleMatched"] is True
    assert mentors["role"] == "Frontend Developer"
    assert all("Weather" not in mentor["bio"] for mentor in mentors["mentors"])


def test_role_matched_six_week_course_and_certificate_download(client):
    registration = client.post("/api/auth/register", json={"fullName": "Frontend Learner", "officialEmail": "frontend.learner@test.in", "password": "Demo@123", "role": "Employee/New Trainee"})
    headers = {"Authorization": f"Bearer {registration.get_json()['accessToken']}"}
    profile = client.put("/api/onboarding", headers=headers, json={
        "fullName": "Frontend Learner", "employeeId": "T-5", "institutionName": "Digital Innovation Centre",
        "departmentName": "Web Experience", "jobRoleName": "Frontend Developer", "designation": "Frontend Developer",
        "workLocation": "Chennai", "availableTimes": {"days": ["Friday"], "time": "12:00-14:00"},
        "skills": [{"skillId": -1203, "name": "React Development", "domain": "Software Development", "level": 2}],
    })
    assert profile.status_code == 200
    catalogue = client.get("/api/courses", headers=headers).get_json()
    assert catalogue["roleTrack"] is True
    assert len(catalogue["courses"]) == 1
    course = catalogue["courses"][0]
    assert "Frontend" in course["title"]
    assert len(course["modules"]) == 6
    assert all(len(module["lessons"]) == 5 for module in course["modules"])

    assert client.post(f"/api/courses/{course['id']}/enroll", headers=headers).status_code == 201
    first_lesson = course["modules"][0]["lessons"][0]
    lesson_completion = client.post(f"/api/courses/{course['id']}/lessons/{first_lesson['id']}/complete", headers=headers)
    assert lesson_completion.status_code == 200
    assert lesson_completion.get_json()["completedWeeks"] == 0
    completion = client.post(f"/api/courses/{course['id']}/progress", headers=headers, json={"progress": 100})
    assert completion.status_code == 200
    assert "final quiz" in completion.get_json()["message"].lower()

    quiz = client.get("/api/assessments", headers=headers).get_json()["assessments"][0]
    answers = {str(question["id"]): question["options"][0] for question in quiz["questions"]}
    passed = client.post(f"/api/assessments/{quiz['id']}/attempt", headers=headers, json={"answers": answers})
    assert passed.status_code == 200 and passed.get_json()["certificateIssued"] is True

    certificates = client.get("/api/certificates", headers=headers).get_json()["certificates"]
    assert len(certificates) == 1
    download = client.get(certificates[0]["downloadUrl"])
    assert download.status_code == 200
    assert download.content_type == "application/pdf"
    assert download.data.startswith(b"%PDF")
