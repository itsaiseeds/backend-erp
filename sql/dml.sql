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
INSERT INTO public.django_content_type (id, app_label, model) VALUES(34, 'aggregator', 'inventorysnapshot');
INSERT INTO public.django_content_type (id, app_label, model) VALUES(35, 'aggregator', 'customorder');
INSERT INTO public.django_content_type (id, app_label, model) VALUES(36, 'aggregator', 'customorderitem');
INSERT INTO public.django_content_type (id, app_label, model) VALUES(37, 'aggregator', 'stage');
INSERT INTO public.django_content_type (id, app_label, model) VALUES(38, 'aggregator', 'loosestocksnapshot');
INSERT INTO public.django_content_type (id, app_label, model) VALUES(39, 'aggregator', 'productdescriptionitem');
INSERT INTO public.django_content_type (id, app_label, model) VALUES(40, 'aggregator', 'party');
INSERT INTO public.django_content_type (id, app_label, model) VALUES(41, 'aggregator', 'inwardrawmaterial');
INSERT INTO public.django_content_type (id, app_label, model) VALUES(42, 'aggregator', 'othermaterialtype');
INSERT INTO public.django_content_type (id, app_label, model) VALUES(43, 'aggregator', 'othermaterialrecipe');
INSERT INTO public.django_content_type (id, app_label, model) VALUES(44, 'aggregator', 'inwardothermaterial');
INSERT INTO public.django_content_type (id, app_label, model) VALUES(45, 'aggregator', 'dispatchentry');
INSERT INTO public.django_content_type (id, app_label, model) VALUES(46, 'aggregator', 'dispatchentryitem');
INSERT INTO public.django_content_type (id, app_label, model) VALUES(47, 'aggregator', 'fieldtrip');
INSERT INTO public.django_content_type (id, app_label, model) VALUES(48, 'aggregator', 'farmervisit');
INSERT INTO public.django_content_type (id, app_label, model) VALUES(49, 'aggregator', 'farmervisitcrop');
INSERT INTO public.django_content_type (id, app_label, model) VALUES(50, 'aggregator', 'farmervisitproduct');
INSERT INTO public.django_content_type (id, app_label, model) VALUES(52, 'authentication', 'godownmanager');
INSERT INTO public.django_content_type (id, app_label, model) VALUES(53, 'aggregator', 'rawmaterialwaste');
INSERT INTO public.django_content_type (id, app_label, model) VALUES(54, 'aggregator', 'stockevent');
INSERT INTO public.django_content_type (id, app_label, model) VALUES(55, 'aggregator', 'pushdevice');
INSERT INTO public.django_content_type (id, app_label, model) VALUES(56, 'aggregator', 'notification');
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
INSERT INTO public.auth_permission (id, "name", content_type_id, codename) VALUES(113, 'Can add inventory snapshot', 34, 'add_inventorysnapshot');
INSERT INTO public.auth_permission (id, "name", content_type_id, codename) VALUES(114, 'Can change inventory snapshot', 34, 'change_inventorysnapshot');
INSERT INTO public.auth_permission (id, "name", content_type_id, codename) VALUES(115, 'Can delete inventory snapshot', 34, 'delete_inventorysnapshot');
INSERT INTO public.auth_permission (id, "name", content_type_id, codename) VALUES(116, 'Can view inventory snapshot', 34, 'view_inventorysnapshot');
INSERT INTO public.auth_permission (id, "name", content_type_id, codename) VALUES(117, 'Can add custom order', 35, 'add_customorder');
INSERT INTO public.auth_permission (id, "name", content_type_id, codename) VALUES(118, 'Can change custom order', 35, 'change_customorder');
INSERT INTO public.auth_permission (id, "name", content_type_id, codename) VALUES(119, 'Can delete custom order', 35, 'delete_customorder');
INSERT INTO public.auth_permission (id, "name", content_type_id, codename) VALUES(120, 'Can view custom order', 35, 'view_customorder');
INSERT INTO public.auth_permission (id, "name", content_type_id, codename) VALUES(121, 'Can add custom order item', 36, 'add_customorderitem');
INSERT INTO public.auth_permission (id, "name", content_type_id, codename) VALUES(122, 'Can change custom order item', 36, 'change_customorderitem');
INSERT INTO public.auth_permission (id, "name", content_type_id, codename) VALUES(123, 'Can delete custom order item', 36, 'delete_customorderitem');
INSERT INTO public.auth_permission (id, "name", content_type_id, codename) VALUES(124, 'Can view custom order item', 36, 'view_customorderitem');
INSERT INTO public.auth_permission (id, "name", content_type_id, codename) VALUES(125, 'Can add stage', 37, 'add_stage');
INSERT INTO public.auth_permission (id, "name", content_type_id, codename) VALUES(126, 'Can change stage', 37, 'change_stage');
INSERT INTO public.auth_permission (id, "name", content_type_id, codename) VALUES(127, 'Can delete stage', 37, 'delete_stage');
INSERT INTO public.auth_permission (id, "name", content_type_id, codename) VALUES(128, 'Can view stage', 37, 'view_stage');
INSERT INTO public.auth_permission (id, "name", content_type_id, codename) VALUES(129, 'Can add loose stock snapshot', 38, 'add_loosestocksnapshot');
INSERT INTO public.auth_permission (id, "name", content_type_id, codename) VALUES(130, 'Can change loose stock snapshot', 38, 'change_loosestocksnapshot');
INSERT INTO public.auth_permission (id, "name", content_type_id, codename) VALUES(131, 'Can delete loose stock snapshot', 38, 'delete_loosestocksnapshot');
INSERT INTO public.auth_permission (id, "name", content_type_id, codename) VALUES(132, 'Can view loose stock snapshot', 38, 'view_loosestocksnapshot');
INSERT INTO public.auth_permission (id, "name", content_type_id, codename) VALUES(133, 'Can add product description item', 39, 'add_productdescriptionitem');
INSERT INTO public.auth_permission (id, "name", content_type_id, codename) VALUES(134, 'Can change product description item', 39, 'change_productdescriptionitem');
INSERT INTO public.auth_permission (id, "name", content_type_id, codename) VALUES(135, 'Can delete product description item', 39, 'delete_productdescriptionitem');
INSERT INTO public.auth_permission (id, "name", content_type_id, codename) VALUES(136, 'Can view product description item', 39, 'view_productdescriptionitem');
INSERT INTO public.auth_permission (id, "name", content_type_id, codename) VALUES(137, 'Can add party', 40, 'add_party');
INSERT INTO public.auth_permission (id, "name", content_type_id, codename) VALUES(138, 'Can change party', 40, 'change_party');
INSERT INTO public.auth_permission (id, "name", content_type_id, codename) VALUES(139, 'Can delete party', 40, 'delete_party');
INSERT INTO public.auth_permission (id, "name", content_type_id, codename) VALUES(140, 'Can view party', 40, 'view_party');
INSERT INTO public.auth_permission (id, "name", content_type_id, codename) VALUES(141, 'Can add inward raw material', 41, 'add_inwardrawmaterial');
INSERT INTO public.auth_permission (id, "name", content_type_id, codename) VALUES(142, 'Can change inward raw material', 41, 'change_inwardrawmaterial');
INSERT INTO public.auth_permission (id, "name", content_type_id, codename) VALUES(143, 'Can delete inward raw material', 41, 'delete_inwardrawmaterial');
INSERT INTO public.auth_permission (id, "name", content_type_id, codename) VALUES(144, 'Can view inward raw material', 41, 'view_inwardrawmaterial');
INSERT INTO public.auth_permission (id, "name", content_type_id, codename) VALUES(145, 'Can add other material type', 42, 'add_othermaterialtype');
INSERT INTO public.auth_permission (id, "name", content_type_id, codename) VALUES(146, 'Can change other material type', 42, 'change_othermaterialtype');
INSERT INTO public.auth_permission (id, "name", content_type_id, codename) VALUES(147, 'Can delete other material type', 42, 'delete_othermaterialtype');
INSERT INTO public.auth_permission (id, "name", content_type_id, codename) VALUES(148, 'Can view other material type', 42, 'view_othermaterialtype');
INSERT INTO public.auth_permission (id, "name", content_type_id, codename) VALUES(149, 'Can add other material recipe', 43, 'add_othermaterialrecipe');
INSERT INTO public.auth_permission (id, "name", content_type_id, codename) VALUES(150, 'Can change other material recipe', 43, 'change_othermaterialrecipe');
INSERT INTO public.auth_permission (id, "name", content_type_id, codename) VALUES(151, 'Can delete other material recipe', 43, 'delete_othermaterialrecipe');
INSERT INTO public.auth_permission (id, "name", content_type_id, codename) VALUES(152, 'Can view other material recipe', 43, 'view_othermaterialrecipe');
INSERT INTO public.auth_permission (id, "name", content_type_id, codename) VALUES(153, 'Can add inward other material', 44, 'add_inwardothermaterial');
INSERT INTO public.auth_permission (id, "name", content_type_id, codename) VALUES(154, 'Can change inward other material', 44, 'change_inwardothermaterial');
INSERT INTO public.auth_permission (id, "name", content_type_id, codename) VALUES(155, 'Can delete inward other material', 44, 'delete_inwardothermaterial');
INSERT INTO public.auth_permission (id, "name", content_type_id, codename) VALUES(156, 'Can view inward other material', 44, 'view_inwardothermaterial');
INSERT INTO public.auth_permission (id, "name", content_type_id, codename) VALUES(157, 'Can add dispatch entry', 45, 'add_dispatchentry');
INSERT INTO public.auth_permission (id, "name", content_type_id, codename) VALUES(158, 'Can change dispatch entry', 45, 'change_dispatchentry');
INSERT INTO public.auth_permission (id, "name", content_type_id, codename) VALUES(159, 'Can delete dispatch entry', 45, 'delete_dispatchentry');
INSERT INTO public.auth_permission (id, "name", content_type_id, codename) VALUES(160, 'Can view dispatch entry', 45, 'view_dispatchentry');
INSERT INTO public.auth_permission (id, "name", content_type_id, codename) VALUES(161, 'Can add dispatch entry item', 46, 'add_dispatchentryitem');
INSERT INTO public.auth_permission (id, "name", content_type_id, codename) VALUES(162, 'Can change dispatch entry item', 46, 'change_dispatchentryitem');
INSERT INTO public.auth_permission (id, "name", content_type_id, codename) VALUES(163, 'Can delete dispatch entry item', 46, 'delete_dispatchentryitem');
INSERT INTO public.auth_permission (id, "name", content_type_id, codename) VALUES(164, 'Can view dispatch entry item', 46, 'view_dispatchentryitem');
INSERT INTO public.auth_permission (id, "name", content_type_id, codename) VALUES(166, 'Can add field trip', 47, 'add_fieldtrip');
INSERT INTO public.auth_permission (id, "name", content_type_id, codename) VALUES(167, 'Can change field trip', 47, 'change_fieldtrip');
INSERT INTO public.auth_permission (id, "name", content_type_id, codename) VALUES(168, 'Can delete field trip', 47, 'delete_fieldtrip');
INSERT INTO public.auth_permission (id, "name", content_type_id, codename) VALUES(169, 'Can view field trip', 47, 'view_fieldtrip');
INSERT INTO public.auth_permission (id, "name", content_type_id, codename) VALUES(170, 'Can add farmer visit', 48, 'add_farmervisit');
INSERT INTO public.auth_permission (id, "name", content_type_id, codename) VALUES(171, 'Can change farmer visit', 48, 'change_farmervisit');
INSERT INTO public.auth_permission (id, "name", content_type_id, codename) VALUES(172, 'Can delete farmer visit', 48, 'delete_farmervisit');
INSERT INTO public.auth_permission (id, "name", content_type_id, codename) VALUES(173, 'Can view farmer visit', 48, 'view_farmervisit');
INSERT INTO public.auth_permission (id, "name", content_type_id, codename) VALUES(174, 'Can add farmer visit crop', 49, 'add_farmervisitcrop');
INSERT INTO public.auth_permission (id, "name", content_type_id, codename) VALUES(175, 'Can change farmer visit crop', 49, 'change_farmervisitcrop');
INSERT INTO public.auth_permission (id, "name", content_type_id, codename) VALUES(176, 'Can delete farmer visit crop', 49, 'delete_farmervisitcrop');
INSERT INTO public.auth_permission (id, "name", content_type_id, codename) VALUES(177, 'Can view farmer visit crop', 49, 'view_farmervisitcrop');
INSERT INTO public.auth_permission (id, "name", content_type_id, codename) VALUES(178, 'Can add farmer visit product', 50, 'add_farmervisitproduct');
INSERT INTO public.auth_permission (id, "name", content_type_id, codename) VALUES(179, 'Can change farmer visit product', 50, 'change_farmervisitproduct');
INSERT INTO public.auth_permission (id, "name", content_type_id, codename) VALUES(180, 'Can delete farmer visit product', 50, 'delete_farmervisitproduct');
INSERT INTO public.auth_permission (id, "name", content_type_id, codename) VALUES(181, 'Can view farmer visit product', 50, 'view_farmervisitproduct');
INSERT INTO public.auth_permission (id, "name", content_type_id, codename) VALUES(182, 'Can add godown manager', 52, 'add_godownmanager');
INSERT INTO public.auth_permission (id, "name", content_type_id, codename) VALUES(183, 'Can change godown manager', 52, 'change_godownmanager');
INSERT INTO public.auth_permission (id, "name", content_type_id, codename) VALUES(184, 'Can delete godown manager', 52, 'delete_godownmanager');
INSERT INTO public.auth_permission (id, "name", content_type_id, codename) VALUES(185, 'Can view godown manager', 52, 'view_godownmanager');
INSERT INTO public.auth_permission (id, "name", content_type_id, codename) VALUES(186, 'Can add raw material waste', 53, 'add_rawmaterialwaste');
INSERT INTO public.auth_permission (id, "name", content_type_id, codename) VALUES(187, 'Can change raw material waste', 53, 'change_rawmaterialwaste');
INSERT INTO public.auth_permission (id, "name", content_type_id, codename) VALUES(188, 'Can delete raw material waste', 53, 'delete_rawmaterialwaste');
INSERT INTO public.auth_permission (id, "name", content_type_id, codename) VALUES(189, 'Can view raw material waste', 53, 'view_rawmaterialwaste');
INSERT INTO public.auth_permission (id, "name", content_type_id, codename) VALUES(190, 'Can add stock event', 54, 'add_stockevent');
INSERT INTO public.auth_permission (id, "name", content_type_id, codename) VALUES(191, 'Can change stock event', 54, 'change_stockevent');
INSERT INTO public.auth_permission (id, "name", content_type_id, codename) VALUES(192, 'Can delete stock event', 54, 'delete_stockevent');
INSERT INTO public.auth_permission (id, "name", content_type_id, codename) VALUES(193, 'Can view stock event', 54, 'view_stockevent');

