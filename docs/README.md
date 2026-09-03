# Capacity Connect

**Capacity Connect – AI-Powered Digital Capacity Building and Learning Management Portal** is a Smart India Hackathon prototype for the Ministry of Earth Sciences (MoES) Smart Education / Skill Development theme.

> Capacity Connect does not merely track course completion. It converts organizational knowledge into verified competency and measurable workforce readiness.

## What is included

- React, Vite, TypeScript, Tailwind, Framer Motion, Recharts, and React Three Fiber frontend.
- Flask REST API using Flask-SQLAlchemy and Flask-JWT-Extended; MySQL is production-ready and SQLite is a zero-setup demo fallback.
- Six role definitions and role-enforced API actions.
- Transparent competency framework scoring, a real SQL-backed 3D Skill Galaxy, adaptive roadmap, courses, progress, certificates, and evidence verification audit trail.
- Prithvi AI grounded retrieval with document/section citations. It uses Gemini when configured and a local lexical retrieval fallback when it is not.
- Expert finder, mentoring requests, Knowledge Legacy Vault documents, community posts, notifications, and a complete severe-weather Scenario Lab.
- Responsive accessible interface, reduced-motion support, PWA configuration, and API tests.

## Folder structure

```text
capacity-connect/
├── frontend/                  # React web and installable PWA
│   └── src/
│       ├── components/GalaxyScene.tsx
│       ├── App.tsx
│       └── styles.css
├── backend/
│   ├── app/models.py          # normalized SQLAlchemy schema
│   ├── app/routes.py          # protected REST endpoints
│   ├── app/services/ai.py     # Gemini provider + trusted local fallback
│   ├── migrations/            # Flask-Migrate notes
│   ├── tests/test_api.py
│   ├── seed.py
│   └── wsgi.py
├── .env.example
└── docs/README.md
```

## Run it on Windows

Prerequisites: Node.js 20+, Python 3.11+, and optionally MySQL 8+. Use two PowerShell terminals from the `capacity-connect` directory.

```powershell
# Terminal 1 – backend
cd backend
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
python seed.py
python wsgi.py
```

```powershell
# Terminal 2 – frontend
cd frontend
npm install
Copy-Item .env.example .env
npm run dev
```

Open `http://localhost:5173`. The API is at `http://localhost:5000/api`.

### Demo mode with SQLite

Do not set `DATABASE_URL`; `seed.py` uses `backend/capacity_connect.db`. This is the quickest path for a laptop demo and still uses the same SQLAlchemy models and API flows.

### MySQL setup

```sql
CREATE DATABASE capacity_connect CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'capacity_user'@'localhost' IDENTIFIED BY 'use-a-strong-password';
GRANT ALL PRIVILEGES ON capacity_connect.* TO 'capacity_user'@'localhost';
FLUSH PRIVILEGES;
```

Set this in `backend/.env`:

```env
DATABASE_URL=mysql+pymysql://capacity_user:use-a-strong-password@localhost/capacity_connect
```

Create versioned migrations after configuring MySQL:

```powershell
flask --app wsgi db init
flask --app wsgi db migrate -m "initial Capacity Connect schema"
flask --app wsgi db upgrade
python seed.py
```

## Demo credentials

All accounts use the password `Demo@123`.

| Role | Email |
|---|---|
| Employee / Learner | `learner@capacityconnect.in` |
| Trainer | `trainer@capacityconnect.in` |
| Subject-Matter Expert / Mentor | `expert@capacityconnect.in` |
| Manager / Department Head | `manager@capacityconnect.in` |
| Organization Administrator | `admin@capacityconnect.in` |
| Super Administrator | `superadmin@capacityconnect.in` |

## Gemini configuration and safe fallback

