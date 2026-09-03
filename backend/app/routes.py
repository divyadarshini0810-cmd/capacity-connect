from datetime import date, datetime, timedelta
from functools import wraps
from io import BytesIO
from uuid import uuid4
from flask import Blueprint, jsonify, request, send_file
from flask_jwt_extended import create_access_token, create_refresh_token, get_jwt_identity, jwt_required, verify_jwt_in_request
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.units import mm
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.pdfgen import canvas
from sqlalchemy import func
from . import db, limiter
from .models import (Assessment, Attempt, AuditLog, Certificate, Comment, CommunityPost, CompetencyFramework,
                     Course, CourseBookmark, Department, EmployeeProfile, Enrollment, Institution, JobRole,
                     KnowledgeChunk, KnowledgeDocument, LearningPath, Lesson, LessonProgress, MentorProfile, MentoringRequest, Module,
                     Notification, Role, RoleSkillRequirement, ScenarioAttempt, ScenarioLab, Skill,
                     SkillEvidence, Question, User, UserSkill, VerificationRecord)
from .services.ai import answer_with_provider

api = Blueprint("api", __name__)


# Capacity Connect creates these structured professional tracks when a learner
# with a matching digital role first opens Courses. They deliberately use a
# six-week university-style layout, but are Capacity Connect courses (not a
# copy of or affiliation with SWAYAM, NPTEL, IBM, or AWS content).
PROFESSIONAL_ROLE_TRACKS = {
    "data analyst": {
        "title": "Professional Data Analytics: Python, SQL and Dashboards",
        "description": "A six-week, project-based programme for turning reliable data into clear decisions.",
        "domain": "Data & Digital",
        "skills": ["Data Analysis Fundamentals", "SQL & Data Querying", "Python for Data Analysis", "Data Visualisation", "Statistical Analysis", "Dashboard Design"],
        "weeks": ["Data foundations and problem framing", "SQL, spreadsheets and data quality", "Python analysis and statistics", "Visualisation and dashboard design", "Data storytelling for decisions", "Portfolio capstone and final quiz"],
    },
    "frontend developer": {
        "title": "Professional Frontend Development: React and Accessible Interfaces",
        "description": "A six-week, hands-on programme for building responsive, accessible and production-ready web interfaces.",
        "domain": "Software Development",
        "skills": ["HTML & CSS", "JavaScript & TypeScript", "React Development", "UI/UX Fundamentals", "Web Accessibility", "Frontend Testing"],
        "weeks": ["Semantic HTML and modern CSS", "JavaScript and TypeScript foundations", "React components and state", "APIs, forms and application flows", "Accessibility, testing and performance", "Portfolio capstone and final quiz"],
    },
    "backend developer": {
        "title": "Professional Backend Development: APIs, Databases and Security",
        "description": "A six-week programme for designing reliable server-side services and secure data APIs.",
        "domain": "Software Development",
        "skills": ["API Design", "Database Design", "Backend Programming", "Authentication & Security", "Testing", "Deployment Fundamentals"],
        "weeks": ["Backend architecture and HTTP", "Data modelling and SQL", "API design and validation", "Authentication and security", "Testing, observability and deployment", "Service capstone and final quiz"],
    },
    "full-stack developer": {
        "title": "Professional Full-Stack Development: From Interface to API",
        "description": "A six-week programme for connecting polished user experiences to reliable application services.",
        "domain": "Software Development",
        "skills": ["HTML & CSS", "JavaScript & TypeScript", "React Development", "API Integration", "Database Design", "Git & Version Control"],
        "weeks": ["Product discovery and interface foundations", "Interactive frontend development", "APIs and application data", "Authentication and integration", "Quality, deployment and collaboration", "Full-stack capstone and final quiz"],
    },
    "ai/ml engineer": {
        "title": "Professional AI and Machine Learning Engineering",
        "description": "A six-week programme for building useful, evaluated and responsibly deployed ML systems.",
        "domain": "Data & Digital",
        "skills": ["Python for Data Analysis", "Machine Learning Fundamentals", "Feature Engineering", "Model Evaluation", "MLOps Fundamentals", "Responsible AI"],
        "weeks": ["ML problem framing and data", "Features and baseline models", "Training and evaluation", "Deep learning and experimentation", "MLOps, monitoring and responsible AI", "ML capstone and final quiz"],
    },
    "gis analyst": {
        "title": "Professional GIS Analysis and Geospatial Intelligence",
        "description": "A six-week programme for producing reliable maps, spatial analysis and operational geospatial insight.",
        "domain": "Data & Digital",
        "skills": ["GIS for Earth Science", "Spatial Analysis", "Remote Sensing", "Cartography", "Python for Geoscience", "Geospatial Data Quality"],
        "weeks": ["Coordinate systems and geospatial data", "GIS data preparation", "Spatial analysis methods", "Remote sensing workflows", "Cartography and communication", "GIS capstone and final quiz"],
    },
}

ROLE_MENTOR_SPECS = {
    "data analyst": [
        ("Capacity Connect Data Mentor Pool", "Data analytics mentor for Python, SQL, data preparation, and repeatable analysis workflows.", "Mon & Wed afternoons", ["Data Analysis Fundamentals", "SQL & Data Querying", "Python for Data Analysis"], ["English", "Hindi"]),
        ("Capacity Connect Dashboard Mentor Pool", "Supports dashboard design, visual communication, and stakeholder-ready data stories.", "Tue & Thu mornings", ["Data Visualisation", "Dashboard Design", "Data Storytelling"], ["English", "Malayalam"]),
        ("Capacity Connect Data Quality Mentor Pool", "Helps learners review data quality, statistical assumptions, and professional analysis practice.", "Friday afternoons", ["Data Cleaning & Quality", "Statistical Analysis", "Spreadsheet Modelling"], ["English", "Hindi"]),
    ],
    "frontend developer": [
        ("Capacity Connect React Mentor Pool", "Supports component design, state management, and practical React development.", "Mon & Thu afternoons", ["React Development", "JavaScript & TypeScript", "API Integration"], ["English", "Hindi"]),
        ("Capacity Connect UX Mentor Pool", "Supports responsive interfaces, accessibility, and user-centred frontend design.", "Tue mornings", ["UI/UX Fundamentals", "Web Accessibility", "Responsive Web Design"], ["English", "Malayalam"]),
        ("Capacity Connect Web Quality Mentor Pool", "Supports testing, performance, and version-control practice for frontend projects.", "Friday mornings", ["Frontend Testing", "Web Performance", "Git & Version Control"], ["English"]),
    ],
}


def role_track_for(user):
    title = (user.job_role.title if user and user.job_role else "").strip().lower()
    return PROFESSIONAL_ROLE_TRACKS.get(title)


def lesson_notes(week_number, week, activity, track):
    """Short, practical reading notes shown inside the in-app course player."""
    competency = track["skills"][min(week_number - 1, len(track["skills"]) - 1)]
    common = [
        f"Week focus: {week}.",
        f"Professional competency: {competency}.",
    ]
    activity_notes = {
        "Welcome and weekly outcomes": [
            "Learning objective: explain the week's outcome and recognise where it is used in professional work.",
            "Start by connecting this topic to one real task from your current or intended job role.",
            "Keep a short learning journal: write one question you want this week to answer.",
        ],
        "Core concepts": [
            "Key idea: reliable work begins with a clearly defined problem, trustworthy inputs, and an outcome that can be checked.",
            "Study note: identify the terms, assumptions, and quality checks used in this topic before choosing a tool or writing code.",
            "Example: describe the same task for a technical colleague and for a decision-maker; notice what changes and what must remain precise.",
        ],
        "Guided demonstration": [
            "Follow the workflow slowly: prepare the input, apply one method, inspect the result, and record what changed.",
            "Pause after each step and predict the next result before reading the explanation.",
            "If your result differs from the example, check naming, data quality, assumptions, and the order of steps.",
        ],
        "Hands-on practice": [
            "Practical task: create a small artefact that uses this week's method - a notebook, query, component, map, dashboard, or written analysis as appropriate.",
            "Use a small, safe example first. Name your files clearly and record the decisions you made.",
            "Success check: another learner should be able to understand your approach, repeat it, and explain the result.",
        ],
        "Reflection and knowledge check": [
            "Review: summarise the three most important ideas in your own words without looking at the notes.",
            "Check yourself: what decision would change if the input was incomplete, inaccurate, or differently scoped?",
            "Before moving on, save one improvement you would make in a second attempt.",
        ],
    }
    return "\n\n".join(common + activity_notes.get(activity, ["Read the lesson, take notes, and apply the concept to a small practical example."]))


