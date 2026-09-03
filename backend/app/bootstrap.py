"""Small, idempotent catalogue used only when a hosted database is brand new."""

from . import db
from .models import Department, Institution, JobRole, Role


ROLE_DATA = (
    ("Employee/Learner", "Builds verified competencies through learning and evidence."),
    ("Trainer", "Creates and evaluates structured learning."),
    ("Subject-Matter Expert/Mentor", "Reviews evidence and preserves expert knowledge."),
    ("Manager/Department Head", "Guides team readiness and capacity building."),
    ("Organization Administrator", "Manages competency frameworks and institutional learning."),
    ("Super Administrator", "Maintains organization-wide platform governance."),
)

JOB_ROLE_DATA = (
    ("Data Analyst", "Data & Digital", "Interprets data and communicates decision-ready insights."),
    ("Frontend Developer", "Software Development", "Builds accessible, responsive web interfaces."),
    ("Backend Developer", "Software Development", "Builds reliable APIs, data services, and integrations."),
    ("Full-Stack Developer", "Software Development", "Connects user interfaces with secure application services."),
    ("AI/ML Engineer", "Data & Digital", "Designs, evaluates, and deploys responsible machine-learning systems."),
    ("GIS Analyst", "Data & Digital", "Uses spatial data and maps to produce operational insights."),
    ("Research Scientist", "Research", "Plans and communicates reproducible scientific research."),
    ("Meteorologist", "Weather & Climate", "Interprets weather information for forecasts and decisions."),
    ("Oceanographer", "Ocean Science", "Analyses ocean observations and coastal information."),
    ("Climate Data Specialist", "Weather & Climate", "Works with climate data, trends, and risk information."),
)


def ensure_platform_baseline():
    """Create registration choices without touching an established deployment."""
    changed = False
    for name, description in ROLE_DATA:
        if not Role.query.filter_by(name=name).first():
            db.session.add(Role(name=name, description=description))
            changed = True

    institution = Institution.query.filter_by(code="CCLN").first()
    if not institution:
        institution = Institution(
            name="Capacity Connect Learning Network",
            code="CCLN",
            location="India",
        )
        db.session.add(institution)
        db.session.flush()
        changed = True

    if not Department.query.filter_by(name="Learning & Digital Services", institution_id=institution.id).first():
        db.session.add(Department(name="Learning & Digital Services", institution_id=institution.id))
        changed = True

    for title, domain, description in JOB_ROLE_DATA:
        if not JobRole.query.filter_by(title=title).first():
            db.session.add(JobRole(title=title, domain=domain, description=description))
            changed = True

    if changed:
        db.session.commit()
