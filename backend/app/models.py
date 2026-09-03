from datetime import datetime
from werkzeug.security import check_password_hash, generate_password_hash
from . import db


class TimestampMixin:
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class Role(db.Model, TimestampMixin):
    __tablename__ = "roles"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(60), unique=True, nullable=False, index=True)
    description = db.Column(db.String(255), nullable=False)


class Institution(db.Model, TimestampMixin):
    __tablename__ = "institutions"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), unique=True, nullable=False)
    code = db.Column(db.String(20), unique=True, nullable=False)
    location = db.Column(db.String(120), nullable=False)


class Department(db.Model, TimestampMixin):
    __tablename__ = "departments"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    institution_id = db.Column(db.Integer, db.ForeignKey("institutions.id"), nullable=False, index=True)
    institution = db.relationship("Institution", backref="departments")
    __table_args__ = (db.UniqueConstraint("name", "institution_id", name="uq_department_institution"),)


class JobRole(db.Model, TimestampMixin):
    __tablename__ = "job_roles"
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(120), unique=True, nullable=False)
    domain = db.Column(db.String(80), nullable=False, index=True)
    description = db.Column(db.Text, nullable=False)


class User(db.Model, TimestampMixin):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    employee_id = db.Column(db.String(40), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role_id = db.Column(db.Integer, db.ForeignKey("roles.id"), nullable=False, index=True)
    institution_id = db.Column(db.Integer, db.ForeignKey("institutions.id"), nullable=False, index=True)
    department_id = db.Column(db.Integer, db.ForeignKey("departments.id"), nullable=True, index=True)
    job_role_id = db.Column(db.Integer, db.ForeignKey("job_roles.id"), nullable=True, index=True)
    experience_years = db.Column(db.Integer, default=0, nullable=False)
    language = db.Column(db.String(20), default="English", nullable=False)
    ai_consent = db.Column(db.Boolean, default=False, nullable=False)
    role = db.relationship("Role")
    institution = db.relationship("Institution")
    department = db.relationship("Department")
    job_role = db.relationship("JobRole")
    development_profile = db.relationship("EmployeeProfile", backref="user", uselist=False, cascade="all, delete-orphan")

    def set_password(self, password): self.password_hash = generate_password_hash(password)
    def check_password(self, password): return check_password_hash(self.password_hash, password)
    def public(self):
        return {"id": self.id, "name": self.name, "email": self.email, "employeeId": self.employee_id,
                "role": self.role.name, "institution": self.institution.name,
                "department": self.department.name if self.department else None,
                "jobRole": self.job_role.title if self.job_role else None, "language": self.language}


class EmployeeProfile(db.Model, TimestampMixin):
    """Employment and learning preferences only; deliberately excludes sensitive personal data."""
    __tablename__ = "employee_profiles"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), unique=True, nullable=False, index=True)
    designation = db.Column(db.String(120), nullable=True)
    work_location = db.Column(db.String(120), nullable=True)
    employment_type = db.Column(db.String(40), nullable=True)
    joining_date = db.Column(db.Date, nullable=True)
    reporting_manager = db.Column(db.String(120), nullable=True)
    responsibilities = db.Column(db.Text, nullable=True)
    certifications_resume = db.Column(db.Text, nullable=True)
    languages_known = db.Column(db.JSON, default=list, nullable=False)
    target_skills = db.Column(db.JSON, default=list, nullable=False)
    development_goals = db.Column(db.Text, nullable=True)
    available_times = db.Column(db.JSON, default=dict, nullable=False)
    hours_per_week = db.Column(db.Integer, default=4, nullable=False)
    preferred_training_language = db.Column(db.String(40), default="English", nullable=False)
    learning_preference = db.Column(db.String(30), default="Blended", nullable=False)
    onboarding_complete = db.Column(db.Boolean, default=False, nullable=False)


class Skill(db.Model, TimestampMixin):
    __tablename__ = "skills"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), unique=True, nullable=False, index=True)
    domain = db.Column(db.String(80), nullable=False, index=True)
    description = db.Column(db.Text, nullable=False)
    importance = db.Column(db.Integer, default=3, nullable=False)
    related_skill_ids = db.Column(db.JSON, default=list, nullable=False)