INSERT INTO public.auth_permission (id, "name", content_type_id, codename) VALUES(194, 'Can add push device', 55, 'add_pushdevice');
INSERT INTO public.auth_permission (id, "name", content_type_id, codename) VALUES(195, 'Can change push device', 55, 'change_pushdevice');
INSERT INTO public.auth_permission (id, "name", content_type_id, codename) VALUES(196, 'Can delete push device', 55, 'delete_pushdevice');
INSERT INTO public.auth_permission (id, "name", content_type_id, codename) VALUES(197, 'Can view push device', 55, 'view_pushdevice');
INSERT INTO public.auth_permission (id, "name", content_type_id, codename) VALUES(198, 'Can add notification', 56, 'add_notification');
INSERT INTO public.auth_permission (id, "name", content_type_id, codename) VALUES(199, 'Can change notification', 56, 'change_notification');
INSERT INTO public.auth_permission (id, "name", content_type_id, codename) VALUES(200, 'Can delete notification', 56, 'delete_notification');
INSERT INTO public.auth_permission (id, "name", content_type_id, codename) VALUES(201, 'Can view notification', 56, 'view_notification');
-- Custom permission (authentication.User.Meta.permissions): gates POST /api/execute-code/.
INSERT INTO public.auth_permission (id, "name", content_type_id, codename) VALUES(165, 'Can execute Python code on the server', 1, 'execute_python_code');

