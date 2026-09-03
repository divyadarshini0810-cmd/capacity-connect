# Database migrations

After setting `DATABASE_URL` for MySQL, initialise versioned schema changes:

```powershell
flask --app wsgi db init
flask --app wsgi db migrate -m "initial Capacity Connect schema"
flask --app wsgi db upgrade
```

The checked-in model schema is the source of truth for this prototype. The employee-development revision adds `employee_profiles` (work context, learning availability, and preferences) and `course_bookmarks`. Generate and apply a migration before deploying those tables to an existing production database.

The `seed.py` script resets the local SQLite demo database automatically when `DATABASE_URL` is absent, making SIH demos runnable without MySQL.