class CompetencyFramework(db.Model, TimestampMixin):
    __tablename__ = "competency_frameworks"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(140), nullable=False)
    job_role_id = db.Column(db.Integer, db.ForeignKey("job_roles.id"), nullable=False, index=True)
    version = db.Column(db.String(24), default="1.0", nullable=False)
    job_role = db.relationship("JobRole", backref="frameworks")


class RoleSkillRequirement(db.Model, TimestampMixin):
    __tablename__ = "role_skill_requirements"
    id = db.Column(db.Integer, primary_key=True)
    framework_id = db.Column(db.Integer, db.ForeignKey("competency_frameworks.id"), nullable=False, index=True)
    skill_id = db.Column(db.Integer, db.ForeignKey("skills.id"), nullable=False, index=True)
    required_level = db.Column(db.Integer, nullable=False)
    criticality = db.Column(db.String(20), default="mandatory", nullable=False)
    expiry_months = db.Column(db.Integer, nullable=True)
    framework = db.relationship("CompetencyFramework", backref="requirements")
    skill = db.relationship("Skill")
    __table_args__ = (db.UniqueConstraint("framework_id", "skill_id", name="uq_framework_skill"),)


class UserSkill(db.Model, TimestampMixin):
    __tablename__ = "user_skills"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    skill_id = db.Column(db.Integer, db.ForeignKey("skills.id"), nullable=False, index=True)
    level = db.Column(db.Integer, nullable=False)
    verified = db.Column(db.Boolean, default=False, nullable=False)
    expires_at = db.Column(db.DateTime, nullable=True)
    user = db.relationship("User", backref="user_skills")
    skill = db.relationship("Skill")
    __table_args__ = (db.UniqueConstraint("user_id", "skill_id", name="uq_user_skill"),)


class SkillEvidence(db.Model, TimestampMixin):
    __tablename__ = "skill_evidence"
    id = db.Column(db.Integer, primary_key=True)
    user_skill_id = db.Column(db.Integer, db.ForeignKey("user_skills.id"), nullable=False, index=True)
    title = db.Column(db.String(180), nullable=False)
    evidence_type = db.Column(db.String(40), nullable=False)
    file_url = db.Column(db.String(255), nullable=True)
    notes = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(20), default="pending", nullable=False, index=True)
    user_skill = db.relationship("UserSkill", backref="evidence")


class VerificationRecord(db.Model, TimestampMixin):
    __tablename__ = "verification_records"
    id = db.Column(db.Integer, primary_key=True)
    evidence_id = db.Column(db.Integer, db.ForeignKey("skill_evidence.id"), nullable=False, index=True)
    verifier_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    decision = db.Column(db.String(20), nullable=False)
    feedback = db.Column(db.Text, nullable=True)
    evidence = db.relationship("SkillEvidence", backref="verification_records")
    verifier = db.relationship("User")


class Course(db.Model, TimestampMixin):
    __tablename__ = "courses"
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(180), nullable=False)
    description = db.Column(db.Text, nullable=False)
    domain = db.Column(db.String(80), nullable=False, index=True)
    level = db.Column(db.String(30), nullable=False)
    duration_hours = db.Column(db.Integer, nullable=False)
    skill_ids = db.Column(db.JSON, default=list, nullable=False)
    trainer_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    trainer = db.relationship("User")


class Module(db.Model, TimestampMixin):
    __tablename__ = "modules"
    id = db.Column(db.Integer, primary_key=True)
    course_id = db.Column(db.Integer, db.ForeignKey("courses.id"), nullable=False, index=True)
    title = db.Column(db.String(180), nullable=False)
    order = db.Column(db.Integer, nullable=False)
    course = db.relationship("Course", backref="modules")


class Lesson(db.Model, TimestampMixin):
    __tablename__ = "lessons"
    id = db.Column(db.Integer, primary_key=True)
    module_id = db.Column(db.Integer, db.ForeignKey("modules.id"), nullable=False, index=True)
    title = db.Column(db.String(180), nullable=False)
    content_type = db.Column(db.String(30), nullable=False)
    content_url = db.Column(db.String(255), nullable=True)
    body = db.Column(db.Text, nullable=True)
    duration_minutes = db.Column(db.Integer, default=15, nullable=False)
    module = db.relationship("Module", backref="lessons")