-- -------------------------------------------------------------------------
-- aggregator_status (generic, enum-like status values)
--   Order lifecycle (1-7) + client verification (8-9) + inward raw-material
--   lot lifecycle (10-11, 16) + field-trip lifecycle (12-15) + return-order
--   lifecycle (17-19). created_by left
--   NULL (seed data). Id 16 (code RAW_MATERIAL_REJECTED) is not contiguous
--   with 10-11: added later, after the field-trip range, and its code must
--   differ from the unrelated order-lifecycle REJECTED row at id 7.
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
INSERT INTO public.aggregator_status (id, created_at, updated_at, is_deleted, deleted_at, deleted_by_id, created_by_id, code, "name", "sequence") VALUES(10, '2026-09-27 00:00:00.000', '2026-09-27 00:00:00.000', false, NULL, NULL, NULL, 'LAB_TESTING', 'Lab Testing', 1);
INSERT INTO public.aggregator_status (id, created_at, updated_at, is_deleted, deleted_at, deleted_by_id, created_by_id, code, "name", "sequence") VALUES(11, '2026-09-27 00:00:00.000', '2026-09-27 00:00:00.000', false, NULL, NULL, NULL, 'IN_USE', 'In Use', 2);
INSERT INTO public.aggregator_status (id, created_at, updated_at, is_deleted, deleted_at, deleted_by_id, created_by_id, code, "name", "sequence") VALUES(12, '2026-08-28 05:22:53.878', '2026-08-28 05:22:53.878', false, NULL, NULL, NULL, 'PLANNED', 'Planned', 1);
INSERT INTO public.aggregator_status (id, created_at, updated_at, is_deleted, deleted_at, deleted_by_id, created_by_id, code, "name", "sequence") VALUES(13, '2026-08-28 05:22:53.878', '2026-08-28 05:22:53.878', false, NULL, NULL, NULL, 'APPROVED', 'Approved', 2);
INSERT INTO public.aggregator_status (id, created_at, updated_at, is_deleted, deleted_at, deleted_by_id, created_by_id, code, "name", "sequence") VALUES(14, '2026-08-28 05:22:53.878', '2026-08-28 05:22:53.878', false, NULL, NULL, NULL, 'IN_PROGRESS', 'In progress', 3);
INSERT INTO public.aggregator_status (id, created_at, updated_at, is_deleted, deleted_at, deleted_by_id, created_by_id, code, "name", "sequence") VALUES(15, '2026-08-28 05:22:53.878', '2026-08-28 05:22:53.878', false, NULL, NULL, NULL, 'COMPLETED', 'Completed', 4);
INSERT INTO public.aggregator_status (id, created_at, updated_at, is_deleted, deleted_at, deleted_by_id, created_by_id, code, "name", "sequence") VALUES(16, '2026-10-01 00:00:00.000', '2026-10-01 00:00:00.000', false, NULL, NULL, NULL, 'RAW_MATERIAL_REJECTED', 'Rejected', 3);
INSERT INTO public.aggregator_status (id, created_at, updated_at, is_deleted, deleted_at, deleted_by_id, created_by_id, code, "name", "sequence") VALUES(17, '2026-10-03 00:00:00.000', '2026-10-03 00:00:00.000', false, NULL, NULL, NULL, 'RETURN_PENDING', 'Return pending', 1);
INSERT INTO public.aggregator_status (id, created_at, updated_at, is_deleted, deleted_at, deleted_by_id, created_by_id, code, "name", "sequence") VALUES(18, '2026-10-03 00:00:00.000', '2026-10-03 00:00:00.000', false, NULL, NULL, NULL, 'RETURN_ACCEPTED', 'Return accepted', 2);
INSERT INTO public.aggregator_status (id, created_at, updated_at, is_deleted, deleted_at, deleted_by_id, created_by_id, code, "name", "sequence") VALUES(19, '2026-10-03 00:00:00.000', '2026-10-03 00:00:00.000', false, NULL, NULL, NULL, 'RETURN_REJECTED', 'Return rejected', 3);

-- -------------------------------------------------------------------------
-- aggregator_stage (seed classification of a product; enum-like, 4 fixed rows)
--   Mirrored by aggregator/models/Stage.py::StageIds. created_by left NULL.
-- -------------------------------------------------------------------------
INSERT INTO public.aggregator_stage (id, created_at, updated_at, is_deleted, deleted_at, deleted_by_id, created_by_id, code, "name", "sequence") VALUES(1, '2026-08-28 05:22:53.878', '2026-08-28 05:22:53.878', false, NULL, NULL, NULL, 'BREEDER', 'Breeder', 1);
INSERT INTO public.aggregator_stage (id, created_at, updated_at, is_deleted, deleted_at, deleted_by_id, created_by_id, code, "name", "sequence") VALUES(2, '2026-08-28 05:22:53.878', '2026-08-28 05:22:53.878', false, NULL, NULL, NULL, 'FOUNDATION', 'Foundation', 2);
INSERT INTO public.aggregator_stage (id, created_at, updated_at, is_deleted, deleted_at, deleted_by_id, created_by_id, code, "name", "sequence") VALUES(3, '2026-08-28 05:22:53.878', '2026-08-28 05:22:53.878', false, NULL, NULL, NULL, 'RESEARCH', 'Research', 3);
INSERT INTO public.aggregator_stage (id, created_at, updated_at, is_deleted, deleted_at, deleted_by_id, created_by_id, code, "name", "sequence") VALUES(4, '2026-08-28 05:22:53.878', '2026-08-28 05:22:53.878', false, NULL, NULL, NULL, 'CERTIFIED', 'Certified', 4);

INSERT INTO public.authentication_user (id, "password", last_login, is_superuser, created_at, updated_at, phone_number, "name", email, totp_secret, totp_enabled, totp_last_counter, failed_totp_attempts, totp_lockout_until, is_verified, is_staff, is_active, date_joined, created_by_id, verified_by_id) VALUES(2, '!unusable', NULL, false, '2026-08-28 05:22:53.878', '2026-08-28 05:22:54.057', '8888888888', 'no totp user', NULL, NULL, false, NULL, 0, NULL, false, false, true, '2026-08-28 05:22:54.057', 1, NULL);
-- User 1 may already exist: the web container's createsuperuser_if_not_exists can win the race after a drop.
INSERT INTO public.authentication_user (id, "password", last_login, is_superuser, created_at, updated_at, phone_number, "name", email, totp_secret, totp_enabled, totp_last_counter, failed_totp_attempts, totp_lockout_until, is_verified, is_staff, is_active, date_joined, created_by_id, verified_by_id) VALUES(1, 'argon2$argon2id$v=19$m=102400,t=2,p=8$R2xUZXNHM2JtQkFhaVhtTjdHTjNZdw$sSm84Zeic9+weLp+hLiBDHtXZDOrKSYeVSmsaR9l/CA', '2026-09-07 00:18:33.996', true, '2026-08-28 05:22:53.878', '2026-08-28 05:22:54.057', '9999999999', 'admin', 'admin@example.com', 'JBSWY3DPEHPK3PXP', true, NULL, 0, NULL, true, true, true, '2026-08-28 05:22:54.057', 1, 1) ON CONFLICT (id) DO UPDATE SET "password" = EXCLUDED."password", "last_login" = EXCLUDED."last_login", "is_superuser" = EXCLUDED."is_superuser", "created_at" = EXCLUDED."created_at", "updated_at" = EXCLUDED."updated_at", "phone_number" = EXCLUDED."phone_number", "name" = EXCLUDED."name", "email" = EXCLUDED."email", "totp_secret" = EXCLUDED."totp_secret", "totp_enabled" = EXCLUDED."totp_enabled", "totp_last_counter" = EXCLUDED."totp_last_counter", "failed_totp_attempts" = EXCLUDED."failed_totp_attempts", "totp_lockout_until" = EXCLUDED."totp_lockout_until", "is_verified" = EXCLUDED."is_verified", "is_staff" = EXCLUDED."is_staff", "is_active" = EXCLUDED."is_active", "date_joined" = EXCLUDED."date_joined", "created_by_id" = EXCLUDED."created_by_id", "verified_by_id" = EXCLUDED."verified_by_id";
INSERT INTO public.authentication_user (id, "password", last_login, is_superuser, created_at, updated_at, phone_number, "name", email, totp_secret, totp_enabled, totp_last_counter, failed_totp_attempts, totp_lockout_until, is_verified, is_staff, is_active, date_joined, created_by_id, verified_by_id) VALUES(3, '!Jg4RntBkly091ZH8an1YkFdBcN3iw6etycyxC71q', NULL, false, '2026-09-07 00:33:09.852', '2026-09-07 00:33:09.857', '0000000000', 'Sales Person User', 'test.salesperson@gmail.com', 'U52KNHEOJXHW4UJZNX7EJNFZXS3S5VUI', true, NULL, 0, NULL, true, false, true, '2026-09-07 00:33:09.857', 1, 1);
INSERT INTO public.authentication_user (id, "password", last_login, is_superuser, created_at, updated_at, phone_number, "name", email, totp_secret, totp_enabled, totp_last_counter, failed_totp_attempts, totp_lockout_until, is_verified, is_staff, is_active, date_joined, created_by_id, verified_by_id) VALUES(4, '!NZUkIEOkrZZK6I49TejjY9YFn1UlA3lxcTyPnVU3', NULL, false, '2026-09-07 00:34:08.192', '2026-09-07 00:34:08.195', '1111111111', 'Sales Admin User', 'test.salesadmin@gmail.com', 'TR4JC6LNBAMKUTV2YGLBVSKUFIPUF7KH', true, NULL, 0, NULL, true, false, true, '2026-09-07 00:34:08.195', 1, 1);
INSERT INTO public.authentication_user (id, "password", last_login, is_superuser, created_at, updated_at, phone_number, "name", email, totp_secret, totp_enabled, totp_last_counter, failed_totp_attempts, totp_lockout_until, is_verified, is_staff, is_active, date_joined, created_by_id, verified_by_id) VALUES(5, '!BLcRI0WOkSbBDCT9rPbsRoSrksTpJctSSDUA1CbC', NULL, false, '2026-09-07 00:36:06.723', '2026-09-07 00:36:06.727', '2222222222', 'Sales Admin User - Stock', 'test.salesadmin.stock@gmail.com', '6MOWDDABZGOL6LN5TCCIW5PGCMSG6SVR', true, NULL, 0, NULL, true, false, true, '2026-09-07 00:36:06.727', 1, 1);
INSERT INTO public.authentication_user (id, "password", last_login, is_superuser, created_at, updated_at, phone_number, "name", email, totp_secret, totp_enabled, totp_last_counter, failed_totp_attempts, totp_lockout_until, is_verified, is_staff, is_active, date_joined, created_by_id, verified_by_id) VALUES(6, '!BLcRI0WOkSbBDCT9rPbsRoSrksTpJctSSDUA1CbC', NULL, false, '2026-09-07 00:36:06.723', '2026-09-07 00:36:06.727', '3333333333', 'Godown Manager User', 'test.godownmanager@gmail.com', 'JBSWY3DPEHPK3PXPJBSWY3DPEHPK3PXP', true, NULL, 0, NULL, true, false, true, '2026-09-07 00:36:06.727', 1, 1);

