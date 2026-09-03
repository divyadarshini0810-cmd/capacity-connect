"""Create realistic, demo-safe MoES-style data. Run: python seed.py"""
from datetime import datetime
from app import create_app, db
from app.models import (Assessment, Certificate, CommunityPost, CompetencyFramework, Course, Department,
                        EmployeeProfile, Enrollment, Institution, JobRole, KnowledgeChunk, KnowledgeDocument,
                        LearningPath, Lesson, MentorProfile, Module, Notification, Question, Role,
                        RoleSkillRequirement, ScenarioLab, Skill, User, UserSkill)

app = create_app()


def add_user(name, email, employee_id, role, institution, department, job_role, password="Demo@123"):
    user = User(name=name, email=email, employee_id=employee_id, role=role, institution=institution, department=department, job_role=job_role, experience_years=6, ai_consent=True)
    user.set_password(password)
    db.session.add(user)
    return user


with app.app_context():
    db.drop_all()
    db.create_all()
    role_map = {}
    for name, description in [
        ("Employee/Learner", "Builds verified competencies through learning and evidence."),
        ("Trainer", "Creates and evaluates structured learning."),
        ("Subject-Matter Expert/Mentor", "Reviews evidence and preserves expert knowledge."),
        ("Manager/Department Head", "Guides team readiness and capacity building."),
        ("Organization Administrator", "Manages competency frameworks and institutional learning."),
        ("Super Administrator", "Maintains organization-wide platform governance."),
    ]:
        role_map[name] = Role(name=name, description=description); db.session.add(role_map[name])
    imd = Institution(name="India Meteorological Department", code="IMD", location="New Delhi")
    incois = Institution(name="Indian National Centre for Ocean Information Services", code="INCOIS", location="Hyderabad")
    ncess = Institution(name="National Centre for Earth Science Studies", code="NCESS", location="Thiruvananthapuram")
    db.session.add_all([imd, incois, ncess]); db.session.flush()
    weather = Department(name="Weather Forecasting", institution=imd); ocean = Department(name="Ocean Services", institution=incois); hazards = Department(name="Natural Hazards", institution=ncess)
    db.session.add_all([weather, ocean, hazards])
    meteorologist = JobRole(title="Forecast Meteorologist", domain="Weather & Climate", description="Interprets observations and communicates impact-based forecasts.")
    ocean_scientist = JobRole(title="Ocean Data Scientist", domain="Ocean Science", description="Assures quality and interprets operational ocean observations.")
    seismologist = JobRole(title="Seismology Analyst", domain="Natural Hazards", description="Processes earthquake observations and supports public information workflows.")
    training_administrator = JobRole(title="Training Administrator", domain="Organizational Development", description="Coordinates employee development, course operations, and competency reporting.")
    db.session.add_all([meteorologist, ocean_scientist, seismologist, training_administrator]); db.session.flush()
    learner = add_user("Aarav Nair", "learner@capacityconnect.in", "IMD-1042", role_map["Employee/Learner"], imd, weather, meteorologist)
    trainer = add_user("Dr. Meera Shah", "trainer@capacityconnect.in", "IMD-0208", role_map["Trainer"], imd, weather, meteorologist)
    expert = add_user("Dr. Kabir Menon", "expert@capacityconnect.in", "INCOIS-0031", role_map["Subject-Matter Expert/Mentor"], incois, ocean, ocean_scientist)
    manager = add_user("Ananya Rao", "manager@capacityconnect.in", "IMD-0009", role_map["Manager/Department Head"], imd, weather, meteorologist)
    admin = add_user("Rishi Iyer", "admin@capacityconnect.in", "MOES-0014", role_map["Organization Administrator"], ncess, hazards, training_administrator)
    super_admin = add_user("Platform Administrator", "superadmin@capacityconnect.in", "MOES-0001", role_map["Super Administrator"], ncess, hazards, seismologist)
    db.session.add_all([learner, trainer, expert, manager, admin, super_admin]); db.session.flush()
    db.session.add_all([
        EmployeeProfile(user=learner, designation="Weather Officer", work_location="New Delhi", employment_type="Permanent", joining_date=datetime(2021, 7, 12).date(), reporting_manager="Ananya Rao", responsibilities="Prepare forecast guidance and communicate risk to response partners.", certifications_resume="Basic weather forecasting certificate; operational radar workshop.", languages_known=["English", "Hindi"], target_skills=["Impact-based Forecasting", "Radar Meteorology"], development_goals="Lead reliable severe-weather briefings this monsoon.", available_times={"days": ["Tuesday", "Thursday"], "time": "16:00–18:00"}, hours_per_week=5, preferred_training_language="English", learning_preference="Blended", onboarding_complete=True),
        EmployeeProfile(user=trainer, designation="Training Scientist", work_location="New Delhi", employment_type="Permanent", joining_date=datetime(2012, 6, 1).date(), reporting_manager="Director, Forecasting", responsibilities="Create learning experiences and coach operational staff.", languages_known=["English", "Hindi"], available_times={"days": ["Tuesday", "Thursday"], "time": "14:00–17:00"}, hours_per_week=6, preferred_training_language="English", learning_preference="Blended", onboarding_complete=True),
        EmployeeProfile(user=expert, designation="Ocean Observation Specialist", work_location="Hyderabad", employment_type="Permanent", joining_date=datetime(2011, 3, 9).date(), reporting_manager="Ocean Services Lead", responsibilities="Review ocean data quality and mentor analysts.", languages_known=["English", "Malayalam"], available_times={"days": ["Wednesday"], "time": "10:00–12:00"}, hours_per_week=4, preferred_training_language="English", learning_preference="Online", onboarding_complete=True),
        EmployeeProfile(user=manager, designation="Forecasting Manager", work_location="New Delhi", employment_type="Permanent", joining_date=datetime(2008, 4, 14).date(), reporting_manager="IMD Operations Director", responsibilities="Set team development priorities and monitor operational readiness.", languages_known=["English", "Hindi"], available_times={"days": ["Monday", "Friday"], "time": "15:00–16:00"}, hours_per_week=3, preferred_training_language="English", learning_preference="Blended", onboarding_complete=True),
        EmployeeProfile(user=admin, designation="Learning Operations Administrator", work_location="Thiruvananthapuram", employment_type="Permanent", joining_date=datetime(2017, 9, 20).date(), reporting_manager="MoES Capacity Lead", responsibilities="Manage organizational learning records, roles, and competency frameworks.", languages_known=["English", "Malayalam"], target_skills=["Project Management", "Professional Communication"], available_times={"days": ["Wednesday"], "time": "14:00–16:00"}, hours_per_week=4, preferred_training_language="English", learning_preference="Online", onboarding_complete=True),
        EmployeeProfile(user=super_admin, designation="Platform Governance Lead", work_location="Thiruvananthapuram", employment_type="Permanent", joining_date=datetime(2010, 1, 1).date(), reporting_manager="MoES Digital Lead", responsibilities="Maintain platform governance and reporting.", languages_known=["English"], available_times={"days": ["Friday"], "time": "11:00–12:00"}, hours_per_week=2, preferred_training_language="English", learning_preference="Online", onboarding_complete=True),
    ])

    raw_skills = [
        ("Radar Meteorology", "Weather & Climate", 5), ("Numerical Weather Prediction", "Weather & Climate", 5), ("Satellite Image Interpretation", "Weather & Climate", 4), ("Impact-based Forecasting", "Weather & Climate", 5),
        ("Climate Data Analysis", "Weather & Climate", 4), ("Ocean Data Quality", "Ocean Science", 5), ("Wave Modelling", "Ocean Science", 4), ("Tsunami Warning Operations", "Ocean Science", 5),
        ("GIS for Earth Science", "Data & Digital", 4), ("Python for Geoscience", "Data & Digital", 5), ("Remote Sensing", "Data & Digital", 4), ("Research Data Management", "Data & Digital", 4),
        ("Seismic Signal Analysis", "Natural Hazards", 5), ("Earthquake Information Workflow", "Natural Hazards", 5), ("Field Safety", "Field Research", 4), ("Hydrological Modelling", "Hydrology", 4), ("Project Management", "Organizational Development", 4), ("Professional Communication", "Organizational Development", 4),
        ("Risk Communication", "Operations", 5), ("Scientific Writing", "Research", 3), ("Open-source Reproducibility", "Data & Digital", 4), ("Polar Observation", "Polar Research", 3), ("Incident Coordination", "Operations", 4),
    ]
    skills = {name: Skill(name=name, domain=domain, importance=importance, description=f"Applied {name.lower()} competency for Earth-science operations.") for name, domain, importance in raw_skills}
    db.session.add_all(skills.values()); db.session.flush()
    links = {"Radar Meteorology": ["Satellite Image Interpretation", "Numerical Weather Prediction", "Impact-based Forecasting"], "Numerical Weather Prediction": ["Python for Geoscience", "Climate Data Analysis"], "Impact-based Forecasting": ["Risk Communication", "Incident Coordination"], "Ocean Data Quality": ["Research Data Management", "Python for Geoscience", "Wave Modelling"], "Tsunami Warning Operations": ["Seismic Signal Analysis", "Risk Communication"], "Seismic Signal Analysis": ["Earthquake Information Workflow", "GIS for Earth Science"]}
    for name, related in links.items(): skills[name].related_skill_ids = [skills[item].id for item in related]

    def framework_for(job, requirements):
        frame = CompetencyFramework(name=f"{job.title} Competency Framework", job_role=job, version="2026.1"); db.session.add(frame); db.session.flush()
        for name, level, criticality in requirements: db.session.add(RoleSkillRequirement(framework=frame, skill=skills[name], required_level=level, criticality=criticality))
    framework_for(meteorologist, [("Radar Meteorology", 4, "critical"), ("Numerical Weather Prediction", 4, "critical"), ("Satellite Image Interpretation", 3, "mandatory"), ("Impact-based Forecasting", 4, "critical"), ("Risk Communication", 4, "mandatory"), ("Python for Geoscience", 3, "optional")])
    framework_for(ocean_scientist, [("Ocean Data Quality", 4, "critical"), ("Wave Modelling", 4, "mandatory"), ("Tsunami Warning Operations", 3, "critical"), ("Python for Geoscience", 4, "mandatory"), ("Research Data Management", 4, "mandatory")])
    framework_for(seismologist, [("Seismic Signal Analysis", 4, "critical"), ("Earthquake Information Workflow", 4, "critical"), ("GIS for Earth Science", 3, "mandatory"), ("Risk Communication", 3, "mandatory")])
    framework_for(training_administrator, [("Project Management", 4, "critical"), ("Professional Communication", 4, "mandatory"), ("Research Data Management", 3, "mandatory")])
    for name, level, verified in [("Radar Meteorology", 2, False), ("Numerical Weather Prediction", 3, False), ("Satellite Image Interpretation", 3, True), ("Impact-based Forecasting", 1, False), ("Risk Communication", 3, True), ("Python for Geoscience", 2, False)]: db.session.add(UserSkill(user=learner, skill=skills[name], level=level, verified=verified))
    for expert_user, names in [(trainer, ["Radar Meteorology", "Numerical Weather Prediction", "Impact-based Forecasting", "Risk Communication"]), (expert, ["Ocean Data Quality", "Wave Modelling", "Tsunami Warning Operations", "Python for Geoscience"]), (manager, ["Radar Meteorology", "Impact-based Forecasting", "Risk Communication"]), (admin, ["Seismic Signal Analysis", "Earthquake Information Workflow", "GIS for Earth Science"])]:
        for name in names: db.session.add(UserSkill(user=expert_user, skill=skills[name], level=5, verified=True))
    db.session.flush()

    course_specs = [
        ("Operational Radar Meteorology", "Weather & Climate", "Intermediate", 12, ["Radar Meteorology", "Satellite Image Interpretation"], "Read radar signatures, identify severe convection, and communicate uncertainty."),
        ("Numerical Weather Prediction Essentials", "Weather & Climate", "Intermediate", 16, ["Numerical Weather Prediction", "Python for Geoscience"], "Use model guidance responsibly in a local forecast workflow."),
        ("Impact-based Forecasting for Monsoon Hazards", "Operations", "Foundation", 10, ["Impact-based Forecasting", "Risk Communication"], "Turn forecast confidence into timely, actionable public guidance."),
        ("Ocean Observation Data QA", "Ocean Science", "Intermediate", 14, ["Ocean Data Quality", "Research Data Management"], "Detect, document, and correct quality issues in operational observations."),
        ("Wave Modelling and Coastal Advisories", "Ocean Science", "Advanced", 18, ["Wave Modelling", "Risk Communication"], "Interpret wave guidance for marine and coastal stakeholders."),
        ("Tsunami Warning Desk Simulation", "Natural Hazards", "Advanced", 15, ["Tsunami Warning Operations", "Seismic Signal Analysis"], "Practise a time-critical end-to-end warning workflow."),
        ("Earthquake Information Workflow", "Natural Hazards", "Foundation", 9, ["Earthquake Information Workflow", "GIS for Earth Science"], "Validate observations and publish clear earthquake information."),
        ("Reproducible Python for Geoscience", "Data & Digital", "Foundation", 11, ["Python for Geoscience", "Open-source Reproducibility"], "Build transparent data analysis notebooks for science operations."),
        ("Project Management for Scientific Teams", "Organizational Development", "Foundation", 8, ["Project Management", "Professional Communication"], "Plan practical learning projects, set milestones, and communicate progress."),
    ]
    courses = []
    for title, domain, level, hours, skill_names, description in course_specs:
        course = Course(title=title, domain=domain, level=level, duration_hours=hours, description=description, skill_ids=[skills[name].id for name in skill_names], trainer=trainer); db.session.add(course); courses.append(course)
    db.session.flush()
    for course in courses:
        db.session.add_all([Module(course=course, title="Understand the operational context", order=1), Module(course=course, title="Practise, document, and reflect", order=2)])
    db.session.flush()
    for course in courses:
        first, second = sorted(course.modules, key=lambda item: item.order)
        db.session.add_all([
            Lesson(module=first, title="Operational briefing", content_type="lesson", body="Review the operational context and the approved workflow.", duration_minutes=18),
            Lesson(module=first, title="Guided example", content_type="case study", body="Work through a realistic Earth-science decision example.", duration_minutes=22),
            Lesson(module=second, title="Practical task", content_type="assignment", body="Apply the method and prepare evidence for review.", duration_minutes=30),
            Lesson(module=second, title="Reflection note", content_type="note", body="Record what changed in your practice and what help you need.", duration_minutes=10),
        ])
        assessment = Assessment(course=course, title=f"{course.title} knowledge check", minutes=20, pass_score=70)
        db.session.add(assessment); db.session.flush()
        db.session.add_all([
            Question(assessment=assessment, prompt=f"Which action best supports the purpose of {course.title}?", options=["Apply the approved workflow and document evidence", "Skip the operational checks", "Rely on an unverified assumption"], correct_answer="Apply the approved workflow and document evidence"),
            Question(assessment=assessment, prompt="What should you do when a practical task is complete?", options=["Submit evidence for expert verification", "Mark the competency verified yourself", "Ignore feedback"], correct_answer="Submit evidence for expert verification"),
        ])
    db.session.add_all([Enrollment(user=learner, course=courses[0], progress=65, status="in_progress"), Enrollment(user=learner, course=courses[2], progress=30, status="in_progress")])
    db.session.add(LearningPath(user=learner, title="Forecast confidence roadmap", plan=[{"week": 1, "title": "Read radar signatures", "status": "complete"}, {"week": 2, "title": "Compare model and observations", "status": "active"}, {"week": 3, "title": "Submit impact forecast evidence", "status": "upcoming"}, {"week": 4, "title": "Mentor verification checkpoint", "status": "upcoming"}]))
    db.session.add_all([
        MentorProfile(user=trainer, bio="Forecasting trainer with 14 years of monsoon operations experience.", availability="Tue & Thu afternoons", skill_ids=[skills["Radar Meteorology"].id, skills["Impact-based Forecasting"].id], languages=["English", "Hindi"]),
        MentorProfile(user=expert, bio="Ocean observation specialist and knowledge steward for coastal hazards.", availability="Wed mornings", skill_ids=[skills["Ocean Data Quality"].id, skills["Tsunami Warning Operations"].id, skills["Python for Geoscience"].id], languages=["English", "Malayalam"]),
    ])
    radar_doc = KnowledgeDocument(title="IMD Severe Convection Desk Guide", domain="Weather & Climate", access_level="organization", source_type="operational guide")
    ocean_doc = KnowledgeDocument(title="INCOIS Ocean Observation Quality Handbook", domain="Ocean Science", access_level="organization", source_type="handbook")
    legacy_doc = KnowledgeDocument(title="Legacy Interview: Communicating Cyclone Uncertainty", domain="Operations", access_level="organization", source_type="expert interview")
    db.session.add_all([radar_doc, ocean_doc, legacy_doc]); db.session.flush()
    db.session.add_all([
        KnowledgeChunk(document=radar_doc, section="Section 3 — Escalation", content="When radar signatures indicate rapidly intensifying convection, the desk scientist checks satellite trends and numerical guidance, records confidence, and escalates through the approved impact-based forecast workflow.", keywords=["radar", "convection", "escalation", "forecast"]),
        KnowledgeChunk(document=radar_doc, section="Section 5 — Uncertainty", content="Operational messages must state the expected impact, place, time window, confidence, and next update. Do not communicate a deterministic outcome where observational uncertainty remains material.", keywords=["uncertainty", "communication", "impact"]),
        KnowledgeChunk(document=ocean_doc, section="Chapter 2 — First-pass QA", content="Check time continuity, range limits, sensor flags, and platform metadata before an ocean observation is released for downstream modelling or advisory use.", keywords=["ocean", "quality", "metadata", "data"]),
        KnowledgeChunk(document=legacy_doc, section="Lesson 4 — Decision communication", content="Senior forecasters recommend communicating what is known, what remains uncertain, and the protective action people can take. Early clear communication builds trust even as forecasts are updated.", keywords=["cyclone", "communication", "trust", "uncertainty"]),
    ])
    db.session.add_all([
        CommunityPost(author=trainer, title="How do you explain changing rainfall confidence?", body="Share wording that is honest about uncertainty while remaining useful to district response teams.", tags=["forecasting", "communication"], post_type="question"),
        CommunityPost(author=expert, title="Checklist for ocean-observation quality review", body="I have shared a short practical checklist for spotting metadata, continuity, and range issues before data moves to modelling.", tags=["ocean", "data-quality"], post_type="best-practice"),
    ])
    db.session.add(ScenarioLab(title="Severe-weather warning response", domain="Weather & Climate", situation="At 14:10 IST, radar shows rapidly intensifying convection moving toward three districts. The latest model run supports heavy rainfall, but the boundary position has a 25 km uncertainty. District control rooms request an immediate alert.", competency_ids=[skills["Radar Meteorology"].id, skills["Impact-based Forecasting"].id, skills["Risk Communication"].id], decisions=[
        {"id": "act", "label": "Issue a time-bound impact alert, state confidence and location uncertainty, and schedule an update in 30 minutes.", "score": 100, "consequence": "District teams receive an actionable early warning and know when to expect the next evidence-led update.", "explanation": "This applies impact-based forecasting: act early on credible risk while making uncertainty transparent.", "improvement": "Attach observed radar movement and notify the escalation channel."},
        {"id": "wait", "label": "Wait for the next model run before notifying districts.", "score": 35, "consequence": "The message may be more precise, but response time is lost during a rapidly evolving event.", "explanation": "Model confirmation is useful, but the existing radar evidence warrants a precautionary operational alert.", "improvement": "Use a provisional alert with an explicit update time."},
        {"id": "certain", "label": "State that severe rain will definitely strike all three districts.", "score": 20, "consequence": "Overconfident wording can undermine trust if the uncertain boundary shifts.", "explanation": "The evidence supports risk, not certainty across the entire area.", "improvement": "Describe location and timing as a confidence range."},
    ]))
    db.session.add_all([Notification(user=learner, title="Evidence checkpoint due", body="Submit your radar interpretation evidence before Friday."), Notification(user=learner, title="New Knowledge Vault lesson", body="An approved cyclone uncertainty interview is ready to explore.")])
    db.session.add(Certificate(user=learner, course=courses[2], verification_code="CC-DEMO-IMPACT", issued_at=datetime(2026, 8, 15)))
    db.session.commit()
    print("Seed complete. Demo users all use password: Demo@123")