class LessonProgress(db.Model, TimestampMixin):
    """A learner's durable completion record for an individual course lesson."""
    __tablename__ = "lesson_progress"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    lesson_id = db.Column(db.Integer, db.ForeignKey("lessons.id"), nullable=False, index=True)
    user = db.relationship("User", backref="lesson_progress_records")
    lesson = db.relationship("Lesson", backref="progress_records")
    __table_args__ = (db.UniqueConstraint("user_id", "lesson_id", name="uq_lesson_progress"),)


class Enrollment(db.Model, TimestampMixin):
    __tablename__ = "enrollments"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    course_id = db.Column(db.Integer, db.ForeignKey("courses.id"), nullable=False, index=True)
    progress = db.Column(db.Integer, default=0, nullable=False)
    status = db.Column(db.String(20), default="enrolled", nullable=False)
    user = db.relationship("User", backref="enrollments")
    course = db.relationship("Course", backref="enrollments")
    __table_args__ = (db.UniqueConstraint("user_id", "course_id", name="uq_enrollment"),)


class CourseBookmark(db.Model, TimestampMixin):
    __tablename__ = "course_bookmarks"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    course_id = db.Column(db.Integer, db.ForeignKey("courses.id"), nullable=False, index=True)
    note = db.Column(db.String(255), nullable=True)
    user = db.relationship("User", backref="course_bookmarks")
    course = db.relationship("Course")
    __table_args__ = (db.UniqueConstraint("user_id", "course_id", name="uq_course_bookmark"),)


class Assessment(db.Model, TimestampMixin):
    __tablename__ = "assessments"
    id = db.Column(db.Integer, primary_key=True)
    course_id = db.Column(db.Integer, db.ForeignKey("courses.id"), nullable=False, index=True)
    title = db.Column(db.String(180), nullable=False)
    minutes = db.Column(db.Integer, nullable=False)
    pass_score = db.Column(db.Integer, default=70, nullable=False)
    course = db.relationship("Course", backref="assessments")


class Question(db.Model, TimestampMixin):
    __tablename__ = "questions"
    id = db.Column(db.Integer, primary_key=True)
    assessment_id = db.Column(db.Integer, db.ForeignKey("assessments.id"), nullable=False, index=True)
    prompt = db.Column(db.Text, nullable=False)
    options = db.Column(db.JSON, default=list, nullable=False)
    correct_answer = db.Column(db.String(255), nullable=False)
    question_type = db.Column(db.String(30), default="multiple_choice", nullable=False)
    assessment = db.relationship("Assessment", backref="questions")


class Attempt(db.Model, TimestampMixin):
    __tablename__ = "attempts"
    id = db.Column(db.Integer, primary_key=True)
    assessment_id = db.Column(db.Integer, db.ForeignKey("assessments.id"), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    score = db.Column(db.Integer, nullable=False)
    answers = db.Column(db.JSON, default=dict, nullable=False)
    assessment = db.relationship("Assessment")
    user = db.relationship("User")


class LearningPath(db.Model, TimestampMixin):
    __tablename__ = "learning_paths"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    title = db.Column(db.String(180), nullable=False)
    plan = db.Column(db.JSON, default=list, nullable=False)
    status = db.Column(db.String(20), default="active", nullable=False)
    user = db.relationship("User", backref="learning_paths")


class MentorProfile(db.Model, TimestampMixin):
    __tablename__ = "mentors"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), unique=True, nullable=False)
    bio = db.Column(db.Text, nullable=False)
    availability = db.Column(db.String(80), nullable=False)
    skill_ids = db.Column(db.JSON, default=list, nullable=False)
    languages = db.Column(db.JSON, default=list, nullable=False)
    user = db.relationship("User", backref=db.backref("mentor_profile", uselist=False))


class MentoringRequest(db.Model, TimestampMixin):
    __tablename__ = "mentoring_requests"
    id = db.Column(db.Integer, primary_key=True)
    learner_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    mentor_id = db.Column(db.Integer, db.ForeignKey("mentors.id"), nullable=False, index=True)
    goal = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(20), default="pending", nullable=False)
    learner = db.relationship("User")
    mentor = db.relationship("MentorProfile")