INSERT INTO public.authentication_admin (id, created_at, updated_at, is_deleted, deleted_at, deleted_by_id, created_by_id, user_id, can_update_stock_count, share_contact) VALUES(1, '2026-09-07 00:34:36.434', '2026-09-07 00:36:17.156', false, NULL, NULL, 1, 4, false, false);
INSERT INTO public.authentication_admin (id, created_at, updated_at, is_deleted, deleted_at, deleted_by_id, created_by_id, user_id, can_update_stock_count, share_contact) VALUES(2, '2026-09-07 00:36:25.485', '2026-09-07 00:36:25.487', false, NULL, NULL, 1, 5, true, true);

INSERT INTO public.aggregator_country (id, created_at, updated_at, is_deleted, deleted_at, "name", iso_code, created_by_id, deleted_by_id) VALUES(1, '2026-09-07 00:23:22.143', '2026-09-07 00:23:22.145', false, NULL, 'India', 'IN', 1, NULL);
INSERT INTO public.aggregator_state (id, created_at, updated_at, is_deleted, deleted_at, "name", code, country_id, created_by_id, deleted_by_id) VALUES(1, '2026-09-07 00:23:44.551', '2026-09-07 00:23:44.553', false, NULL, 'Gujarat', 'GJ', 1, 1, NULL);
INSERT INTO public.aggregator_state (id, created_at, updated_at, is_deleted, deleted_at, "name", code, country_id, created_by_id, deleted_by_id) VALUES(2, '2026-09-07 00:23:57.717', '2026-09-07 00:23:57.720', false, NULL, 'Rajasthan', 'RJ', 1, 1, NULL);

INSERT INTO public.aggregator_city (id, created_at, updated_at, is_deleted, deleted_at, "name", created_by_id, deleted_by_id, state_id) VALUES(1, '2026-09-07 00:24:32.835', '2026-09-07 00:24:32.839', false, NULL, 'Surat', 1, NULL, 1);
INSERT INTO public.aggregator_city (id, created_at, updated_at, is_deleted, deleted_at, "name", created_by_id, deleted_by_id, state_id) VALUES(2, '2026-09-07 00:24:41.255', '2026-09-07 00:24:41.259', false, NULL, 'Ahmedabad', 1, NULL, 1);
INSERT INTO public.aggregator_city (id, created_at, updated_at, is_deleted, deleted_at, "name", created_by_id, deleted_by_id, state_id) VALUES(3, '2026-09-07 00:24:50.456', '2026-09-07 00:24:50.459', false, NULL, 'Rajkot', 1, NULL, 1);
INSERT INTO public.aggregator_city (id, created_at, updated_at, is_deleted, deleted_at, "name", created_by_id, deleted_by_id, state_id) VALUES(4, '2026-09-07 00:25:00.461', '2026-09-07 00:25:00.464', false, NULL, 'Jaipur', 1, NULL, 2);
INSERT INTO public.aggregator_city (id, created_at, updated_at, is_deleted, deleted_at, "name", created_by_id, deleted_by_id, state_id) VALUES(5, '2026-09-07 00:25:55.888', '2026-09-07 00:25:55.892', false, NULL, 'Jaisalmer', 1, NULL, 2);

INSERT INTO public.authentication_salesperson (id, created_at, updated_at, is_deleted, deleted_at, deleted_by_id, created_by_id, user_id, city_id) VALUES(1, '2026-09-07 00:33:35.796', '2026-09-07 00:33:35.801', false, NULL, NULL, 1, 3, 2);
INSERT INTO public.authentication_godownmanager (id, created_at, updated_at, is_deleted, deleted_at, deleted_by_id, created_by_id, user_id) VALUES(1, '2026-09-07 00:33:35.796', '2026-09-07 00:33:35.801', false, NULL, NULL, 1, 6);

INSERT INTO public.aggregator_crop (id, created_at, updated_at, is_deleted, deleted_at, deleted_by_id, created_by_id, "name") VALUES(1, '2026-09-07 00:26:28.109', '2026-09-07 00:26:28.111', false, NULL, NULL, 1, 'Castor');
INSERT INTO public.aggregator_crop (id, created_at, updated_at, is_deleted, deleted_at, deleted_by_id, created_by_id, "name") VALUES(2, '2026-09-07 00:26:42.132', '2026-09-07 00:26:42.133', false, NULL, NULL, 1, 'Bajari');

INSERT INTO public.aggregator_product (id, created_at, updated_at, is_deleted, deleted_at, deleted_by_id, created_by_id, public_id, "name", crop_id, stage_id, selling_price, image_url) VALUES(1, '2026-09-07 00:28:02.358', '2026-09-07 00:28:12.045', false, NULL, NULL, 1, 'P-I34V7RI1JPUH', 'SAI-33', 1, 1, 120.00, '');
INSERT INTO public.aggregator_product (id, created_at, updated_at, is_deleted, deleted_at, deleted_by_id, created_by_id, public_id, "name", crop_id, stage_id, selling_price, image_url) VALUES(2, '2026-09-07 00:28:40.714', '2026-09-07 00:28:40.718', false, NULL, NULL, 1, 'P-NQ8N4LF7MJYQ', 'SAI-3353', 2, 1, 250.00, '');

INSERT INTO public.aggregator_productpackaging (id, created_at, updated_at, is_deleted, deleted_at, deleted_by_id, created_by_id, public_id, product_id, packet_weight, packets, selling_price) VALUES(1, '2026-09-07 00:29:08.487', '2026-09-07 00:29:15.227', false, NULL, NULL, 1, 'PP-U4UYPFOF08NZ', 1, 1.000, 40, 4800.00);
INSERT INTO public.aggregator_productpackaging (id, created_at, updated_at, is_deleted, deleted_at, deleted_by_id, created_by_id, public_id, product_id, packet_weight, packets, selling_price) VALUES(2, '2026-09-07 00:29:29.899', '2026-09-07 00:29:29.904', false, NULL, NULL, 1, 'PP-5SVE39LY2XEI', 2, 1.500, 20, 5000.00);

