import 'package:flutter/widgets.dart';
import 'sidebar_item_model.dart';

/// A labelled cluster of sidebar entries.
///
/// Grouping is presentation only: [SidebarItems.ITEMS] stays the flat source
/// of truth for routing and permissions, so a group never decides whether a
/// tab is reachable.
class SidebarGroupModel {
  final String id;
  final String label;
  final IconData icon;
  final List<String> itemIds;

  const SidebarGroupModel({
    required this.id,
    required this.label,
    required this.icon,
    required this.itemIds,
  });
}

/// A group paired with the items the current role may actually see.
class ResolvedSidebarGroup {
  final SidebarGroupModel? group;
  final List<SidebarItemModel> items;

  const ResolvedSidebarGroup({required this.items, this.group});

  /// Ungrouped entries (Dashboard) render as plain rows, not under a header.
  bool get isStandalone => group == null;

  bool containsItem(String? id) =>
      id != null && items.any((item) => item.id == id);
}
