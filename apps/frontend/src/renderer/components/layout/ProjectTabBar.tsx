import { useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { Plus, RefreshCw, LayoutGrid, Rows3, Table2 } from 'lucide-react';
import { cn } from '../../lib/utils';
import { Button } from '../ui/button';
import { Tooltip, TooltipContent, TooltipTrigger } from '../ui/tooltip';
import { Separator } from '../ui/separator';
import { SortableProjectTab } from './SortableProjectTab';
import { ActiveAgentsBadge } from './ActiveAgentsBadge';
import { UsageIndicator } from '../status/UsageIndicator';
import { AuthStatusIndicator } from '../auth/AuthStatusIndicator';
import type { Project } from '../../../shared/types';
import type { SidebarView } from './Sidebar';
import type { ViewMode } from '../../contexts/ViewStateContext';
import { isRefreshableView } from '../../hooks/useGlobalRefresh';

interface ProjectTabBarProps {
  projects: Project[];
  activeProjectId: string | null;
  onProjectSelect: (projectId: string) => void;
  onProjectClose: (projectId: string) => void;
  onAddProject: () => void;
  className?: string;
  /** Map of project ID to GitHub enabled status */
  projectGitHubStatus?: Record<string, boolean>;
  /** Current active view */
  activeView?: SidebarView;
  /** View mode for kanban (full, compact, table) */
  viewMode?: ViewMode;
  /** Callback to change view mode */
  onViewModeChange?: (mode: ViewMode) => void;
  /** Refresh function */
  onRefresh?: () => void;
  /** Whether refresh is in progress */
  isRefreshing?: boolean;
}

export function ProjectTabBar({
  projects,
  activeProjectId,
  onProjectSelect,
  onProjectClose,
  onAddProject,
  className,
  projectGitHubStatus,
  activeView,
  viewMode,
  onViewModeChange,
  onRefresh,
  isRefreshing = false,
}: ProjectTabBarProps) {
  const { t } = useTranslation(['common', 'tasks']);

  const showViewModeSelector = activeView === 'kanban' && viewMode && onViewModeChange;
  const showRefreshButton = activeView && isRefreshableView(activeView) && onRefresh;

  // Keyboard shortcuts for tab navigation
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Skip if in input fields
      if (
        e.target instanceof HTMLInputElement ||
        e.target instanceof HTMLTextAreaElement ||
        (e.target as HTMLElement)?.isContentEditable
      ) {
        return;
      }

      const isMod = e.metaKey || e.ctrlKey;
      if (!isMod) return;

      // Cmd/Ctrl + 1-9: Switch to tab N
      if (e.key >= '1' && e.key <= '9') {
        e.preventDefault();
        const index = parseInt(e.key) - 1;
        if (index < projects.length) {
          onProjectSelect(projects[index].id);
        }
        return;
      }

      // Cmd/Ctrl + Tab: Next tab
      // Cmd/Ctrl + Shift + Tab: Previous tab
      if (e.key === 'Tab') {
        e.preventDefault();
        const currentIndex = projects.findIndex((p) => p.id === activeProjectId);
        if (currentIndex === -1 || projects.length === 0) return;

        const nextIndex = e.shiftKey
          ? (currentIndex - 1 + projects.length) % projects.length
          : (currentIndex + 1) % projects.length;
        onProjectSelect(projects[nextIndex].id);
        return;
      }

      // Cmd/Ctrl + W: Close current tab (only if more than one tab)
      if (e.key === 'w' && activeProjectId && projects.length > 1) {
        e.preventDefault();
        onProjectClose(activeProjectId);
      }

      // Cmd/Ctrl + R: Refresh (if available)
      if (e.key === 'r' && showRefreshButton && !isRefreshing) {
        e.preventDefault();
        onRefresh?.();
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [projects, activeProjectId, onProjectSelect, onProjectClose, showRefreshButton, isRefreshing, onRefresh]);

  if (projects.length === 0) {
    return null;
  }

  return (
    <div className={cn(
      'flex items-center gap-1.5',
      'overflow-x-auto scrollbar-thin scrollbar-thumb-border scrollbar-track-transparent',
      'px-1',
      className
    )}>
      {/* Project pills - floating badges */}
      {projects.map((project, index) => {
        const isActiveTab = activeProjectId === project.id;
        const hasGitHub = projectGitHubStatus?.[project.id] ?? false;
        return (
          <SortableProjectTab
            key={project.id}
            project={project}
            isActive={isActiveTab}
            canClose={projects.length > 1}
            tabIndex={index}
            hasGitHub={hasGitHub}
            onSelect={() => onProjectSelect(project.id)}
            onClose={(e) => {
              e.stopPropagation();
              onProjectClose(project.id);
            }}
          />
        );
      })}

      {/* Spacer */}
      <div className="flex-1 min-w-4" />

      {/* View mode selector - only shown on kanban view */}
      {showViewModeSelector && (
        <>
          <div className="flex items-center gap-0.5 shrink-0">
            <Tooltip>
              <TooltipTrigger asChild>
                <Button
                  variant="ghost"
                  size="icon"
                  className={cn(
                    'h-7 w-7 rounded-full',
                    viewMode === 'kanban-full' && 'bg-primary/10 text-primary hover:bg-primary/20'
                  )}
                  onClick={() => onViewModeChange('kanban-full')}
                  aria-label={t('tasks:viewMode.full')}
                >
                  <LayoutGrid className="h-3.5 w-3.5" />
                </Button>
              </TooltipTrigger>
              <TooltipContent side="bottom">{t('tasks:viewMode.full')}</TooltipContent>
            </Tooltip>

            <Tooltip>
              <TooltipTrigger asChild>
                <Button
                  variant="ghost"
                  size="icon"
                  className={cn(
                    'h-7 w-7 rounded-full',
                    viewMode === 'kanban-compact' && 'bg-primary/10 text-primary hover:bg-primary/20'
                  )}
                  onClick={() => onViewModeChange('kanban-compact')}
                  aria-label={t('tasks:viewMode.compact')}
                >
                  <Rows3 className="h-3.5 w-3.5" />
                </Button>
              </TooltipTrigger>
              <TooltipContent side="bottom">{t('tasks:viewMode.compact')}</TooltipContent>
            </Tooltip>

            <Tooltip>
              <TooltipTrigger asChild>
                <Button
                  variant="ghost"
                  size="icon"
                  className={cn(
                    'h-7 w-7 rounded-full',
                    viewMode === 'table' && 'bg-primary/10 text-primary hover:bg-primary/20'
                  )}
                  onClick={() => onViewModeChange('table')}
                  aria-label={t('tasks:viewMode.table')}
                >
                  <Table2 className="h-3.5 w-3.5" />
                </Button>
              </TooltipTrigger>
              <TooltipContent side="bottom">{t('tasks:viewMode.table')}</TooltipContent>
            </Tooltip>
          </div>

          <Separator orientation="vertical" className="h-5 mx-1" />
        </>
      )}

      {/* Refresh button - shown on refreshable views */}
      {showRefreshButton && (
        <Tooltip>
          <TooltipTrigger asChild>
            <Button
              variant="ghost"
              size="icon"
              className="h-7 w-7 rounded-full shrink-0"
              onClick={onRefresh}
              disabled={isRefreshing}
              aria-label={t('common:buttons.refresh')}
            >
              <RefreshCw className={cn('h-3.5 w-3.5', isRefreshing && 'animate-spin')} />
            </Button>
          </TooltipTrigger>
          <TooltipContent side="bottom">
            {t('common:buttons.refresh')}
            <kbd className="ml-2 px-1 py-0.5 text-xs bg-muted rounded border border-border font-mono">
              {typeof navigator !== 'undefined' && navigator.platform.toUpperCase().indexOf('MAC') >= 0 ? '⌘' : 'Ctrl+'}R
            </kbd>
          </TooltipContent>
        </Tooltip>
      )}

      {/* Separator before status indicators */}
      {(showViewModeSelector || showRefreshButton) && (
        <Separator orientation="vertical" className="h-5 mx-1" />
      )}

      {/* Active agents indicator */}
      <ActiveAgentsBadge />

      {/* Status indicators and actions */}
      <AuthStatusIndicator />
      <UsageIndicator />
      <Button
        variant="ghost"
        size="icon"
        className="h-7 w-7 rounded-full shrink-0"
        onClick={onAddProject}
        aria-label={t('common:projectTab.addProjectAriaLabel')}
      >
        <Plus className="h-4 w-4" />
      </Button>
    </div>
  );
}