INSERT INTO public.aggregator_othermaterialtype (id, created_at, updated_at, is_deleted, deleted_at, deleted_by_id, created_by_id, "name", unit_type) VALUES(1, '2026-09-07 00:30:00.000', '2026-09-07 00:30:00.002', false, NULL, NULL, 1, 'bag_outer_cover', 'kg');
INSERT INTO public.aggregator_othermaterialtype (id, created_at, updated_at, is_deleted, deleted_at, deleted_by_id, created_by_id, "name", unit_type) VALUES(2, '2026-09-07 00:30:00.100', '2026-09-07 00:30:00.102', false, NULL, NULL, 1, 'packet_outer_cover', 'kg');
INSERT INTO public.aggregator_othermaterialtype (id, created_at, updated_at, is_deleted, deleted_at, deleted_by_id, created_by_id, "name", unit_type) VALUES(3, '2026-09-07 00:30:00.200', '2026-09-07 00:30:00.202', false, NULL, NULL, 1, 'leaflets', 'count');
-- -------------------------------------------------------------------------
-- Sequence sync
-- -------------------------------------------------------------------------
-- The inserts above set explicit primary keys, which does NOT advance each
-- table's identity/serial sequence. Re-sync every seeded table so the next
-- row created through the ORM/API gets an id after the seeded maximum instead
-- of colliding from id=1.
SELECT setval(pg_get_serial_sequence('public.django_content_type', 'id'),         (SELECT MAX(id) FROM public.django_content_type));
SELECT setval(pg_get_serial_sequence('public.auth_permission', 'id'),             (SELECT MAX(id) FROM public.auth_permission));
SELECT setval(pg_get_serial_sequence('public.aggregator_status', 'id'),           (SELECT MAX(id) FROM public.aggregator_status));
SELECT setval(pg_get_serial_sequence('public.aggregator_stage', 'id'),            (SELECT MAX(id) FROM public.aggregator_stage));
SELECT setval(pg_get_serial_sequence('public.authentication_user', 'id'),         (SELECT MAX(id) FROM public.authentication_user));
SELECT setval(pg_get_serial_sequence('public.authentication_admin', 'id'),        (SELECT MAX(id) FROM public.authentication_admin));
SELECT setval(pg_get_serial_sequence('public.authentication_salesperson', 'id'),  (SELECT MAX(id) FROM public.authentication_salesperson));
SELECT setval(pg_get_serial_sequence('public.authentication_godownmanager', 'id'), (SELECT MAX(id) FROM public.authentication_godownmanager));
SELECT setval(pg_get_serial_sequence('public.aggregator_country', 'id'),          (SELECT MAX(id) FROM public.aggregator_country));
SELECT setval(pg_get_serial_sequence('public.aggregator_state', 'id'),            (SELECT MAX(id) FROM public.aggregator_state));
SELECT setval(pg_get_serial_sequence('public.aggregator_city', 'id'),             (SELECT MAX(id) FROM public.aggregator_city));
SELECT setval(pg_get_serial_sequence('public.aggregator_crop', 'id'),             (SELECT MAX(id) FROM public.aggregator_crop));
SELECT setval(pg_get_serial_sequence('public.aggregator_product', 'id'),          (SELECT MAX(id) FROM public.aggregator_product));
SELECT setval(pg_get_serial_sequence('public.aggregator_productpackaging', 'id'), (SELECT MAX(id) FROM public.aggregator_productpackaging));
SELECT setval(pg_get_serial_sequence('public.aggregator_othermaterialtype', 'id'),    (SELECT MAX(id) FROM public.aggregator_othermaterialtype));


-- >>> DUMMY DATA BEGIN (tests/conftest.py skips everything up to DUMMY DATA END)
-- =========================================================================
-- Dummy data for manual testing
--   Sample rows for every table not seeded above, at most 5 rows per table,
--   weighted towards SAI-33 (product 1) with a little SAI-3353 (product 2).
--   Every date is relative to today (India time), so lots stay "reached" and
--   the counts stay "today's" whenever the file is loaded. Public ids are
--   readable (<PREFIX>DUMMY0000001).
--
--   Stock picture it produces (all derived at read time, nothing stored):
--     SAI-33   raw 1900 kg in use (+300 kg rejected, not spendable) - 960 bagged - 80 loose
--              - 37.5 wasted = 822.5 kg available; 20 bags counted, 5 reserved.
--     SAI-3353 raw 400 kg in use - 330 packed (bags + loose) - 5.5 wasted = 64.5 kg.
--     Packing material is stocked well above what the packed packets use.
--   Orders cover every lifecycle state: BOOKED, CONFIRMED, DISPATCHED (agency),
--   DELIVERED (own vehicle), ON_HOLD; custom orders: BOOKED, CONFIRMED, DISPATCHED.
--   Relies on the seed ids above: users 1-5 (3 = sales person, 4 = admin),
--   cities 1-5, crops 1-2, products 1-2, packagings 1-2, material types 1-3,
--   statuses 1-19 (16 = Rejected raw lot, 17-19 = return order), user 6 = godown manager.
-- =========================================================================

-- "Today" in the project's timezone, matching InventoryOperations.today().
CREATE FUNCTION pg_temp.today_ist() RETURNS date LANGUAGE sql AS
$$ SELECT (now() AT TIME ZONE 'Asia/Kolkata')::date $$;

-- -------------------------------------------------------------------------
-- A frozen product (is_usable = false): shows how the freeze reads. It is still
-- listed by the management endpoints, flagged; the catalogue and the recipe
-- picker omit it, and every inward / waste / packaging / count / booking write
-- for it is refused until it is switched back on.
-- -------------------------------------------------------------------------
INSERT INTO public.aggregator_product (id, created_at, updated_at, is_deleted, deleted_at, deleted_by_id, created_by_id, public_id, "name", crop_id, stage_id, selling_price, image_url, is_usable) VALUES(3, now(), now(), false, NULL, NULL, 1, 'P-DUMMY0000003', 'SAI-99', 1, 1, 110.00, '', false);
INSERT INTO public.aggregator_productpackaging (id, created_at, updated_at, is_deleted, deleted_at, deleted_by_id, created_by_id, public_id, product_id, packet_weight, packets, selling_price) VALUES(3, now(), now(), false, NULL, NULL, 1, 'PP-DUMMY000003', 3, 1.000, 20, 2200.00);
SELECT setval(pg_get_serial_sequence('public.aggregator_product', 'id'),          (SELECT MAX(id) FROM public.aggregator_product));
SELECT setval(pg_get_serial_sequence('public.aggregator_productpackaging', 'id'), (SELECT MAX(id) FROM public.aggregator_productpackaging));

-- -------------------------------------------------------------------------
-- Geography: pincodes + addresses
-- -------------------------------------------------------------------------
INSERT INTO public.aggregator_pincode (id, created_at, updated_at, is_deleted, created_by_id, code, city_id) VALUES
(1, now(), now(), false, 1, '395003', 1),
(2, now(), now(), false, 1, '380001', 2),
(3, now(), now(), false, 1, '360001', 3),
(4, now(), now(), false, 1, '302001', 4),
(5, now(), now(), false, 1, '345001', 5);

INSERT INTO public.aggregator_address (id, created_at, updated_at, is_deleted, created_by_id, address_line_1, address_line_2, city_id, state_id, country_id, pincode_id) VALUES
(1, now(), now(), false, 1, '12 Ring Road Industrial Estate', 'Near Textile Market', 1, 1, 1, 1),
(2, now(), now(), false, 1, '44 CG Road', 'Navrangpura', 2, 1, 1, 2),
(3, now(), now(), false, 1, '7 Kalawad Road', 'Opp. Agro Mandi', 3, 1, 1, 3),
(4, now(), now(), false, 1, '21 MI Road', 'Near Sindhi Camp', 4, 2, 1, 4),
(5, now(), now(), false, 1, '5 Gadisar Marg', 'Fort Area', 5, 2, 1, 5);

-- -------------------------------------------------------------------------
-- Master data: transport agencies, contacts, parties, product descriptions
-- -------------------------------------------------------------------------
INSERT INTO public.aggregator_transportagency (id, created_at, updated_at, is_deleted, created_by_id, "name") VALUES
(1, now(), now(), false, 1, 'Shree Maruti Courier'),
(2, now(), now(), false, 1, 'VRL Logistics'),
(3, now(), now(), false, 1, 'Gati Transport'),
(4, now(), now(), false, 1, 'Patel Roadways'),
(5, now(), now(), false, 1, 'Sai Cargo Movers');

INSERT INTO public.aggregator_contact (id, created_at, updated_at, is_deleted, created_by_id, "name", phone_number) VALUES
(1, now(), now(), false, 3, 'Mahesh Desai', '9825011001'),
(2, now(), now(), false, 3, 'Kiran Shah', '9825011002'),
(3, now(), now(), false, 3, 'Jayesh Patel', '9825011003'),
(4, now(), now(), false, 3, 'Rakesh Sharma', '9829011004'),
(5, now(), now(), false, 3, 'Bhanwar Singh', '9829011005');

INSERT INTO public.aggregator_party (id, created_at, updated_at, is_deleted, created_by_id, "name", city_id, contact_number) VALUES
(1, now(), now(), false, 4, 'Shree Agro Traders', 1, '9898100001'),
(2, now(), now(), false, 4, 'Gujarat Seed Suppliers', 2, '9898100002'),
(3, now(), now(), false, 4, 'Rajkot Packaging Co', 3, '9898100003'),
(4, now(), now(), false, 4, 'Jaipur Poly Industries', 4, '9898100004'),
(5, now(), now(), false, 4, 'Marwar Agro Inputs', 5, '9898100005');

