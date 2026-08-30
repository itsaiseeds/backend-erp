-- =============================================================================
-- DML: Seed Data
-- Backend ERP - PostgreSQL
-- =============================================================================
-- Seeds the reference data Django requires:
--   * django_content_type  (one row per model)
--   * auth_permission      (add / change / delete / view per content type)
--
-- Content types and permissions are seeded for the built-in apps AND for the
-- project's own models (authentication.user/admin/salesperson and the
-- aggregator master-data models) so that non-superuser staff can be granted
-- per-model admin access through Django's group/permission system.
--
-- The default superuser is created at runtime by the `createsuperuser_if_not_exists`
-- command (see scripts/entrypoint.sh); the two authentication_user rows below
-- are reconciliation seeds that make the same accounts exist after a reload.
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
    (6, 'admin',       'logentry'),
    (7, 'authentication', 'user'),
    (8, 'authentication', 'admin'),
    (9, 'authentication', 'salesperson'),
    (10, 'aggregator',   'country'),
    (11, 'aggregator',   'state'),
    (12, 'aggregator',   'city'),
    (13, 'aggregator',   'pincode'),
    (14, 'aggregator',   'address')
ON CONFLICT DO NOTHING;

SELECT setval('django_content_type_id_seq', 14);

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
    (24, 'Can view log entry',       6, 'view_logentry'),
    -- authentication.user (content_type_id = 7)
    (25, 'Can add user',        7, 'add_user'),
    (26, 'Can change user',     7, 'change_user'),
    (27, 'Can delete user',     7, 'delete_user'),
    (28, 'Can view user',       7, 'view_user'),
    -- authentication.admin (content_type_id = 8)
    (29, 'Can add admin',        8, 'add_admin'),
    (30, 'Can change admin',     8, 'change_admin'),
    (31, 'Can delete admin',     8, 'delete_admin'),
    (32, 'Can view admin',       8, 'view_admin'),
    -- authentication.salesperson (content_type_id = 9)
    (33, 'Can add sales person',        9, 'add_salesperson'),
    (34, 'Can change sales person',     9, 'change_salesperson'),
    (35, 'Can delete sales person',     9, 'delete_salesperson'),
    (36, 'Can view sales person',       9, 'view_salesperson'),
    -- aggregator.country (content_type_id = 10)
    (37, 'Can add country',        10, 'add_country'),
    (38, 'Can change country',     10, 'change_country'),
    (39, 'Can delete country',     10, 'delete_country'),
    (40, 'Can view country',       10, 'view_country'),
    -- aggregator.state (content_type_id = 11)
    (41, 'Can add state',        11, 'add_state'),
    (42, 'Can change state',     11, 'change_state'),
    (43, 'Can delete state',     11, 'delete_state'),
    (44, 'Can view state',       11, 'view_state'),
    -- aggregator.city (content_type_id = 12)
    (45, 'Can add city',        12, 'add_city'),
    (46, 'Can change city',     12, 'change_city'),
    (47, 'Can delete city',     12, 'delete_city'),
    (48, 'Can view city',       12, 'view_city'),
    -- aggregator.pincode (content_type_id = 13)
    (49, 'Can add pincode',        13, 'add_pincode'),
    (50, 'Can change pincode',     13, 'change_pincode'),
    (51, 'Can delete pincode',     13, 'delete_pincode'),
    (52, 'Can view pincode',       13, 'view_pincode'),
    -- aggregator.address (content_type_id = 14)
    (53, 'Can add address',        14, 'add_address'),
    (54, 'Can change address',     14, 'change_address'),
    (55, 'Can delete address',     14, 'delete_address'),
    (56, 'Can view address',       14, 'view_address')
ON CONFLICT DO NOTHING;

SELECT setval('auth_permission_id_seq', 56);

INSERT INTO public.authentication_user
(id, "password", last_login, is_superuser, created_at, updated_at, phone_number, "name", email, totp_secret, totp_enabled, is_verified, is_staff, is_active, date_joined, created_by_id, verified_by_id)
VALUES(1, 'pbkdf2_sha256$1000000$UGqt8oGnUaTMbuaqbfbc5N$gosDWLrsqUTN2ws6uEwb828K/FAkYHstAzNzhdevkbk=', NULL, true, '2026-08-27 23:52:53.878', '2026-08-27 23:52:54.057', '9999999999', 'admin', 'admin@example.com', 'JBSWY3DPEHPK3PXP', true, true, true, true, '2026-08-27 23:52:54.057', 1, 1);

