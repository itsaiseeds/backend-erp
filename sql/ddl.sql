-- =============================================================================
-- DDL: Django Built-in Tables
-- Backend ERP - PostgreSQL
-- =============================================================================
-- Creates all tables required by Django's built-in apps:
--   django.contrib.admin
--   django.contrib.auth
--   django.contrib.contenttypes
--   django.contrib.sessions
--
-- Run: bash scripts/reload_db.sh --step ddl
-- =============================================================================

BEGIN;

-- -------------------------------------------------------------------------
-- django_migrations (required by Django internals even with migrations disabled)
-- -------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS django_migrations (
    id          BIGSERIAL    PRIMARY KEY,
    app         VARCHAR(255) NOT NULL,
    name        VARCHAR(255) NOT NULL,
    applied     TIMESTAMP    NOT NULL
);

CREATE INDEX IF NOT EXISTS django_migrations_app_idx ON django_migrations (app);

-- -------------------------------------------------------------------------
-- django_content_type
-- -------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS django_content_type (
    id         BIGSERIAL    PRIMARY KEY,
    app_label  VARCHAR(100) NOT NULL,
    model      VARCHAR(100) NOT NULL,
    UNIQUE (app_label, model)
);

-- -------------------------------------------------------------------------
-- auth_permission
-- -------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS auth_permission (
    id              BIGSERIAL    PRIMARY KEY,
    name            VARCHAR(255) NOT NULL,
    content_type_id BIGINT       NOT NULL REFERENCES django_content_type (id),
    codename        VARCHAR(100) NOT NULL,
    UNIQUE (content_type_id, codename)
);

CREATE INDEX IF NOT EXISTS auth_permission_content_type_id_idx ON auth_permission (content_type_id);

-- -------------------------------------------------------------------------
-- auth_group
-- -------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS auth_group (
    id   BIGSERIAL    PRIMARY KEY,
    name VARCHAR(150) NOT NULL UNIQUE
);

-- -------------------------------------------------------------------------
-- auth_group_permissions
-- -------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS auth_group_permissions (
    id            BIGSERIAL PRIMARY KEY,
    group_id      BIGINT    NOT NULL REFERENCES auth_group (id) ON DELETE CASCADE,
    permission_id BIGINT    NOT NULL REFERENCES auth_permission (id) ON DELETE CASCADE,
    UNIQUE (group_id, permission_id)
);

CREATE INDEX IF NOT EXISTS auth_group_permissions_group_id_idx ON auth_group_permissions (group_id);
CREATE INDEX IF NOT EXISTS auth_group_permissions_permission_id_idx ON auth_group_permissions (permission_id);

-- -------------------------------------------------------------------------
-- auth_user
-- -------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS auth_user (
    id           BIGSERIAL     PRIMARY KEY,
    password     VARCHAR(128)  NOT NULL,
    last_login   TIMESTAMP     NULL,
    is_superuser BOOLEAN       NOT NULL DEFAULT FALSE,
    username     VARCHAR(150)  NOT NULL UNIQUE,
    first_name   VARCHAR(150)  NOT NULL DEFAULT '',
    last_name    VARCHAR(150)  NOT NULL DEFAULT '',
    email        VARCHAR(254)  NOT NULL DEFAULT '',
    is_staff     BOOLEAN       NOT NULL DEFAULT FALSE,
    is_active    BOOLEAN       NOT NULL DEFAULT TRUE,
    date_joined  TIMESTAMP     NOT NULL
);

-- -------------------------------------------------------------------------
-- auth_user_groups
-- -------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS auth_user_groups (
    id       BIGSERIAL PRIMARY KEY,
    user_id  BIGINT    NOT NULL REFERENCES auth_user (id) ON DELETE CASCADE,
    group_id BIGINT    NOT NULL REFERENCES auth_group (id) ON DELETE CASCADE,
    UNIQUE (user_id, group_id)
);

CREATE INDEX IF NOT EXISTS auth_user_groups_user_id_idx ON auth_user_groups (user_id);
CREATE INDEX IF NOT EXISTS auth_user_groups_group_id_idx ON auth_user_groups (group_id);

-- -------------------------------------------------------------------------
-- auth_user_user_permissions
-- -------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS auth_user_user_permissions (
    id            BIGSERIAL PRIMARY KEY,
    user_id       BIGINT    NOT NULL REFERENCES auth_user (id) ON DELETE CASCADE,
    permission_id BIGINT    NOT NULL REFERENCES auth_permission (id) ON DELETE CASCADE,
    UNIQUE (user_id, permission_id)
);

CREATE INDEX IF NOT EXISTS auth_user_user_permissions_user_id_idx ON auth_user_user_permissions (user_id);
CREATE INDEX IF NOT EXISTS auth_user_user_permissions_permission_id_idx ON auth_user_user_permissions (permission_id);

-- -------------------------------------------------------------------------
-- django_session
-- -------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS django_session (
    session_key  VARCHAR(40) NOT NULL PRIMARY KEY,
    session_data TEXT        NOT NULL,
    expire_date  TIMESTAMP   NOT NULL
);

CREATE INDEX IF NOT EXISTS django_session_expire_date_idx ON django_session (expire_date);

-- -------------------------------------------------------------------------
-- django_admin_log
-- -------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS django_admin_log (
    id              BIGSERIAL    PRIMARY KEY,
    action_time     TIMESTAMP    NOT NULL,
    user_id         BIGINT       NULL REFERENCES auth_user (id) ON DELETE SET NULL,
    content_type_id BIGINT       NULL REFERENCES django_content_type (id),
    object_id       TEXT         NULL,
    object_repr     VARCHAR(200) NOT NULL,
    action_flag     SMALLINT     NOT NULL,
    change_message  TEXT         NOT NULL
);

CREATE INDEX IF NOT EXISTS django_admin_log_user_id_idx ON django_admin_log (user_id);
CREATE INDEX IF NOT EXISTS django_admin_log_content_type_id_idx ON django_admin_log (content_type_id);

COMMIT;