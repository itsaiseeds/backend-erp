-- =============================================================================
-- DML: Seed Data
-- Backend ERP - PostgreSQL
-- =============================================================================
-- Seeds the reference data Django requires:
--   * django_content_type  (one row per model)
--   * auth_permission      (add / change / delete / view per content type)
--
-- Only tables that are SQL-managed (listed in sql/ddl.sql) are seeded here.
-- The `authentication_*` tables are managed by Django migrations, and the
-- default superuser is created at runtime by the `createsuperuser_if_not_exists`
-- command (see scripts/entrypoint.sh) — neither is seeded here.
--
-- Run: bash scripts/reload_db.sh --step dml
-- =============================================================================

BEGIN;

-- -------------------------------------------------------------------------
-- django_content_type
-- -------------------------------------------------------------------------
INSERT INTO django_content_type (id, app_label, model) VALUES
    (1, 'auth',        'user'),
    (2, 'auth',        'group'),
    (3, 'auth',        'permission'),
    (4, 'contenttypes', 'contenttype'),
    (5, 'sessions',    'session'),
    (6, 'admin',       'logentry')
ON CONFLICT DO NOTHING;

SELECT setval('django_content_type_id_seq', 6);

-- -------------------------------------------------------------------------
-- auth_permission
-- -------------------------------------------------------------------------
INSERT INTO auth_permission (id, name, content_type_id, codename) VALUES
    -- auth.user (content_type_id = 1)
    ( 1, 'Can add user',        1, 'add_user'),
    ( 2, 'Can change user',     1, 'change_user'),
    ( 3, 'Can delete user',     1, 'delete_user'),
    ( 4, 'Can view user',       1, 'view_user'),
    -- auth.group (content_type_id = 2)
    ( 5, 'Can add group',       2, 'add_group'),
    ( 6, 'Can change group',    2, 'change_group'),
    ( 7, 'Can delete group',    2, 'delete_group'),
    ( 8, 'Can view group',      2, 'view_group'),
    -- auth.permission (content_type_id = 3)
    ( 9, 'Can add permission',        3, 'add_permission'),
    (10, 'Can change permission',     3, 'change_permission'),
    (11, 'Can delete permission',     3, 'delete_permission'),
    (12, 'Can view permission',       3, 'view_permission'),
    -- contenttypes.contenttype (content_type_id = 4)
    (13, 'Can add content type',        4, 'add_contenttype'),
    (14, 'Can change content type',     4, 'change_contenttype'),
    (15, 'Can delete content type',     4, 'delete_contenttype'),
    (16, 'Can view content type',       4, 'view_contenttype'),
    -- sessions.session (content_type_id = 5)
    (17, 'Can add session',        5, 'add_session'),
    (18, 'Can change session',     5, 'change_session'),
    (19, 'Can delete session',     5, 'delete_session'),
    (20, 'Can view session',       5, 'view_session'),
    -- admin.logentry (content_type_id = 6)
    (21, 'Can add log entry',        6, 'add_logentry'),
    (22, 'Can change log entry',     6, 'change_logentry'),
    (23, 'Can delete log entry',     6, 'delete_logentry'),
    (24, 'Can view log entry',       6, 'view_logentry')
ON CONFLICT DO NOTHING;

SELECT setval('auth_permission_id_seq', 24);

INSERT INTO public.authentication_user
(id, "password", last_login, is_superuser, created_at, updated_at, phone_number, "name", email, totp_secret, totp_enabled, is_verified, is_staff, is_active, date_joined, created_by_id, verified_by_id)
VALUES(1, 'pbkdf2_sha256$1000000$UGqt8oGnUaTMbuaqbfbc5N$gosDWLrsqUTN2ws6uEwb828K/FAkYHstAzNzhdevkbk=', NULL, true, '2026-08-27 23:52:53.878', '2026-08-27 23:52:54.057', '9999999999', 'admin', 'admin@example.com', 'JBSWY3DPEHPK3PXP', true, true, true, true, '2026-08-27 23:52:54.057', NULL, NULL);

-- A second user with NO TOTP set, used by integration tests to exercise the
-- "TOTP not enrolled" negative path over HTTP (no ORM access in these tests).
INSERT INTO public.authentication_user
(id, "password", last_login, is_superuser, created_at, updated_at, phone_number, "name", email, totp_secret, totp_enabled, is_verified, is_staff, is_active, date_joined, created_by_id, verified_by_id)
VALUES(2, '!unusable', NULL, false, '2026-08-27 23:52:53.878', '2026-08-27 23:52:54.057', '8888888888', 'no totp user', NULL, NULL, false, false, false, true, '2026-08-27 23:52:54.057', 1, NULL);

COMMIT;