-- A second user with NO TOTP set, used by integration tests to exercise the
-- "TOTP not enrolled" negative path over HTTP (no ORM access in these tests).
INSERT INTO public.authentication_user
(id, "password", last_login, is_superuser, created_at, updated_at, phone_number, "name", email, totp_secret, totp_enabled, is_verified, is_staff, is_active, date_joined, created_by_id, verified_by_id)
VALUES(2, '!unusable', NULL, false, '2026-08-27 23:52:53.878', '2026-08-27 23:52:54.057', '8888888888', 'no totp user', NULL, NULL, false, false, false, true, '2026-08-27 23:52:54.057', 1, NULL);

-- The seed rows above are inserted with explicit ids, so advance the sequence
-- to the highest id to keep ORM/admin-created rows from colliding.
SELECT setval('authentication_user_id_seq', 2, true);

-- -------------------------------------------------------------------------
-- Geography master data (country -> state -> city)
-- Needed so admin/salesperson creation can pick a city. The single seed tree
-- is also what the integration tests rely on (city ids drift with real data).
-- -------------------------------------------------------------------------
INSERT INTO public.aggregator_country
(id, created_at, updated_at, is_deleted, deleted_at, "name", iso_code, created_by_id, deleted_by_id)
VALUES(1, '2026-08-27 23:52:53.878', '2026-08-27 23:52:54.057', false, NULL, 'India', 'IN', 1, NULL);

INSERT INTO public.aggregator_state
(id, created_at, updated_at, is_deleted, deleted_at, "name", code, country_id, created_by_id, deleted_by_id)
VALUES(1, '2026-08-27 23:52:53.878', '2026-08-27 23:52:54.057', false, NULL, 'Maharashtra', 'MH', 1, 1, NULL);

INSERT INTO public.aggregator_city
(id, created_at, updated_at, is_deleted, deleted_at, "name", created_by_id, deleted_by_id, state_id)
VALUES(1, '2026-08-27 23:52:53.878', '2026-08-27 23:52:54.057', false, NULL, 'Pune', 1, NULL, 1);

INSERT INTO public.aggregator_pincode
(id, created_at, updated_at, is_deleted, deleted_at, code, city_id, created_by_id, deleted_by_id)
VALUES(1, '2026-08-27 23:52:53.878', '2026-08-27 23:52:54.057', false, NULL, '411001', 1, 1, NULL);

SELECT setval('aggregator_country_id_seq', 1);
SELECT setval('aggregator_state_id_seq', 1);
SELECT setval('aggregator_city_id_seq', 1);
SELECT setval('aggregator_pincode_id_seq', 1);

-- -------------------------------------------------------------------------
-- Rolled-up users used by the integration tests
--   * an application Admin (7777777777) with a known, enabled TOTP secret, and
--   * a plain verified user (6666666666) with a known, enabled TOTP secret.
-- Both authenticate over HTTP exactly like the seeded superuser above.
-- -------------------------------------------------------------------------
INSERT INTO public.authentication_user
(id, "password", last_login, is_superuser, created_at, updated_at, phone_number, "name", email, totp_secret, totp_enabled, is_verified, is_staff, is_active, date_joined, created_by_id, verified_by_id)
VALUES(3, '!unusable', NULL, false, '2026-08-27 23:52:53.878', '2026-08-27 23:52:54.057', '7777777777', 'seed admin', 'seed-admin@example.com', 'KRSXG5CTMVRXEZLU', true, true, false, true, '2026-08-27 23:52:54.057', 1, 1);

INSERT INTO public.authentication_user
(id, "password", last_login, is_superuser, created_at, updated_at, phone_number, "name", email, totp_secret, totp_enabled, is_verified, is_staff, is_active, date_joined, created_by_id, verified_by_id)
VALUES(4, '!unusable', NULL, false, '2026-08-27 23:52:53.878', '2026-08-27 23:52:54.057', '6666666666', 'plain user', NULL, 'IJQXGZJTGMFWC3LN', true, true, false, true, '2026-08-27 23:52:54.057', 1, 1);

SELECT setval('authentication_user_id_seq', 4, true);

INSERT INTO public.authentication_admin
(id, created_at, updated_at, is_deleted, deleted_at, deleted_by_id, created_by_id, user_id, can_update_stock_count)
VALUES(1, '2026-08-27 23:52:53.878', '2026-08-27 23:52:54.057', false, NULL, NULL, 1, 3, true);

SELECT setval('authentication_admin_id_seq', 1);

COMMIT;
