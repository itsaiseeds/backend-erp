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
INSERT INTO public.django_content_type (id, app_label, model) VALUES(1, 'authentication', 'user');
INSERT INTO public.django_content_type (id, app_label, model) VALUES(2, 'authtoken', 'tokenproxy');
INSERT INTO public.django_content_type (id, app_label, model) VALUES(3, 'authentication', 'salesperson');
INSERT INTO public.django_content_type (id, app_label, model) VALUES(4, 'aggregator', 'country');
INSERT INTO public.django_content_type (id, app_label, model) VALUES(5, 'aggregator', 'state');
INSERT INTO public.django_content_type (id, app_label, model) VALUES(6, 'aggregator', 'city');
INSERT INTO public.django_content_type (id, app_label, model) VALUES(7, 'aggregator', 'pincode');
INSERT INTO public.django_content_type (id, app_label, model) VALUES(8, 'authentication', 'admin');
INSERT INTO public.django_content_type (id, app_label, model) VALUES(14, 'aggregator', 'address');
INSERT INTO public.django_content_type (id, app_label, model) VALUES(15, 'aggregator', 'status');
INSERT INTO public.django_content_type (id, app_label, model) VALUES(16, 'aggregator', 'transportagency');
INSERT INTO public.django_content_type (id, app_label, model) VALUES(17, 'aggregator', 'contact');
INSERT INTO public.django_content_type (id, app_label, model) VALUES(18, 'aggregator', 'client');
INSERT INTO public.django_content_type (id, app_label, model) VALUES(19, 'aggregator', 'clientaddress');
INSERT INTO public.django_content_type (id, app_label, model) VALUES(20, 'aggregator', 'clientcontact');
INSERT INTO public.django_content_type (id, app_label, model) VALUES(21, 'aggregator', 'clienttransportagency');
INSERT INTO public.django_content_type (id, app_label, model) VALUES(22, 'aggregator', 'product');
INSERT INTO public.django_content_type (id, app_label, model) VALUES(23, 'aggregator', 'productpackaging');
INSERT INTO public.django_content_type (id, app_label, model) VALUES(24, 'aggregator', 'dispatchdetails');
INSERT INTO public.django_content_type (id, app_label, model) VALUES(25, 'aggregator', 'privatedispatchdetails');
INSERT INTO public.django_content_type (id, app_label, model) VALUES(26, 'aggregator', 'order');
INSERT INTO public.django_content_type (id, app_label, model) VALUES(27, 'aggregator', 'orderitem');
INSERT INTO public.django_content_type (id, app_label, model) VALUES(28, 'aggregator', 'crop');
INSERT INTO public.django_content_type (id, app_label, model) VALUES(29, 'contenttypes', 'contenttype');
INSERT INTO public.django_content_type (id, app_label, model) VALUES(30, 'sessions', 'session');
INSERT INTO public.django_content_type (id, app_label, model) VALUES(31, 'admin', 'logentry');
INSERT INTO public.django_content_type (id, app_label, model) VALUES(32, 'auth', 'group');
INSERT INTO public.django_content_type (id, app_label, model) VALUES(33, 'auth', 'permission');