def ensure_role_courses(user):
    """Return the role-specific course catalogue, creating one durable track when needed."""
    track = role_track_for(user)
    if not track:
        return []
    course = Course.query.filter_by(title=track["title"]).first()
    if course:
        # Upgrade early generated tracks so existing learners receive the full
        # in-player notes instead of the original one-line activity label.
        updated = False
        for order, module in enumerate(sorted(course.modules, key=lambda item: item.order), start=1):
            week = module.title.split(": ", 1)[-1]
            for lesson in module.lessons:
                activity = lesson.title.rsplit(" - ", 1)[-1]
                if not lesson.body or lesson.body.startswith("Week "):
                    lesson.body = lesson_notes(order, week, activity, track)
                    updated = True
        if updated:
            db.session.commit()
        return [course]

    skill_ids = []
    for name in track["skills"]:
        skill = Skill.query.filter(func.lower(Skill.name) == name.lower()).first()
        if not skill:
            skill = Skill(name=name, domain=track["domain"], description=f"Professional competency for the {user.job_role.title} learning track.", importance=3)
            db.session.add(skill)
            db.session.flush()
        skill_ids.append(skill.id)

    course = Course(title=track["title"], description=track["description"], domain=track["domain"], level="Professional", duration_hours=36, skill_ids=skill_ids)
    db.session.add(course)
    db.session.flush()
    lesson_pattern = [
        ("Welcome and weekly outcomes", "video", 12),
        ("Core concepts", "lesson", 28),
        ("Guided demonstration", "demo", 22),
        ("Hands-on practice", "assignment", 45),
        ("Reflection and knowledge check", "knowledge_check", 15),
    ]
    for order, week in enumerate(track["weeks"], start=1):
        module = Module(course_id=course.id, title=f"Week {order}: {week}", order=order)
        db.session.add(module)
        db.session.flush()
        for lesson_title, content_type, minutes in lesson_pattern:
            db.session.add(Lesson(module_id=module.id, title=f"{week} - {lesson_title}", content_type=content_type, duration_minutes=minutes, body=lesson_notes(order, week, lesson_title, track)))

    assessment = Assessment(course_id=course.id, title=f"{track['title']} - final professional quiz", minutes=30, pass_score=70)
    db.session.add(assessment)
    db.session.flush()
    options = ["To produce reliable, usable professional outcomes", "To skip planning and validation", "To avoid collaborating with stakeholders", "To replace all human judgement"]
    prompts = [
        f"What is the main purpose of {track['skills'][0]} in professional practice?",
        "What should be checked before sharing a professional deliverable?",
        "Why is feedback useful during a project?",
        "What makes a workflow repeatable?",
        "When should quality checks be performed?",
        "What should a final portfolio demonstrate?",
    ]
    for prompt in prompts:
        db.session.add(Question(assessment_id=assessment.id, prompt=prompt, options=options, correct_answer=options[0], question_type="multiple_choice"))
    db.session.commit()
    return [course]


def ensure_role_mentors(user):
    """Create clearly labelled demo mentor pools only for the learner's selected professional role."""
    role_key = (user.job_role.title if user.job_role else "").strip().lower()
    specs = ROLE_MENTOR_SPECS.get(role_key, [])
    if not specs:
        return []
    ensure_role_courses(user)
    mentor_role = Role.query.filter_by(name="Subject-Matter Expert/Mentor").first() or user.role
    profiles = []
    for index, (name, bio, availability, skills, languages) in enumerate(specs, start=1):
        code = f"CC-{role_key.replace(' ', '-')}-{index}".lower()
        mentor_user = User.query.filter_by(email=f"{code}@capacityconnect.local").first()
        if not mentor_user:
            mentor_user = User(name=name, email=f"{code}@capacityconnect.local", employee_id=f"CC-MENTOR-{role_key[:3].upper()}-{index}", role=mentor_role, institution=user.institution, department=user.department, job_role=user.job_role, experience_years=8, ai_consent=True)
            mentor_user.set_password(uuid4().hex)
            db.session.add(mentor_user)
            db.session.flush()
        profile = MentorProfile.query.filter_by(user_id=mentor_user.id).first()
        skill_ids = []
        for skill_name in skills:
            skill = Skill.query.filter(func.lower(Skill.name) == skill_name.lower()).first()
            if not skill:
                skill = Skill(name=skill_name, domain=role_track_for(user)["domain"], description=f"Professional competency supported by the {user.job_role.title} mentor pool.", importance=3)
                db.session.add(skill)
                db.session.flush()
            skill_ids.append(skill.id)
        if not profile:
            profile = MentorProfile(user_id=mentor_user.id, bio=bio, availability=availability, skill_ids=skill_ids, languages=languages)
            db.session.add(profile)
        else:
            profile.bio, profile.availability, profile.skill_ids, profile.languages = bio, availability, skill_ids, languages
        profiles.append(profile)
    db.session.commit()
    return profiles


def assessment_for_course(course_id):
    return Assessment.query.filter_by(course_id=course_id).order_by(Assessment.created_at.asc()).first()


def certificate_issued_if_eligible(enrollment):
    """Issue exactly one certificate only after course completion and the final quiz pass."""
    if not enrollment or enrollment.progress < 100:
        return False
    assessment = assessment_for_course(enrollment.course_id)
    if assessment:
        passed = Attempt.query.filter_by(user_id=enrollment.user_id, assessment_id=assessment.id).filter(Attempt.score >= assessment.pass_score).first()
        if not passed:
            return False
    if Certificate.query.filter_by(user_id=enrollment.user_id, course_id=enrollment.course_id).first():
        return False
    db.session.add(Certificate(user_id=enrollment.user_id, course_id=enrollment.course_id, verification_code=f"CC-{uuid4().hex[:10].upper()}"))
    return True


def current_user():
    return db.session.get(User, int(get_jwt_identity()))


def roles_allowed(*roles):
    def outer(fn):
        @wraps(fn)
        def inner(*args, **kwargs):
            verify_jwt_in_request()
            user = current_user()
            if not user or user.role.name not in roles:
                return jsonify(error="You are not authorized to perform this action."), 403
            return fn(*args, **kwargs)
        return inner
    return outer


def audit(actor_id, action, target_type, target_id, metadata=None):
    db.session.add(AuditLog(actor_id=actor_id, action=action, target_type=target_type, target_id=str(target_id), metadata_json=metadata or {}))


def completed_lesson_ids(course, user_id):
    if not user_id:
        return set()
    lesson_ids = [lesson.id for module in course.modules for lesson in module.lessons]
    if not lesson_ids:
        return set()
    return {item.lesson_id for item in LessonProgress.query.filter_by(user_id=user_id).filter(LessonProgress.lesson_id.in_(lesson_ids)).all()}


def course_public(course, user_id=None):
    enrollment = Enrollment.query.filter_by(course_id=course.id, user_id=user_id).first() if user_id else None
    skills = Skill.query.filter(Skill.id.in_(course.skill_ids or [])).all()
    bookmark = CourseBookmark.query.filter_by(course_id=course.id, user_id=user_id).first() if user_id else None
    assessment = assessment_for_course(course.id)
    latest_attempt = Attempt.query.filter_by(user_id=user_id, assessment_id=assessment.id).order_by(Attempt.created_at.desc()).first() if user_id and assessment else None
    completed_ids = completed_lesson_ids(course, user_id)
    return {"id": course.id, "title": course.title, "description": course.description, "domain": course.domain,
            "level": course.level, "durationHours": course.duration_hours, "trainer": course.trainer.name if course.trainer else "Capacity Connect Faculty",
            "skills": [skill.name for skill in skills], "progress": enrollment.progress if enrollment else None,
            "enrolled": bool(enrollment), "bookmarked": bool(bookmark),
            "finalQuiz": {"id": assessment.id, "title": assessment.title, "minutes": assessment.minutes, "passScore": assessment.pass_score,
                          "passed": bool(latest_attempt and latest_attempt.score >= assessment.pass_score)} if assessment else None,
            "modules": [{"id": m.id, "title": m.title, "lessons": [{"id": lesson.id, "title": lesson.title, "type": lesson.content_type, "minutes": lesson.duration_minutes, "body": lesson.body or "Lesson notes will be added by the course facilitator.", "completed": lesson.id in completed_ids} for lesson in sorted(m.lessons, key=lambda item: item.id)]} for m in sorted(course.modules, key=lambda item: item.order)]}


