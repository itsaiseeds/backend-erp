class AppStrings {
  AppStrings._();

  static const String APP_NAME = 'Admin - Saiseeds';
  static const String APP_TAGLINE = 'Saiseeds Admin Platform';

  static const String LOGIN = 'Login';
  static const String LOGOUT = 'Logout';
  static const String SIGN_IN = 'Sign In';

  static const String LOGIN_HEADING = 'Sign in';
  static const String LOGIN_EYEBROW = 'SAISEEDS ADMIN PLATFORM';
  static const String LOGIN_SUBHEADING =
      'Authorised access with phone number and authenticator code.';

  static const String PHONE_NUMBER = 'Phone Number';
  static const String PHONE_COUNTRY_CODE_IN = '+91';
  static const String LOGIN_PHONE_HINT = '10-digit mobile number';
  static const String LOGIN_PHONE_REQUIRED = 'Phone number is required.';
  static const String LOGIN_PHONE_INVALID =
      'Enter a valid 10-digit phone number.';

  static const String AUTHENTICATION_CODE = 'Authentication Code';
  static const String LOGIN_OTP_REQUIRED = 'Authentication code is required.';
  static const String LOGIN_OTP_INVALID = 'Enter the full 6-digit code.';
  static const String LOGIN_OTP_HELPER = '6-digit authenticator code';
  static const String LOGIN_SECURE_NOTE = 'Protected by two-factor sign-in';
  static const String LOGIN_LOGO_LABEL = 'Saiseeds';

  static const String LOGIN_FAILED = 'Unable to sign in. Please try again.';
  static const String LOGIN_FAILED_TITLE = 'Sign in failed';
  static const String LOGIN_NOT_AUTHORISED =
      'You are not authorised to access this portal. Contact an administrator '
      'if you believe this is a mistake.';
  static const String ERROR_UNEXPECTED_RESPONSE =
      'Unexpected response from server.';

  static const String LOGIN_BRAND_HEADLINE = 'Grown with precision.';
  static const String LOGIN_BRAND_TAGLINE =
      'The operations platform behind every Saiseeds batch — inventory, '
      'orders, and field sales in one place.';
  static const String LOGIN_BRAND_FOOTER =
      'Saiseeds internal platform. Authorised personnel only.';

  static const String DASHBOARD = 'Dashboard';
  static const String PROFILE = 'Profile';
  static const String ADMINS = 'Admins';
  static const String SALES_PEOPLE = 'Sales People';

  static const String SIDEBAR_COLLAPSE = 'Collapse sidebar';
  static const String SIDEBAR_EXPAND = 'Expand sidebar';

  static const String SENTRY_TEST_BUTTON = 'Send test error';
  static const String SENTRY_TEST_SENT_TITLE = 'Test error sent';
  static const String SENTRY_TEST_SENT_BODY =
      'A sample error was reported. Check GlitchTip to confirm it arrived.';
  static const String SENTRY_TEST_EXCEPTION =
      'Saiseeds admin test error: triggered from the dashboard.';
  static const String DASHBOARD_LAUNCHING_SOON_TITLE = 'Launching soon';
  static const String DASHBOARD_LAUNCHING_SOON_BODY =
      'The overview dashboard is being built. Live metrics for administrators, '
      'sales people, and platform activity will appear here once the reporting '
      'endpoints go live.';

  static const String ADMINS_EMPTY_TITLE = 'No administrators loaded';
  static const String ADMINS_EMPTY_BODY =
      'The administrator directory is not connected yet.';
  static const String SALES_PEOPLE_EMPTY_TITLE = 'No sales people loaded';
  static const String SALES_PEOPLE_EMPTY_BODY =
      'The sales team directory is not connected yet.';

  static const String PROFILE_SIGNED_IN_AS = 'SIGNED IN AS';
  static const String PROFILE_PERMISSIONS = 'Permissions';
  static const String PROFILE_PERMISSION_CREATE_ADMIN =
      'Create administrator accounts';
  static const String PROFILE_PERMISSION_CREATE_SALES_PERSON =
      'Create sales person accounts';
  static const String PROFILE_PERMISSION_GRANTED = 'Granted';
  static const String PROFILE_PERMISSION_RESTRICTED = 'Restricted';
  static const String PROFILE_UNAVAILABLE_TITLE = 'Profile unavailable';
  static const String PROFILE_UNAVAILABLE_BODY =
      'No account details are stored for this session. Sign in again to '
      'continue.';
  static const String PROFILE_VALUE_UNKNOWN = 'Not available';
  static const String PROFILE_ROLE_UNKNOWN = 'Unassigned';
  static const String PROFILE_SESSION_SIGN_OUT_HINT =
      'Ends this browser session and returns you to the sign-in screen.';
  static const String PROFILE_PERMISSION_CREATE_ADMIN_HINT =
      'Invite new administrators and issue their authenticator setup.';
  static const String PROFILE_PERMISSION_CREATE_SALES_PERSON_HINT =
      'Onboard sales people and manage their directory records.';
  static const String PROFILE_PERMISSION_SUMMARY_ALL =
      'Full access across both account directories.';
  static const String PROFILE_PERMISSION_SUMMARY_PARTIAL =
      'Access is limited to one account directory.';
  static const String PROFILE_PERMISSION_SUMMARY_NONE =
      'No account creation rights on this platform.';

  static const String LOGOUT_CONFIRM_TITLE = 'Sign out';
  static const String LOGOUT_CONFIRM_BODY =
      'You will be returned to the sign-in screen.';

  static const String LOADING = 'Loading...';
  static const String RETRY = 'Retry';
  static const String CANCEL = 'Cancel';
  static const String CONFIRM = 'Confirm';
  static const String OK = 'OK';
  static const String SAVE = 'Save';
  static const String EDIT = 'Edit';
  static const String DELETE = 'Delete';
  static const String SEARCH = 'Search...';
  static const String NO_RESULTS_FOUND = 'No results found';
  static const String REQUIRED_MARKER = ' *';
  static const String TYPE_TO_SEARCH = 'Type to search...';
  static const String NO_DATA_FOUND = 'No data found.';
  static const String SOMETHING_WENT_WRONG =
      'Something went wrong. Please try again.';
  static const String SESSION_EXPIRED =
      'Your session has expired. Please login again.';
  static const String ERROR_NETWORK =
      'Could not reach the server. Check your connection and try again.';
  static const String ERROR_TIMEOUT =
      'The server took too long to respond. Please try again.';
  static const String ERROR_CANCELLED = 'The request was cancelled.';
  static const String ERROR_RATE_LIMITED =
      'Too many attempts. Please try again later.';
  static const String ERROR_FORBIDDEN =
      'You do not have permission to perform this action.';
  static const String ERROR_NOT_FOUND = 'The requested item was not found.';
  static const String ERROR_SERVER =
      'The server encountered an error. Please try again.';

  static const String PAGE_NOT_FOUND_TITLE = 'Page Not Found';
  static const String PAGE_NOT_FOUND_BODY =
      'The page you are looking for does not exist.';

  static const String MOBILE_BLOCK_TITLE = 'Better Experience on Desktop';
  static const String MOBILE_BLOCK_BODY =
      'This portal is optimized for desktop and tablet screens. '
      'Please switch to a larger device for the best experience.';

  static const String TABLE_SEARCH = 'Search';
  static const String TABLE_SEARCH_WITHIN_RESULTS = 'Search within results...';
  static const String TABLE_ADD_FILTER = 'Add Filter';
  static const String TABLE_FILTER_VALUE_HINT = 'Value';
  static const String TABLE_APPLY_FILTER = 'Apply filter';
  static const String TABLE_DISCARD_FILTER = 'Discard filter';
  static const String TABLE_REMOVE_FILTER = 'Remove filter';
  static const String TABLE_CLEAR_SEARCH = 'Clear search';
  static const String TABLE_SORT_ASCENDING = 'Sort ascending';
  static const String TABLE_SORT_DESCENDING = 'Sort descending';
  static const String TABLE_TOGGLE_SORT_ORDER = 'Toggle sort order';
  static const String TABLE_PIN_COLUMN = 'Pin column';
  static const String TABLE_UNPIN_COLUMN = 'Unpin column';
  static const String TABLE_RESIZE_COLUMN = 'Resize column';
  static const String TABLE_SELECT_COLUMN_LABEL = 'Select';
  static const String TABLE_ACTIONS_COLUMN_LABEL = 'Actions';

  static const String CLIENTS = 'Clients';
  static const String CLIENT_STATUS_VERIFIED = 'Verified';
  static const String CLIENT_STATUS_PENDING = 'Pending';
  static const String CLIENTS_VIEW_PENDING = 'Pending requests';
  static const String CLIENTS_VIEW_VERIFIED = 'Verified clients';
  static const String CLIENT_STATUS_OPTION_VERIFIED = 'Accepted clients';
  static const String CLIENT_STATUS_OPTION_PENDING = 'Pending clients';
  static const String CLIENTS_TABLE_SEARCH_HINT = 'Search clients...';
  static const String CLIENTS_EMPTY_STATE_TITLE = 'No clients yet';
  static const String CLIENTS_EMPTY_STATE_BODY =
      'Clients created by sales people will appear here.';
  static const String CLIENTS_PENDING_EMPTY_TITLE = 'Nothing to review';
  static const String CLIENTS_PENDING_EMPTY_BODY =
      'New client requests will appear here for approval.';
  static const String CLIENTS_LOAD_FAILED_TITLE = 'Could not load clients';

  static const String COLUMN_COMPANY_NAME = 'Company';
  static const String COLUMN_COMPANY_PHONE = 'Phone';
  static const String COLUMN_PRIMARY_CONTACT = 'Primary Contact';
  static const String COLUMN_PRIMARY_ADDRESS = 'Primary Address';
  static const String COLUMN_GST_NUMBER = 'GST Number';

  static const String CLIENT_ACCEPT = 'Accept';
  static const String CLIENT_REJECT = 'Reject';
  static const String CLIENT_ACCEPT_TITLE = 'Accept this client?';
  static const String CLIENT_ACCEPT_BODY =
      'The client will be verified and moved to the clients list.';
  static const String CLIENT_ACCEPTED_TITLE = 'Client accepted';
  static const String CLIENT_UPDATED_TITLE = 'Client updated';
  static const String CLIENT_DETAILS_TITLE = 'Client details';
  static const String CLIENT_EDIT_TITLE = 'Edit client';

  static const String FILTER_BY_COMPANY_NAME = 'company_name';
  static const String FILTER_BY_ADDRESS = 'address';
  static const String FILTER_BY_STATUS = 'status';
  static const String FILTER_BY_VERIFIED_BY = 'verified_by';
  static const String FILTER_BY_CREATED_BY = 'created_by';
  static const String FILTER_BY_CITY_ID = 'city_id';
  static const String SORT_BY_COMPANY_NAME = 'company_name';

  static const String CLIENT_SECTION_ADDRESSES = 'Addresses';
  static const String CLIENT_SECTION_CONTACTS = 'Contacts';
  static const String CLIENT_SECTION_TRANSPORT = 'Transport agencies';
  static const String CLIENT_PRIMARY_BADGE = 'Primary';
  static const String FILTER_OPERATOR_EQUALS = '=';
  static const String DATE_RANGE_HINT = 'Select dates';
  static const String DATE_PICK_HINT = 'Select a date';
  static const String DATE_RANGE_HELP = 'Select date range';
  static const String DATE_RANGE_APPLY = 'Apply';
  static const String DATE_RANGE_ARROW = '→';
  static const String DATE_RANGE_FROM = 'From';
  static const String DATE_RANGE_UNTIL = 'Until';
  static const String DATE_RANGE_CANCEL = 'Cancel';
  static const String DATE_RANGE_CLEAR = 'Clear';
  static const String DATE_RANGE_TODAY = 'Today';
  static const String DATE_RANGE_LAST_7 = 'Last 7 days';
  static const String DATE_RANGE_LAST_30 = 'Last 30 days';
  static const String DATE_RANGE_LAST_90 = 'Last 90 days';
  static const String DATE_RANGE_LAST_6M = 'Last 6 months';
  static const String DATE_RANGE_LAST_YEAR = 'Last 1 year';
  static const String SMALL_SCREEN_TITLE = 'Best experienced on desktop';
  static const String SMALL_SCREEN_BODY =
      'The Saiseeds admin portal is designed for desktop screens. Open this '
      'page on a desktop or widen your window for the full experience.';
  static const String SMALL_SCREEN_HINT = 'Minimum width: 1200px';
  static const String CLIENT_STEP_DETAILS = 'Details';
  static const String CLIENT_STEP_ADDRESSES = 'Addresses';
  static const String CLIENT_STEP_CONTACTS = 'Contacts';
  static const String CLIENT_STEP_TRANSPORT = 'Transport';
  static const String CLIENT_STEP_PROGRESS = 'Step';
  static const String CLIENT_ADD_ADDRESS = 'Add address';
  static const String CLIENT_ADD_CONTACT = 'Add contact';
  static const String CLIENT_ADD_TRANSPORT = 'Add transport agency';
  static const String CLIENT_RAIL_ADDRESSES_HINT = 'Manage client addresses.';
  static const String CLIENT_RAIL_CONTACTS_HINT = 'Manage client contacts.';
  static const String CLIENT_RAIL_TRANSPORT_HINT =
      'Manage client transport agencies.';
  static const String CLIENT_ADDRESS_LABEL = 'Label';
  static const String CLIENT_ADDRESS_LINE_1 = 'Address line 1';
  static const String CLIENT_ADDRESS_LINE_2 = 'Address line 2';
  static const String CLIENT_ADDRESS_PINCODE = 'Pincode';
  static const String CLIENT_ADDRESS_CITY = 'City';
  static const String CLIENT_CONTACT_NAME = 'Name';
  static const String CLIENT_CONTACT_PHONE = 'Phone number';
  static const String CLIENT_CONTACT_ROLE = 'Role';
  static const String CLIENT_TRANSPORT_NAME = 'Agency name';
  static const String CLIENT_MARK_PRIMARY = 'Primary';
  static const String CLIENT_REMOVE_ENTRY = 'Remove';
  static const String STEP_BACK = 'Back';
  static const String STEP_NEXT = 'Next';
  static const String VALIDATION_ONE_PRIMARY =
      'Exactly one entry must be primary.';
  static const String VALIDATION_AT_LEAST_ONE =
      'At least one entry is required.';
  static const String VALIDATION_CITY_REQUIRED = 'City is required.';
  static const String CLIENT_CREATED_BY_LABEL = 'Added by';
  static const String CLIENT_COMPANY_NAME_HINT = 'Registered business name';
  static const String CLIENT_GST_HINT = '15-character GSTIN';
  static const String VALIDATION_GST_REQUIRED = 'GST number is required.';
  static const String VALIDATION_GST_INVALID =
      'Enter a valid 15-character GST number.';
  static const String TABLE_SELECT_ALL_ON_PAGE = 'Select all on this page';
  static const String TABLE_SELECT_ROW = 'Select row';
  static const String TABLE_CLEAR_SELECTION = 'Clear selection';
  static const String TABLE_SCROLL_HINT = 'Scroll for more columns';
  static const String TABLE_ITEM_SELECTED_SINGULAR = 'item selected';
  static const String TABLE_ITEM_SELECTED_PLURAL = 'items selected';
  static const String TABLE_PIN_LIMIT_TITLE = 'Pin limit reached';
  static const String TABLE_PIN_LIMIT_BODY =
      'Unpin another column before pinning a new one.';
  static const String TABLE_EMPTY_TITLE = 'No records found';
  static const String TABLE_EMPTY_BODY =
      'No records match the current search and filters.';
  static const String TABLE_COLUMN_SETTINGS = 'Column settings';
  static const String TABLE_COLUMN_SETTINGS_TITLE = 'Display preferences';
  static const String TABLE_COLUMN_SETTINGS_SUBTITLE =
      'Choose which columns appear in the table.';
  static const String TABLE_COLUMN_SETTINGS_DONE = 'Done';
  static const String TABLE_BULK_DELETE = 'Delete';
  static const String TABLE_REFRESH = 'Refresh';
  static const String TABLE_VALUE_UNAVAILABLE = '—';

  static const String ADMINS_TABLE_SEARCH_HINT = 'Search administrators...';
  static const String SALES_PEOPLE_TABLE_SEARCH_HINT = 'Search sales people...';
  static const String COLUMN_NAME = 'Name';
  static const String COLUMN_PHONE_NUMBER = 'Phone Number';
  static const String COLUMN_ROLE = 'Role';
  static const String COLUMN_STATUS = 'Status';
  static const String ADMINS_SUBTITLE =
      'Administrator accounts with access to the Saiseeds admin platform.';
  static const String SALES_PEOPLE_SUBTITLE =
      'Field sales accounts registered on the Saiseeds platform.';
  static const String STATUS_ACTIVE = 'Active';
  static const String STATUS_INACTIVE = 'Inactive';
  static const String SORT_BY_NAME = 'name';
  static const String SORT_BY_CREATED_AT = 'created_at';
  static const String FILTER_BY_NAME = 'name';
  static const String FILTER_BY_PHONE_NUMBER = 'phone_number';
  static const String FILTER_BY_ROLE = 'role';
  static const String SORT_LABEL_CREATED_AT = 'Created At';
  static const String TABLE_BULK_DELETE_TITLE = 'Delete selected records';
  static const String TABLE_BULK_DELETE_BODY =
      'This permanently removes the selected records. This cannot be undone.';
  static const String TABLE_BULK_DELETE_DONE_TITLE = 'Delete complete';
  static const String TABLE_BULK_DELETE_FAILED_TITLE = 'Delete failed';
  static const String TABLE_BULK_DELETE_FAILED_BODY =
      'One or more records could not be deleted.';

  static const String ADD_ADMIN = 'Add Administrator';
  static const String EDIT_ADMIN = 'Edit Administrator';
  static const String ADD_SALES_PERSON = 'Add Sales Person';
  static const String EDIT_SALES_PERSON = 'Edit Sales Person';
  static const String ADD_ADMIN_SUBTITLE =
      'Create an administrator account with platform access.';
  static const String EDIT_ADMIN_SUBTITLE =
      'Update the administrator account details.';
  static const String ADD_SALES_PERSON_SUBTITLE =
      'Register a field sales account on the platform.';
  static const String EDIT_SALES_PERSON_SUBTITLE =
      'Update the sales person account details.';

  static const String FIELD_NAME = 'Name';
  static const String FIELD_NAME_HINT = 'Full name';
  static const String FIELD_EMAIL = 'Email';
  static const String FIELD_EMAIL_HINT = 'name@example.com';
  static const String FIELD_EMAIL_OPTIONAL = 'Email (optional)';
  static const String FIELD_PHONE_HINT = '10-digit mobile number';
  static const String FIELD_CITY = 'City';
  static const String FIELD_CITY_HINT = 'Select a city';
  static const String FIELD_STOCK_PERMISSION = 'Can update stock count';
  static const String FIELD_STOCK_PERMISSION_HINT =
      'Allows this administrator to adjust inventory counts.';

  static const String VALIDATION_NAME_REQUIRED = 'Name is required.';
  static const String VALIDATION_PHONE_REQUIRED = 'Phone number is required.';
  static const String VALIDATION_PHONE_INVALID =
      'Enter a valid 10-digit phone number.';
  static const String VALIDATION_EMAIL_INVALID = 'Enter a valid email address.';

  static const String CREATE = 'Create';
  static const String UPDATE = 'Update';
  static const String CLOSE = 'Close';
  static const String VIEW_DETAILS = 'View details';

  static const String ADMIN_CREATED_TITLE = 'Administrator created';
  static const String ADMIN_UPDATED_TITLE = 'Administrator updated';
  static const String ADMIN_DELETED_TITLE = 'Administrator deleted';
  static const String SALES_PERSON_CREATED_TITLE = 'Sales person created';
  static const String SALES_PERSON_UPDATED_TITLE = 'Sales person updated';
  static const String SALES_PERSON_DELETED_TITLE = 'Sales person deleted';

  static const String DELETE_ADMIN_TITLE = 'Delete administrator';
  static const String DELETE_ADMIN_BODY =
      'This permanently removes the administrator account. This cannot be '
      'undone.';
  static const String DELETE_SALES_PERSON_TITLE = 'Delete sales person';
  static const String DELETE_SALES_PERSON_BODY =
      'This permanently removes the sales person account. This cannot be '
      'undone.';

  static const String ADMIN_DETAIL_TITLE = 'Administrator details';
  static const String SALES_PERSON_DETAIL_TITLE = 'Sales person details';
  static const String DETAIL_SECTION_ACCOUNT = 'Account';
  static const String DETAIL_SECTION_ACCOUNT_HINT =
      'Identity and contact details on record.';
  static const String DETAIL_SECTION_AUTHENTICATOR = 'Authenticator';
  static const String DETAIL_SECTION_AUTHENTICATOR_HINT =
      'Scan this code in an authenticator app to enable sign-in.';
  static const String DETAIL_FIELD_CREATED_BY = 'Created By';
  static const String DETAIL_FIELD_CREATED_AT = 'Created At';
  static const String SALES_PERSON_EDIT_HINT =
      'Update the sales person account details.';
  static const String VIEW_MODE_TOAST_TITLE = 'View mode';
  static const String VIEW_MODE_TOAST_BODY =
      'Select the edit action in the header to change these details.';
  static const String VIEW_MODE_LOCKED_TOAST_BODY =
      'This field is read-only and cannot be edited.';
  static const String TOTP_MANUAL_ENTRY = 'Setup key';
  static const String TOTP_SEND_WHATSAPP = 'WhatsApp';
  static const String TOTP_DOWNLOAD_QR = 'Download QR';
  static const String TOTP_NO_PHONE = 'No phone number on record.';
  static const String TOTP_DOWNLOAD_FAILED = 'Could not prepare the QR image.';
  static const String TOTP_QR_FILE_SUFFIX = '-authenticator-qr.png';
  static const String TOTP_QR_FALLBACK_NAME = 'saiseeds';
  static const String TOTP_WHATSAPP_GREETING = 'Hello';
  static const String TOTP_WHATSAPP_INTRO =
      'Welcome to Saiseeds. Your account is ready.';
  static const String TOTP_WHATSAPP_STEPS =
      'To sign in, open any authenticator app (Google Authenticator, Authy) '
      'and scan the QR code attached to this message.';
  static const String TOTP_WHATSAPP_CLOSING =
      'Keep this code private. It is what signs you in.';
  static const String TOTP_WHATSAPP_QR_TITLE = 'Saiseeds sign-in QR';
  static const String TOTP_QR_ATTACH_HINT =
      'Attach the downloaded QR image to the chat.';
  static const String TOTP_UNAVAILABLE =
      'No authenticator setup code is available for this account.';

  static const String COLUMN_EMAIL = 'Email';
  static const String COLUMN_CITY = 'City';
  static const String COLUMN_CREATED_BY = 'Created By';
  static const String COLUMN_VERIFIED_BY = 'Verified By';
  static const String COLUMN_CREATED_AT = 'Created At';
  static const String COLUMN_STOCK_PERMISSION = 'Stock Access';
  static const String PERMISSION_ALLOWED = 'Allowed';
  static const String PERMISSION_DENIED = 'Denied';

  static const String ADMINS_LOAD_FAILED_TITLE =
      'Could not load administrators';
  static const String SALES_PEOPLE_LOAD_FAILED_TITLE =
      'Could not load sales people';
  static const String ADMINS_EMPTY_STATE_TITLE = 'No administrators yet';
  static const String ADMINS_EMPTY_STATE_BODY =
      'Add an administrator to give someone access to this platform.';
  static const String SALES_PEOPLE_EMPTY_STATE_TITLE = 'No sales people yet';
  static const String SALES_PEOPLE_EMPTY_STATE_BODY =
      'Add a sales person to register a field account.';
  static const String CITIES_UNAVAILABLE =
      'City list is unavailable. Refresh the page and try again.';
  static const String SORT_BY_EMAIL = 'email';
  static const String FILTER_BY_EMAIL = 'email';
  static const String FILTER_BY_CITY = 'city';

  static const String PRODUCTS = 'Products';
  static const String PRODUCTS_TABLE_SEARCH_HINT = 'Search products...';
  static const String PRODUCTS_LOAD_FAILED_TITLE = 'Could not load products';
  static const String PRODUCTS_EMPTY_STATE_TITLE = 'No products yet';
  static const String PRODUCTS_EMPTY_STATE_BODY =
      'Add a product to make it available for orders.';
  static const String ADD_PRODUCT = 'Add Product';
  static const String EDIT_PRODUCT = 'Edit Product';
  static const String ADD_PRODUCT_SUBTITLE =
      'Register a product against a crop with its pricing.';
  static const String EDIT_PRODUCT_SUBTITLE =
      'Update the product name, crop, or pricing.';
  static const String PRODUCT_CREATED_TITLE = 'Product created';
  static const String PRODUCT_UPDATED_TITLE = 'Product updated';
  static const String PRODUCT_DELETED_TITLE = 'Product deleted';
  static const String DELETE_PRODUCT_TITLE = 'Delete product';
  static const String DELETE_PRODUCT_BODY =
      'This product will be removed permanently. This action cannot be undone.';
  static const String PRODUCT_DETAIL_TITLE = 'Product details';
  static const String PRODUCT_DETAIL_SUBTITLE =
      'Crop association and pricing on record.';

  static const String COLUMN_CROP = 'Crop';
  static const String COLUMN_STAGE = 'Stage';
  static const String COLUMN_DESCRIPTION = 'Description';
  static const String PRODUCT_STAGE_HINT = 'Select a stage';
  static const String PRODUCT_STEP_BASIC = 'Basics';
  static const String PRODUCT_STEP_DETAILS = 'Details';
  static const String PRODUCT_STEP_IMAGE = 'Image';
  static const String PRODUCT_PICK_IMAGE = 'Choose image';
  static const String PRODUCT_REPLACE_IMAGE = 'Replace image';
  static const String PRODUCT_REMOVE_IMAGE = 'Remove image';
  static const String PRODUCT_IMAGE_EMPTY = 'No image selected';
  static const String IMAGE_ZOOM_IN = 'Zoom in';
  static const String IMAGE_ZOOM_OUT = 'Zoom out';
  static const String IMAGE_RESET = 'Reset zoom';
  static const String IMAGE_LOAD_FAILED = 'Image could not be loaded.';
  static const String IMAGE_VIEW_HINT = 'Click to enlarge';
  static const String PRODUCT_IMAGE_OPTIONAL = 'Optional. PNG or JPG.';
  static const String PRODUCT_DESCRIPTION_LABEL = 'Description points';
  static const String PRODUCT_ADD_POINT = 'Add point';
  static const String PRODUCT_POINT_HINT = 'Enter a description point';
  static const String PRODUCT_REMOVE_POINT = 'Remove point';
  static const String VALIDATION_STAGE_REQUIRED = 'Stage is required.';
  static const String COLUMN_SELLING_PRICE = 'Selling Price (per Kg)';
  static const String COLUMN_BAG_SELLING_PRICE = 'Selling Price';
  static const String FIELD_BAG_SELLING_PRICE = 'Selling Price (total)';
  static const String FIELD_BAG_SELLING_PRICE_HINT = 'Enter total bag price';
  static const String FIELD_BAG_SELLING_PRICE_HELPER =
      'Autofilled as product rate x packet weight x packets. Edit to override.';

  static const String SORT_BY_SELLING_PRICE = 'selling_price';
  static const String FILTER_BY_CROP = 'crop';

  static const String FIELD_PRODUCT_NAME = 'Product Name';
  static const String FIELD_PRODUCT_NAME_HINT = 'Enter product name';
  static const String FIELD_SELLING_PRICE = 'Selling Price (per Kg)';
  static const String FIELD_SELLING_PRICE_HINT = 'Enter price per kilogram';
  static const String FIELD_SELLING_PRICE_HELPER =
      'Rate per kilogram. Packet and bag prices derive from this and the '
      'weight sold.';
  static const String FIELD_CROP = 'Crop';
  static const String FIELD_CROP_HINT = 'Select a crop';

  static const String VALIDATION_CROP_REQUIRED = 'Crop is required.';
  static const String VALIDATION_PRICE_REQUIRED = 'Price is required.';
  static const String VALIDATION_PRICE_INVALID =
      'Enter a valid amount of 0 or more.';

  static const String CROPS_UNAVAILABLE =
      'Crop list is unavailable. Refresh the page and try again.';
  static const String CROP_CREATE_OPTION_PREFIX = 'Create crop';
  static const String CROP_CREATE_CONFIRM_TITLE = 'Create new crop';
  static const String CROP_CREATE_CONFIRM_BODY_PREFIX =
      'This crop does not exist yet. Create';
  static const String CROP_CREATE_CONFIRM_BODY_SUFFIX =
      'and use it for this product?';
  static const String CROP_CREATED_TITLE = 'Crop created';
  static const String CROP_CREATE_FAILED_TITLE = 'Could not create crop';

  static const String PRODUCT_PACKAGINGS = 'Product Packagings';
  static const String PRODUCT_PACKAGINGS_TABLE_SEARCH_HINT =
      'Search packagings...';
  static const String PRODUCT_PACKAGINGS_LOAD_FAILED_TITLE =
      'Could not load product packagings';
  static const String PRODUCT_PACKAGINGS_EMPTY_STATE_TITLE =
      'No product packagings yet';
  static const String PRODUCT_PACKAGINGS_EMPTY_STATE_BODY =
      'Add a packaging to define how a product is sold in packets.';
  static const String ADD_PRODUCT_PACKAGING = 'Add Packaging';
  static const String EDIT_PRODUCT_PACKAGING = 'Edit Packaging';
  static const String ADD_PRODUCT_PACKAGING_SUBTITLE =
      'Define the packet weight, packet count, and price for a product.';
  static const String EDIT_PRODUCT_PACKAGING_SUBTITLE =
      'Update the packet weight, packet count, or price of this packaging.';
  static const String PRODUCT_PACKAGING_CREATED_TITLE = 'Packaging created';
  static const String PRODUCT_PACKAGING_UPDATED_TITLE = 'Packaging updated';
  static const String PRODUCT_PACKAGING_DELETED_TITLE = 'Packaging deleted';
  static const String DELETE_PRODUCT_PACKAGING_TITLE = 'Delete packaging';
  static const String DELETE_PRODUCT_PACKAGING_BODY =
      'This packaging will be removed permanently. '
      'This action cannot be undone.';
  static const String PRODUCT_PACKAGING_DETAIL_TITLE = 'Packaging details';
  static const String PRODUCT_PACKAGING_DETAIL_SUBTITLE =
      'Packet configuration and pricing on record.';

  static const String COLUMN_PRODUCT = 'Product';
  static const String COLUMN_PACKET_WEIGHT = 'Packet Weight (kg)';
  static const String COLUMN_PACKETS = 'Packets';
  static const String COLUMN_TOTAL_WEIGHT = 'Total Weight (kg)';

  static const String SORT_BY_PRODUCT = 'product';
  static const String SORT_BY_PACKET_WEIGHT = 'packet_weight';
  static const String SORT_BY_PACKETS = 'packets';
  static const String SORT_BY_TOTAL_WEIGHT = 'total_weight';
  static const String FILTER_BY_PRODUCT = 'product';

  static const String FIELD_PRODUCT = 'Product';
  static const String FIELD_PRODUCT_HINT = 'Select a product';
  static const String FIELD_PACKET_WEIGHT = 'Packet Weight (kg)';
  static const String FIELD_PACKET_WEIGHT_HINT =
      'Enter the weight of one packet';
  static const String FIELD_PACKETS = 'Packets';
  static const String FIELD_PACKETS_HINT = 'Enter the number of packets';

  static const String VALIDATION_PRODUCT_REQUIRED = 'Product is required.';
  static const String VALIDATION_POSITIVE_AMOUNT_REQUIRED =
      'This value is required.';
  static const String VALIDATION_POSITIVE_AMOUNT_INVALID =
      'Enter a valid amount greater than 0.';
  static const String VALIDATION_COUNT_INVALID =
      'Enter a whole number of 1 or more.';

  static const String PRODUCTS_UNAVAILABLE =
      'Product list is unavailable. Refresh the page and try again.';
  static const String SELECTED_PRODUCT_SUMMARY_TITLE = 'Selected product';
  static const String SELECTED_PRODUCT_SUMMARY_HINT =
      'Read-only details of the product this packaging belongs to.';
  static const String SELECTED_PRODUCT_NONE =
      'Pick a product to see its details here.';
  static const String ORDERS = 'Order Management';
  static const String ORDERS_EMPTY_STATE_TITLE = 'No orders found';
  static const String ORDERS_EMPTY_STATE_BODY =
      'Orders booked by your sales team will appear here.';
  static const String ORDERS_LOAD_FAILED_TITLE = 'Could not load orders';
  static const String ORDERS_TABLE_SEARCH_HINT = 'Search by client';

  static const String ORDER_STATUS_BOOKED = 'Booked';
  static const String ORDER_STATUS_UNDER_REVIEW = 'Under review';
  static const String ORDER_STATUS_CONFIRMED = 'Confirmed';
  static const String ORDER_STATUS_DISPATCHED = 'Dispatched';
  static const String ORDER_STATUS_DELIVERED = 'Delivered';
  static const String ORDER_STATUS_ON_HOLD = 'On hold';
  static const String ORDER_STATUS_REJECTED = 'Rejected';

  static const String COLUMN_ORDER_CLIENT = 'Client';
  static const String COLUMN_ORDER_STATUS = 'Status';
  static const String COLUMN_ORDER_AMOUNT = 'Amount';
  static const String COLUMN_ORDER_ID = 'Order ID';
  static const String COLUMN_ORDER_ADDRESS = 'Delivery Address';
  static const String COLUMN_ORDER_DISPATCH = 'Dispatch';
  static const String COLUMN_ORDER_VERIFIED_BY = 'Verified By';
  static const String COLUMN_ORDER_CLIENT_ONBOARDED_BY = 'Client Added By';
  static const String COLUMN_ORDER_PLACED = 'Placed';
  static const String COLUMN_ORDER_EXPECTED = 'Expected';
  static const String COLUMN_ORDER_SALES_PERSON = 'Sales Person';
  static const String COLUMN_ORDER_ACTIONS = 'Order Actions';

  static const String ORDER_VERIFY = 'Verify';
  static const String ORDER_UNVERIFY = 'Unverify';
  static const String ORDER_HOLD = 'Hold';
  static const String ORDER_REJECT = 'Reject';

  static const String ORDER_VERIFY_TITLE = 'Verify this order?';
  static const String ORDER_VERIFY_BODY =
      'The order is approved against the current stock count and its bags are reserved.';
  static const String ORDER_VERIFY_DONE = 'Order verified';

  static const String ORDER_UNVERIFY_TITLE = 'Withdraw approval?';
  static const String ORDER_UNVERIFY_BODY =
      'The order returns to Under review and the bags it reserved are released.';
  static const String ORDER_UNVERIFY_DONE = 'Approval withdrawn';

  static const String ORDER_HOLD_TITLE = 'Put this order on hold?';
  static const String ORDER_HOLD_BODY =
      'The order is paused and any bags it reserved are released. It can be resumed by verifying it again.';
  static const String ORDER_HOLD_DONE = 'Order on hold';

  static const String ORDER_REJECT_TITLE = 'Reject this order?';
  static const String ORDER_REJECT_BODY =
      'Rejection is permanent. No action moves an order out of Rejected, and any reserved bags are released.';
  static const String ORDER_REJECT_DONE = 'Order rejected';

  static const String ORDER_VERIFY_BLOCKED =
      'Only a booked, under-review or held order can be verified.';
  static const String ORDER_UNVERIFY_BLOCKED =
      'Only a confirmed order can be unverified.';
  static const String ORDER_HOLD_BLOCKED =
      'A dispatched, delivered or rejected order cannot be held.';
  static const String ORDER_REJECT_BLOCKED =
      'A dispatched or delivered order cannot be rejected.';
  static const String ORDER_EDIT_BLOCKED =
      'A dispatched or delivered order can no longer be edited.';

  static const String ORDER_DETAILS_TITLE = 'Order details';
  static const String ORDER_UPDATED_TITLE = 'Order updated';
  static const String ORDER_EDIT_LOCKED_TITLE = 'Order locked';
  static const String ORDER_EDIT_LOCKED_BODY =
      'A dispatched order can no longer be edited.';
  static const String ORDER_QUANTITY_LABEL = 'Quantity';
  static const String ORDER_ADD_ITEM = 'Add item';
  static const String ORDER_PICK_PRODUCTS_TITLE = 'Add products';
  static const String ORDER_PICK_PRODUCTS_SUBTITLE =
      'Choose the bags to add to this order.';
  static const String ORDER_PICK_SEARCH_HINT = 'Search products...';
  static const String ORDER_PICK_EMPTY = 'No packagings match your search.';
  static const String ORDER_PICK_ADD = 'ADD';
  static const String ORDER_PICK_CONFIRM = 'Add these products';
  static const String ORDER_PICK_SELECTED_NONE = 'Nothing selected yet';
  static const String ORDER_PICK_ON_ORDER = 'On this order';
  static const String TABLE_ROW_ACTIONS = 'Options';
  static const String TABLE_ROW_ACTIONS_TOOLTIP = 'Order options';
  static const String ORDER_PICK_ALREADY_TITLE = 'Already on this order';
  static const String ORDER_PICK_ALREADY_BODY =
      'Close this and raise the quantity on the existing line instead.';
  static const String ORDER_PICK_SELECTED_ONE = 'bag selected';
  static const String ORDER_PICK_SELECTED_MANY = 'bags selected';
  static const String ORDER_REMOVE_ITEM = 'Remove item';
  static const String ORDER_NEW_ITEM = 'New item';
  static const String ORDER_NEGOTIATED_PRICE_LABEL = 'Negotiated price';
  static const String ORDER_PICK_DELIVERY_DATE = 'Pick a delivery date';
  static const String ORDER_STEP_PREFIX = 'Step';
  static const String LABEL_SEPARATOR = ':';
  static const String ORDER_STEP_SUMMARY_CAPTION = 'Order overview';
  static const String ORDER_STEP_ITEMS_CAPTION = 'Bags on this order';
  static const String ORDER_STEP_DELIVERY_CAPTION = 'Where it is going';
  static const String ORDER_STEP_SUMMARY = 'Summary';
  static const String ORDER_STEP_ITEMS = 'Items';
  static const String ORDER_STEP_DELIVERY = 'Delivery';

  static const String ORDER_PUBLIC_ID_LABEL = 'Order ID';
  static const String ORDER_PLACED_BY_LABEL = 'Booked by';
  static const String ORDER_CLIENT_ONBOARDED_BY_LABEL = 'Client onboarded by';
  static const String ORDER_VERIFIED_BY_LABEL = 'Verified by';
  static const String ORDER_AWAITING_VERIFICATION = 'Awaiting verification';
  static const String ORDER_TOTAL_AMOUNT_LABEL = 'Total amount';
  static const String ORDER_TOTAL_PACKETS_LABEL = 'Total packets';
  static const String ORDER_ITEM_COUNT_LABEL = 'Items';
  static const String ORDER_BAG_COUNT_LABEL = 'Bags';
  static const String ORDER_DELIVERY_ADDRESS_LABEL = 'Delivery address';
  static const String ORDER_CITY_LABEL = 'City';
  static const String ORDER_DISPATCH_MODE_LABEL = 'Dispatch';
  static const String ORDER_TRANSPORT_AGENCY_LABEL = 'Transport agency';
  static const String ORDER_EXPECTED_DELIVERY_LABEL = 'Expected delivery';
  static const String ORDER_PLACED_ON_LABEL = 'Booked on';
  static const String ORDER_DISPATCH_AGENCY = 'Transport agency';
  static const String ORDER_DISPATCH_PRIVATE = 'Private dispatch';
  static const String ORDER_QUANTITY_PREFIX = 'Qty';
  static const String ORDER_PER_BAG = 'per bag';
  static const String ORDER_LIST_PRICE_LABEL = 'List price';
  static const String ORDER_NO_ITEMS = 'This order has no lines.';
  static const String TIMEZONE_IST = 'IST';
}