1. Create an API key in [Google AI Studio](https://aistudio.google.com/).
2. Add `GEMINI_API_KEY=your-key` and `GEMINI_MODEL=gemini-3.7-flash` to `backend/.env`.
3. Restart the Flask server.

The application does not need a Gemini key to work. `app/services/ai.py` ranks approved `KnowledgeChunk` records locally and responds only when a trusted source matches. When Gemini is configured, it receives only the already-selected approved context and is instructed to refuse unsupported answers. Responses identify the configured Gemini model or **Local trusted retrieval**.

AI skill-gap suggestions are clearly advisory; they never make employment decisions and remain editable by the learner or manager.

## API map

| Method | Endpoint | Purpose |
|---|---|---|
| POST | `/api/auth/login` | JWT login with rate limiting |
| GET | `/api/me` | Current user and competency summary |
| GET | `/api/dashboard` | Learner and manager metrics |
| GET | `/api/skills/galaxy` | SQL-backed 3D / accessible skill nodes |
| POST | `/api/skills/analyze` | Explainable skill-gap and weekly plan |
| GET | `/api/courses` | Searchable learning catalogue |
| POST | `/api/courses/:id/enroll` | Enrol in a course |
| POST | `/api/courses/:id/progress` | Save progress and issue completion certificate |
| GET | `/api/profile` | Competency passport, evidence, badges |
| POST | `/api/evidence` | Submit evidence for expert review |
| POST | `/api/evidence/:id/review` | Authorized verification decision |
| POST | `/api/knowledge/search` | Prithvi AI trusted-source search |
| GET | `/api/mentors` | Explainable mentor recommendations |
| POST | `/api/mentors/requests` | Send mentoring request |
| GET/POST | `/api/community/posts` | Knowledge-sharing community |
| GET | `/api/scenarios` | Scenario Lab content |
| POST | `/api/scenarios/:id/attempt` | Score a learner decision |
| GET | `/api/certificates/:code` | Public certificate verification |

## Architecture

```mermaid
flowchart LR
  U[Employee / Trainer / Expert / Manager] --> W[React + Vite PWA]
  W -->|JWT REST| A[Flask API]
  A --> C[Competency engine]
  A --> L[LMS, evidence, mentor, scenario services]
  A --> K[Prithvi AI provider]
  K -->|optional| G[Gemini API]
  K -->|always available| R[Local trusted retrieval]
  A --> D[(MySQL / SQLite demo)]
  D --> S[Skills, framework, evidence, knowledge chunks]
```

## Database ER diagram

```mermaid
erDiagram
  USERS }o--|| ROLES : has
  USERS }o--|| INSTITUTIONS : belongs_to
  USERS }o--o| JOB_ROLES : holds
  JOB_ROLES ||--o{ COMPETENCY_FRAMEWORKS : defines
  COMPETENCY_FRAMEWORKS ||--o{ ROLE_SKILL_REQUIREMENTS : requires
  ROLE_SKILL_REQUIREMENTS }o--|| SKILLS : references
  USERS ||--o{ USER_SKILLS : develops
  USER_SKILLS }o--|| SKILLS : measures
  USER_SKILLS ||--o{ SKILL_EVIDENCE : proves
  SKILL_EVIDENCE ||--o{ VERIFICATION_RECORDS : reviewed_by
  COURSES ||--o{ MODULES : contains
  MODULES ||--o{ LESSONS : contains
  USERS ||--o{ ENROLLMENTS : takes
  COURSES ||--o{ ENROLLMENTS : tracks
  KNOWLEDGE_DOCUMENTS ||--o{ KNOWLEDGE_CHUNKS : splits_into
  USERS ||--o| MENTORS : may_be
  MENTORS ||--o{ MENTORING_REQUESTS : receives
  SCENARIO_LABS ||--o{ SCENARIO_ATTEMPTS : scores
```

## Learner workflow

```mermaid
flowchart LR
  A[Onboarding + consent] --> B[Role framework comparison]
  B --> C[AI-assisted, editable learning plan]
  C --> D[Course + assessment + practical task]
  D --> E[Evidence upload]
  E --> F[Trainer / expert review]
  F --> G[Verified competency passport]
  G --> H[Team and organization readiness metrics]
```

## Testing and quality checks

```powershell
# Backend
cd backend
pytest -q

# Frontend
cd frontend
npm run build
npm run test
```

The backend tests cover login, authenticated dashboard access, the transparent critical-gap calculation, progress/certificate workflow, and role-based protection of verification actions.

## Security and responsible AI notes

- Passwords use Werkzeug secure hashing; access and refresh JWTs are issued by Flask-JWT-Extended.
- High-risk endpoints are rate limited. Inputs and file-size limits are validated server-side.
- CORS is allowlisted through `.env`; queries use SQLAlchemy rather than string-built SQL.
- Evidence decisions produce verification records and audit logs; user data and model prompts are not logged.
- All AI-derived skills need human review and user consent. Document queries use only approved knowledge chunks.
- For a production deployment, add HTTPS, object storage with malware scanning, CSRF protection for cookie deployments, secrets management, structured security events, database backups, and a production WSGI server.

## Deployment

1. Configure production `SECRET_KEY`, `JWT_SECRET_KEY`, `DATABASE_URL`, `CORS_ORIGINS`, and optional `GEMINI_API_KEY` in a secure secret store.
2. Build the frontend with `npm run build`, then serve `frontend/dist` from a CDN or reverse proxy.
3. Run Flask behind Gunicorn/Waitress with a managed MySQL database; apply migrations before releasing the API.
4. Configure the reverse proxy to forward `/api` to Flask and enforce HTTPS, payload limits, and security headers.
5. Seed only non-production demo environments.

## Three-minute SIH demo flow

1. Sign in as `learner@capacityconnect.in` and point out the readiness score, evidence-backed skills, and current roadmap.
2. Open **Skill Galaxy**; select the red critical node and explain current versus required competence and the accessible status label.
3. Open **AI Skill-Gap Analysis** to show the recommendation’s reason and editable weekly plan.
4. Enrol in a relevant course, log progress, and submit evidence from the **Competency Passport**.
5. Ask **Prithvi AI** how to communicate forecast uncertainty; show cited approved guide sections and local fallback label.
6. Request a mentor, then complete the **Severe-weather warning response** Scenario Lab.
7. Open **Readiness Reports** to close the loop: individual learning is now visible as transparent organizational capacity insight.

## Future scope

- SSO via Government/organization identity providers and a full permission matrix per institution.
- Document upload, PDF/DOCX extraction, embeddings, multilingual voice transcription, and reviewer queues.
- Full course authoring, timed randomized assessments, QR image generation, calendar integrations, and scheduled notifications.
- Additional scenario labs for cyclone monitoring, ocean interpretation, field safety, and earthquake information workflows.
- Live analytics, CSV import/export, downloadable PDF reports, offline lesson packages, and mobile-native synchronization.

## Common problems

| Symptom | Fix |
|---|---|
| `py` is not recognised | Install Python 3.11+ and select “Add Python to PATH”, then reopen PowerShell. |
| MySQL connection error | Verify `DATABASE_URL`, database name, server status, user privilege, and install `PyMySQL`. Use SQLite demo mode first. |
| CORS browser error | Set `CORS_ORIGINS=http://localhost:5173` in backend `.env` and restart Flask. |
| Blank 3D view | Check WebGL/browser hardware acceleration; the functional 2D metrics remain available in the page side panel. |
| Gemini answer unavailable | The local trusted retrieval fallback should still answer when source chunks match. Verify the API key only if Gemini is required. |