def employee_profile_public(user):
    profile = user.development_profile
    if not profile:
        return {"onboardingComplete": False, "availableTimes": {}, "hoursPerWeek": 4}
    return {
        "onboardingComplete": profile.onboarding_complete,
        "designation": profile.designation, "workLocation": profile.work_location,
        "employmentType": profile.employment_type, "joiningDate": profile.joining_date.isoformat() if profile.joining_date else None,
        "reportingManager": profile.reporting_manager, "responsibilities": profile.responsibilities,
        "certificationsResume": profile.certifications_resume, "languagesKnown": profile.languages_known or [],
        "targetSkills": profile.target_skills or [], "developmentGoals": profile.development_goals,
        "availableTimes": profile.available_times or {}, "hoursPerWeek": profile.hours_per_week,
        "preferredTrainingLanguage": profile.preferred_training_language, "learningPreference": profile.learning_preference,
    }


def recommendation_for(user, row):
    profile = user.development_profile
    priority_terms = " ".join((profile.target_skills or []) + ([profile.development_goals] if profile and profile.development_goals else [])).lower() if profile else ""
    courses = [item for item in Course.query.all() if row["skillId"] in (item.skill_ids or [])]
    course = sorted(courses, key=lambda item: (row["skill"].lower() not in item.title.lower(), item.duration_hours))[0] if courses else None
    mentors = [item for item in MentorProfile.query.filter(MentorProfile.user_id != user.id).all() if row["skillId"] in (item.skill_ids or [])]
    if profile and profile.preferred_training_language:
        language = profile.preferred_training_language.lower()
        mentors.sort(key=lambda item: language not in [name.lower() for name in (item.languages or [])])
    mentor = mentors[0] if mentors else None
    manager_priority = "Manager priority" if row["skill"].lower() in priority_terms else "Role requirement"
    return {
        **row,
        "whyRequired": f"{manager_priority}: {user.job_role.title if user.job_role else 'your role'} requires this competency for operational work.",
        "verificationStatus": "Verified" if row["status"] == "verified" else "Needs verification" if row["current"] else "Not started",
        "recommendedCourse": {"id": course.id, "title": course.title, "durationHours": course.duration_hours} if course else None,
        "mentor": {"id": mentor.id, "name": mentor.user.name, "availability": mentor.availability, "languages": mentor.languages} if mentor else None,
    }


def user_analysis(user):
    if not user.job_role:
        return {"gapScore": 0, "requirements": [], "criticalGaps": [], "coverage": 0}
    framework = CompetencyFramework.query.filter_by(job_role_id=user.job_role_id).order_by(CompetencyFramework.created_at.desc()).first()
    requirements = framework.requirements if framework else []
    user_skills = {item.skill_id: item for item in user.user_skills}
    rows, weighted_gap = [], 0
    total_weight = 0
    for requirement in requirements:
        user_skill = user_skills.get(requirement.skill_id)
        current = user_skill.level if user_skill else 0
        gap = max(0, requirement.required_level - current)
        weight = 2 if requirement.criticality == "critical" else 1
        weighted_gap += (gap / 5) * weight
        total_weight += weight
        status = "verified" if user_skill and user_skill.verified and gap == 0 else "learning" if current else ("critical-gap" if requirement.criticality == "critical" else "missing")
        rows.append({"skillId": requirement.skill.id, "skill": requirement.skill.name, "domain": requirement.skill.domain,
                     "current": current, "required": requirement.required_level, "gapPercent": round((gap / requirement.required_level) * 100) if requirement.required_level else 0,
                     "status": status, "criticality": requirement.criticality, "importance": requirement.skill.importance})
    gap_score = round((weighted_gap / total_weight) * 100) if total_weight else 0
    return {"gapScore": gap_score, "requirements": rows, "criticalGaps": [row for row in rows if row["status"] == "critical-gap"], "coverage": 100 - gap_score}


@api.get("/health")
def health():
    return jsonify(status="ok", service="Capacity Connect API", storage="SQLAlchemy")


@api.post("/auth/login")
@limiter.limit("5 per minute")
def login():
    payload = request.get_json(silent=True) or {}
    email, password = payload.get("email", "").strip().lower(), payload.get("password", "")
    user = User.query.filter(func.lower(User.email) == email).first()
    if not user or not user.check_password(password):
        return jsonify(error="Invalid email or password."), 401
    audit(user.id, "login", "user", user.id)
    db.session.commit()
    return jsonify(accessToken=create_access_token(identity=str(user.id)), refreshToken=create_refresh_token(identity=str(user.id)), user=user.public())


@api.post("/auth/refresh")
@jwt_required(refresh=True)
def refresh():
    return jsonify(accessToken=create_access_token(identity=get_jwt_identity()))


ROLE_CHOICES = {
    "Employee/New Trainee": "Employee/Learner",
    "Trainer": "Trainer",
    "Expert/Mentor": "Subject-Matter Expert/Mentor",
    "Manager": "Manager/Department Head",
    "Administrator": "Organization Administrator",
}


@api.get("/onboarding/options")
def onboarding_options():
    return jsonify(
        roles=[{"label": label, "value": value} for label, value in ROLE_CHOICES.items()],
        institutions=[{"id": item.id, "name": item.name, "location": item.location} for item in Institution.query.order_by(Institution.name).all()],
        departments=[{"id": item.id, "name": item.name, "institutionId": item.institution_id} for item in Department.query.order_by(Department.name).all()],
        jobRoles=[{"id": item.id, "title": item.title, "domain": item.domain} for item in JobRole.query.order_by(JobRole.title).all()],
        skills=[{"id": item.id, "name": item.name, "domain": item.domain} for item in Skill.query.order_by(Skill.domain, Skill.name).all()],
    )


@api.post("/auth/register")
@limiter.limit("3 per minute")
def register():
    payload = request.get_json(silent=True) or {}
    name, email, password = str(payload.get("fullName", "")).strip(), str(payload.get("officialEmail", "")).strip().lower(), str(payload.get("password", ""))
    role_name = ROLE_CHOICES.get(str(payload.get("role", "")).strip())
    if len(name) < 3 or "@" not in email or len(password) < 8 or not role_name:
        return jsonify(error="Enter your full name, official email, a password of at least 8 characters, and an account role."), 400
    if User.query.filter(func.lower(User.email) == email).first():
        return jsonify(error="An account with this official email already exists."), 409
    institution = Institution.query.order_by(Institution.id).first()
    role = Role.query.filter_by(name=role_name).first()
    if not institution or not role:
        return jsonify(error="The platform setup is incomplete. Please contact an administrator."), 503
    user = User(name=name, email=email, employee_id=f"NEW-{uuid4().hex[:8].upper()}", role=role, institution=institution)
    user.set_password(password)
    db.session.add(user); db.session.flush()
    db.session.add(EmployeeProfile(user_id=user.id, onboarding_complete=False))
    audit(user.id, "registered", "user", user.id, {"role": role_name})
    db.session.commit()
    return jsonify(accessToken=create_access_token(identity=str(user.id)), refreshToken=create_refresh_token(identity=str(user.id)), user=user.public(), needsOnboarding=True), 201