INSERT INTO public.aggregator_productdescriptionitem (id, created_at, updated_at, is_deleted, created_by_id, product_id, "text", sequence) VALUES
(1, now(), now(), false, 1, 1, 'High-yielding castor hybrid', 1),
(2, now(), now(), false, 1, 1, 'Tolerant to wilt and root rot', 2),
(3, now(), now(), false, 1, 1, 'Matures in 150-160 days', 3),
(4, now(), now(), false, 1, 2, 'Drought-tolerant bajari hybrid', 1),
(5, now(), now(), false, 1, 2, 'Suited to sandy soils of Rajasthan', 2);

-- -------------------------------------------------------------------------
-- Clients (+ address / contact / transport agency links)
--   Clients 1-4 verified; client 5 still VERIFICATION_PENDING (status 8).
-- -------------------------------------------------------------------------
INSERT INTO public.aggregator_client (id, created_at, updated_at, is_deleted, created_by_id, public_id, company_name, company_phone, gst_number, status_id, verified_by_id, verified_at) VALUES
(1, now(), now(), false, 3, 'C-DUMMY0000001', 'Desai Agro Centre', '0261400001', '24AAACD1001A1Z1', 9, 4, now()),
(2, now(), now(), false, 3, 'C-DUMMY0000002', 'Shah Krishi Bhandar', '0792500002', '24AAACS1002B1Z2', 9, 4, now()),
(3, now(), now(), false, 3, 'C-DUMMY0000003', 'Patel Seeds & Fertilizers', '0281600003', '24AAACP1003C1Z3', 9, 4, now()),
(4, now(), now(), false, 3, 'C-DUMMY0000004', 'Sharma Beej Bhandar', '0141700004', '08AAACS1004D1Z4', 9, 4, now()),
(5, now(), now(), false, 3, 'C-DUMMY0000005', 'Marwar Kisan Sewa Kendra', '0299200005', '08AAACM1005E1Z5', 8, NULL, NULL);

INSERT INTO public.aggregator_clientaddress (id, created_at, updated_at, is_deleted, created_by_id, client_id, address_id, label, is_primary) VALUES
(1, now(), now(), false, 3, 1, 1, 'Head Office', true),
(2, now(), now(), false, 3, 2, 2, 'Head Office', true),
(3, now(), now(), false, 3, 3, 3, 'Warehouse', true),
(4, now(), now(), false, 3, 4, 4, 'Head Office', true),
(5, now(), now(), false, 3, 5, 5, 'Shop', true);

INSERT INTO public.aggregator_clientcontact (id, created_at, updated_at, is_deleted, created_by_id, client_id, contact_id, "role", is_primary) VALUES
(1, now(), now(), false, 3, 1, 1, 'Owner', true),
(2, now(), now(), false, 3, 2, 2, 'Owner', true),
(3, now(), now(), false, 3, 3, 3, 'Manager', true),
(4, now(), now(), false, 3, 4, 4, 'Owner', true),
(5, now(), now(), false, 3, 5, 5, 'Owner', true);

INSERT INTO public.aggregator_clienttransportagency (id, created_at, updated_at, is_deleted, created_by_id, client_id, transport_agency_id, is_primary) VALUES
(1, now(), now(), false, 3, 1, 1, true),
(2, now(), now(), false, 3, 2, 2, true),
(3, now(), now(), false, 3, 3, 3, true),
(4, now(), now(), false, 3, 4, 4, true),
(5, now(), now(), false, 3, 5, 5, true);

-- -------------------------------------------------------------------------
-- Inward raw material (SAI-33 gets four lots, SAI-3353 one)
--   status 10 = Lab Testing (not in stock yet), 11 = In Use.
-- -------------------------------------------------------------------------
INSERT INTO public.aggregator_inwardrawmaterial (id, created_at, updated_at, is_deleted, created_by_id, public_id, lot_no, effective_date, lab_sampling_date, product_id, party_id, quantity_kg, status_id) VALUES
(1, now(), now(), false, 6, 'IR-DUMMY0000001', 'SUP-LOT-A1', pg_temp.today_ist() - 24, pg_temp.today_ist() - 27, 1, 1, 1000.000, 11),
(2, now(), now(), false, 6, 'IR-DUMMY0000002', 'SUP-LOT-A2', pg_temp.today_ist() - 14, pg_temp.today_ist() - 17, 1, 2, 500.000, 11),
(3, now(), now(), false, 6, 'IR-DUMMY0000003', 'SUP-LOT-A3', pg_temp.today_ist() - 4, pg_temp.today_ist() - 7, 1, 1, 400.000, 11),
(4, now(), now(), false, 6, 'IR-DUMMY0000004', 'SUP-LOT-A4', pg_temp.today_ist() - 6, pg_temp.today_ist() - 9, 1, 2, 300.000, 16),
(5, now(), now(), false, 6, 'IR-DUMMY0000005', 'SUP-LOT-A5', pg_temp.today_ist() - 20, pg_temp.today_ist() - 23, 2, 5, 400.000, 11);

-- Raw material written off as waste (undated)
INSERT INTO public.aggregator_rawmaterialwaste (id, created_at, updated_at, is_deleted, created_by_id, public_id, product_id, quantity_kg, reason) VALUES
(1, now(), now(), false, 4, 'WS-DUMMY0000001', 1, 20.000, 'Rain damage during storage'),
(2, now(), now(), false, 4, 'WS-DUMMY0000002', 1, 12.500, 'Spillage while bagging'),
(3, now(), now(), false, 4, 'WS-DUMMY0000003', 1, 5.000, 'Rodent damage'),
(4, now(), now(), false, 4, 'WS-DUMMY0000004', 2, 5.000, 'Moisture / fungus'),
(5, now(), now(), false, 4, 'WS-DUMMY0000005', 2, 0.500, 'Sampling loss');

-- -------------------------------------------------------------------------
-- Packing (other) material: recipes + inward lots
--   Per packet: SAI-33 1kg = 1 leaflet + 0.010 kg packet cover + 0.005 kg bag cover;
--               SAI-3353 1.5kg = 1 leaflet + 0.015 kg packet cover.
-- -------------------------------------------------------------------------
INSERT INTO public.aggregator_othermaterialrecipe (id, created_at, updated_at, is_deleted, created_by_id, public_id, product_id, material_type_id, packet_weight, quantity) VALUES
(1, now(), now(), false, 4, 'OMR-DUMMY0000001', 1, 3, 1.000, 1.000),
(2, now(), now(), false, 4, 'OMR-DUMMY0000002', 1, 2, 1.000, 0.010),
(3, now(), now(), false, 4, 'OMR-DUMMY0000003', 1, 1, 1.000, 0.005),
(4, now(), now(), false, 4, 'OMR-DUMMY0000004', 2, 3, 1.500, 1.000),
(5, now(), now(), false, 4, 'OMR-DUMMY0000005', 2, 2, 1.500, 0.015);

INSERT INTO public.aggregator_inwardothermaterial (id, created_at, updated_at, is_deleted, created_by_id, public_id, effective_date, party_id, recipe_id, quantity) VALUES
(1, now(), now(), false, 6, 'IO-DUMMY0000001', pg_temp.today_ist() - 22, 3, 1, 1500.000),
(2, now(), now(), false, 6, 'IO-DUMMY0000002', pg_temp.today_ist() - 8, 3, 1, 800.000),
(3, now(), now(), false, 6, 'IO-DUMMY0000003', pg_temp.today_ist() - 22, 4, 2, 25.000),
(4, now(), now(), false, 6, 'IO-DUMMY0000004', pg_temp.today_ist() - 22, 4, 3, 15.000),
(5, now(), now(), false, 6, 'IO-DUMMY0000005', pg_temp.today_ist() - 8, 3, 5, 10.000);

-- -------------------------------------------------------------------------
-- Daily stock counts: bags (today is complete for both packagings) + loose
-- -------------------------------------------------------------------------
INSERT INTO public.aggregator_inventorysnapshot (id, created_at, updated_at, is_deleted, created_by_id, public_id, snapshot_date, product_packaging_id, bags, counted_at) VALUES
(1, now(), now(), false, 5, 'INV-DUMMY0000001', pg_temp.today_ist(), 1, 20, now()),
(2, now(), now(), false, 5, 'INV-DUMMY0000002', pg_temp.today_ist(), 2, 8, now()),
(3, now(), now(), false, 5, 'INV-DUMMY0000003', pg_temp.today_ist() - 1, 1, 24, (pg_temp.today_ist() - 1) + time '09:00'),
(4, now(), now(), false, 5, 'INV-DUMMY0000004', pg_temp.today_ist() - 1, 2, 9, (pg_temp.today_ist() - 1) + time '09:00'),
(5, now(), now(), false, 5, 'INV-DUMMY0000005', pg_temp.today_ist() - 2, 1, 28, (pg_temp.today_ist() - 2) + time '09:00');