-- -------------------------------------------------------------------------
-- auth_permission
-- -------------------------------------------------------------------------
INSERT INTO public.auth_permission (id, "name", content_type_id, codename) VALUES(1, 'Can add user', 1, 'add_user');
INSERT INTO public.auth_permission (id, "name", content_type_id, codename) VALUES(2, 'Can change user', 1, 'change_user');
INSERT INTO public.auth_permission (id, "name", content_type_id, codename) VALUES(3, 'Can delete user', 1, 'delete_user');
INSERT INTO public.auth_permission (id, "name", content_type_id, codename) VALUES(4, 'Can view user', 1, 'view_user');
INSERT INTO public.auth_permission (id, "name", content_type_id, codename) VALUES(5, 'Can add Token', 2, 'add_tokenproxy');
INSERT INTO public.auth_permission (id, "name", content_type_id, codename) VALUES(6, 'Can change Token', 2, 'change_tokenproxy');
INSERT INTO public.auth_permission (id, "name", content_type_id, codename) VALUES(7, 'Can delete Token', 2, 'delete_tokenproxy');
INSERT INTO public.auth_permission (id, "name", content_type_id, codename) VALUES(8, 'Can view Token', 2, 'view_tokenproxy');
INSERT INTO public.auth_permission (id, "name", content_type_id, codename) VALUES(9, 'Can add sales person', 3, 'add_salesperson');
INSERT INTO public.auth_permission (id, "name", content_type_id, codename) VALUES(10, 'Can change sales person', 3, 'change_salesperson');
INSERT INTO public.auth_permission (id, "name", content_type_id, codename) VALUES(11, 'Can delete sales person', 3, 'delete_salesperson');
INSERT INTO public.auth_permission (id, "name", content_type_id, codename) VALUES(12, 'Can view sales person', 3, 'view_salesperson');
INSERT INTO public.auth_permission (id, "name", content_type_id, codename) VALUES(13, 'Can add country', 4, 'add_country');
INSERT INTO public.auth_permission (id, "name", content_type_id, codename) VALUES(14, 'Can change country', 4, 'change_country');
INSERT INTO public.auth_permission (id, "name", content_type_id, codename) VALUES(15, 'Can delete country', 4, 'delete_country');
INSERT INTO public.auth_permission (id, "name", content_type_id, codename) VALUES(16, 'Can view country', 4, 'view_country');
INSERT INTO public.auth_permission (id, "name", content_type_id, codename) VALUES(17, 'Can add state', 5, 'add_state');
INSERT INTO public.auth_permission (id, "name", content_type_id, codename) VALUES(18, 'Can change state', 5, 'change_state');
INSERT INTO public.auth_permission (id, "name", content_type_id, codename) VALUES(19, 'Can delete state', 5, 'delete_state');
INSERT INTO public.auth_permission (id, "name", content_type_id, codename) VALUES(20, 'Can view state', 5, 'view_state');
INSERT INTO public.auth_permission (id, "name", content_type_id, codename) VALUES(21, 'Can add city', 6, 'add_city');
INSERT INTO public.auth_permission (id, "name", content_type_id, codename) VALUES(22, 'Can change city', 6, 'change_city');
INSERT INTO public.auth_permission (id, "name", content_type_id, codename) VALUES(23, 'Can delete city', 6, 'delete_city');
INSERT INTO public.auth_permission (id, "name", content_type_id, codename) VALUES(24, 'Can view city', 6, 'view_city');
INSERT INTO public.auth_permission (id, "name", content_type_id, codename) VALUES(25, 'Can add pincode', 7, 'add_pincode');
INSERT INTO public.auth_permission (id, "name", content_type_id, codename) VALUES(26, 'Can change pincode', 7, 'change_pincode');
INSERT INTO public.auth_permission (id, "name", content_type_id, codename) VALUES(27, 'Can delete pincode', 7, 'delete_pincode');
INSERT INTO public.auth_permission (id, "name", content_type_id, codename) VALUES(28, 'Can view pincode', 7, 'view_pincode');
INSERT INTO public.auth_permission (id, "name", content_type_id, codename) VALUES(29, 'Can add admin', 8, 'add_admin');
INSERT INTO public.auth_permission (id, "name", content_type_id, codename) VALUES(30, 'Can change admin', 8, 'change_admin');
INSERT INTO public.auth_permission (id, "name", content_type_id, codename) VALUES(31, 'Can delete admin', 8, 'delete_admin');
INSERT INTO public.auth_permission (id, "name", content_type_id, codename) VALUES(32, 'Can view admin', 8, 'view_admin');
INSERT INTO public.auth_permission (id, "name", content_type_id, codename) VALUES(33, 'Can add address', 14, 'add_address');
INSERT INTO public.auth_permission (id, "name", content_type_id, codename) VALUES(34, 'Can change address', 14, 'change_address');
INSERT INTO public.auth_permission (id, "name", content_type_id, codename) VALUES(35, 'Can delete address', 14, 'delete_address');
INSERT INTO public.auth_permission (id, "name", content_type_id, codename) VALUES(36, 'Can view address', 14, 'view_address');
INSERT INTO public.auth_permission (id, "name", content_type_id, codename) VALUES(37, 'Can add status', 15, 'add_status');
INSERT INTO public.auth_permission (id, "name", content_type_id, codename) VALUES(38, 'Can change status', 15, 'change_status');
INSERT INTO public.auth_permission (id, "name", content_type_id, codename) VALUES(39, 'Can delete status', 15, 'delete_status');
INSERT INTO public.auth_permission (id, "name", content_type_id, codename) VALUES(40, 'Can view status', 15, 'view_status');
INSERT INTO public.auth_permission (id, "name", content_type_id, codename) VALUES(41, 'Can add transport agency', 16, 'add_transportagency');
INSERT INTO public.auth_permission (id, "name", content_type_id, codename) VALUES(42, 'Can change transport agency', 16, 'change_transportagency');
INSERT INTO public.auth_permission (id, "name", content_type_id, codename) VALUES(43, 'Can delete transport agency', 16, 'delete_transportagency');
INSERT INTO public.auth_permission (id, "name", content_type_id, codename) VALUES(44, 'Can view transport agency', 16, 'view_transportagency');
INSERT INTO public.auth_permission (id, "name", content_type_id, codename) VALUES(45, 'Can add contact', 17, 'add_contact');
INSERT INTO public.auth_permission (id, "name", content_type_id, codename) VALUES(46, 'Can change contact', 17, 'change_contact');
INSERT INTO public.auth_permission (id, "name", content_type_id, codename) VALUES(47, 'Can delete contact', 17, 'delete_contact');
INSERT INTO public.auth_permission (id, "name", content_type_id, codename) VALUES(48, 'Can view contact', 17, 'view_contact');
INSERT INTO public.auth_permission (id, "name", content_type_id, codename) VALUES(49, 'Can add client', 18, 'add_client');
INSERT INTO public.auth_permission (id, "name", content_type_id, codename) VALUES(50, 'Can change client', 18, 'change_client');
INSERT INTO public.auth_permission (id, "name", content_type_id, codename) VALUES(51, 'Can delete client', 18, 'delete_client');
INSERT INTO public.auth_permission (id, "name", content_type_id, codename) VALUES(52, 'Can view client', 18, 'view_client');
INSERT INTO public.auth_permission (id, "name", content_type_id, codename) VALUES(53, 'Can add client address', 19, 'add_clientaddress');
INSERT INTO public.auth_permission (id, "name", content_type_id, codename) VALUES(54, 'Can change client address', 19, 'change_clientaddress');
INSERT INTO public.auth_permission (id, "name", content_type_id, codename) VALUES(55, 'Can delete client address', 19, 'delete_clientaddress');
INSERT INTO public.auth_permission (id, "name", content_type_id, codename) VALUES(56, 'Can view client address', 19, 'view_clientaddress');
INSERT INTO public.auth_permission (id, "name", content_type_id, codename) VALUES(57, 'Can add client contact', 20, 'add_clientcontact');
INSERT INTO public.auth_permission (id, "name", content_type_id, codename) VALUES(58, 'Can change client contact', 20, 'change_clientcontact');
INSERT INTO public.auth_permission (id, "name", content_type_id, codename) VALUES(59, 'Can delete client contact', 20, 'delete_clientcontact');
INSERT INTO public.auth_permission (id, "name", content_type_id, codename) VALUES(60, 'Can view client contact', 20, 'view_clientcontact');
INSERT INTO public.auth_permission (id, "name", content_type_id, codename) VALUES(61, 'Can add client transport agency', 21, 'add_clienttransportagency');
INSERT INTO public.auth_permission (id, "name", content_type_id, codename) VALUES(62, 'Can change client transport agency', 21, 'change_clienttransportagency');
INSERT INTO public.auth_permission (id, "name", content_type_id, codename) VALUES(63, 'Can delete client transport agency', 21, 'delete_clienttransportagency');
INSERT INTO public.auth_permission (id, "name", content_type_id, codename) VALUES(64, 'Can view client transport agency', 21, 'view_clienttransportagency');
INSERT INTO public.auth_permission (id, "name", content_type_id, codename) VALUES(65, 'Can add product', 22, 'add_product');
INSERT INTO public.auth_permission (id, "name", content_type_id, codename) VALUES(66, 'Can change product', 22, 'change_product');
INSERT INTO public.auth_permission (id, "name", content_type_id, codename) VALUES(67, 'Can delete product', 22, 'delete_product');
INSERT INTO public.auth_permission (id, "name", content_type_id, codename) VALUES(68, 'Can view product', 22, 'view_product');
INSERT INTO public.auth_permission (id, "name", content_type_id, codename) VALUES(69, 'Can add product packaging', 23, 'add_productpackaging');
INSERT INTO public.auth_permission (id, "name", content_type_id, codename) VALUES(70, 'Can change product packaging', 23, 'change_productpackaging');
INSERT INTO public.auth_permission (id, "name", content_type_id, codename) VALUES(71, 'Can delete product packaging', 23, 'delete_productpackaging');
INSERT INTO public.auth_permission (id, "name", content_type_id, codename) VALUES(72, 'Can view product packaging', 23, 'view_productpackaging');
INSERT INTO public.auth_permission (id, "name", content_type_id, codename) VALUES(73, 'Can add dispatch details', 24, 'add_dispatchdetails');
INSERT INTO public.auth_permission (id, "name", content_type_id, codename) VALUES(74, 'Can change dispatch details', 24, 'change_dispatchdetails');
INSERT INTO public.auth_permission (id, "name", content_type_id, codename) VALUES(75, 'Can delete dispatch details', 24, 'delete_dispatchdetails');
INSERT INTO public.auth_permission (id, "name", content_type_id, codename) VALUES(76, 'Can view dispatch details', 24, 'view_dispatchdetails');
INSERT INTO public.auth_permission (id, "name", content_type_id, codename) VALUES(77, 'Can add private dispatch details', 25, 'add_privatedispatchdetails');
INSERT INTO public.auth_permission (id, "name", content_type_id, codename) VALUES(78, 'Can change private dispatch details', 25, 'change_privatedispatchdetails');
INSERT INTO public.auth_permission (id, "name", content_type_id, codename) VALUES(79, 'Can delete private dispatch details', 25, 'delete_privatedispatchdetails');
INSERT INTO public.auth_permission (id, "name", content_type_id, codename) VALUES(80, 'Can view private dispatch details', 25, 'view_privatedispatchdetails');
INSERT INTO public.auth_permission (id, "name", content_type_id, codename) VALUES(81, 'Can add order', 26, 'add_order');
INSERT INTO public.auth_permission (id, "name", content_type_id, codename) VALUES(82, 'Can change order', 26, 'change_order');
INSERT INTO public.auth_permission (id, "name", content_type_id, codename) VALUES(83, 'Can delete order', 26, 'delete_order');
INSERT INTO public.auth_permission (id, "name", content_type_id, codename) VALUES(84, 'Can view order', 26, 'view_order');
INSERT INTO public.auth_permission (id, "name", content_type_id, codename) VALUES(85, 'Can add order item', 27, 'add_orderitem');
INSERT INTO public.auth_permission (id, "name", content_type_id, codename) VALUES(86, 'Can change order item', 27, 'change_orderitem');
INSERT INTO public.auth_permission (id, "name", content_type_id, codename) VALUES(87, 'Can delete order item', 27, 'delete_orderitem');
INSERT INTO public.auth_permission (id, "name", content_type_id, codename) VALUES(88, 'Can view order item', 27, 'view_orderitem');
INSERT INTO public.auth_permission (id, "name", content_type_id, codename) VALUES(89, 'Can add crop', 28, 'add_crop');
INSERT INTO public.auth_permission (id, "name", content_type_id, codename) VALUES(90, 'Can change crop', 28, 'change_crop');
INSERT INTO public.auth_permission (id, "name", content_type_id, codename) VALUES(91, 'Can delete crop', 28, 'delete_crop');
INSERT INTO public.auth_permission (id, "name", content_type_id, codename) VALUES(92, 'Can view crop', 28, 'view_crop');
INSERT INTO public.auth_permission (id, "name", content_type_id, codename) VALUES(93, 'Can add content type', 29, 'add_contenttype');
INSERT INTO public.auth_permission (id, "name", content_type_id, codename) VALUES(94, 'Can change content type', 29, 'change_contenttype');
INSERT INTO public.auth_permission (id, "name", content_type_id, codename) VALUES(95, 'Can delete content type', 29, 'delete_contenttype');
INSERT INTO public.auth_permission (id, "name", content_type_id, codename) VALUES(96, 'Can view content type', 29, 'view_contenttype');
INSERT INTO public.auth_permission (id, "name", content_type_id, codename) VALUES(97, 'Can add session', 30, 'add_session');
INSERT INTO public.auth_permission (id, "name", content_type_id, codename) VALUES(98, 'Can change session', 30, 'change_session');
INSERT INTO public.auth_permission (id, "name", content_type_id, codename) VALUES(99, 'Can delete session', 30, 'delete_session');
INSERT INTO public.auth_permission (id, "name", content_type_id, codename) VALUES(100, 'Can view session', 30, 'view_session');
INSERT INTO public.auth_permission (id, "name", content_type_id, codename) VALUES(101, 'Can add log entry', 31, 'add_logentry');
INSERT INTO public.auth_permission (id, "name", content_type_id, codename) VALUES(102, 'Can change log entry', 31, 'change_logentry');
INSERT INTO public.auth_permission (id, "name", content_type_id, codename) VALUES(103, 'Can delete log entry', 31, 'delete_logentry');
INSERT INTO public.auth_permission (id, "name", content_type_id, codename) VALUES(104, 'Can view log entry', 31, 'view_logentry');
INSERT INTO public.auth_permission (id, "name", content_type_id, codename) VALUES(105, 'Can add group', 32, 'add_group');
INSERT INTO public.auth_permission (id, "name", content_type_id, codename) VALUES(106, 'Can change group', 32, 'change_group');
INSERT INTO public.auth_permission (id, "name", content_type_id, codename) VALUES(107, 'Can delete group', 32, 'delete_group');
INSERT INTO public.auth_permission (id, "name", content_type_id, codename) VALUES(108, 'Can view group', 32, 'view_group');
INSERT INTO public.auth_permission (id, "name", content_type_id, codename) VALUES(109, 'Can add permission', 33, 'add_permission');
INSERT INTO public.auth_permission (id, "name", content_type_id, codename) VALUES(110, 'Can change permission', 33, 'change_permission');
INSERT INTO public.auth_permission (id, "name", content_type_id, codename) VALUES(111, 'Can delete permission', 33, 'delete_permission');
INSERT INTO public.auth_permission (id, "name", content_type_id, codename) VALUES(112, 'Can view permission', 33, 'view_permission');