@api.get("/me")
@jwt_required()
def me():
    user = current_user()
    analysis = user_analysis(user)
    verified = sum(1 for skill in user.user_skills if skill.verified)
    profile = employee_profile_public(user)
    completion = 100 if profile["onboardingComplete"] else 30
    return jsonify(**user.public(), **profile, analysis=analysis, verifiedSkills=verified, learningStreak=7, profileCompletion=completion)


@api.route("/onboarding", methods=["GET", "PUT"])
@jwt_required()
def onboarding():
    user = current_user()
    if request.method == "GET":
        return jsonify(user=user.public(), profile=employee_profile_public(user), skills=[{"skillId": item.skill_id, "name": item.skill.name, "level": item.level, "verified": item.verified} for item in user.user_skills])
    payload = request.get_json(silent=True) or {}
    profile = user.development_profile or EmployeeProfile(user_id=user.id)
    if not profile.id:
        db.session.add(profile)
    for source, attribute in {"fullName": "name", "employeeId": "employee_id", "experienceYears": "experience_years", "preferredTrainingLanguage": "language"}.items():
        if source in payload and str(payload[source]).strip():
            setattr(user, attribute, int(payload[source]) if source == "experienceYears" else str(payload[source]).strip())
    institution_id = payload.get("institutionId")
    department_id = payload.get("departmentId")
    job_role_id = payload.get("jobRoleId")
    if institution_id:
        institution = db.session.get(Institution, int(institution_id))
        if institution: user.institution = institution
    institution_name = str(payload.get("institutionName", "")).strip()
    if institution_name:
        institution = Institution.query.filter(func.lower(Institution.name) == institution_name.lower()).first()
        if not institution:
            institution = Institution(
                name=institution_name[:150],
                code=f"ORG-{uuid4().hex[:12].upper()}",
                location=str(payload.get("workLocation") or "Not specified")[:120],
            )
            db.session.add(institution)
            db.session.flush()
        user.institution = institution
    if department_id:
        department = db.session.get(Department, int(department_id))
        if department and department.institution_id == user.institution_id: user.department = department
    if job_role_id:
        job_role = db.session.get(JobRole, int(job_role_id))
        if job_role: user.job_role = job_role
    # Typed workplace details are intentionally supported alongside the curated lists.
    # This keeps registration practical for digital, research, and emerging roles.
    department_name = str(payload.get("departmentName", "")).strip()
    if department_name:
        if not user.institution_id:
            return jsonify(error="Select an institution before entering a department."), 400
        department = Department.query.filter(
            Department.institution_id == user.institution_id,
            func.lower(Department.name) == department_name.lower(),
        ).first()
        if not department:
            department = Department(name=department_name[:120], institution_id=user.institution_id)
            db.session.add(department)
        user.department = department
    job_role_name = str(payload.get("jobRoleName", "")).strip()
    if job_role_name:
        job_role = JobRole.query.filter(func.lower(JobRole.title) == job_role_name.lower()).first()
        if not job_role:
            job_role = JobRole(title=job_role_name[:120], domain="General & Digital Services", description="Employee-defined role awaiting competency mapping.")
            db.session.add(job_role)
        user.job_role = job_role
    profile_fields = {
        "designation": "designation", "workLocation": "work_location", "employmentType": "employment_type",
        "reportingManager": "reporting_manager", "responsibilities": "responsibilities", "certificationsResume": "certifications_resume",
        "developmentGoals": "development_goals", "preferredTrainingLanguage": "preferred_training_language", "learningPreference": "learning_preference",
    }
    for source, attribute in profile_fields.items():
        if source in payload: setattr(profile, attribute, str(payload[source]).strip() if payload[source] is not None else None)
    if payload.get("joiningDate"):
        try: profile.joining_date = date.fromisoformat(payload["joiningDate"])
        except ValueError: return jsonify(error="Use YYYY-MM-DD for the joining date."), 400
    for source, attribute in {"languagesKnown": "languages_known", "targetSkills": "target_skills", "availableTimes": "available_times"}.items():
        if source in payload and isinstance(payload[source], (list, dict)): setattr(profile, attribute, payload[source])
    if "hoursPerWeek" in payload:
        profile.hours_per_week = max(1, min(40, int(payload["hoursPerWeek"])))
    if isinstance(payload.get("skills"), list):
        for item in payload["skills"]:
            skill_name = str(item.get("name", "")).strip()
            skill = db.session.get(Skill, item.get("skillId")) or Skill.query.filter(func.lower(Skill.name) == skill_name.lower()).first()
            if not skill and skill_name:
                skill = Skill(
                    name=skill_name[:120],
                    domain=str(item.get("domain") or "Digital & Data")[:80],
                    description="Employee-selected role skill awaiting organisational mapping.",
                    importance=3,
                )
                db.session.add(skill)
                db.session.flush()
            if skill:
                record = UserSkill.query.filter_by(user_id=user.id, skill_id=skill.id).first()
                if not record:
                    record = UserSkill(user_id=user.id, skill_id=skill.id, level=1); db.session.add(record)
                record.level = max(1, min(5, int(item.get("level", 1))))
    db.session.flush()
    profile.onboarding_complete = bool(user.employee_id and user.department_id and user.job_role_id and profile.designation and profile.work_location and profile.available_times)
    audit(user.id, "updated_onboarding", "user", user.id)
    db.session.commit()
    return jsonify(message="Employee profile saved. Your training recommendations are ready.", onboardingComplete=profile.onboarding_complete, profile=employee_profile_public(user))


@api.get("/dashboard")
@jwt_required()
def dashboard():
    user, analysis = current_user(), user_analysis(current_user())
    enrollments = Enrollment.query.filter_by(user_id=user.id).all()
    courses = [course_public(row.course, user.id) for row in enrollments]
    mentor = MentorProfile.query.filter(MentorProfile.user_id != user.id).first()
    schedule = generated_learning_schedule(user)
    notifications = Notification.query.filter_by(user_id=user.id).order_by(Notification.created_at.desc()).limit(4).all()
    return jsonify(
        welcome=f"Welcome back, {user.name.split()[0]}", analysis=analysis,
        metrics={"verifiedSkills": sum(x.verified for x in user.user_skills), "activeCourses": len(enrollments), "learningStreak": 7, "readiness": analysis["coverage"]},
        roadmap=(LearningPath.query.filter_by(user_id=user.id, status="active").first().plan if user.learning_paths else []),
        courses=courses, upcoming=[{"title": "Cyclone forecast interpretation assessment", "date": "Tomorrow · 10:30 IST", "type": "Assessment"}, {"title": "Mentor checkpoint", "date": "Friday · 15:00 IST", "type": "Mentoring"}],
        todaySchedule=schedule[:2], nextCourse=next((item for item in courses if item["progress"] is not None and item["progress"] < 100), None),
        notifications=[{"id": item.id, "title": item.title, "body": item.body, "read": item.read} for item in notifications],
        mentor={"name": mentor.user.name, "availability": mentor.availability, "expertise": [Skill.query.get(s).name for s in mentor.skill_ids[:2]]} if mentor else None,
        manager={"teamCoverage": 72, "criticalShortage": 3, "trainingPassRate": 84, "knowledgeRisk": 2,
                   "heatmap": [{"skill": "Radar Meteorology", "available": 62, "required": 85}, {"skill": "Ocean Data QA", "available": 76, "required": 80}, {"skill": "Seismic Analysis", "available": 48, "required": 75}, {"skill": "GIS", "available": 88, "required": 80}]}
    )


@api.get("/skills/galaxy")
@jwt_required()
def galaxy():
    user, analysis = current_user(), user_analysis(current_user())
    rows = {row["skillId"]: row for row in analysis["requirements"]}
    skills = Skill.query.order_by(Skill.importance.desc()).all()
    nodes = []
    for skill in skills:
        row = rows.get(skill.id)
        nodes.append({"id": skill.id, "name": skill.name, "domain": skill.domain, "importance": skill.importance,
                      "status": row["status"] if row else "learning", "current": row["current"] if row else 0, "required": row["required"] if row else 0,
                      "gapPercent": row["gapPercent"] if row else 0, "criticality": row["criticality"] if row else "optional",
                      "connections": skill.related_skill_ids or []})
    return jsonify(nodes=nodes, analysis=analysis, view="employee")


