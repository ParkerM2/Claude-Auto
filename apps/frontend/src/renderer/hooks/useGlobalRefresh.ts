import { useState, useCallback } from 'react';
import type { SidebarView } from '../components/layout/Sidebar';

/**
 * Views that support refresh functionality
 */
export const REFRESHABLE_VIEWS: SidebarView[] = [
  'kanban',
  'github-issues',
  'github-prs',
  'roadmap',
  'context',
  'changelog',
  'worktrees',
];

/**
 * Check if a view supports refresh
 */
export function isRefreshableView(view: SidebarView): boolean {
  return REFRESHABLE_VIEWS.includes(view);
}

interface UseGlobalRefreshOptions {
  /** Refresh functions mapped by view */
  refreshFunctions: Partial<Record<SidebarView, () => void | Promise<void>>>;
  /** Current active view */
  activeView: SidebarView;
}

interface UseGlobalRefreshReturn {
  /** Whether any refresh is in progress */
  isRefreshing: boolean;
  /** Trigger refresh for the current view */
  refresh: () => Promise<void>;
}

/**
 * Hook to manage global refresh functionality across different views.
 * Pass a map of view -> refresh function, and call refresh() to trigger
 * the appropriate one based on the active view.
 */
export function useGlobalRefresh({
  refreshFunctions,
  activeView,
}: UseGlobalRefreshOptions): UseGlobalRefreshReturn {
  const [isRefreshing, setIsRefreshing] = useState(false);

  const refresh = useCallback(async () => {
    const fn = refreshFunctions[activeView];
    if (!fn) return;

    setIsRefreshing(true);
    try {
      await fn();
    } finally {
      setIsRefreshing(false);
    }
  }, [refreshFunctions, activeView]);

  return {
    isRefreshing,
    refresh,
  };
}
