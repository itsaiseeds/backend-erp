-- =============================================================================
-- DML: Dev Seed Data
-- Backend ERP - PostgreSQL
-- =============================================================================
-- Populates content types, permissions, and a default superuser.
-- DEV ONLY — never run against production.
--
-- Run: bash scripts/reload_db.sh --step dml
-- =============================================================================

BEGIN;

-- -------------------------------------------------------------------------
-- django_content_type (one row per model Django knows about)
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
-- auth_permission (add / change / delete / view for each model)
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

-- -------------------------------------------------------------------------
-- Default superuser  (username: admin / password: admin)
-- Password hash: PBKDF2 SHA256, 1500000 iterations
-- -------------------------------------------------------------------------
INSERT INTO public.auth_user (id, "password", last_login, is_superuser, username, first_name, last_name, email, is_staff, is_active, date_joined) VALUES(1, 'pbkdf2_sha256$1500000$0rmo5ZMlW4ia6yc0axl59h$gCQl0JPNSoJ0Hu8HpQD69OEuHxhOY0NO8jTGClma9oQ=', '2026-08-25 18:19:57.798', true, 'admin', '', '', 'admin@example.com', true, true, '2026-08-25 18:19:57.798');
INSERT INTO public.auth_user (id, "password", last_login, is_superuser, username, first_name, last_name, email, is_staff, is_active, date_joined) VALUES(2, 'pbkdf2_sha256$1500000$n4oJdspqtOiwuvpsbuNtIO$YnME46AxGFlXOS4a4hzoWoIDJ9Kjx8hSHrkeE5ghPZU=', '2026-08-25 18:19:57.798', true, 'xZist', '', '', 'xZist@example.com', true, true, '2026-08-25 18:19:57.798');

SELECT setval('auth_user_id_seq', 2);

-- Grant all permissions to superusers
INSERT INTO auth_user_user_permissions (user_id, permission_id)
SELECT id, unnest(ARRAY(SELECT id FROM auth_permission)) FROM auth_user WHERE is_superuser = TRUE
ON CONFLICT DO NOTHING;

COMMIT;