@api.route("/skills/analyze", methods=["GET", "POST"])
@jwt_required()
@limiter.limit("10 per minute")
def analyze_skills():
    user, analysis = current_user(), user_analysis(current_user())
    missing = sorted([row for row in analysis["requirements"] if row["gapPercent"]], key=lambda row: (row["criticality"] != "critical", -row["gapPercent"]))
    recommendations = []
    for row in missing[:4]:
        # JSON membership is evaluated in Python here so the prototype behaves the
        # same on SQLite demo mode and MySQL production mode.
        course = next((item for item in Course.query.all() if row["skillId"] in (item.skill_ids or [])), None)
        mentor = next((item for item in MentorProfile.query.all() if row["skillId"] in (item.skill_ids or [])), None)
        recommendations.append({"skill": row["skill"], "severity": "High" if row["criticality"] == "critical" else "Moderate", "why": f"Your current level is {row['current']}/5; your {user.job_role.title} framework requires {row['required']}/5.", "course": course.title if course else "Guided practice assignment", "mentor": mentor.user.name if mentor else "Subject-matter expert pool", "estimated": f"{max(2, row['gapPercent']//16)} weeks"})
    weekly = [{"week": i + 1, "focus": item["skill"], "target": "Complete a focused lesson, practise with an evidence task, and request mentor feedback."} for i, item in enumerate(recommendations)]
    return jsonify(analysis=analysis, recommendations=recommendations, weeklyPlan=weekly, disclaimer="AI-assisted recommendations are advisory only. They do not make employment decisions and can be corrected by the learner or manager.")


@api.get("/skill-gaps")
@jwt_required()
def skill_gaps():
    user = current_user()
    rows = [recommendation_for(user, row) for row in user_analysis(user)["requirements"]]
    rows.sort(key=lambda item: (item["gapPercent"] == 0, item["criticality"] != "critical", -item["gapPercent"]))
    return jsonify(skillGaps=rows, summary=user_analysis(user), purpose="Compare your current competency with your job-role requirements and start the next useful learning action.")


def generated_learning_schedule(user):
    profile = user.development_profile
    availability = profile.available_times if profile else {}
    days = availability.get("days", []) if isinstance(availability, dict) else []
    time_window = availability.get("time", "your available time") if isinstance(availability, dict) else "your available time"
    rows = [recommendation_for(user, row) for row in user_analysis(user)["requirements"] if row["gapPercent"]]
    rows.sort(key=lambda item: (item["criticality"] != "critical", -item["gapPercent"]))
    plan = []
    for index, row in enumerate(rows[:4]):
        course = row["recommendedCourse"]
        plan.append({
            "week": index + 1, "skill": row["skill"], "title": course["title"] if course else f"Guided practice: {row['skill']}",
            "courseId": course["id"] if course else None, "deadline": (date.today() + timedelta(days=(index + 1) * 7)).isoformat(),
            "schedule": f"{', '.join(days) if days else 'Choose learning days'} · {time_window}",
            "assessment": f"{row['skill']} knowledge check", "mentor": row["mentor"]["name"] if row["mentor"] else "Request a subject-matter expert", "status": "next" if index == 0 else "planned",
        })
    return plan


@api.route("/learning-plan", methods=["GET", "PUT"])
@jwt_required()
def learning_plan():
    user = current_user()
    profile = user.development_profile or EmployeeProfile(user_id=user.id)
    if not profile.id:
        db.session.add(profile); db.session.flush()
    if request.method == "PUT":
        payload = request.get_json(silent=True) or {}
        if isinstance(payload.get("availableTimes"), dict): profile.available_times = payload["availableTimes"]
        if "hoursPerWeek" in payload: profile.hours_per_week = max(1, min(40, int(payload["hoursPerWeek"])))
        audit(user.id, "updated_learning_availability", "employee_profile", profile.id)
        db.session.commit()
    plan = generated_learning_schedule(user)
    existing = LearningPath.query.filter_by(user_id=user.id, status="active").first()
    if existing:
        existing.plan = plan
    else:
        db.session.add(LearningPath(user_id=user.id, title="Personalized development schedule", plan=plan))
    db.session.commit()
    return jsonify(plan=plan, availability=profile.available_times or {}, hoursPerWeek=profile.hours_per_week, generatedFrom=["job role", "required competencies", "verified skills", "missing skills", "manager priorities", "availability"])


@api.get("/courses")
@jwt_required()
def list_courses():
    query, domain = request.args.get("q", "").lower(), request.args.get("domain", "")
    user = current_user()
    courses = ensure_role_courses(user) or Course.query.order_by(Course.created_at.desc()).all()
    if query: courses = [course for course in courses if query in (course.title + " " + course.description).lower()]
    if domain: courses = [course for course in courses if course.domain == domain]
    return jsonify(courses=[course_public(course, user.id) for course in courses], roleTrack=role_track_for(user) is not None)


@api.post("/courses/<int:course_id>/enroll")
@jwt_required()
def enroll(course_id):
    course, user = db.session.get(Course, course_id), current_user()
    if not course: return jsonify(error="Course not found."), 404
    enrollment = Enrollment.query.filter_by(user_id=user.id, course_id=course_id).first()
    if enrollment: return jsonify(message="You are already enrolled.", course=course_public(course, user.id))
    db.session.add(Enrollment(user_id=user.id, course_id=course_id))
    audit(user.id, "enrolled", "course", course_id)
    db.session.commit()
    return jsonify(message="Course added to your learning roadmap.", course=course_public(course, user.id)), 201


@api.post("/courses/<int:course_id>/lessons/<int:lesson_id>/complete")
@jwt_required()
def complete_lesson(course_id, lesson_id):
    user, course, lesson = current_user(), db.session.get(Course, course_id), db.session.get(Lesson, lesson_id)
    if not course or not lesson or lesson.module.course_id != course.id:
        return jsonify(error="Lesson not found in this course."), 404
    enrollment = Enrollment.query.filter_by(user_id=user.id, course_id=course.id).first()
    if not enrollment:
        return jsonify(error="Enroll in the course before completing lessons."), 400
    record = LessonProgress.query.filter_by(user_id=user.id, lesson_id=lesson.id).first()
    if not record:
        db.session.add(LessonProgress(user_id=user.id, lesson_id=lesson.id))
        db.session.flush()

    modules = sorted(course.modules, key=lambda item: item.order)
    completed_ids = completed_lesson_ids(course, user.id)
    completed_weeks = sum(1 for module in modules if module.lessons and all(item.id in completed_ids for item in module.lessons))
    enrollment.progress = round((completed_weeks / len(modules)) * 100) if modules else 0
    enrollment.status = "completed" if completed_weeks == len(modules) and modules else "in_progress"
    certificate_issued = certificate_issued_if_eligible(enrollment)
    audit(user.id, "completed_lesson", "lesson", lesson.id, {"courseId": course.id, "progress": enrollment.progress})
    db.session.commit()
    message = f"Lesson marked complete. {completed_weeks} of {len(modules)} weeks fully complete."
    if certificate_issued:
        message = "All course lessons and the final quiz are complete. Your professional certificate is ready."
    return jsonify(message=message, progress=enrollment.progress, completedWeeks=completed_weeks, completedLessonIds=sorted(completed_ids), certificateIssued=certificate_issued)


@api.post("/courses/<int:course_id>/bookmark")
@jwt_required()
def bookmark_course(course_id):
    user, course = current_user(), db.session.get(Course, course_id)
    if not course: return jsonify(error="Course not found."), 404
    bookmark = CourseBookmark.query.filter_by(user_id=user.id, course_id=course.id).first()
    if bookmark:
        db.session.delete(bookmark); saved = False
    else:
        bookmark = CourseBookmark(user_id=user.id, course_id=course.id, note=str((request.get_json(silent=True) or {}).get("note", ""))[:255])
        db.session.add(bookmark); saved = True
    audit(user.id, "updated_course_bookmark", "course", course.id, {"saved": saved})
    db.session.commit()
    return jsonify(message="Course saved for later." if saved else "Course removed from saved list.", bookmarked=saved)


