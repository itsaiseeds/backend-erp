# Backend ERP — Skills Index

> Master knowledge base for the Saiseeds Backend ERP project.
> Every file under `skills/` covers one domain. Read them before making changes.

---

## Project at a Glance

| | |
|---|---|
| **Framework** | Django 5.2 LTS |
| **Database** | PostgreSQL 18 |
| **Python** | 3.14 |
| **Container** | Docker Compose (web + db) |
| **Schema management** | Raw SQL (no Django migrations) |
| **Seed data** | Raw SQL, dev-only |

---

## Files

| File | What it covers |
|---|---|
| [skills/database.md](skills/database.md) | DDL, DML, reload script, schema conventions |
| [skills/setup.md](skills/setup.md) | Environment files, first-time setup, daily workflow |
| [skills/django.md](skills/django.md) | Settings, apps, middleware, MIGRATION_MODULES |
| [skills/docker.md](skills/docker.md) | Dockerfile, docker-compose, services, volumes |
| [skills/conventions.md](skills/conventions.md) | Code style, patterns, naming, adding new features |

---

## Quick Reference

### Start developing
```bash
docker-compose up -d                         # start PostgreSQL + Django
bash scripts/reload_db.sh --step all
# Django is now running at http://localhost:8000/admin/
# Login: admin / admin
```

### Add a new table
1. Write `CREATE TABLE` in `sql/ddl.sql`
2. Write any seed `INSERT`s in `sql/dml.sql`
3. Run `bash scripts/reload_db.sh --step all`
4. Update this skills index if the change is architectural

### Key files you will touch often
- `config/settings.py` — Django config
- `sql/ddl.sql` — schema
- `sql/dml.sql` — seed data
- `scripts/reload_db.sh` — DB management script
- `.env.dev` — local connection params
