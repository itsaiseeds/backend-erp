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
  static const String SAVE = 'Save';
  static const String EDIT = 'Edit';
  static const String DELETE = 'Delete';
  static const String SEARCH = 'Search...';
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
  static const String SMALL_SCREEN_TITLE = 'Best viewed on a larger screen';
  static const String SMALL_SCREEN_BODY =
      'The Saiseeds admin portal is built for tablets and desktops. Open this '
      'page on a wider screen for the full experience.';
  static const String SMALL_SCREEN_HINT = 'Minimum width: 768px';
  static const String CLIENT_STEP_DETAILS = 'Details';
  static const String CLIENT_STEP_ADDRESSES = 'Addresses';
  static const String CLIENT_STEP_CONTACTS = 'Contacts';
  static const String CLIENT_STEP_TRANSPORT = 'Transport';
  static const String CLIENT_STEP_PROGRESS = 'Step';
  static const String CLIENT_ADD_ADDRESS = 'Add address';
  static const String CLIENT_ADD_CONTACT = 'Add contact';
  static const String CLIENT_ADD_TRANSPORT = 'Add transport agency';
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
  static const String VALIDATION_ONE_PRIMARY = 'Exactly one entry must be primary.';
  static const String VALIDATION_AT_LEAST_ONE = 'At least one entry is required.';
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
  static const String TOTP_MANUAL_ENTRY = 'Setup key';
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
  static const String COLUMN_BUYING_PRICE = 'Buying Price';
  static const String COLUMN_SELLING_PRICE = 'Selling Price';
  static const String COLUMN_MARGIN_PER_PACKET = 'Margin Per Packet';

  static const String SORT_BY_BUYING_PRICE = 'buying_price';
  static const String SORT_BY_SELLING_PRICE = 'selling_price';
  static const String SORT_BY_MARGIN_PER_PACKET = 'margin_per_packet';
  static const String FILTER_BY_CROP = 'crop';

  static const String FIELD_PRODUCT_NAME = 'Product Name';
  static const String FIELD_PRODUCT_NAME_HINT = 'Enter product name';
  static const String FIELD_BUYING_PRICE = 'Buying Price';
  static const String FIELD_BUYING_PRICE_HINT = 'Enter buying price';
  static const String FIELD_SELLING_PRICE = 'Selling Price';
  static const String FIELD_SELLING_PRICE_HINT = 'Enter selling price';
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
}
