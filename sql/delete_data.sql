-- =============================================================================
-- delete_data.sql -- hard-delete ALL business data, keep users + auth.
-- =============================================================================
--
-- WHAT IT DOES
--   Physical DELETE of every row of user-entered business data: orders and
--   their lines, custom orders, dispatch challans, clients, products, the stock
--   ledger, inward lots, field trips and the geo addresses. Nothing is soft-
--   deleted and nothing is archived -- `is_deleted` rows go too.
--
--   The database is left in exactly the state a fresh `sql/ddl.sql` +
--   `sql/dml.sql` load would produce, minus the demo business rows that dml.sql
--   also seeds.
--
-- WHAT IT KEEPS (and why each one is not negotiable)
--   authentication_*            the users themselves, plus their roles.
--   authtoken_token             Android bearer tokens, so people stay logged in.
--   django_session              the admin website's session cookies.
--   auth_*, django_content_type Django's permission machinery. Several
--                               permissions' display names come from these
--                               rows, and the soft-delete guards call
--                               `has_perm()`, so emptying them breaks deletes.
--   authentication_user_groups / authentication_user_user_permissions
--                               per-user permission grants.
--   django_migrations           never touched; `migrate --fake` depends on it.
--   aggregator_pushdevice       each user's push-notification device token.
--                               Deleting these silently breaks push for
--                               everyone until they re-register, and nothing
--                               else in the wipe depends on them.
--   django_admin_log            the admin site's action history. Kept as an
--                               audit trail of who touched what.
--
--   aggregator_country / _state / _city
--                               `authentication_salesperson.city_id` is
--                               ON DELETE RESTRICT, so deleting cities would
--                               leave every sales person pointing at nothing.
--                               Country and state are RESTRICT from city, so
--                               they come along.
--   aggregator_pincode          referenced by Address, i.e. by every client that
--                               is about to be re-created.
--   aggregator_status           `StatusIds` hard-codes ids 1-19 and every
--                               Order / Client / InwardRawMaterial / FieldTrip
--                               row needs a status row to point at. Deleting
--                               these breaks order creation outright.
--   aggregator_stage            same story via `StageIds`; Product.stage.
--   aggregator_crop             Product.crop.
--
-- HOW THE ORDER IS DERIVED
--   One DELETE per table, children strictly before parents, and deliberately
--   NO CASCADE anywhere. A mistake in the order therefore raises instead of
--   silently taking a kept table with it, and the surrounding transaction rolls
--   the whole wipe back.
--
--   Note on `aggregator_dispatchentry` / `aggregator_dispatchentryitem`:
--   DispatchEntry declares ForeignKeys to order / custom_order / client /
--   address / city in the model, but sql/ddl.sql never added the matching
--   FOREIGN KEY constraints, so Postgres will NOT stop this script from
--   deleting an order that a challan still points at. They are deleted here
--   anyway, second -- after the stock ledger, before the orders -- so the
--   script stays correct if those constraints are ever added. Worth fixing in
--   ddl.sql separately.
--
--   The stock ledger is deleted as well, lines before events, so the balances
--   derived from it can never disagree with a hard-deleted bag or inward lot.
--   After the wipe the sequences are rewound to match, so the first new order
--   gets id 1 rather than continuing from the old high-water mark.
--
-- HOW TO RUN
--     psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -f sql/delete_data.sql
--
--   Intended for preprod resets and local dev. Take a backup first: this is
--   irreversible, and without the guard nothing stops it being pointed at
--   production. `-v ON_ERROR_STOP=1` is what makes psql abort at the first
--   violation -- the script relies on it rather than on the CASCADE option.
--
--   The summary at the very bottom reports what survived.
-- =============================================================================

BEGIN;

-- -----------------------------------------------------------------------------
-- 1. Deepest children -- they only ever point at the tables below them.
-- -----------------------------------------------------------------------------

-- The stock ledger's lines. Must go before the events that own them, and
-- before the products / packagings / material types they name.
DELETE FROM public.aggregator_stockeventline;