-- -------------------------------------------------------------------------
-- aggregator_status (generic, enum-like status values)
--   Order lifecycle + client verification. created_by left NULL (seed data).
-- -------------------------------------------------------------------------
INSERT INTO public.aggregator_status (id, created_at, updated_at, is_deleted, deleted_at, deleted_by_id, created_by_id, code, "name", "sequence") VALUES(1, '2026-08-28 05:22:53.878', '2026-08-28 05:22:53.878', false, NULL, NULL, NULL, 'BOOKED', 'Booked', 1);
INSERT INTO public.aggregator_status (id, created_at, updated_at, is_deleted, deleted_at, deleted_by_id, created_by_id, code, "name", "sequence") VALUES(2, '2026-08-28 05:22:53.878', '2026-08-28 05:22:53.878', false, NULL, NULL, NULL, 'UNDER_REVIEW', 'Under review', 2);
INSERT INTO public.aggregator_status (id, created_at, updated_at, is_deleted, deleted_at, deleted_by_id, created_by_id, code, "name", "sequence") VALUES(3, '2026-08-28 05:22:53.878', '2026-08-28 05:22:53.878', false, NULL, NULL, NULL, 'CONFIRMED', 'Confirmed', 3);
INSERT INTO public.aggregator_status (id, created_at, updated_at, is_deleted, deleted_at, deleted_by_id, created_by_id, code, "name", "sequence") VALUES(4, '2026-08-28 05:22:53.878', '2026-08-28 05:22:53.878', false, NULL, NULL, NULL, 'DISPATCHED', 'Dispatched', 4);
INSERT INTO public.aggregator_status (id, created_at, updated_at, is_deleted, deleted_at, deleted_by_id, created_by_id, code, "name", "sequence") VALUES(5, '2026-08-28 05:22:53.878', '2026-08-28 05:22:53.878', false, NULL, NULL, NULL, 'DELIVERED', 'Delivered', 5);
INSERT INTO public.aggregator_status (id, created_at, updated_at, is_deleted, deleted_at, deleted_by_id, created_by_id, code, "name", "sequence") VALUES(6, '2026-08-28 05:22:53.878', '2026-08-28 05:22:53.878', false, NULL, NULL, NULL, 'ON_HOLD', 'On hold', 6);
INSERT INTO public.aggregator_status (id, created_at, updated_at, is_deleted, deleted_at, deleted_by_id, created_by_id, code, "name", "sequence") VALUES(7, '2026-08-28 05:22:53.878', '2026-08-28 05:22:53.878', false, NULL, NULL, NULL, 'REJECTED', 'Rejected', 7);
INSERT INTO public.aggregator_status (id, created_at, updated_at, is_deleted, deleted_at, deleted_by_id, created_by_id, code, "name", "sequence") VALUES(8, '2026-08-28 05:22:53.878', '2026-08-28 05:22:53.878', false, NULL, NULL, NULL, 'VERIFICATION_PENDING', 'Verification pending', 1);
INSERT INTO public.aggregator_status (id, created_at, updated_at, is_deleted, deleted_at, deleted_by_id, created_by_id, code, "name", "sequence") VALUES(9, '2026-08-28 05:22:53.878', '2026-08-28 05:22:53.878', false, NULL, NULL, NULL, 'VERIFIED', 'Verified', 2);


