import { createContext, useContext, useState, useCallback, useMemo } from 'react';
import type { ReactNode } from 'react';

/**
 * View mode for the Kanban board display
 * - 'kanban-full': Full-size Kanban cards with all details
 * - 'kanban-compact': Compact Kanban cards showing minimal info
 * - 'table': Jira-style table view with expandable rows
 */
export type ViewMode = 'kanban-full' | 'kanban-compact' | 'table';

interface ViewState {
  showArchived: boolean;
  viewMode: ViewMode;
}

interface ViewStateContextValue extends ViewState {
  setShowArchived: (show: boolean) => void;
  toggleShowArchived: () => void;
  setViewMode: (mode: ViewMode) => void;
}

const ViewStateContext = createContext<ViewStateContextValue | null>(null);

interface ViewStateProviderProps {
  children: ReactNode;
}

/**
 * ViewStateProvider manages view state that needs to be shared across
 * different project pages (kanban, ideation, etc.).
 *
 * Currently manages:
 * - showArchived: Whether to show archived items in views
 * - viewMode: Display mode for Kanban board (full, compact, or table view)
 */
export function ViewStateProvider({ children }: ViewStateProviderProps) {
  const [showArchived, setShowArchivedState] = useState(false);
  const [viewMode, setViewModeState] = useState<ViewMode>('kanban-full');

  const setShowArchived = useCallback((show: boolean) => {
    setShowArchivedState(show);
  }, []);

  const toggleShowArchived = useCallback(() => {
    setShowArchivedState((prev) => !prev);
  }, []);

  const setViewMode = useCallback((mode: ViewMode) => {
    setViewModeState(mode);
  }, []);

  const value = useMemo<ViewStateContextValue>(
    () => ({
      showArchived,
      setShowArchived,
      toggleShowArchived,
      viewMode,
      setViewMode,
    }),
    [showArchived, setShowArchived, toggleShowArchived, viewMode, setViewMode]
  );

  return (
    <ViewStateContext.Provider value={value}>
      {children}
    </ViewStateContext.Provider>
  );
}

/**
 * Hook to access view state from within the ViewStateProvider tree.
 *
 * @throws Error if used outside of ViewStateProvider
 *
 * @example
 * ```tsx
 * function KanbanBoard() {
 *   const { showArchived, toggleShowArchived, viewMode, setViewMode } = useViewState();
 *
 *   return (
 *     <div>
 *       <button onClick={toggleShowArchived}>
 *         {showArchived ? 'Hide archived' : 'Show archived'}
 *       </button>
 *       <button onClick={() => setViewMode('kanban-compact')}>
 *         Compact View
 *       </button>
 *     </div>
 *   );
 * }
 * ```
 */
export function useViewState(): ViewStateContextValue {
  const context = useContext(ViewStateContext);

  if (!context) {
    throw new Error('useViewState must be used within a ViewStateProvider');
  }

  return context;
}

/**
 * Optional hook that returns null if used outside provider.
 * Useful for components that may or may not be within the provider tree.
 */
export function useViewStateOptional(): ViewStateContextValue | null {
  return useContext(ViewStateContext);
}