@api.post("/courses/<int:course_id>/progress")
@jwt_required()
def save_progress(course_id):
    enrollment = Enrollment.query.filter_by(user_id=current_user().id, course_id=course_id).first()
    if not enrollment: return jsonify(error="Enroll before updating progress."), 400
    progress = int((request.get_json(silent=True) or {}).get("progress", enrollment.progress))
    enrollment.progress = max(0, min(100, progress))
    enrollment.status = "completed" if enrollment.progress == 100 else "in_progress"
    certificate_issued = certificate_issued_if_eligible(enrollment)
    audit(current_user().id, "updated_course_progress", "course", course_id, {"progress": enrollment.progress})
    db.session.commit()
    course = db.session.get(Course, course_id)
    needs_quiz = bool(assessment_for_course(course_id))
    message = "Progress saved."
    if certificate_issued:
        message = "Course and final quiz complete. Your professional certificate is ready."
    elif enrollment.progress == 100 and needs_quiz:
        message = "Weekly learning is complete. Pass the final quiz to unlock your certificate."
    return jsonify(message=message, progress=enrollment.progress, status=enrollment.status, course=course_public(course, enrollment.user_id))


@api.get("/assessments")
@jwt_required()
def assessments():
    user = current_user()
    role_courses = ensure_role_courses(user)
    entries = Assessment.query.filter(Assessment.course_id.in_([course.id for course in role_courses])).order_by(Assessment.created_at.desc()).all() if role_courses else Assessment.query.order_by(Assessment.created_at.desc()).all()
    data = []
    for item in entries:
        latest = Attempt.query.filter_by(user_id=user.id, assessment_id=item.id).order_by(Attempt.created_at.desc()).first()
        data.append({
            "id": item.id, "title": item.title, "course": item.course.title, "courseId": item.course_id,
            "skills": [skill.name for skill in Skill.query.filter(Skill.id.in_(item.course.skill_ids or [])).all()],
            "minutes": item.minutes, "passScore": item.pass_score, "attempt": {"score": latest.score, "passed": latest.score >= item.pass_score} if latest else None,
            "questions": [{"id": question.id, "prompt": question.prompt, "options": question.options, "type": question.question_type} for question in item.questions],
        })
    return jsonify(assessments=data, evidenceTypes=["practical task", "field note", "assignment", "project"])


@api.post("/assessments/<int:assessment_id>/attempt")
@jwt_required()
def submit_assessment(assessment_id):
    assessment, payload, user = db.session.get(Assessment, assessment_id), request.get_json(silent=True) or {}, current_user()
    if not assessment: return jsonify(error="Assessment not found."), 404
    answers = payload.get("answers", {})
    if not isinstance(answers, dict) or not assessment.questions: return jsonify(error="Answer the assessment questions before submitting."), 400
    correct = sum(1 for question in assessment.questions if str(answers.get(str(question.id), "")) == question.correct_answer)
    score = round((correct / len(assessment.questions)) * 100)
    attempt = Attempt(assessment_id=assessment.id, user_id=user.id, score=score, answers=answers)
    db.session.add(attempt)
    db.session.flush()
    enrollment = Enrollment.query.filter_by(user_id=user.id, course_id=assessment.course_id).first()
    certificate_issued = certificate_issued_if_eligible(enrollment) if score >= assessment.pass_score else False
    audit(user.id, "completed_assessment", "assessment", assessment.id, {"score": score})
    db.session.commit()
    message = "Assessment passed. Complete all six weeks to unlock your professional certificate."
    if certificate_issued:
        message = "Assessment passed. Your Capacity Connect professional certificate is ready to download."
    elif score < assessment.pass_score:
        message = "Keep learning and try again when you are ready."
    return jsonify(score=score, passed=score >= assessment.pass_score, passScore=assessment.pass_score, certificateIssued=certificate_issued, message=message)


@api.get("/profile")
@jwt_required()
def profile():
    user = current_user()
    skills = [{"name": item.skill.name, "level": item.level, "verified": item.verified, "domain": item.skill.domain} for item in user.user_skills]
    evidence = [{"id": e.id, "title": e.title, "skill": e.user_skill.skill.name, "status": e.status, "type": e.evidence_type} for item in user.user_skills for e in item.evidence]
    certs = [{"course": item.course.title, "code": item.verification_code, "issued": item.issued_at.date().isoformat()} for item in Certificate.query.filter_by(user_id=user.id).all()]
    return jsonify(user=user.public(), analysis=user_analysis(user), skills=skills, evidence=evidence, certificates=certs, badges=["Evidence Builder", "Monsoon Ready", "Knowledge Contributor"], growth=[{"month": "Apr", "score": 43}, {"month": "May", "score": 51}, {"month": "Jun", "score": 58}, {"month": "Jul", "score": 64}, {"month": "Aug", "score": 72}])


@api.get("/certificates")
@jwt_required()
def certificates():
    user = current_user()
    entries = Certificate.query.filter_by(user_id=user.id).order_by(Certificate.issued_at.desc()).all()
    verified = [item for item in user.user_skills if item.verified]
    return jsonify(
        certificates=[{"course": item.course.title, "code": item.verification_code, "issued": item.issued_at.date().isoformat(), "verifyUrl": f"/api/certificates/{item.verification_code}", "downloadUrl": f"/api/certificates/{item.verification_code}/download"} for item in entries],
        verifiedCompetencies=[{"skill": item.skill.name, "level": item.level, "domain": item.skill.domain} for item in verified],
        badges=["Evidence Builder", "Operational learner", "Knowledge contributor"],
    )


@api.get("/trainer/dashboard")
@roles_allowed("Trainer")
def trainer_dashboard():
    user = current_user()
    courses = Course.query.filter_by(trainer_id=user.id).all()
    pending = [item for item in SkillEvidence.query.filter_by(status="pending").all()]
    return jsonify(
        purpose="Create practical learning, review evidence, and give useful feedback.",
        courses=[course_public(item) for item in courses],
        pendingSubmissions=[{"id": item.id, "title": item.title, "learner": item.user_skill.user.name, "skill": item.user_skill.skill.name} for item in pending],
        assessmentCount=sum(len(item.assessments) for item in courses),
    )


@api.post("/trainer/courses")
@roles_allowed("Trainer")
def trainer_create_course():
    payload, user = request.get_json(silent=True) or {}, current_user()
    title, description = str(payload.get("title", "")).strip(), str(payload.get("description", "")).strip()
    skill_ids = [int(item) for item in payload.get("skillIds", []) if db.session.get(Skill, int(item))]
    if len(title) < 5 or len(description) < 15 or not skill_ids:
        return jsonify(error="Add a course title, practical description, and at least one competency."), 400
    course = Course(title=title, description=description, domain=str(payload.get("domain", "Professional Development")), level=str(payload.get("level", "Foundation")), duration_hours=max(1, min(80, int(payload.get("durationHours", 4)))), skill_ids=skill_ids, trainer_id=user.id)
    db.session.add(course); db.session.flush()
    db.session.add_all([Module(course=course, title="Learn the operational context", order=1), Module(course=course, title="Practise and submit evidence", order=2)])
    audit(user.id, "created_course", "course", course.id); db.session.commit()
    return jsonify(message="Course created for your learners.", course=course_public(course)), 201


@api.post("/trainer/courses/<int:course_id>/assessments")
@roles_allowed("Trainer")
def trainer_create_assessment(course_id):
    course, payload, user = db.session.get(Course, course_id), request.get_json(silent=True) or {}, current_user()
    if not course or course.trainer_id != user.id: return jsonify(error="Choose one of your courses."), 404
    title = str(payload.get("title", "")).strip()
    questions = payload.get("questions", [])
    if len(title) < 5 or not isinstance(questions, list) or not questions: return jsonify(error="Add an assessment title and at least one question."), 400
    assessment = Assessment(
        course_id=course.id, title=title,
        minutes=max(5, min(120, int(payload.get("minutes", 20)))),
        pass_score=max(40, min(100, int(payload.get("passScore", 70)))),
    )
    db.session.add(assessment); db.session.flush()
    for item in questions:
        if item.get("prompt") and isinstance(item.get("options"), list) and item.get("correctAnswer") in item["options"]:
            db.session.add(Question(assessment_id=assessment.id, prompt=str(item["prompt"]), options=item["options"], correct_answer=str(item["correctAnswer"])))
    audit(user.id, "created_assessment", "assessment", assessment.id); db.session.commit()
    return jsonify(message="Assessment created.", assessmentId=assessment.id), 201


