import 'package:flutter/material.dart';
import 'package:toastification/toastification.dart';
import '../theme/app_spacing.dart';
import '../theme/app_typography.dart';

enum AppToastType { success, error, warning, info }

class ToastUtils {
  ToastUtils._();

  static const Duration _autoClose = Duration(seconds: 4);
  static const Duration _animation = Duration(milliseconds: 300);

  static ToastificationItem showSuccess(
    BuildContext context,
    String title, {
    String? description,
  }) => show(
    context: context,
    title: title,
    description: description,
    type: AppToastType.success,
  );

  static ToastificationItem showError(
    BuildContext context,
    String title, {
    String? description,
  }) => show(
    context: context,
    title: title,
    description: description,
    type: AppToastType.error,
  );

  static ToastificationItem showWarning(
    BuildContext context,
    String title, {
    String? description,
  }) => show(
    context: context,
    title: title,
    description: description,
    type: AppToastType.warning,
  );

  static ToastificationItem showInfo(
    BuildContext context,
    String title, {
    String? description,
  }) => show(
    context: context,
    title: title,
    description: description,
    type: AppToastType.info,
  );

  static ToastificationItem show({
    required BuildContext context,
    required String title,
    String? description,
    AppToastType type = AppToastType.success,
    Duration autoCloseDuration = _autoClose,
  }) {
    return toastification.show(
      context: context,
      title: Text(title, style: AppTypography.label),
      description: description != null
          ? Text(description, style: AppTypography.bodySmall)
          : null,
      autoCloseDuration: autoCloseDuration,
      type: _resolveType(type),
      style: ToastificationStyle.flat,
      alignment: Alignment.topRight,
      animationDuration: _animation,
      borderRadius: BorderRadius.circular(AppRadius.lg),
      showProgressBar: true,
      pauseOnHover: true,
      dragToClose: true,
      applyBlurEffect: false,
    );
  }

  static ToastificationType _resolveType(AppToastType type) {
    switch (type) {
      case AppToastType.success:
        return ToastificationType.success;
      case AppToastType.error:
        return ToastificationType.error;
      case AppToastType.warning:
        return ToastificationType.warning;
      case AppToastType.info:
        return ToastificationType.info;
    }
  }
}