class MentorSession(db.Model, TimestampMixin):
    __tablename__ = "mentor_sessions"
    id = db.Column(db.Integer, primary_key=True)
    request_id = db.Column(db.Integer, db.ForeignKey("mentoring_requests.id"), nullable=False)
    scheduled_for = db.Column(db.DateTime, nullable=False)
    notes = db.Column(db.Text, nullable=True)
    request = db.relationship("MentoringRequest", backref="sessions")


class KnowledgeDocument(db.Model, TimestampMixin):
    __tablename__ = "knowledge_documents"
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(180), nullable=False)
    domain = db.Column(db.String(80), nullable=False, index=True)
    access_level = db.Column(db.String(40), default="organization", nullable=False)
    status = db.Column(db.String(20), default="approved", nullable=False, index=True)
    source_type = db.Column(db.String(40), default="document", nullable=False)


class KnowledgeChunk(db.Model, TimestampMixin):
    __tablename__ = "knowledge_chunks"
    id = db.Column(db.Integer, primary_key=True)
    document_id = db.Column(db.Integer, db.ForeignKey("knowledge_documents.id"), nullable=False, index=True)
    section = db.Column(db.String(100), nullable=False)
    content = db.Column(db.Text, nullable=False)
    keywords = db.Column(db.JSON, default=list, nullable=False)
    document = db.relationship("KnowledgeDocument", backref="chunks")


class CommunityPost(db.Model, TimestampMixin):
    __tablename__ = "community_posts"
    id = db.Column(db.Integer, primary_key=True)
    author_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    title = db.Column(db.String(180), nullable=False)
    body = db.Column(db.Text, nullable=False)
    tags = db.Column(db.JSON, default=list, nullable=False)
    post_type = db.Column(db.String(30), default="discussion", nullable=False)
    author = db.relationship("User")


class Comment(db.Model, TimestampMixin):
    __tablename__ = "comments"
    id = db.Column(db.Integer, primary_key=True)
    post_id = db.Column(db.Integer, db.ForeignKey("community_posts.id"), nullable=False, index=True)
    author_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    body = db.Column(db.Text, nullable=False)
    accepted = db.Column(db.Boolean, default=False, nullable=False)
    post = db.relationship("CommunityPost", backref="comments")
    author = db.relationship("User")


class Notification(db.Model, TimestampMixin):
    __tablename__ = "notifications"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    title = db.Column(db.String(180), nullable=False)
    body = db.Column(db.Text, nullable=False)
    read = db.Column(db.Boolean, default=False, nullable=False)
    user = db.relationship("User", backref="notifications")


class ScenarioLab(db.Model, TimestampMixin):
    __tablename__ = "scenario_labs"
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(180), nullable=False)
    domain = db.Column(db.String(80), nullable=False)
    situation = db.Column(db.Text, nullable=False)
    decisions = db.Column(db.JSON, nullable=False)
    competency_ids = db.Column(db.JSON, default=list, nullable=False)


class ScenarioAttempt(db.Model, TimestampMixin):
    __tablename__ = "scenario_attempts"
    id = db.Column(db.Integer, primary_key=True)
    scenario_id = db.Column(db.Integer, db.ForeignKey("scenario_labs.id"), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    decision = db.Column(db.String(255), nullable=False)
    score = db.Column(db.Integer, nullable=False)
    scenario = db.relationship("ScenarioLab")
    user = db.relationship("User")


class Certificate(db.Model, TimestampMixin):
    __tablename__ = "certificates"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    course_id = db.Column(db.Integer, db.ForeignKey("courses.id"), nullable=False)
    verification_code = db.Column(db.String(64), unique=True, nullable=False, index=True)
    issued_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    user = db.relationship("User")
    course = db.relationship("Course")


class AuditLog(db.Model, TimestampMixin):
    __tablename__ = "audit_logs"
    id = db.Column(db.Integer, primary_key=True)
    actor_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True, index=True)
    action = db.Column(db.String(100), nullable=False, index=True)
    target_type = db.Column(db.String(60), nullable=False)
    target_id = db.Column(db.String(60), nullable=False)
    metadata_json = db.Column(db.JSON, default=dict, nullable=False)
    actor = db.relationship("User")