@api.get("/manager/dashboard")
@roles_allowed("Manager/Department Head")
def manager_dashboard():
    manager = current_user()
    team = User.query.filter_by(department_id=manager.department_id).filter(User.id != manager.id).all()
    rows = []
    for employee in team:
        analysis = user_analysis(employee)
        rows.append({"id": employee.id, "name": employee.name, "jobRole": employee.job_role.title if employee.job_role else "Unassigned", "coverage": analysis["coverage"], "criticalGaps": len(analysis["criticalGaps"]), "goals": (employee.development_profile.target_skills if employee.development_profile else [])})
    return jsonify(purpose="See team development needs, set human-reviewed priorities, and monitor progress.", team=rows, averageCoverage=round(sum(item["coverage"] for item in rows) / len(rows)) if rows else 0)


@api.post("/manager/priorities")
@roles_allowed("Manager/Department Head")
def manager_priorities():
    payload, manager = request.get_json(silent=True) or {}, current_user()
    employee = db.session.get(User, payload.get("employeeId"))
    if not employee or employee.department_id != manager.department_id: return jsonify(error="Choose an employee in your department."), 404
    priorities = [str(item).strip() for item in payload.get("targetSkills", []) if str(item).strip()]
    profile = employee.development_profile or EmployeeProfile(user_id=employee.id)
    if not profile.id: db.session.add(profile)
    profile.target_skills = priorities[:8]
    audit(manager.id, "set_development_priorities", "user", employee.id, {"targetSkills": priorities})
    db.session.commit()
    return jsonify(message="Development priorities saved. Recommendations will reflect them."), 200


@api.get("/admin/overview")
@roles_allowed("Organization Administrator", "Super Administrator")
def admin_overview():
    return jsonify(
        purpose="Manage people, organization structure, job-role competencies, courses, and readiness reporting.",
        counts={"users": User.query.count(), "institutions": Institution.query.count(), "departments": Department.query.count(), "jobRoles": JobRole.query.count(), "courses": Course.query.count()},
        users=[{"id": item.id, "name": item.name, "email": item.email, "role": item.role.name, "department": item.department.name if item.department else "Unassigned"} for item in User.query.order_by(User.name).all()],
        jobRoles=[{"id": item.id, "title": item.title, "competencies": len(CompetencyFramework.query.filter_by(job_role_id=item.id).first().requirements) if CompetencyFramework.query.filter_by(job_role_id=item.id).first() else 0} for item in JobRole.query.order_by(JobRole.title).all()],
    )


@api.post("/evidence")
@jwt_required()
def submit_evidence():
    user, payload = current_user(), request.get_json(silent=True) or {}
    user_skill = UserSkill.query.filter_by(user_id=user.id, skill_id=payload.get("skillId")).first()
    skill_name = str(payload.get("skillName", "")).strip()
    if not user_skill and skill_name:
        skill = Skill.query.filter(func.lower(Skill.name) == skill_name.lower()).first()
        if not skill:
            domain = str(payload.get("skillDomain") or (user.job_role.domain if user.job_role else "Professional Development"))[:80]
            skill = Skill(name=skill_name[:120], domain=domain, description=f"Learner-selected competency: {skill_name[:120]}", importance=3)
            db.session.add(skill)
            db.session.flush()
        user_skill = UserSkill.query.filter_by(user_id=user.id, skill_id=skill.id).first()
        if not user_skill:
            user_skill = UserSkill(user_id=user.id, skill_id=skill.id, level=1, verified=False)
            db.session.add(user_skill)
            db.session.flush()
    if not user_skill: return jsonify(error="Type a competency or choose one of the suggested options."), 400
    title = str(payload.get("title", "")).strip()
    if len(title) < 4: return jsonify(error="Evidence title must be at least four characters."), 400
    evidence = SkillEvidence(user_skill_id=user_skill.id, title=title, evidence_type=payload.get("type", "project"), notes=payload.get("notes", ""))
    db.session.add(evidence); audit(user.id, "submitted_evidence", "skill_evidence", "pending", {"title": title}); db.session.commit()
    return jsonify(message="Evidence submitted for expert review.", evidenceId=evidence.id), 201


@api.get("/evidence/pending")
@roles_allowed("Trainer", "Subject-Matter Expert/Mentor", "Organization Administrator", "Super Administrator")
def pending_evidence():
    reviewer = current_user()
    entries = SkillEvidence.query.filter_by(status="pending").order_by(SkillEvidence.created_at.asc()).all()
    return jsonify(submissions=[{
        "id": item.id, "title": item.title, "type": item.evidence_type, "notes": item.notes,
        "employee": item.user_skill.user.name, "skill": item.user_skill.skill.name,
        "submitted": item.created_at.date().isoformat(), "reviewerRole": reviewer.role.name,
    } for item in entries])


@api.post("/evidence/<int:evidence_id>/review")
@roles_allowed("Trainer", "Subject-Matter Expert/Mentor", "Organization Administrator", "Super Administrator")
def review_evidence(evidence_id):
    evidence, payload, reviewer = db.session.get(SkillEvidence, evidence_id), request.get_json(silent=True) or {}, current_user()
    if not evidence: return jsonify(error="Evidence not found."), 404
    decision = payload.get("decision")
    if decision not in {"approved", "revisions_requested", "rejected"}: return jsonify(error="Use approved, revisions_requested, or rejected."), 400
    evidence.status = decision
    if decision == "approved": evidence.user_skill.verified = True
    db.session.add(VerificationRecord(evidence_id=evidence.id, verifier_id=reviewer.id, decision=decision, feedback=payload.get("feedback", "")))
    audit(reviewer.id, "reviewed_evidence", "skill_evidence", evidence.id, {"decision": decision}); db.session.commit()
    return jsonify(message="Verification decision saved.", status=decision)


@api.post("/knowledge/search")
@jwt_required()
def knowledge_search():
    query = (request.get_json(silent=True) or {}).get("query", "").strip().lower()
    if not query: return jsonify(error="Enter a search question."), 400
    chunks = KnowledgeChunk.query.join(KnowledgeDocument).filter(KnowledgeDocument.status == "approved").all()
    result = answer_with_provider(query, chunks)
    return jsonify(**result, disclaimer="Prithvi AI answers only from approved organizational sources. Verify guidance against operating procedures.")


@api.get("/knowledge/documents")
@jwt_required()
def knowledge_documents():
    docs = KnowledgeDocument.query.order_by(KnowledgeDocument.created_at.desc()).all()
    return jsonify(documents=[{"id": doc.id, "title": doc.title, "domain": doc.domain, "status": doc.status, "type": doc.source_type, "chunks": len(doc.chunks)} for doc in docs])


@api.get("/mentors")
@jwt_required()
def mentors():
    user, analysis = current_user(), user_analysis(current_user())
    gap_ids = {row["skillId"] for row in analysis["requirements"] if row["gapPercent"]}
    role_profiles = ensure_role_mentors(user)
    profiles = role_profiles or MentorProfile.query.filter(MentorProfile.user_id != user.id).all()
    role_course = ensure_role_courses(user)
    if role_course:
        gap_ids.update(role_course[0].skill_ids or [])
    data = []
    for profile in profiles:
        mentor_skills = [db.session.get(Skill, skill_id) for skill_id in profile.skill_ids]
        mentor_skill_names = [skill.name for skill in mentor_skills if skill]
        matched = [skill.name for skill in mentor_skills if skill and skill.id in gap_ids]
        data.append({"id": profile.id, "name": profile.user.name, "institution": profile.user.institution.name, "department": profile.user.department.name if profile.user.department else "", "bio": profile.bio, "availability": profile.availability, "skills": mentor_skill_names, "languages": profile.languages, "matchReason": f"Matches {', '.join(matched[:2]) or 'your learning goals'} and is available {profile.availability}."})
    data.sort(key=lambda item: sum(skill in item["matchReason"] for skill in item["skills"]), reverse=True)
    return jsonify(mentors=data, roleMatched=bool(role_profiles), role=user.job_role.title if user.job_role else None)