INSERT INTO public.aggregator_loosestocksnapshot (id, created_at, updated_at, is_deleted, created_by_id, public_id, snapshot_date, product_id, packet_weight, packets, counted_at) VALUES
(1, now(), now(), false, 5, 'LS-DUMMY0000001', pg_temp.today_ist(), 1, 1.000, 60, now()),
(2, now(), now(), false, 5, 'LS-DUMMY0000002', pg_temp.today_ist(), 2, 1.500, 20, now()),
(3, now(), now(), false, 5, 'LS-DUMMY0000003', pg_temp.today_ist() - 1, 1, 1.000, 75, (pg_temp.today_ist() - 1) + time '09:00'),
(4, now(), now(), false, 5, 'LS-DUMMY0000004', pg_temp.today_ist() - 1, 2, 1.500, 15, (pg_temp.today_ist() - 1) + time '09:00'),
(5, now(), now(), false, 5, 'LS-DUMMY0000005', pg_temp.today_ist() - 3, 1, 1.000, 50, (pg_temp.today_ist() - 3) + time '09:00');

-- -------------------------------------------------------------------------
-- Dispatch records (attached to the DISPATCHED / DELIVERED orders below)
--   dispatchdetails 1 -> order 2 and 2 -> custom order 2 (agency / LR);
--   privatedispatchdetails 1 -> order 4 (own vehicle, no LR).
-- -------------------------------------------------------------------------
INSERT INTO public.aggregator_dispatchdetails (id, created_at, updated_at, is_deleted, client_id, dispatched_by_id, dispatch_date, from_city_id, to_city_id, lr_number, driver_name, driver_number, vehicle_number) VALUES
(1, now(), now(), false, 2, 4, pg_temp.today_ist() - 1, 1, 2, 'LR-GJ-100234', 'Ramesh Patel', '9726000001', 'GJ05AB1234'),
(2, now(), now(), false, 2, 4, pg_temp.today_ist() - 1, 1, 2, '', 'Suresh Rathod', '9726000002', 'GJ05CD5678');

INSERT INTO public.aggregator_privatedispatchdetails (id, created_at, updated_at, is_deleted, client_id, dispatched_by_id, dispatch_date, from_city_id, to_city_id, vehicle_number, driver_number, driver_name) VALUES
(1, now(), now(), false, 4, 4, pg_temp.today_ist() - 3, 1, 4, 'GJ05EF9012', '9726000003', 'Dinesh Solanki');

-- -------------------------------------------------------------------------
-- Orders (bag orders): one per lifecycle state worth testing
--   1 CONFIRMED (3)  reserves 5 bags      2 DISPATCHED (4) agency, yesterday
--   3 BOOKED (1)                          4 DELIVERED (5)  own vehicle
--   5 ON_HOLD (6)
-- -------------------------------------------------------------------------
INSERT INTO public.aggregator_order (id, created_at, updated_at, is_deleted, created_by_id, public_id, client_id, delivery_address_id, status_id, expected_delivery_date, actual_delivery_date, dispatch_details_id, private_dispatch_details_id, transport_agency_id, special_comments, verified_by_id, verified_at) VALUES
(1, now(), now(), false, 3, 'ORD-DUMMY0000001', 1, 1, 3, pg_temp.today_ist() + 5, NULL, NULL, NULL, 1, 'Deliver before sowing season', 4, now()),
(2, now(), now(), false, 3, 'ORD-DUMMY0000002', 2, 2, 4, pg_temp.today_ist() + 2, NULL, 1, NULL, 2, '', 4, now()),
(3, now(), now(), false, 3, 'ORD-DUMMY0000003', 3, 3, 1, pg_temp.today_ist() + 9, NULL, NULL, NULL, 3, 'Call before dispatch', NULL, NULL),
(4, now(), now(), false, 3, 'ORD-DUMMY0000004', 4, 4, 5, pg_temp.today_ist() - 1, pg_temp.today_ist() - 1, NULL, 1, NULL, '', 4, now()),
(5, now(), now(), false, 3, 'ORD-DUMMY0000005', 1, 1, 6, pg_temp.today_ist() + 12, NULL, NULL, NULL, 1, 'Payment pending - hold', 4, now());

INSERT INTO public.aggregator_orderitem (id, created_at, updated_at, is_deleted, created_by_id, order_id, product_packaging_id, negotiated_selling_price, quantity) VALUES
(1, now(), now(), false, 3, 1, 1, 4800.00, 5),
(2, now(), now(), false, 3, 2, 1, 4800.00, 4),
(3, now(), now(), false, 3, 3, 1, 4750.00, 10),
(4, now(), now(), false, 3, 3, 2, 5000.00, 3),
(5, now(), now(), false, 3, 4, 2, 5000.00, 2);

-- Custom (loose-packet) orders: BOOKED (3), CONFIRMED (1), DISPATCHED (2)
INSERT INTO public.aggregator_customorder (id, created_at, updated_at, is_deleted, created_by_id, public_id, client_id, delivery_address_id, status_id, expected_delivery_date, actual_delivery_date, dispatch_details_id, private_dispatch_details_id, special_comments, verified_by_id, verified_at) VALUES
(1, now(), now(), false, 3, 'CORD-DUMMY0000001', 1, 1, 3, pg_temp.today_ist() + 4, NULL, NULL, NULL, 'Trial packets for dealers', 4, now()),
(2, now(), now(), false, 3, 'CORD-DUMMY0000002', 2, 2, 4, pg_temp.today_ist() + 2, NULL, 2, NULL, '', 4, now()),
(3, now(), now(), false, 3, 'CORD-DUMMY0000003', 3, 3, 1, pg_temp.today_ist() + 8, NULL, NULL, NULL, 'Mixed sample packets', NULL, NULL);

INSERT INTO public.aggregator_customorderitem (id, created_at, updated_at, is_deleted, created_by_id, custom_order_id, product_id, negotiated_selling_price, packet_weight, packets) VALUES
(1, now(), now(), false, 3, 1, 1, 125.00, 1.000, 30),
(2, now(), now(), false, 3, 2, 1, 125.00, 1.000, 20),
(3, now(), now(), false, 3, 3, 1, 125.00, 1.000, 5),
(4, now(), now(), false, 3, 3, 2, 260.00, 1.500, 10);

-- -------------------------------------------------------------------------
-- Dispatch challans for the three dispatched / delivered orders
--   (the challan reads the delivery address as client_address_id)
-- -------------------------------------------------------------------------
INSERT INTO public.aggregator_dispatchentry (id, created_at, updated_at, is_deleted, public_id, challan_number, order_id, custom_order_id, dispatch_details_id, client_id, client_address_id, contact_name, contact_number, dispatched_at, from_city_id, to_city_id, vehicle_number, driver_name, driver_number) VALUES
(1, now(), now(), false, 'DE-DUMMY0000001', to_char(pg_temp.today_ist() - 1, 'YYYYMMDD') || '-0001', 2, NULL, 1, 2, 2, 'Kiran Shah', '9825011002', (pg_temp.today_ist() - 1) + time '15:00', 1, 2, 'GJ05AB1234', 'Ramesh Patel', '9726000001'),
(2, now(), now(), false, 'DE-DUMMY0000002', to_char(pg_temp.today_ist() - 3, 'YYYYMMDD') || '-0001', 4, NULL, NULL, 4, 4, 'Rakesh Sharma', '9829011004', (pg_temp.today_ist() - 3) + time '11:00', 1, 4, 'GJ05EF9012', 'Dinesh Solanki', '9726000003'),
(3, now(), now(), false, 'DE-DUMMY0000003', to_char(pg_temp.today_ist() - 1, 'YYYYMMDD') || '-0002', NULL, 2, 2, 2, 2, 'Kiran Shah', '9825011002', (pg_temp.today_ist() - 1) + time '16:00', 1, 2, 'GJ05CD5678', 'Suresh Rathod', '9726000002');

INSERT INTO public.aggregator_dispatchentryitem (id, created_at, updated_at, is_deleted, created_by_id, dispatch_entry_id, product_packaging_id, product_id, packet_weight, negotiated_selling_price, quantity, lot_number) VALUES
(1, now(), now(), false, 4, 1, 1, NULL, NULL, 4800.00, 4, 'SAI33-LOT-001'),
(2, now(), now(), false, 4, 2, 2, NULL, NULL, 5000.00, 2, 'SAI3353-LOT-001'),
(3, now(), now(), false, 4, 3, NULL, 1, 1.000, 125.00, 20, 'SAI33-LOT-002');