-- Dispatch challan lines.
DELETE FROM public.aggregator_dispatchentryitem;

-- Crops and products recorded on a farmer visit.
DELETE FROM public.aggregator_farmervisitcrop;
DELETE FROM public.aggregator_farmervisitproduct;

-- Recipe layers of a stock snapshot (bag or loose stock).
DELETE FROM public.aggregator_packedrecipelayer;

-- -----------------------------------------------------------------------------
-- 2. Order and stock detail -- the ledger first, so nothing moves stock before
--    the movement history it recorded is gone.
-- -----------------------------------------------------------------------------

-- The stock ledger. Every movement ever recorded, so the balances derived from
-- it can never disagree with a hard-deleted bag or inward lot.
DELETE FROM public.aggregator_stockevent;

-- Dispatch challans. Points at an order, a custom order, a client and an
-- address -- all of which are deleted further down.
DELETE FROM public.aggregator_dispatchentry;

-- Farmer visits, still attached to their field trip.
DELETE FROM public.aggregator_farmervisit;

-- Order lines. The reason `aggregator_order` cannot be deleted first: these
-- rows hang off it and nothing else holds them.
DELETE FROM public.aggregator_orderitem;

-- Custom order lines.
DELETE FROM public.aggregator_customorderitem;

-- Return order lines. A return order interlocks with three other tables, so it
-- is called out separately below.
DELETE FROM public.aggregator_returnorderitem;

-- Notifications raised about orders. ON DELETE CASCADE from order, but the rows
-- are listed explicitly so the wipe does not depend on a cascade firing.
DELETE FROM public.aggregator_notification;

-- Bag / loose stock snapshots, which are the *positions* the ledger moves.
DELETE FROM public.aggregator_inventorysnapshot;
DELETE FROM public.aggregator_loosestocksnapshot;

-- Inward raw material lots and inward other material.
DELETE FROM public.aggregator_inwardrawmaterial;
DELETE FROM public.aggregator_inwardothermaterial;

-- Lab tests: one per raw lot, referenced by aggregator_inwardrawmaterial.lab_testing_id,
-- so they go right after the lots.
DELETE FROM public.aggregator_labtesting;

-- Raw material written off as waste.
DELETE FROM public.aggregator_rawmaterialwaste;

-- The client's own lists, all keyed on aggregator_client.
DELETE FROM public.aggregator_clientaddress;
DELETE FROM public.aggregator_clientcontact;
DELETE FROM public.aggregator_clienttransportagency;

-- Product description bullets.
DELETE FROM public.aggregator_productdescriptionitem;

-- Packing recipes (a recipe of a product in one other-material type).
DELETE FROM public.aggregator_othermaterialrecipe;

-- -----------------------------------------------------------------------------
-- 3. Return orders, then the orders themselves.
--
--    A return order is the awkward one: it is ON DELETE RESTRICT from
--    aggregator_order, while the stock ledger and both inward tables are ON
--    DELETE RESTRICT *back into* it. So it has to wait for those three (all
--    gone by now, one section up) and go before the order it points at.
--
--    Both orders RESTRICT their dispatch details, so the orders have to go
--    before those; the clients and addresses are still around and go below.
-- -----------------------------------------------------------------------------
DELETE FROM public.aggregator_returnorder;

DELETE FROM public.aggregator_order;
DELETE FROM public.aggregator_customorder;

-- Field trips (city + status + approver).
DELETE FROM public.aggregator_fieldtrip;

-- Packaging variants of a product. Order lines are already gone, so this is
-- what finally lets aggregator_product go.
DELETE FROM public.aggregator_productpackaging;

-- -----------------------------------------------------------------------------
-- 4. Dispatch details, then the clients.
--
--    Dispatch details are ON DELETE RESTRICT from an order *and* from a client,
--    so they sit between the two: after the orders that name them, before the
--    clients that do.
-- -----------------------------------------------------------------------------
DELETE FROM public.aggregator_dispatchdetails;
DELETE FROM public.aggregator_privatedispatchdetails;