@api.post("/mentors/requests")
@jwt_required()
def request_mentor():
    payload, user = request.get_json(silent=True) or {}, current_user()
    profile = db.session.get(MentorProfile, payload.get("mentorId"))
    if not profile or profile.user_id == user.id: return jsonify(error="Choose a valid mentor."), 400
    goal = str(payload.get("goal", "")).strip()
    if len(goal) < 8: return jsonify(error="Tell the mentor a little more about your learning goal."), 400
    record = MentoringRequest(learner_id=user.id, mentor_id=profile.id, goal=goal)
    db.session.add(record); db.session.add(Notification(user_id=profile.user_id, title="New mentoring request", body=f"{user.name} requested support: {goal}")); audit(user.id, "requested_mentoring", "mentor", profile.id); db.session.commit()
    return jsonify(message="Mentoring request sent.", requestId=record.id), 201


@api.get("/community/posts")
@jwt_required()
def posts():
    entries = CommunityPost.query.order_by(CommunityPost.created_at.desc()).all()
    return jsonify(posts=[{"id": post.id, "title": post.title, "body": post.body, "tags": post.tags, "type": post.post_type, "author": post.author.name, "comments": len(post.comments), "date": post.created_at.strftime("%d %b")} for post in entries])


@api.post("/community/posts")
@jwt_required()
def create_post():
    payload, user = request.get_json(silent=True) or {}, current_user()
    title, body = str(payload.get("title", "")).strip(), str(payload.get("body", "")).strip()
    if len(title) < 5 or len(body) < 15: return jsonify(error="Add a descriptive title and a useful post of at least 15 characters."), 400
    post = CommunityPost(author_id=user.id, title=title, body=body, tags=payload.get("tags", []), post_type=payload.get("type", "discussion"))
    db.session.add(post); audit(user.id, "created_community_post", "post", "pending"); db.session.commit()
    return jsonify(message="Your knowledge post is now visible to the community.", id=post.id), 201


@api.get("/scenarios")
@jwt_required()
def scenarios():
    entries = ScenarioLab.query.all()
    return jsonify(scenarios=[{"id": item.id, "title": item.title, "domain": item.domain, "situation": item.situation, "decisions": [{"id": choice["id"], "label": choice["label"]} for choice in item.decisions], "competencies": [Skill.query.get(skill_id).name for skill_id in item.competency_ids]} for item in entries])


@api.post("/scenarios/<int:scenario_id>/attempt")
@jwt_required()
def attempt_scenario(scenario_id):
    scenario, payload = db.session.get(ScenarioLab, scenario_id), request.get_json(silent=True) or {}
    if not scenario: return jsonify(error="Scenario not found."), 404
    choice = next((item for item in scenario.decisions if item["id"] == payload.get("decision")), None)
    if not choice: return jsonify(error="Choose one of the provided actions."), 400
    attempt = ScenarioAttempt(scenario_id=scenario.id, user_id=current_user().id, decision=choice["id"], score=choice["score"])
    db.session.add(attempt); audit(current_user().id, "completed_scenario", "scenario", scenario.id, {"score": choice["score"]}); db.session.commit()
    return jsonify(score=choice["score"], consequence=choice["consequence"], explanation=choice["explanation"], improvement=choice["improvement"], competencies=[Skill.query.get(skill_id).name for skill_id in scenario.competency_ids])


@api.get("/notifications")
@jwt_required()
def notifications():
    entries = Notification.query.filter_by(user_id=current_user().id).order_by(Notification.created_at.desc()).all()
    return jsonify(notifications=[{"id": item.id, "title": item.title, "body": item.body, "read": item.read, "time": item.created_at.strftime("%d %b %H:%M")} for item in entries])


def draw_centered_fitted(pdf, value, y, maximum_width, font="Helvetica-Bold", size=28, minimum_size=16):
    """Draw a single professional certificate line without overflowing its border."""
    value = str(value)
    current_size = size
    while current_size > minimum_size and stringWidth(value, font, current_size) > maximum_width:
        current_size -= 1
    pdf.setFont(font, current_size)
    pdf.drawCentredString(landscape(A4)[0] / 2, y, value)


@api.get("/certificates/<code>/download")
def download_certificate(code):
    item = Certificate.query.filter_by(verification_code=code.upper()).first()
    if not item:
        return jsonify(error="No certificate found with that verification code."), 404

    width, height = landscape(A4)
    stream = BytesIO()
    pdf = canvas.Canvas(stream, pagesize=(width, height), pageCompression=1)
    # A restrained professional certificate rather than a browser screenshot.
    pdf.setFillColor(colors.HexColor("#06111f"))
    pdf.rect(0, 0, width, height, stroke=0, fill=1)
    pdf.setStrokeColor(colors.HexColor("#21d4fd"))
    pdf.setLineWidth(1.5)
    pdf.rect(14 * mm, 14 * mm, width - 28 * mm, height - 28 * mm, stroke=1, fill=0)
    pdf.setStrokeColor(colors.HexColor("#6ee7b7"))
    pdf.setLineWidth(0.5)
    pdf.rect(18 * mm, 18 * mm, width - 36 * mm, height - 36 * mm, stroke=1, fill=0)
    pdf.setFillColor(colors.HexColor("#21d4fd"))
    pdf.setFont("Helvetica-Bold", 17)
    pdf.drawCentredString(width / 2, height - 40 * mm, "CAPACITY CONNECT")
    pdf.setFillColor(colors.white)
    pdf.setFont("Helvetica-Bold", 31)
    pdf.drawCentredString(width / 2, height - 57 * mm, "Certificate of Professional Completion")
    pdf.setFillColor(colors.HexColor("#b9c9dc"))
    pdf.setFont("Helvetica", 13)
    pdf.drawCentredString(width / 2, height - 75 * mm, "This certifies that")
    pdf.setFillColor(colors.HexColor("#6ee7b7"))
    draw_centered_fitted(pdf, item.user.name, height - 93 * mm, width - 90 * mm, size=30)
    pdf.setFillColor(colors.HexColor("#b9c9dc"))
    pdf.setFont("Helvetica", 13)
    pdf.drawCentredString(width / 2, height - 110 * mm, "has successfully completed the professional learning programme")
    pdf.setFillColor(colors.white)
    draw_centered_fitted(pdf, item.course.title, height - 127 * mm, width - 80 * mm, size=23, minimum_size=13)
    issued = item.issued_at.strftime("%d %B %Y")
    pdf.setFillColor(colors.HexColor("#b9c9dc"))
    pdf.setFont("Helvetica", 12)
    pdf.drawCentredString(width / 2, height - 145 * mm, f"Completed on {issued}")
    pdf.setStrokeColor(colors.HexColor("#21d4fd"))
    pdf.line(width / 2 - 44 * mm, height - 168 * mm, width / 2 + 44 * mm, height - 168 * mm)
    pdf.setFillColor(colors.HexColor("#6ee7b7"))
    pdf.setFont("Helvetica-Bold", 11)
    pdf.drawCentredString(width / 2, height - 177 * mm, "CAPACITY CONNECT LEARNING OFFICE")
    pdf.setFillColor(colors.HexColor("#b9c9dc"))
    pdf.setFont("Helvetica", 9)
    pdf.drawCentredString(width / 2, 25 * mm, f"Verification code: {item.verification_code}  |  Verify at Capacity Connect")
    pdf.save()
    stream.seek(0)
    return send_file(stream, mimetype="application/pdf", as_attachment=True, download_name=f"Capacity-Connect-{item.verification_code}.pdf")


@api.get("/certificates/<code>")
def certificate(code):
    item = Certificate.query.filter_by(verification_code=code).first()
    if not item: return jsonify(valid=False, message="No certificate found with that verification code."), 404
    return jsonify(valid=True, learner=item.user.name, course=item.course.title, issued=item.issued_at.date().isoformat(), verificationCode=item.verification_code)