-- -------------------------------------------------------------------------
-- Field trips by the seeded sales person (user 3): one per state
--   status 12 Planned, 13 Approved, 14 In progress, 15 Completed
-- -------------------------------------------------------------------------
INSERT INTO public.aggregator_fieldtrip (id, created_at, updated_at, is_deleted, created_by_id, public_id, city_id, village, status_id, expected_start_at, expected_end_at, started_at, ended_at, approved_by_id, approved_at) VALUES
(1, now(), now(), false, 3, 'FT-DUMMY0000001', 2, 'Sanand', 12, (pg_temp.today_ist() + 3) + time '09:00', (pg_temp.today_ist() + 3) + time '17:00', NULL, NULL, NULL, NULL),
(2, now(), now(), false, 3, 'FT-DUMMY0000002', 3, 'Gondal', 13, (pg_temp.today_ist() + 1) + time '09:00', (pg_temp.today_ist() + 1) + time '17:00', NULL, NULL, 4, now()),
(3, now(), now(), false, 3, 'FT-DUMMY0000003', 1, 'Bardoli', 14, pg_temp.today_ist() + time '09:00', pg_temp.today_ist() + time '17:00', pg_temp.today_ist() + time '09:30', NULL, 4, now()),
(4, now(), now(), false, 3, 'FT-DUMMY0000004', 4, 'Chomu', 15, (pg_temp.today_ist() - 5) + time '09:00', (pg_temp.today_ist() - 5) + time '17:00', (pg_temp.today_ist() - 5) + time '09:15', (pg_temp.today_ist() - 5) + time '16:40', 4, now()),
(5, now(), now(), false, 3, 'FT-DUMMY0000005', 5, 'Pokaran', 15, (pg_temp.today_ist() - 9) + time '09:00', (pg_temp.today_ist() - 9) + time '17:00', (pg_temp.today_ist() - 9) + time '09:20', (pg_temp.today_ist() - 9) + time '17:05', NULL, NULL);

INSERT INTO public.aggregator_farmervisit (id, created_at, updated_at, is_deleted, created_by_id, public_id, field_trip_id, farmer_name, contact_number, village, land_area_bigha) VALUES
(1, now(), now(), false, 3, 'FV-DUMMY0000001', 3, 'Bhikhabhai Chaudhary', '9099000001', 'Bardoli', 12.5000),
(2, now(), now(), false, 3, 'FV-DUMMY0000002', 3, 'Ramanbhai Patel', '9099000002', 'Bardoli', 8.0000),
(3, now(), now(), false, 3, 'FV-DUMMY0000003', 4, 'Gopal Meena', '9099000003', 'Chomu', 20.0000),
(4, now(), now(), false, 3, 'FV-DUMMY0000004', 4, 'Hanuman Jat', '9099000004', 'Chomu', 15.2500),
(5, now(), now(), false, 3, 'FV-DUMMY0000005', 5, 'Mohan Singh', '9099000005', 'Pokaran', 30.0000);

INSERT INTO public.aggregator_farmervisitcrop (id, created_at, updated_at, is_deleted, created_by_id, farmer_visit_id, crop_id) VALUES
(1, now(), now(), false, 3, 1, 1),
(2, now(), now(), false, 3, 2, 1),
(3, now(), now(), false, 3, 3, 2),
(4, now(), now(), false, 3, 4, 2),
(5, now(), now(), false, 3, 5, 2);

INSERT INTO public.aggregator_farmervisitproduct (id, created_at, updated_at, is_deleted, created_by_id, farmer_visit_id, product_id) VALUES
(1, now(), now(), false, 3, 1, 1),
(2, now(), now(), false, 3, 2, 1),
(3, now(), now(), false, 3, 3, 2),
(4, now(), now(), false, 3, 4, 2),
(5, now(), now(), false, 3, 5, 2);

-- Sequence sync for the dummy tables
SELECT setval(pg_get_serial_sequence('public.aggregator_pincode', 'id'),                (SELECT MAX(id) FROM public.aggregator_pincode));
SELECT setval(pg_get_serial_sequence('public.aggregator_address', 'id'),                (SELECT MAX(id) FROM public.aggregator_address));
SELECT setval(pg_get_serial_sequence('public.aggregator_transportagency', 'id'),        (SELECT MAX(id) FROM public.aggregator_transportagency));
SELECT setval(pg_get_serial_sequence('public.aggregator_contact', 'id'),                (SELECT MAX(id) FROM public.aggregator_contact));
SELECT setval(pg_get_serial_sequence('public.aggregator_party', 'id'),                  (SELECT MAX(id) FROM public.aggregator_party));
SELECT setval(pg_get_serial_sequence('public.aggregator_productdescriptionitem', 'id'), (SELECT MAX(id) FROM public.aggregator_productdescriptionitem));
SELECT setval(pg_get_serial_sequence('public.aggregator_client', 'id'),                 (SELECT MAX(id) FROM public.aggregator_client));
SELECT setval(pg_get_serial_sequence('public.aggregator_clientaddress', 'id'),          (SELECT MAX(id) FROM public.aggregator_clientaddress));
SELECT setval(pg_get_serial_sequence('public.aggregator_clientcontact', 'id'),          (SELECT MAX(id) FROM public.aggregator_clientcontact));
SELECT setval(pg_get_serial_sequence('public.aggregator_clienttransportagency', 'id'),  (SELECT MAX(id) FROM public.aggregator_clienttransportagency));
SELECT setval(pg_get_serial_sequence('public.aggregator_inwardrawmaterial', 'id'),      (SELECT MAX(id) FROM public.aggregator_inwardrawmaterial));
SELECT setval(pg_get_serial_sequence('public.aggregator_rawmaterialwaste', 'id'),       (SELECT MAX(id) FROM public.aggregator_rawmaterialwaste));
SELECT setval(pg_get_serial_sequence('public.aggregator_othermaterialrecipe', 'id'),    (SELECT MAX(id) FROM public.aggregator_othermaterialrecipe));
SELECT setval(pg_get_serial_sequence('public.aggregator_inwardothermaterial', 'id'),    (SELECT MAX(id) FROM public.aggregator_inwardothermaterial));
SELECT setval(pg_get_serial_sequence('public.aggregator_inventorysnapshot', 'id'),      (SELECT MAX(id) FROM public.aggregator_inventorysnapshot));
SELECT setval(pg_get_serial_sequence('public.aggregator_loosestocksnapshot', 'id'),     (SELECT MAX(id) FROM public.aggregator_loosestocksnapshot));
SELECT setval(pg_get_serial_sequence('public.aggregator_dispatchdetails', 'id'),        (SELECT MAX(id) FROM public.aggregator_dispatchdetails));
SELECT setval(pg_get_serial_sequence('public.aggregator_privatedispatchdetails', 'id'), (SELECT MAX(id) FROM public.aggregator_privatedispatchdetails));
SELECT setval(pg_get_serial_sequence('public.aggregator_order', 'id'),                  (SELECT MAX(id) FROM public.aggregator_order));
SELECT setval(pg_get_serial_sequence('public.aggregator_orderitem', 'id'),              (SELECT MAX(id) FROM public.aggregator_orderitem));
SELECT setval(pg_get_serial_sequence('public.aggregator_customorder', 'id'),            (SELECT MAX(id) FROM public.aggregator_customorder));
SELECT setval(pg_get_serial_sequence('public.aggregator_customorderitem', 'id'),        (SELECT MAX(id) FROM public.aggregator_customorderitem));
SELECT setval(pg_get_serial_sequence('public.aggregator_dispatchentry', 'id'),          (SELECT MAX(id) FROM public.aggregator_dispatchentry));
SELECT setval(pg_get_serial_sequence('public.aggregator_dispatchentryitem', 'id'),      (SELECT MAX(id) FROM public.aggregator_dispatchentryitem));
SELECT setval(pg_get_serial_sequence('public.aggregator_fieldtrip', 'id'),              (SELECT MAX(id) FROM public.aggregator_fieldtrip));
SELECT setval(pg_get_serial_sequence('public.aggregator_farmervisit', 'id'),            (SELECT MAX(id) FROM public.aggregator_farmervisit));
SELECT setval(pg_get_serial_sequence('public.aggregator_farmervisitcrop', 'id'),        (SELECT MAX(id) FROM public.aggregator_farmervisitcrop));
SELECT setval(pg_get_serial_sequence('public.aggregator_farmervisitproduct', 'id'),     (SELECT MAX(id) FROM public.aggregator_farmervisitproduct));
-- <<< DUMMY DATA END

COMMIT;