DELETE FROM public.aggregator_client;

-- -----------------------------------------------------------------------------
-- 5. The masters those rows were pointing at.
-- -----------------------------------------------------------------------------

-- Products (crop + stage are kept).
DELETE FROM public.aggregator_product;

-- Standalone contacts, transport agencies, parties, other material types.
DELETE FROM public.aggregator_contact;
DELETE FROM public.aggregator_transportagency;
DELETE FROM public.aggregator_party;
DELETE FROM public.aggregator_othermaterialtype;

-- -----------------------------------------------------------------------------
-- 6. Last: the client's postal addresses. These sit on top of the geo master
--    data (country / state / city / pincode), which is kept.
-- -----------------------------------------------------------------------------
DELETE FROM public.aggregator_address;

-- -----------------------------------------------------------------------------
-- 7. Verify the wipe, then rewind the sequences of the tables we emptied.
--
--    A DELETE leaves the id sequence at its old high-water mark, so the next
--    order created on preprod would get a five-digit id instead of 1. This puts
--    each one back where a fresh ddl.sql + dml.sql load would leave it, which is
--    what `sql/dml.sql` does at its own end.
--
--    COALESCE(MAX(id), 1) with is_called = false is the empty-table case: the
--    sequence is not advanced, so the next nextval() hands back 1.
--
--    Only the deleted tables are listed. The kept tables' sequences must not
--    move -- aggregator_city still has its rows, so rewinding it would hand out
--    ids that already exist.
--
--    The loop then walks the rest of the public schema looking for any table
--    that came out empty without being on the list, and warns if it finds one.
--    That is what catches a table added to the models since this script was
--    written: the wipe would look successful and quietly leave its rows behind.
--    A warning rather than an exception, because a kept table with no rows yet
--    is normal -- expected_empty is the list of those known to be allowed to
--    sit empty, so anything reported really is a surprise.
-- -----------------------------------------------------------------------------
DO $$
DECLARE
    wiped   constant text[] := ARRAY[
        'aggregator_stockeventline',
        'aggregator_dispatchentryitem',
        'aggregator_farmervisitcrop',
        'aggregator_farmervisitproduct',
        'aggregator_packedrecipelayer',
        'aggregator_stockevent',
        'aggregator_dispatchentry',
        'aggregator_farmervisit',
        'aggregator_orderitem',
        'aggregator_customorderitem',
        'aggregator_returnorderitem',
        'aggregator_notification',
        'aggregator_inventorysnapshot',
        'aggregator_loosestocksnapshot',
        'aggregator_inwardrawmaterial',
        'aggregator_inwardothermaterial',
        'aggregator_labtesting',
        'aggregator_rawmaterialwaste',
        'aggregator_clientaddress',
        'aggregator_clientcontact',
        'aggregator_clienttransportagency',
        'aggregator_productdescriptionitem',
        'aggregator_othermaterialrecipe',
        'aggregator_order',
        'aggregator_customorder',
        'aggregator_returnorder',
        'aggregator_fieldtrip',
        'aggregator_productpackaging',
        'aggregator_dispatchdetails',
        'aggregator_privatedispatchdetails',
        'aggregator_client',
        'aggregator_product',
        'aggregator_contact',
        'aggregator_transportagency',
        'aggregator_party',
        'aggregator_othermaterialtype',
        'aggregator_address'
    ];
    -- Kept tables that are allowed to be empty. Without this list the warning
    -- below would fire on every fresh database, for tables nobody expects to
    -- have rows yet, and get ignored -- which defeats the point.
    expected_empty constant text[] := ARRAY[
        'authtoken_token',
        'auth_group',
        'auth_group_permissions',
        'authentication_user_groups',
        'authentication_user_user_permissions',
        'django_admin_log',
        'django_migrations',
        'django_session'
    ];
    missed  text[] := '{}';
    target  text;
    other   text;
    rows_left bigint;
