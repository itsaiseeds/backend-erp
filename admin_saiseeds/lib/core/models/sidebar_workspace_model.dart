import 'package:flutter/widgets.dart';
import 'sidebar_item_model.dart';

/// A labelled cluster of tabs inside a workspace.
///
/// A group with no [label] renders its items as plain rows under no header,
/// which is how standalone entries like Dashboard stay ungrouped.
class SidebarGroupModel {
  final String id;
  final String? label;
  final List<String> itemIds;

  const SidebarGroupModel({
    required this.id,
    required this.itemIds,
    this.label,
  });

  bool get isStandalone => label == null;
}

/// One half of the sidebar: the tabs a user works in daily, or the masters
/// they configure once.
///
/// Splitting is presentation only: [SidebarItems.ITEMS] stays the flat source
/// of truth for routing and permissions, so a workspace never decides whether
/// a tab is reachable.
class SidebarWorkspaceModel {
  final String id;
  final String label;
  final String hint;
  final IconData icon;
  final List<SidebarGroupModel> groups;

  const SidebarWorkspaceModel({
    required this.id,
    required this.label,
    required this.hint,
    required this.icon,
    required this.groups,
  });

  List<String> get itemIds => [
    for (final SidebarGroupModel group in groups) ...group.itemIds,
  ];
}

/// A group paired with the items the current role may actually see.
class ResolvedSidebarGroup {
  final SidebarGroupModel group;
  final List<SidebarItemModel> items;

  const ResolvedSidebarGroup({required this.group, required this.items});

  String get id => group.id;

  String? get label => group.label;

  bool get isStandalone => group.isStandalone;

  bool containsItem(String? id) =>
      id != null && items.any((item) => item.id == id);
}

/// A workspace paired with the groups and items the current role may see.
class ResolvedSidebarWorkspace {
  final SidebarWorkspaceModel workspace;
  final List<ResolvedSidebarGroup> groups;

  const ResolvedSidebarWorkspace({
    required this.workspace,
    required this.groups,
  });

  String get id => workspace.id;

  List<SidebarItemModel> get items => [
    for (final ResolvedSidebarGroup group in groups) ...group.items,
  ];

  bool get isEmpty => groups.isEmpty;

  bool containsItem(String? id) =>
      id != null && groups.any((group) => group.containsItem(id));
}