-- Two base USERS, please dont remove these rows; 
INSERT INTO public.authentication_user
(id, "password", last_login, is_superuser, created_at, updated_at, phone_number, "name", email, totp_secret, totp_enabled, totp_last_counter, failed_totp_attempts, totp_lockout_until, is_verified, is_staff, is_active, date_joined, created_by_id, verified_by_id)
VALUES(1, 'pbkdf2_sha256$1000000$UGqt8oGnUaTMbuaqbfbc5N$gosDWLrsqUTN2ws6uEwb828K/FAkYHstAzNzhdevkbk=', NULL, true, '2026-08-27 23:52:53.878', '2026-08-27 23:52:54.057', '9999999999', 'admin', 'admin@example.com', 'JBSWY3DPEHPK3PXP', true, NULL, 0, NULL, true, true, true, '2026-08-27 23:52:54.057', 1, 1);

-- A second user with NO TOTP set, used by integration tests to exercise the
-- "TOTP not enrolled" negative path over HTTP (no ORM access in these tests).
INSERT INTO public.authentication_user
(id, "password", last_login, is_superuser, created_at, updated_at, phone_number, "name", email, totp_secret, totp_enabled, totp_last_counter, failed_totp_attempts, totp_lockout_until, is_verified, is_staff, is_active, date_joined, created_by_id, verified_by_id)
VALUES(2, '!unusable', NULL, false, '2026-08-27 23:52:53.878', '2026-08-27 23:52:54.057', '8888888888', 'no totp user', NULL, NULL, false, NULL, 0, NULL, false, false, true, '2026-08-27 23:52:54.057', 1, NULL);

-- -------------------------------------------------------------------------
-- Sequence sync
-- -------------------------------------------------------------------------
-- The inserts above set explicit primary keys, which does NOT advance each
-- table's identity/serial sequence. Re-sync every seeded table so the next
-- row created through the ORM/API gets an id after the seeded maximum instead
-- of colliding from id=1.
SELECT setval(pg_get_serial_sequence('public.django_content_type', 'id'), (SELECT MAX(id) FROM public.django_content_type));
SELECT setval(pg_get_serial_sequence('public.auth_permission', 'id'),     (SELECT MAX(id) FROM public.auth_permission));
SELECT setval(pg_get_serial_sequence('public.aggregator_status', 'id'),   (SELECT MAX(id) FROM public.aggregator_status));
SELECT setval(pg_get_serial_sequence('public.authentication_user', 'id'), (SELECT MAX(id) FROM public.authentication_user));

COMMIT;