BEGIN
    -- Rewind, and confirm each table really did come out empty.
    FOREACH target IN ARRAY wiped LOOP
        EXECUTE format('SELECT count(*) FROM public.%I', target) INTO rows_left;
        IF rows_left <> 0 THEN
            RAISE EXCEPTION 'public.% still holds % row(s) after the wipe.', target, rows_left;
        END IF;

        IF pg_get_serial_sequence('public.' || target, 'id') IS NOT NULL THEN
            EXECUTE format(
                'SELECT setval(pg_get_serial_sequence(%L, %L), COALESCE(MAX(id), 1), MAX(id) IS NOT NULL) FROM public.%I',
                'public.' || target, 'id', target
            );
        END IF;
    END LOOP;

    -- Anything else that ended up empty was not on the list. Either a table
    -- added since this script was written, or a kept table that happened to
    -- have no rows to begin with.
    FOR other IN
        SELECT c.relname
          FROM pg_class c
          JOIN pg_namespace n ON n.oid = c.relnamespace
         WHERE n.nspname = 'public'
           AND c.relkind = 'r'
           AND NOT (c.relname = ANY (wiped))
           AND NOT (c.relname = ANY (expected_empty))
    LOOP
        EXECUTE format('SELECT count(*) FROM public.%I', other) INTO rows_left;
        IF rows_left = 0 THEN
            missed := missed || other;
        END IF;
    END LOOP;

    IF array_length(missed, 1) IS NOT NULL THEN
        RAISE WARNING
            'these tables are empty and are NOT in the wipe list -- confirm they are meant to stay empty: %',
            array_to_string(missed, ', ');
    END IF;
END
$$;

COMMIT;

-- -----------------------------------------------------------------------------
-- Summary: what survived, and how much of it there is.
--
-- The wipe itself is already asserted inside the transaction above, so every
-- business table is guaranteed to be at 0 here.
-- -----------------------------------------------------------------------------
SELECT 'KEPT -- users & auth' AS section, count(*) AS rows FROM public.authentication_user
UNION ALL SELECT 'KEPT -- sales people',     count(*) FROM public.authentication_salesperson
UNION ALL SELECT 'KEPT -- admins',           count(*) FROM public.authentication_admin
UNION ALL SELECT 'KEPT -- godown managers',  count(*) FROM public.authentication_godownmanager
UNION ALL SELECT 'KEPT -- lab testers',      count(*) FROM public.authentication_labtester
UNION ALL SELECT 'KEPT -- api tokens',       count(*) FROM public.authtoken_token
UNION ALL SELECT 'KEPT -- permissions',      count(*) FROM public.auth_permission
UNION ALL SELECT 'KEPT -- content types',    count(*) FROM public.django_content_type
UNION ALL SELECT 'KEPT -- countries',        count(*) FROM public.aggregator_country
UNION ALL SELECT 'KEPT -- states',           count(*) FROM public.aggregator_state
UNION ALL SELECT 'KEPT -- cities',           count(*) FROM public.aggregator_city
UNION ALL SELECT 'KEPT -- pincodes',         count(*) FROM public.aggregator_pincode
UNION ALL SELECT 'KEPT -- statuses',         count(*) FROM public.aggregator_status
UNION ALL SELECT 'KEPT -- stages',           count(*) FROM public.aggregator_stage
UNION ALL SELECT 'KEPT -- crops',            count(*) FROM public.aggregator_crop
UNION ALL SELECT 'KEPT -- push devices',     count(*) FROM public.aggregator_pushdevice
UNION ALL SELECT 'KEPT -- admin log',        count(*) FROM public.django_admin_log
UNION ALL SELECT 'KEPT -- geo total',        (SELECT count(*) FROM public.aggregator_country)
                                          + (SELECT count(*) FROM public.aggregator_state)
                                          + (SELECT count(*) FROM public.aggregator_city)
                                          + (SELECT count(*) FROM public.aggregator_pincode)
UNION ALL SELECT 'WIPED -- business tables', 36;