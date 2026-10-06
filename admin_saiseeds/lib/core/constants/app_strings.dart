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
  static const String GODOWN_MANAGERS = 'Godown Managers';

  static const String SIDEBAR_COLLAPSE = 'Collapse sidebar';
  static const String SIDEBAR_EXPAND = 'Expand sidebar';

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
  static const String SOMETHING_WENT_WRONG_TITLE = 'Action failed';
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
  static const String FARMERS_ENDPOINT_MISSING =
      'The farmers list is not available on this server yet.';
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
  static const String DATE_RANGE_LAST_60 = 'Last 60 days';
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
  static const String GODOWN_MANAGERS_TABLE_SEARCH_HINT =
      'Search godown managers...';
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
  static const String ADD_GODOWN_MANAGER = 'Add Godown Manager';
  static const String EDIT_GODOWN_MANAGER = 'Edit Godown Manager';
  static const String ADD_ADMIN_SUBTITLE =
      'Create an administrator account with platform access.';
  static const String EDIT_ADMIN_SUBTITLE =
      'Update the administrator account details.';
  static const String ADD_SALES_PERSON_SUBTITLE =
      'Register a field sales account on the platform.';
  static const String EDIT_SALES_PERSON_SUBTITLE =
      'Update the sales person account details.';
  static const String ADD_GODOWN_MANAGER_SUBTITLE =
      'Register a godown manager account on the platform.';
  static const String EDIT_GODOWN_MANAGER_SUBTITLE =
      'Update the godown manager account details.';

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
  static const String GODOWN_MANAGER_CREATED_TITLE = 'Godown manager created';
  static const String GODOWN_MANAGER_UPDATED_TITLE = 'Godown manager updated';
  static const String GODOWN_MANAGER_DELETED_TITLE = 'Godown manager deleted';

  static const String DELETE_ADMIN_TITLE = 'Delete administrator';
  static const String DELETE_ADMIN_BODY =
      'This permanently removes the administrator account. This cannot be '
      'undone.';
  static const String DELETE_SALES_PERSON_TITLE = 'Delete sales person';
  static const String DELETE_SALES_PERSON_BODY =
      'This permanently removes the sales person account. This cannot be '
      'undone.';
  static const String DELETE_GODOWN_MANAGER_TITLE = 'Delete godown manager';
  static const String DELETE_GODOWN_MANAGER_BODY =
      'This permanently removes the godown manager account. This cannot be '
      'undone.';

  static const String ADMIN_DETAIL_TITLE = 'Administrator details';
  static const String SALES_PERSON_DETAIL_TITLE = 'Sales person details';
  static const String GODOWN_MANAGER_DETAIL_TITLE = 'Godown manager details';
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
  static const String GODOWN_MANAGER_EDIT_HINT =
      'Update the godown manager account details.';
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
  static const String GODOWN_MANAGERS_LOAD_FAILED_TITLE =
      'Could not load godown managers';
  static const String GODOWN_MANAGERS_EMPTY_STATE_TITLE =
      'No godown managers yet';
  static const String GODOWN_MANAGERS_EMPTY_STATE_BODY =
      'Add a godown manager to register a warehouse account.';
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

  static const String PRODUCT_PACKAGINGS = 'Packagings';
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
  static const String SORT_BY_MATERIAL_TYPE = 'material_type';
  static const String SORT_BY_PACKETS = 'packets';
  static const String SORT_BY_TOTAL_WEIGHT = 'total_weight';
  static const String FILTER_BY_PRODUCT = 'product';
  static const String FILTER_BY_MATERIAL_TYPE = 'material_type';

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
  static const String COLUMN_ORDER_SPECIAL_COMMENTS = 'Special Comments';

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

  // -- Return orders --------------------------------------------------------

  static const String RETURN_ORDERS = 'Return Orders';

  static const String RETURN_ORDER_STATUS_PENDING = 'Pending';
  static const String RETURN_ORDER_STATUS_ACCEPTED = 'Accepted';
  static const String RETURN_ORDER_STATUS_REJECTED = 'Rejected';

  static const String RETURN_ORDERS_EMPTY_STATE_TITLE = 'No returns found';
  static const String RETURN_ORDERS_EMPTY_STATE_BODY =
      'Returns raised by your sales team will appear here.';
  static const String RETURN_ORDERS_TABLE_SEARCH_HINT =
      'Search by client or order';
  static const String RETURN_ORDERS_LOAD_FAILED_TITLE =
      'Could not load returns';

  static const String COLUMN_RETURN_ID = 'Return ID';
  static const String COLUMN_RETURN_CLIENT = 'Client';
  static const String COLUMN_RETURN_ORDER = 'Order';
  static const String RETURN_ORDER_ORDER_STATUS = 'Order status';
  static const String COLUMN_RETURN_STATUS = 'Status';
  static const String COLUMN_RETURN_DATE = 'Return Date';
  static const String COLUMN_RETURN_KG = 'Weight';
  static const String COLUMN_RETURN_PACKETS = 'Packets';
  static const String COLUMN_RETURN_AMOUNT = 'Amount';
  static const String COLUMN_RETURN_RAISED_BY = 'Raised By';
  static const String COLUMN_RETURN_DECIDED_BY = 'Decided By';
  static const String COLUMN_RETURN_ACTIONS = 'Return Actions';

  static const String RETURN_ORDER_DETAILS_TITLE = 'Return details';
  static const String RETURN_ORDER_ITEMS_TITLE_ONE = '1 returned line';
  static const String RETURN_ORDER_ITEMS_TITLE_MANY = '%s returned lines';
  static const String RETURN_ORDER_ITEM_PACKET_SUMMARY = '%s x %t packets';
  static const String RETURN_ORDER_INWARD_RAW_TITLE = 'Raw material lots';
  static const String RETURN_ORDER_INWARD_OTHER_TITLE = 'Other material lots';
  static const String RETURN_ORDER_MATERIALS_BOOKED_YES =
      'Packing materials were booked back in as other raw material.';
  static const String RETURN_ORDER_MATERIALS_BOOKED_NO =
      'Packing materials were not booked back in.';
  static const String RETURN_ORDER_ACCEPT = 'Accept';
  static const String RETURN_ORDER_REJECT = 'Reject';
  static const String RETURN_ORDER_UNREJECT = 'Unreject';
  static const String RETURN_ORDER_REVERT_ACCEPT = 'Revert accept';
  static const String RETURN_ORDER_EDIT = 'Edit';

  static const String RETURN_ORDER_ACCEPT_TITLE = 'Accept this return?';
  static const String RETURN_ORDER_ACCEPT_BODY =
      'The returned packets are booked back in as raw material stock, dated today.';
  static const String RETURN_ORDER_ACCEPT_DONE = 'Return accepted';

  static const String RETURN_ORDER_REJECT_TITLE = 'Reject this return?';
  static const String RETURN_ORDER_REJECT_BODY =
      'The return is rejected and its packets stay claimed on the order until it is unrejected or the return is deleted.';
  static const String RETURN_ORDER_REJECT_DONE = 'Return rejected';

  static const String RETURN_ORDER_UNREJECT_TITLE = 'Bring this return back?';
  static const String RETURN_ORDER_UNREJECT_BODY =
      'The return goes back to pending so it can be accepted or rejected again.';
  static const String RETURN_ORDER_UNREJECT_DONE = 'Return back to pending';

  static const String RETURN_ORDER_REVERT_ACCEPT_TITLE =
      'Undo this acceptance?';
  static const String RETURN_ORDER_REVERT_ACCEPT_BODY =
      'The inward stock booked by this acceptance is reversed and the return goes back to pending.';
  static const String RETURN_ORDER_REVERT_ACCEPT_DONE = 'Acceptance undone';

  static const String RETURN_ORDER_ACCEPT_BLOCKED =
      'Only a pending return can be accepted.';
  static const String RETURN_ORDER_REJECT_BLOCKED =
      'Only a pending return can be rejected.';
  static const String RETURN_ORDER_UNREJECT_BLOCKED =
      'Only a rejected return can be brought back.';
  static const String RETURN_ORDER_REVERT_ACCEPT_BLOCKED =
      'Only an accepted return can have its acceptance undone.';
  static const String RETURN_ORDER_EDIT_BLOCKED =
      'Only a pending return can be edited.';

  static const String RETURN_ORDER_ACCEPT_INCLUDE_MATERIALS =
      'Book the packing materials back in too';
  static const String RETURN_ORDER_ACCEPT_INCLUDE_MATERIALS_HINT =
      'The bags and labels come back with the packets. Tick each recipe below to say what they are made of.';
  static const String RETURN_ORDER_ACCEPT_RECIPES_TITLE =
      'Packing material recipes';
  static const String RETURN_ORDER_ACCEPT_RECIPES_EMPTY =
      'No recipes are defined for these lines, so the packing materials cannot be booked in.';
  static const String RETURN_ORDER_ACCEPT_PICK_AT_LEAST_ONE =
      'Every line needs at least one recipe, and one recipe per material type.';
  static const String RETURN_ORDER_ACCEPT_LOADING_RECIPES =
      'Loading recipes...';
  static const String RETURN_ORDER_ACCEPT_PENDING_SUMMARY =
      '%p packets, %w kg, worth %a';
  static const String RETURN_ORDER_ACCEPT_LINE_TITLE = '%s (%w packets)';
  static const String RETURN_ORDER_ACCEPT_RECIPE_SUMMARY = 'Uses %q';
  static const String RETURN_ORDER_ACCEPT_RECIPE_DELETED =
      '%s (recipe since deleted)';

  static const String RETURN_ORDER_EDIT_TITLE = 'Edit return';
  static const String RETURN_ORDER_EDIT_DATE = 'Return date';
  static const String RETURN_ORDER_EDIT_PACKETS = 'Packets';
  static const String RETURN_ORDER_EDIT_PRICE = 'Price per packet';
  static const String RETURN_ORDER_EDIT_TOTAL = 'Total';
  static const String RETURN_ORDER_EDIT_SAVE = 'Save changes';
  static const String RETURN_ORDER_EDIT_REPLACEMENT_WARNING =
      'Saving replaces every line of this return. Remove a line to delete it.';
  static const String RETURN_ORDER_EDIT_DONE = 'Return updated';
  static const String RETURN_ORDER_EDIT_EMPTY =
      'A return must keep at least one line.';
  static const String RETURN_ORDER_EDIT_WILL_BE_REMOVED = 'Dropped on save';
  static const String RETURN_ORDER_EDIT_NOTHING_DROPPED =
      'Nothing queued to drop. Use Remove on the Items step and the line '
      'shows up here until you save.';
  static const String RETURN_ORDER_EDIT_PACKETS_MIN = 'At least 1 packet';
  static const String RETURN_ORDER_EDIT_PRICE_INVALID = 'Enter a price';
  static const String RETURN_ORDER_EDIT_RESTORE = 'Put back';
  static const String RETURN_ORDER_EDIT_REMOVE = 'Remove';

  static const String RETURN_ORDER_STEP_SUMMARY = 'Summary';
  static const String RETURN_ORDER_STEP_ITEMS = 'Items';
  static const String RETURN_ORDER_STEP_REVIEW = 'Review';
  static const String RETURN_ORDER_STEP_SUMMARY_CAPTION = 'Return overview';
  static const String RETURN_ORDER_STEP_ITEMS_CAPTION = 'Returned lines';
  static const String RETURN_ORDER_STEP_REVIEW_CAPTION =
      'Dropped lines and totals';

  static const String RETURN_ORDER_ITEM_COUNT_ONE = 'item';
  static const String RETURN_ORDER_ITEM_COUNT_MANY = 'items';
  static const String RETURN_ORDER_MATERIALS_BOOKED =
      'Packing materials booked: %s';
  static const String RETURN_ORDER_MATERIALS_NOT_BOOKED =
      'Packing materials were not booked in.';
  static const String RETURN_ORDER_ACCEPTED_BY = 'Accepted by %s';
  static const String RETURN_ORDER_REJECTED_BY = 'Rejected by %s';
  static const String RETURN_ORDER_INWARD_LOTS = 'Inward lots';

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
  static const String ORDER_PICK_PRODUCTS_SUBTITLE_PACKETS =
      'Choose the packets to add to this order.';
  static const String ORDER_PICK_PER_PACKET = 'per packet';
  static const String ORDER_PICK_SEARCH_HINT = 'Search products...';
  static const String ORDER_PICK_EMPTY = 'No packagings match your search.';
  static const String ORDER_PICK_ADD = 'ADD';
  static const String ORDER_PICK_CONFIRM = 'Add these products';
  static const String ORDER_PICK_SELECTED_NONE = 'Nothing selected yet';
  static const String ORDER_PICK_ON_ORDER = 'On this order';
  static const String STOCK_UPDATED = 'Stock Updated';
  static const String STOCK_NOT_UPDATED = 'Stock not updated';
  static const String PARTIES = 'Party Management';
  static const String PARTY_DETAIL_TITLE = 'Party details';
  static const String PARTY_DETAIL_SUBTITLE =
      'Name and city on record for this party.';
  static const String ADD_PARTY = 'Add party';
  static const String ADD_PARTY_SUBTITLE = 'Register a party in the directory.';
  static const String EDIT_PARTY_SUBTITLE = 'Update the party details.';
  static const String PARTY_CREATED_TITLE = 'Party created';
  static const String PARTY_UPDATED_TITLE = 'Party updated';
  static const String PARTY_DELETED_TITLE = 'Party deleted';
  static const String DELETE_PARTY_TITLE = 'Delete party';
  static const String DELETE_PARTY_BODY =
      'This permanently removes the party. This cannot be undone.';
  static const String COLUMN_PARTY_NAME = 'Party Name';
  static const String COLUMN_PARTY_CONTACT = 'Contact Number';
  static const String COLUMN_PARTY_TYPE = 'Type';
  static const String FIELD_PARTY_NAME_HINT = 'Party name';
  static const String FIELD_PARTY_CONTACT_HINT = '10-digit mobile number';
  static const String FIELD_PARTY_TYPE = 'Party type';
  static const String FIELD_PARTY_TYPE_HINT = 'Search a party type';
  static const String PARTY_TYPE_RAW_MATERIAL = 'Raw Material';
  static const String PARTY_TYPE_OTHER_MATERIAL = 'Other Material';
  static const String VALIDATION_PARTY_TYPE_REQUIRED = 'Party type is required.';
  static const String PARTIES_TABLE_SEARCH_HINT = 'Search parties...';
  static const String PARTIES_EMPTY_STATE_TITLE = 'No parties yet';
  static const String PARTIES_EMPTY_STATE_BODY =
      'Add a party to start building the directory.';
  static const String PARTIES_LOAD_FAILED_TITLE = 'Could not load parties';
  static const String VALIDATION_PARTY_NAME_REQUIRED =
      'Party name is required.';
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
  static const String ORDER_STEP_RETURNS = 'Returns';
  static const String ORDER_STEP_NET_SALE = 'Net sale';
  static const String ORDER_STEP_RETURNS_CAPTION = 'Goods that came back';
  static const String ORDER_STEP_NET_SALE_CAPTION = 'What the sale is worth';
  static const String ORDER_NO_RETURNS =
      'No goods were returned against this order.';
  static const String ORDER_FIELD_ORDER_VALUE = 'Order value';
  static const String ORDER_FIELD_RETURNED_VALUE = 'Returned value';
  static const String ORDER_FIELD_NET_SALE = 'Net sale';

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

  static const String DISPATCH_CHALLANS = 'Dispatch Orders';
  static const String COLUMN_DISPATCH_ID = 'Dispatch ID';
  static const String COLUMN_CHALLAN_NUMBER = 'Challan Number';
  static const String COLUMN_LR_NUMBER = 'LR Number';
  static const String COLUMN_DISPATCH_DATE = 'Dispatch Date';
  static const String COLUMN_TRANSPORT_TYPE = 'Transport';
  static const String COLUMN_VEHICLE_NUMBER = 'Vehicle';
  static const String COLUMN_DRIVER = 'Driver';
  static const String COLUMN_FROM_CITY = 'From City';
  static const String COLUMN_TO_CITY = 'To City';
  static const String COLUMN_RECEIVER = 'Receiver';
  static const String COLUMN_RECEIVER_ADDRESS = 'Delivery Address';
  static const String COLUMN_CONTACT_PERSON = 'Contact Person';
  static const String COLUMN_HSN_CODE = 'HSN Code';
  static const String COLUMN_FINANCIAL_YEAR = 'Financial Year';
  static const String COLUMN_ITEM_COUNT = 'Items';
  static const String COLUMN_TOTAL_PACKETS = 'Packets';
  static const String COLUMN_TOTAL_AMOUNT = 'Total Amount';
  static const String TRANSPORT_PRIVATE = 'Private';
  static const String TRANSPORT_AGENCY = 'Agency';
  static const String DOWNLOAD = 'Download';
  static const String CHALLAN_EDIT_LR = 'Edit LR';
  static const String CHALLAN_LR_TITLE = 'LR number';
  static const String ORDER_LR_ACTION = 'Add LR number';
  static const String ORDER_LR_SUBTITLE =
      'Record the transporter LR against this dispatched order.';
  static const String ORDER_LR_BLOCKED =
      'Only a dispatched order can carry an LR number.';
  static const String CHALLAN_LR_SUBTITLE =
      'Record the transporter LR against this dispatch.';
  static const String CHALLAN_LR_SAVED = 'LR number saved';
  static const String FIELD_LR_NUMBER_HINT = 'Transporter LR number';
  static const String CHALLAN_DOWNLOAD = 'Download challan';
  static const String CHALLAN_VIEW = 'View challan';
  static const String CHALLAN_PREVIEW_TITLE = 'Delivery challan';
  static const String CHALLAN_FILE_PREFIX = 'challan-';
  static const String EXPORTS = 'Exports';
  static const String EXPORT = 'Export';
  static const String EXPORT_SUBTITLE =
      'Pick a report, choose the days it covers, and download it as a '
      'spreadsheet.';
  static const String EXPORT_CARD_ACTION = 'Choose dates';
  static const String EXPORT_BUILDING = 'Building...';
  static const String EXPORT_HINT_TITLE = 'Good to know';
  static const String EXPORT_HINT_WINDOW = 'A window can cover up to 62 days.';
  static const String EXPORT_HINT_ROWS =
      'Every report lands as one row per line, ready to filter or pivot.';
  static const String EXPORT_HINT_HISTORY =
      'Inventory Snapshots can run without dates for the full history.';
  static const String EXPORT_DIALOG_TITLE = 'Export report';
  static const String EXPORT_DIALOG_SUBTITLE =
      'Choose the days to include, then download.';
  static const String EXPORT_FORMAT_LABEL = 'Format';
  static const String EXPORT_FORMAT_SHEET = 'Spreadsheet';
  static const String EXPORT_FORMAT_SHEET_BODY = 'One row per line item';
  static const String EXPORT_FORMAT_RECEIPTS = 'Delivery challans';
  static const String EXPORT_FORMAT_RECEIPTS_BODY = 'A PDF each, in a zip';
  static const String EXPORT_RECEIPTS_DONE = 'Challans downloaded';
  static const String EXPORT_RANGE_LABEL = 'Date range';
  static const String EXPORT_RANGE_HINT = 'Choose the days to include';
  static const String EXPORT_START_DATE = 'Start date';
  static const String EXPORT_END_DATE = 'End date';
  static const String EXPORT_RANGE_REQUIRED = 'Choose both dates.';
  static const String EXPORT_RANGE_BACKWARDS =
      'The end date cannot be before the start date.';
  static const String EXPORT_RANGE_TOO_LONG =
      'A window can span at most 31 days.';
  static const String EXPORT_EMPTY = 'Nothing to export for those dates.';
  static const String EXPORT_FAILED = 'Could not build the export.';
  static const String EXPORT_DONE = 'Export downloaded';
  static const String EXPORT_ROWS_ONE = 'row';
  static const String EXPORT_ROWS_MANY = 'rows';
  static const String EXPORT_ORDERS = 'Orders';
  static const String EXPORT_ORDERS_BODY =
      'Orders booked in the window, one row per line item.';
  static const String EXPORT_CUSTOM_ORDERS = 'Custom Orders';
  static const String EXPORT_CUSTOM_ORDERS_BODY =
      'Loose-packet orders booked in the window, one row per line item.';
  static const String EXPORT_DISPATCH_RECEIPTS = 'Dispatch Receipts';
  static const String EXPORT_DISPATCH_RECEIPTS_BODY =
      'Challans for orders and custom orders booked in the window.';
  static const String EXPORT_INWARD_ENTRIES = 'Inward Entries';
  static const String EXPORT_INWARD_ENTRIES_BODY =
      'Raw and other material received in the window, grouped by day.';
  static const String EXPORT_INVENTORY_SNAPSHOTS = 'Inventory Snapshots';
  static const String EXPORT_INVENTORY_SNAPSHOTS_BODY =
      'Bag and loose stock counts. Leave the dates empty for all history.';
  static const String EXPORT_WINDOW_OPTIONAL =
      'Optional for this report -- leave both empty for the full history.';
  static const String COLUMN_PRODUCT_USABLE = 'Availability';
  static const String PRODUCT_USABLE_YES = 'Available';
  static const String PRODUCT_USABLE_NO = 'Frozen';
  static const String FIELD_PRODUCT_USABLE = 'Available for use';
  static const String FIELD_PRODUCT_USABLE_ON =
      'Can be ordered, counted and packed.';
  static const String FIELD_PRODUCT_USABLE_OFF =
      'Frozen: nothing new can be created against it. Its history stays.';
  static const String PRINT = 'Print';
  static const String CUSTOM_ORDERS = 'Custom Orders';
  static const String COLUMN_CUSTOM_ORDER_CITY = 'City';
  static const String COLUMN_CUSTOM_ORDER_ITEMS = 'Items';
  static const String COLUMN_CUSTOM_ORDER_PACKETS = 'Packets';
  static const String COLUMN_CUSTOM_ORDER_EXPECTED = 'Expected Delivery';
  static const String CUSTOM_ORDERS_SEARCH_HINT = 'Search custom orders...';
  static const String CUSTOM_ORDERS_EMPTY_TITLE = 'No custom orders found';
  static const String CUSTOM_ORDERS_EMPTY_BODY =
      'Loose-packet orders booked for verified clients will appear here.';
  static const String CUSTOM_ORDER_PER_PACKET = 'per packet';
  static const String CUSTOM_ORDER_ADD = 'Book custom order';
  static const String CUSTOM_ORDER_STEP_CLIENT = 'Client';
  static const String CUSTOM_ORDER_STEP_CLIENT_CAPTION = 'Who it is for';
  static const String CUSTOM_ORDER_STEP_ITEMS_CAPTION = 'Packets on this order';
  static const String CUSTOM_ORDER_STEP_DELIVERY_CAPTION = 'When and where';
  static const String CUSTOM_ORDER_ADD_SUBTITLE =
      'Book a loose-packet order for a verified client.';
  static const String CUSTOM_ORDER_DETAIL_TITLE = 'Custom order';
  static const String CUSTOM_ORDER_DETAIL_SUBTITLE =
      'Review the order and its lines.';
  static const String CUSTOM_ORDER_CREATED = 'Custom order booked';
  static const String CUSTOM_ORDER_UPDATED = 'Custom order updated';
  static const String CUSTOM_ORDER_DELETED = 'Custom order deleted';
  static const String CUSTOM_ORDER_DELETE_TITLE = 'Delete this custom order?';
  static const String CUSTOM_ORDER_DELETE_BODY =
      'The order and all of its lines are removed. This cannot be undone.';
  static const String CUSTOM_ORDER_DELETE_BLOCKED =
      'A dispatched order cannot be deleted.';
  static const String CUSTOM_ORDER_LOAD_FAILED = 'Could not load custom orders';
  static const String CUSTOM_ORDER_ITEMS_TITLE = 'Order lines';
  static const String CUSTOM_ORDER_ADD_LINE = 'Add line';
  static const String CUSTOM_ORDER_NO_LINES = 'Add at least one order line.';
  static const String CUSTOM_ORDER_LINE_INVALID =
      'Every line needs a product, a packet weight, packets and a price.';
  static const String FIELD_NEGOTIATED_PRICE = 'Negotiated price';
  static const String FIELD_NEGOTIATED_PRICE_HINT = 'Price per packet';
  static const String FIELD_SPECIAL_COMMENTS = 'Special comments';
  static const String FIELD_SPECIAL_COMMENTS_HINT = 'Optional notes';
  static const String FIELD_EXPECTED_DELIVERY = 'Expected delivery date';
  static const String FIELD_ACTUAL_DELIVERY = 'Actual delivery date';
  static const String FIELD_DELIVERY_ADDRESS_PICK = 'Delivery address';
  static const String FIELD_CLIENT_HINT = 'Select a client';
  static const String VALIDATION_PACKET_WEIGHT_REQUIRED =
      'Select a packet weight.';
  static const String VALIDATION_CLIENT_REQUIRED = 'Select a client.';
  static const String VALIDATION_ADDRESS_REQUIRED =
      'Select a delivery address.';
  static const String FIELD_PACKET_WEIGHT_SELECT = 'Packet Weight (kg)';
  static const String FIELD_PACKET_WEIGHT_SELECT_HINT =
      'Select a packet weight';
  static const String FIELD_PACKET_WEIGHT_PICK_PRODUCT =
      'Choose a product first';
  static const String FIELD_PACKET_WEIGHT_NONE =
      'This product has no packagings configured.';
  static const String CHALLAN_PRINT_FAILED = 'Could not open the print dialog.';
  static const String CHALLAN_DOWNLOAD_FAILED =
      'Could not generate the challan PDF.';
  static const String CHALLAN_DETAIL_TITLE = 'Dispatch challan';
  static const String CHALLAN_DETAIL_SUBTITLE =
      'Items and lot numbers on this dispatch.';
  static const String CHALLAN_ITEMS_EMPTY = 'This challan has no items.';
  static const String CHALLANS_TABLE_SEARCH_HINT = 'Search dispatches...';
  static const String CHALLANS_EMPTY_STATE_TITLE = 'No dispatches';
  static const String CHALLANS_EMPTY_STATE_BODY =
      'No dispatch challans were recorded in this date range.';
  static const String CHALLANS_LOAD_FAILED_TITLE = 'Could not load dispatches';
  static const String COLUMN_LOT_NUMBER = 'Lot Number';
  static const String FILTER_BY_DATE_RANGE = 'date_range';
  static const String FILTER_LABEL_DATE_RANGE = 'Dispatch Window';
  static const String FILTER_LABEL_CITY = 'Destination City';
  static const String FILTER_LABEL_CLIENT = 'Client';
  static const String SORT_LABEL_DISPATCH_DATE = 'Dispatch Date';
  static const String SORT_LABEL_CREATED = 'Created';
  static const String SORT_BY_DISPATCH_DATE = 'dispatch_date';

  static const String WORKSPACE_OPERATIONS = 'Operations';
  static const String WORKSPACE_OPERATIONS_HINT = 'Day-to-day work';
  static const String WORKSPACE_SETUP = 'Setup';
  static const String WORKSPACE_SETUP_HINT = 'Configuration & masters';
  static const String WORKSPACE_SWITCH_LABEL = 'Workspace';
  static const String GROUP_ORDERS = 'Order Management';
  static const String GROUP_DAILY_STOCK = 'Daily Stock Update';
  static const String GROUP_STOCK_ANALYSIS = 'Stock Analysis';
  static const String GROUP_INWARD = 'Inward Operations';
  static const String GROUP_CATALOGUE = 'Product Configuration';
  static const String GROUP_ONBOARDING = 'Client & Party';
  static const String GROUP_USER_MANAGEMENT = 'User Management';
  static const String GROUP_FARMER_TRIPS = 'Farmer & Trips';

  static const String ORDER_DISPATCH = 'Dispatch';
  static const String ORDER_DISPATCH_TITLE = 'Dispatch order';
  static const String ORDER_DISPATCH_SUBTITLE =
      'Record the vehicle, driver and lot numbers.';
  static const String ORDER_DISPATCH_DONE = 'Order dispatched';
  static const String ORDER_DISPATCH_BLOCKED =
      'Only a verified order can be dispatched.';
  static const String ORDER_REVERT_DISPATCH = 'Revert dispatch';
  static const String ORDER_REVERT_DISPATCH_BLOCKED =
      'Only a dispatched order can be reverted.';
  static const String ORDER_REVERT_DISPATCH_TITLE = 'Revert this dispatch?';
  static const String ORDER_REVERT_DISPATCH_BODY =
      'This returns the order to Confirmed so it can be dispatched again.';
  static const String ORDER_REVERT_DISPATCH_DONE = 'Dispatch reverted';
  static const String DISPATCH_STEP_TRANSPORT = 'Transport';
  static const String DISPATCH_STEP_ITEMS = 'Lot numbers';
  static const String DISPATCH_STEP_SUMMARY = 'Summary';
  static const String DISPATCH_STEP_TRANSPORT_CAPTION =
      'Where it ships from and who is driving.';
  static const String DISPATCH_STEP_ITEMS_CAPTION =
      'Record the lot number for each bag.';
  static const String DISPATCH_STEP_SUMMARY_CAPTION =
      'Check the details, then dispatch.';
  static const String FIELD_FROM_CITY = 'From City';
  static const String FIELD_DRIVER_NAME = 'Driver name';
  static const String FIELD_DRIVER_NAME_HINT = 'Name of the driver';
  static const String FIELD_DRIVER_NUMBER = 'Driver number';
  static const String FIELD_VEHICLE_NUMBER = 'Vehicle number';
  static const String FIELD_VEHICLE_NUMBER_HINT = 'e.g. GJ01AB1234';
  static const String FIELD_LOT_NUMBER = 'Lot number';
  static const String FIELD_LOT_NUMBER_HINT = 'Lot number for this bag';
  static const String FIELD_LOT_NUMBER_RECENT_HINT =
      'Pick a recent lot number or type a new one';
  static const String LOT_NUMBERS_UNAVAILABLE =
      'Recent lot numbers could not be loaded';
  static const String DISPATCH_ITEMS_EMPTY = 'This order has no bags.';
  static const String DISPATCHED_TITLE = 'Order dispatched';
  static const String VALIDATION_FROM_CITY_REQUIRED = 'From city is required.';
  static const String DISPATCH_SUMMARY_ITEMS = 'Bags';

  static const String PRODUCT_STOCK = 'Product Stock';
  static const String RAW_MATERIAL_STOCK = 'Raw Material';

  static const String OTHER_MATERIAL_STOCK = 'Material Stock';
  static const String PACKETS_PER_BAG_SUFFIX = 'packets / bag';
  static const String FILTER_BY_TYPE = 'type';
  static const String FILTER_LABEL_PRODUCT = 'Product';
  static const String FILTER_LABEL_TYPE = 'Type';
  static const String FILTER_LABEL_MATERIAL_TYPE = 'Material Type';
  static const String SORT_LABEL_PRODUCT = 'Product';
  static const String SORT_LABEL_PACKET_WEIGHT = 'Packet Weight';
  static const String SORT_LABEL_MATERIAL_TYPE = 'Material Type';
  static const String COLUMN_ON_HAND = 'On Hand';
  static const String OTHER_MATERIAL_STOCK_TABLE_SEARCH_HINT =
      'Search other material stock...';
  static const String OTHER_MATERIAL_STOCK_EMPTY_STATE_TITLE =
      'No other material stock';
  static const String OTHER_MATERIAL_STOCK_EMPTY_STATE_BODY =
      'Record an inward other-material lot to start tracking stock.';
  static const String OTHER_MATERIAL_STOCK_LOAD_FAILED_TITLE =
      'Could not load other material stock';

  static const String COLUMN_STOCK_TYPE = 'Type';
  static const String COLUMN_INCOMING_KG = 'Incoming (kg)';
  static const String COLUMN_PACKED_KG = 'Packed (kg)';
  static const String COLUMN_AVAILABLE_KG = 'Available (kg)';
  static const String COLUMN_REJECTED_KG = 'Rejected (kg)';

  static const String STOCK_KIND_BAG = 'Bag';
  static const String STOCK_KIND_LOOSE = 'Packet';

  static const String PRODUCT_STOCK_TABLE_SEARCH_HINT =
      'Search product stock...';
  static const String PRODUCT_STOCK_EMPTY_STATE_TITLE = 'No stock positions';
  static const String PRODUCT_STOCK_EMPTY_STATE_BODY =
      'Add a product packaging to start tracking stock.';
  static const String PRODUCT_STOCK_LOAD_FAILED_TITLE =
      'Could not load product stock';

  static const String RAW_MATERIAL_STOCK_TABLE_SEARCH_HINT =
      'Search raw material stock...';
  static const String RAW_MATERIAL_STOCK_EMPTY_STATE_TITLE =
      'No raw material stock';
  static const String RAW_MATERIAL_STOCK_EMPTY_STATE_BODY =
      'Record an inward raw-material lot to start tracking stock.';
  static const String RAW_MATERIAL_STOCK_LOAD_FAILED_TITLE =
      'Could not load raw material stock';
  static const String STOCK_AS_OF_PREFIX = 'As of';

  static const String INWARD_RAW_MATERIALS = 'Raw Material';
  static const String OTHER_RAW_MATERIALS = 'Material Recipes';
  static const String OTHER_MATERIAL_INWARD = 'Other Material';

  static const String COLUMN_RECIPE = 'Recipe';

  static const String FIELD_RECIPE = 'Recipe';
  static const String FIELD_RECIPE_HINT = 'Search a recipe';

  static const String OTHER_INWARD_DETAIL_TITLE = 'Other material lot';
  static const String OTHER_INWARD_DETAIL_SUBTITLE =
      'Recipe, party and quantity received for this lot.';
  static const String ADD_OTHER_INWARD = 'Add lot';
  static const String ADD_OTHER_INWARD_SUBTITLE =
      'Record an inward other-material lot.';
  static const String OTHER_INWARD_CREATED_TITLE = 'Lot recorded';
  static const String OTHER_INWARD_DELETED_TITLE = 'Lot deleted';
  static const String DELETE_OTHER_INWARD_TITLE = 'Delete lot';
  static const String DELETE_OTHER_INWARD_BODY =
      'This permanently removes the other-material lot. This cannot be undone.';
  static const String OTHER_INWARD_TABLE_SEARCH_HINT =
      'Search other material...';
  static const String OTHER_INWARD_EMPTY_STATE_TITLE =
      'No other material lots yet';
  static const String OTHER_INWARD_EMPTY_STATE_BODY =
      'Record an inward lot to start tracking other material.';
  static const String OTHER_INWARD_LOAD_FAILED_TITLE =
      'Could not load other material lots';
  static const String VALIDATION_RECIPE_REQUIRED = 'Recipe is required.';

  static const String COLUMN_PARTY = 'Party';
  static const String COLUMN_QUANTITY_KG = 'Quantity (kg)';
  static const String COLUMN_LAB_SAMPLING_DATE = 'Lab Sampling Date';
  static const String COLUMN_EFFECTIVE_DATE = 'Effective Date';
  static const String COLUMN_MATERIAL_TYPE = 'Material Type';
  static const String COLUMN_QUANTITY = 'Quantity';
  static const String COLUMN_UNIT_TYPE = 'Unit';

  static const String STATUS_LAB_TESTING = 'Lab Testing';
  static const String STATUS_IN_USE = 'In Use';

  static const String FIELD_PARTY = 'Party';
  static const String FIELD_ORGANIZER = 'Organizer';
  static const String FIELD_PARTY_HINT = 'Search a party';
  static const String FIELD_QUANTITY_KG = 'Quantity (kg)';
  static const String FIELD_QUANTITY_KG_HINT = 'Weight received in kg';
  static const String FIELD_LAB_SAMPLING_DATE = 'Lab sampling date';
  static const String FIELD_FARMER_NAME = 'Farmer name';
  static const String FIELD_FARMER_NAME_HINT = "Supplier's farmer or village name";
  static const String FIELD_MATERIAL_TYPE = 'Material type';
  static const String FIELD_MATERIAL_TYPE_HINT = 'Search a material type';
  static const String FIELD_RECIPE_QUANTITY = 'Quantity';
  static const String FIELD_RECIPE_QUANTITY_HINT = 'Amount per packet';

  static const String INWARD_DETAIL_TITLE = 'Raw material lot';
  static const String INWARD_DETAIL_SUBTITLE =
      'Product, party and lab sampling details for this lot.';
  static const String ADD_INWARD = 'Add lot';
  static const String ADD_INWARD_SUBTITLE =
      'Record an inward raw-material lot.';
  static const String EDIT_INWARD_SUBTITLE =
      'Update the sampling date or mark the lot in use.';
  static const String INWARD_CREATED_TITLE = 'Lot recorded';
  static const String INWARD_UPDATED_TITLE = 'Lot updated';
  static const String INWARD_DELETED_TITLE = 'Lot deleted';
  static const String DELETE_INWARD_TITLE = 'Delete lot';
  static const String DELETE_INWARD_BODY =
      'This permanently removes the raw-material lot. This cannot be undone.';
  static const String INWARD_TABLE_SEARCH_HINT = 'Search raw material...';
  static const String INWARD_EMPTY_STATE_TITLE = 'No raw material lots yet';
  static const String INWARD_EMPTY_STATE_BODY =
      'Record an inward lot to start tracking raw material.';
  static const String INWARD_LOAD_FAILED_TITLE =
      'Could not load raw material lots';
  static const String INWARD_MARK_IN_USE = 'Mark in use';
  static const String INWARD_MARK_IN_USE_TITLE = 'Mark this lot in use?';
  static const String INWARD_MARK_IN_USE_BODY =
      'The lot moves from Lab Testing to In Use.';
  static const String INWARD_MARK_IN_USE_DONE = 'Lot marked in use';
  static const String INWARD_MARK_IN_USE_BLOCKED =
      'This lot is already in use.';
  static const String INWARD_STATUS_LOCKED_NOTE =
      'A lot already in use cannot change status.';
  static const String STATUS_REJECTED = 'Rejected';
  static const String INWARD_MARK_IN_USE_REJECTED =
      'A rejected lot must go back to Lab Testing first.';
  static const String INWARD_MARK_REJECTED = 'Mark rejected';
  static const String INWARD_MARK_REJECTED_TITLE = 'Reject this lot?';
  static const String INWARD_MARK_REJECTED_BODY =
      'The lot moves from Lab Testing to Rejected and stops counting '
      'toward usable stock.';
  static const String INWARD_MARK_REJECTED_DONE = 'Lot rejected';
  static const String INWARD_REVERT_TITLE = 'Send back to Lab Testing?';
  static const String INWARD_REVERT_BODY =
      'The lot returns to Lab Testing and its effective date is cleared.';
  static const String INWARD_REVERT = 'Send to Lab Testing';
  static const String INWARD_REVERT_DONE = 'Lot sent to Lab Testing';
  static const String INWARD_STATUS_CHANGE_LABEL = 'Change status';
  static const String INWARD_STATUS_KEEP = 'Leave unchanged';
  static const String COLUMN_LOT_NO = 'Lot No.';
  static const String FIELD_LOT_NO = 'Lot number';
  static const String FIELD_LOT_NO_HINT = 'e.g. SUP-LOT-A1';
  static const String VALIDATION_LOT_NO_REQUIRED = 'Lot number is required.';

  static const String RECIPE_DETAIL_TITLE = 'Material recipe';
  static const String RECIPE_DETAIL_SUBTITLE =
      'Material consumed per packet of this product.';
  static const String ADD_RECIPE = 'Add recipe';
  static const String ADD_RECIPE_SUBTITLE =
      'Define the material a packet consumes.';
  static const String RECIPE_CREATED_TITLE = 'Recipe created';
  static const String RECIPE_UPDATED_TITLE = 'Recipe updated';
  static const String RECIPE_DELETED_TITLE = 'Recipe deleted';
  static const String DELETE_RECIPE_TITLE = 'Delete recipe';
  static const String DELETE_RECIPE_BODY =
      'This permanently removes the recipe. This cannot be undone.';
  static const String RECIPE_TABLE_SEARCH_HINT = 'Search recipes...';
  static const String RECIPE_EMPTY_STATE_TITLE = 'No recipes yet';
  static const String RECIPE_EMPTY_STATE_BODY =
      'Add a recipe to define what a packet consumes.';
  static const String RECIPE_LOAD_FAILED_TITLE = 'Could not load recipes';

  static const String VALIDATION_PARTY_REQUIRED = 'Party is required.';
  static const String VALIDATION_MATERIAL_TYPE_REQUIRED =
      'Material type is required.';
  static const String VALIDATION_LAB_DATE_REQUIRED =
      'Lab sampling date is required.';

  static const String BAG_STOCK = 'Bag Stocks';
  static const String PACKET_STOCK = 'Packet Stock';

  static const String STOCK_UPDATE_ACTION = 'Update Stock';
  static const String STOCK_CONFIRM_TITLE = 'Update today\'s stock';
  static const String STOCK_CONFIRM_BODY =
      'Are you sure you want to record these counts?';
  static const String STOCK_CONFIRM_ACTION = 'Confirm';
  static const String STOCK_NOTHING_ENTERED_TITLE = 'Nothing to update';
  static const String STOCK_NOTHING_ENTERED_BODY =
      'Enter at least one count before updating.';
  static const String STOCK_COUNT_HINT = '0';

  static const String COLUMN_STOCK_ON_HAND = 'On Hand';
  static const String COLUMN_STOCK_RESERVED = 'Reserved';
  static const String COLUMN_STOCK_CONSUMED = 'Consumed';
  static const String COLUMN_STOCK_AVAILABLE = 'Available';
  static const String COLUMN_STOCK_COUNTED = 'Stock Count';
  static const String COLUMN_PACKETS_PER_BAG = 'Packets / Bag';

  static const String BAG_STOCK_TABLE_SEARCH_HINT = 'Search bag stock...';
  static const String BAG_STOCK_EMPTY_STATE_TITLE = 'No bag stock yet';
  static const String BAG_STOCK_EMPTY_STATE_BODY =
      'Add a product packaging to start counting sealed bags.';
  static const String BAG_STOCK_LOAD_FAILED_TITLE = 'Could not load bag stock';
  static const String BAG_STOCK_UPDATED_TITLE = 'Bag stock updated';

  static const String PACKET_STOCK_TABLE_SEARCH_HINT = 'Search packet stock...';
  static const String PACKET_STOCK_EMPTY_STATE_TITLE = 'No packet stock yet';
  static const String PACKET_STOCK_EMPTY_STATE_BODY =
      'Add a product to start counting loose sample packets.';
  static const String PACKET_STOCK_LOAD_FAILED_TITLE =
      'Could not load packet stock';
  static const String PACKET_STOCK_UPDATED_TITLE = 'Packet stock updated';

  static const String FIELD_TRIPS = 'Field Trips';
  static const String FARMERS = 'Farmers';

  static const String COLUMN_TRIP_ID = 'Trip ID';
  static const String COLUMN_VILLAGE = 'Village';
  static const String COLUMN_SALES_PERSON = 'Sales Person';
  static const String COLUMN_EXPECTED_START = 'Expected Start';
  static const String COLUMN_EXPECTED_END = 'Expected End';
  static const String COLUMN_STARTED_AT = 'Started At';
  static const String COLUMN_ENDED_AT = 'Ended At';
  static const String COLUMN_APPROVED_BY = 'Approved By';
  static const String COLUMN_APPROVED_AT = 'Approved At';
  static const String COLUMN_FARMER_VISITS = 'Farmers';
  static const String COLUMN_FARMER_NAME = 'Farmer';
  static const String COLUMN_CONTACT_NUMBER = 'Contact';
  static const String COLUMN_LAND_AREA = 'Land (Bigha)';
  static const String COLUMN_CROPS = 'Crops';
  static const String COLUMN_USES_OUR_PRODUCTS = 'Our Products';
  static const String COLUMN_PRODUCTS_USED = 'Products';

  static const String FIELD_TRIP_STATUS_PLANNED = 'Planned';
  static const String FIELD_TRIP_STATUS_APPROVED = 'Approved';
  static const String FIELD_TRIP_STATUS_IN_PROGRESS = 'In Progress';
  static const String FIELD_TRIP_STATUS_COMPLETED = 'Completed';

  static const String FIELD_TRIPS_TABLE_SEARCH_HINT = 'Search by village...';
  static const String FIELD_TRIPS_EMPTY_STATE_TITLE = 'No field trips yet';
  static const String FIELD_TRIPS_EMPTY_STATE_BODY =
      'A field trip appears here once a salesperson plans one.';
  static const String FIELD_TRIPS_LOAD_FAILED_TITLE =
      'Could not load field trips';

  static const String FIELD_TRIP_DETAIL_TITLE = 'Field trip';
  static const String FIELD_TRIP_SECTION_PLAN = 'Trip plan';
  static const String FIELD_TRIP_SECTION_PEOPLE = 'People';
  static const String FIELD_TRIP_SECTION_PROGRESS = 'Progress';
  static const String FIELD_TRIP_SECTION_APPROVAL = 'Approval';
  static const String FIELD_TRIP_SECTION_FARMERS = 'Farmers visited';
  static const String FIELD_TRIP_STEP_PLAN_CAPTION = 'Where and when';
  static const String FIELD_TRIP_STEP_PROGRESS_CAPTION =
      'How far the trip has got';
  static const String FIELD_TRIP_STEP_FARMERS_CAPTION =
      'Farmers recorded on this trip';
  static const String FIELD_TRIP_TIMELINE_PLANNED = 'Planned';
  static const String FIELD_TRIP_TIMELINE_APPROVED = 'Approved';
  static const String FIELD_TRIP_TIMELINE_STARTED = 'Started';
  static const String FIELD_TRIP_TIMELINE_ENDED = 'Ended';
  static const String FIELD_TRIP_TIMELINE_PENDING = 'Not yet';
  static const String FIELD_TRIP_FARMERS_EMPTY =
      'No farmers recorded on this trip yet.';
  static const String FIELD_TRIP_FARMERS_FAILED =
      'Could not load the farmers on this trip.';

  static const String EDIT_FIELD_TRIP = 'Edit trip';
  static const String EDIT_FIELD_TRIP_SUBTITLE =
      'Change the plan while the trip is still unapproved.';
  static const String FIELD_TRIP_UPDATED_TITLE = 'Trip updated';
  static const String FIELD_VILLAGE = 'Village';
  static const String FIELD_VILLAGE_HINT = 'Village the trip covers';
  static const String FIELD_EXPECTED_START = 'Expected start';
  static const String FIELD_EXPECTED_END = 'Expected end';
  static const String VALIDATION_VILLAGE_REQUIRED = 'Village is required.';
  static const String VALIDATION_EXPECTED_START_REQUIRED =
      'Expected start is required.';
  static const String VALIDATION_EXPECTED_END_REQUIRED =
      'Expected end is required.';
  static const String VALIDATION_EXPECTED_END_BEFORE_START =
      'Expected end must fall on or after the start.';

  static const String FIELD_TRIP_APPROVE = 'Approve';
  static const String FIELD_TRIP_APPROVE_TITLE = 'Approve this trip?';
  static const String FIELD_TRIP_APPROVE_BODY =
      'The salesperson can start the trip once it is approved.';
  static const String FIELD_TRIP_APPROVED_DONE = 'Trip approved';
  static const String FIELD_TRIP_UNAPPROVE = 'Unapprove';
  static const String FIELD_TRIP_UNAPPROVE_TITLE = 'Withdraw approval?';
  static const String FIELD_TRIP_UNAPPROVE_BODY =
      'The trip returns to Planned and cannot be started until it is '
      'approved again.';
  static const String FIELD_TRIP_UNAPPROVED_DONE = 'Approval withdrawn';
  static const String DELETE_FIELD_TRIP_TITLE = 'Delete trip';
  static const String DELETE_FIELD_TRIP_BODY =
      'This permanently removes the field trip. This cannot be undone.';
  static const String FIELD_TRIP_DELETED_TITLE = 'Trip deleted';

  static const String FARMERS_EMPTY_STATE_TITLE = 'No farmers yet';
  static const String FARMERS_EMPTY_STATE_BODY =
      'Every farmer recorded on a field trip will be listed here.';
  static const String FARMERS_LOAD_FAILED_TITLE = 'Could not load farmers';
  static const String FARMERS_TABLE_SEARCH_HINT = 'Search by farmer name...';

  static const String COLUMN_VISIT_COUNT = 'Visits';
  static const String COLUMN_LAST_VISITED = 'Last Visited';
  static const String COLUMN_SALES_PEOPLE = 'Met By';

  static const String FARMER_DETAIL_TITLE = 'Farmer';
  static const String FARMER_DETAIL_SUBTITLE =
      'Everything recorded about this farmer across their visits.';
  static const String FARMER_SECTION_PROFILE = 'Profile';
  static const String FARMER_SECTION_CROPS = 'Crops grown';
  static const String FARMER_SECTION_PRODUCTS = 'Our products used';
  static const String FARMER_SECTION_SALES_PEOPLE = 'Met by';
  static const String FARMER_SECTION_VISITS = 'Visit history';
  static const String FARMER_CROPS_EMPTY = 'No crops recorded.';
  static const String FARMER_PRODUCTS_EMPTY =
      'This farmer does not use any of our products.';
  static const String FARMER_SALES_PEOPLE_EMPTY =
      'No salesperson recorded against this farmer.';
  static const String FARMER_VISITS_EMPTY = 'No visits recorded yet.';
  static const String FARMER_USES_PRODUCTS_YES = 'Yes';
  static const String FARMER_USES_PRODUCTS_NO = 'No';

  static const String GROUP_WASTE_MANAGEMENT = 'Waste Management';

  static const String WASTE_MANAGEMENT = 'Waste Management';

  static const String WASTE_DETAIL_TITLE = 'Raw material waste';
  static const String WASTE_DETAIL_SUBTITLE =
      'Product, quantity and reason for this write-off.';
  static const String ADD_WASTE = 'Record waste';
  static const String ADD_WASTE_SUBTITLE =
      "Write off unusable kilograms from a product's raw material.";
  static const String EDIT_WASTE_SUBTITLE =
      'Correct the wasted quantity or the reason.';
  static const String WASTE_CREATED_TITLE = 'Waste recorded';
  static const String WASTE_UPDATED_TITLE = 'Waste updated';
  static const String WASTE_DELETED_TITLE = 'Waste entry deleted';
  static const String DELETE_WASTE_TITLE = 'Delete waste entry';
  static const String DELETE_WASTE_BODY =
      "This returns the kilograms to the product's available raw material. "
      'This cannot be undone.';
  static const String WASTE_TABLE_SEARCH_HINT = 'Search waste entries...';
  static const String WASTE_EMPTY_STATE_TITLE = 'No waste recorded yet';
  static const String WASTE_EMPTY_STATE_BODY =
      'Record a write-off when raw material is spoiled or spilled.';
  static const String WASTE_LOAD_FAILED_TITLE = 'Could not load waste entries';

  static const String WASTE_EDIT = 'Edit entry';
  static const String WASTE_REASON_MISSING = 'No reason given';

  static const String COLUMN_REASON = 'Reason';
  static const String COLUMN_REFERENCE = 'Reference';

  static const String FIELD_REASON = 'Reason';
  static const String FIELD_REASON_HINT = 'Why it was wasted (optional)';
}
