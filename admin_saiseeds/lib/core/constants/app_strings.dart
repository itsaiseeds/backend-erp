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
  static const String SIDEBAR_NAVIGATION = 'Navigation';
  static const String SIDEBAR_ACCOUNT = 'Account';

  static const String DASHBOARD_OVERVIEW_TITLE = 'Overview';
  static const String DASHBOARD_OVERVIEW_SUBTITLE =
      'Operational snapshot of the Saiseeds admin workspace.';
  static const String DASHBOARD_STAT_ADMINS = 'Administrators';
  static const String DASHBOARD_STAT_SALES_PEOPLE = 'Sales People';
  static const String DASHBOARD_STAT_ACTIVE_SESSION = 'Active Session';
  static const String DASHBOARD_STAT_PENDING = 'Awaiting Data';
  static const String DASHBOARD_STAT_PLACEHOLDER = '—';
  static const String DASHBOARD_STAT_NOT_WIRED = 'Not connected';
  static const String DASHBOARD_STAT_SIGNED_IN = 'Signed in';
  static const String DASHBOARD_NOTICE_TITLE = 'Live data pending';
  static const String DASHBOARD_NOTICE_BODY =
      'Reporting endpoints are not connected yet. Figures appear here once the '
      'backend metrics API is available.';

  static const String ADMINS_EMPTY_TITLE = 'No administrators loaded';
  static const String ADMINS_EMPTY_BODY =
      'The administrator directory is not connected yet.';
  static const String SALES_PEOPLE_EMPTY_TITLE = 'No sales people loaded';
  static const String SALES_PEOPLE_EMPTY_BODY =
      'The sales team directory is not connected yet.';

  static const String PROFILE_EYEBROW = 'ACCOUNT PROFILE';
  static const String PROFILE_SUBHEADING =
      'Your identity, contact details, and platform permissions.';
  static const String PROFILE_ACCOUNT_DETAILS = 'Account Details';
  static const String PROFILE_ACCOUNT_DETAILS_HINT =
      'Sourced from your authenticated session.';
  static const String PROFILE_PERMISSIONS = 'Permissions';
  static const String PROFILE_PERMISSIONS_HINT =
      'What this account is authorised to do.';
  static const String PROFILE_FIELD_NAME = 'Full Name';
  static const String PROFILE_FIELD_PHONE = 'Phone Number';
  static const String PROFILE_FIELD_ROLE = 'Role';
  static const String PROFILE_FIELD_USER_ID = 'User ID';
  static const String PROFILE_PERMISSION_CREATE_ADMIN =
      'Create administrator accounts';
  static const String PROFILE_PERMISSION_CREATE_SALES_PERSON =
      'Create sales person accounts';
  static const String PROFILE_PERMISSION_GRANTED = 'Granted';
  static const String PROFILE_PERMISSION_RESTRICTED = 'Restricted';
  static const String PROFILE_SESSION_SECTION = 'Session';
  static const String PROFILE_SESSION_HINT =
      'Sign out to clear this session from the browser.';
  static const String PROFILE_UNAVAILABLE_TITLE = 'Profile unavailable';
  static const String PROFILE_UNAVAILABLE_BODY =
      'No account details are stored for this session. Sign in again to '
      'continue.';
  static const String PROFILE_VALUE_UNKNOWN = 'Not available';
  static const String PROFILE_ROLE_UNKNOWN = 'Unassigned';

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
}
