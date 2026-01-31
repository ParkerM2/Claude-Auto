import { useState, useMemo, memo } from 'react';
import { useTranslation } from 'react-i18next';
import { ChevronDown, ChevronRight, Clock, MoreVertical, Target, Bug, Wrench, FileCode, Shield, Gauge, Palette, AlertTriangle, Loader2, Archive, GitPullRequest, ExternalLink } from 'lucide-react';
import { Collapsible, CollapsibleTrigger, CollapsibleContent } from './ui/collapsible';
import { Badge } from './ui/badge';
import { Button } from './ui/button';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from './ui/dropdown-menu';
import { PRStatusBadge } from './PRStatusBadge';
import { PhaseProgressIndicator } from './PhaseProgressIndicator';
import { cn, formatRelativeTime, sanitizeMarkdownForDisplay } from '../lib/utils';
import {
  TASK_CATEGORY_LABELS,
  TASK_CATEGORY_COLORS,
  TASK_COMPLEXITY_COLORS,
  TASK_COMPLEXITY_LABELS,
  TASK_IMPACT_COLORS,
  TASK_IMPACT_LABELS,
  TASK_PRIORITY_COLORS,
  TASK_PRIORITY_LABELS,
  EXECUTION_PHASE_LABELS,
  EXECUTION_PHASE_BADGE_COLORS,
  TASK_STATUS_COLUMNS,
  TASK_STATUS_LABELS,
  TASK_STATUS_COLORS,
  JSON_ERROR_PREFIX,
  JSON_ERROR_TITLE_SUFFIX
} from '../../shared/constants';
import { isIncompleteHumanReview } from '../stores/task-store';
import type { Task, TaskCategory, TaskStatus } from '../../shared/types';

// Category icon mapping (same as TaskCard)
const CategoryIcon: Record<TaskCategory, typeof Target> = {
  feature: Target,
  bug_fix: Bug,
  refactoring: Wrench,
  documentation: FileCode,
  security: Shield,
  performance: Gauge,
  ui_ux: Palette,
  infrastructure: Wrench,
  testing: FileCode
};

export interface TaskTableRowProps {
  task: Task;
  onClick: () => void;
  onStatusChange?: (newStatus: TaskStatus) => void;
  defaultOpen?: boolean;
}

// Custom comparator for React.memo
function taskTableRowPropsAreEqual(prevProps: TaskTableRowProps, nextProps: TaskTableRowProps): boolean {
  const prevTask = prevProps.task;
  const nextTask = nextProps.task;

  // Fast path: same reference
  if (
    prevTask === nextTask &&
    prevProps.onClick === nextProps.onClick &&
    prevProps.onStatusChange === nextProps.onStatusChange &&
    prevProps.defaultOpen === nextProps.defaultOpen
  ) {
    return true;
  }

  // Compare only the fields that affect rendering
  return (
    prevTask.id === nextTask.id &&
    prevTask.status === nextTask.status &&
    prevTask.title === nextTask.title &&
    prevTask.description === nextTask.description &&
    prevTask.updatedAt === nextTask.updatedAt &&
    prevTask.reviewReason === nextTask.reviewReason &&
    prevTask.executionProgress?.phase === nextTask.executionProgress?.phase &&
    prevTask.executionProgress?.phaseProgress === nextTask.executionProgress?.phaseProgress &&
    prevTask.subtasks.length === nextTask.subtasks.length &&
    prevTask.metadata?.category === nextTask.metadata?.category &&
    prevTask.metadata?.complexity === nextTask.metadata?.complexity &&
    prevTask.metadata?.impact === nextTask.metadata?.impact &&
    prevTask.metadata?.priority === nextTask.metadata?.priority &&
    prevTask.metadata?.archivedAt === nextTask.metadata?.archivedAt &&
    prevTask.metadata?.prUrl === nextTask.metadata?.prUrl &&
    prevTask.metadata?.prStatus?.state === nextTask.metadata?.prStatus?.state &&
    prevTask.subtasks.every((s, i) => s.status === nextTask.subtasks[i]?.status)
  );
}

/**
 * TaskTableRow - A collapsible table row component for displaying tasks in table view.
 * Uses Radix Collapsible for accessible expand/collapse functionality.
 * Supports multiple rows being expanded simultaneously.
 */
export const TaskTableRow = memo(function TaskTableRow({
  task,
  onClick,
  onStatusChange,
  defaultOpen = false,
}: TaskTableRowProps) {
  const { t } = useTranslation(['tasks', 'errors']);
  const [isOpen, setIsOpen] = useState(defaultOpen);

  const isRunning = task.status === 'in_progress';
  const executionPhase = task.executionProgress?.phase;
  const hasActiveExecution = executionPhase && executionPhase !== 'idle' && executionPhase !== 'complete' && executionPhase !== 'failed';
  const isIncomplete = isIncompleteHumanReview(task);
  const isArchived = !!task.metadata?.archivedAt;

  // Memoize display title with JSON error handling
  const displayTitle = useMemo(() => {
    if (task.title.endsWith(JSON_ERROR_TITLE_SUFFIX)) {
      const baseName = task.title.slice(0, -JSON_ERROR_TITLE_SUFFIX.length);
      return `${baseName} ${t('errors:task.jsonError.titleSuffix')}`;
    }
    return task.title;
  }, [task.title, t]);

  // Memoize sanitized description
  const sanitizedDescription = useMemo(() => {
    if (!task.description) return null;
    if (task.description.startsWith(JSON_ERROR_PREFIX)) {
      const errorMessage = task.description.slice(JSON_ERROR_PREFIX.length);
      const translatedDesc = t('errors:task.jsonError.description', { error: errorMessage });
      return sanitizeMarkdownForDisplay(translatedDesc, 300);
    }
    return sanitizeMarkdownForDisplay(task.description, 300);
  }, [task.description, t]);

  // Memoize relative time
  const relativeTime = useMemo(
    () => formatRelativeTime(task.updatedAt),
    [task.updatedAt]
  );

  // Memoize status menu items
  const statusMenuItems = useMemo(() => {
    if (!onStatusChange) return null;
    return TASK_STATUS_COLUMNS.filter(status => status !== task.status).map((status) => (
      <DropdownMenuItem
        key={status}
        onClick={(e) => {
          e.stopPropagation();
          onStatusChange(status);
        }}
      >
        {t(TASK_STATUS_LABELS[status])}
      </DropdownMenuItem>
    ));
  }, [task.status, onStatusChange, t]);

  // Get status badge styling
  const getStatusBadgeClass = (status: string) => {
    return TASK_STATUS_COLORS[status as keyof typeof TASK_STATUS_COLORS] || 'bg-muted text-muted-foreground';
  };

  // Handle row click to open task details modal
  const handleRowClick = (e: React.MouseEvent) => {
    // Don't trigger if clicking on interactive elements
    const target = e.target as HTMLElement;
    if (target.closest('button') || target.closest('[role="menuitem"]')) {
      return;
    }
    onClick();
  };

  // Handle PR link click
  const handleViewPR = (e: React.MouseEvent) => {
    e.stopPropagation();
    if (task.metadata?.prUrl && window.electronAPI?.openExternal) {
      window.electronAPI.openExternal(task.metadata.prUrl);
    }
  };

  return (
    <Collapsible open={isOpen} onOpenChange={setIsOpen} asChild>
      <div className="contents">
        {/* Main row - acts as the trigger */}
        <CollapsibleTrigger asChild>
          <tr
            className={cn(
              'cursor-pointer transition-colors border-b border-border/50',
              'hover:bg-muted/30',
              isRunning && 'bg-primary/5',
              isArchived && 'opacity-60',
              isOpen && 'bg-muted/20'
            )}
            onClick={handleRowClick}
            aria-expanded={isOpen}
            aria-label={t('tasks:table.expandRow', { title: displayTitle })}
          >
            {/* Expand/Collapse chevron */}
            <td className="w-10 px-3 py-3">
              <div className="flex items-center justify-center">
                {isOpen ? (
                  <ChevronDown className="h-4 w-4 text-muted-foreground" />
                ) : (
                  <ChevronRight className="h-4 w-4 text-muted-foreground" />
                )}
              </div>
            </td>

            {/* Title */}
            <td className="px-3 py-3 max-w-[300px]">
              <div className="flex items-center gap-2 min-w-0">
                <span
                  className="font-medium text-sm text-foreground truncate"
                  title={displayTitle}
                >
                  {displayTitle}
                </span>
                {isIncomplete && (
                  <AlertTriangle className="h-3.5 w-3.5 text-orange-400 shrink-0" />
                )}
              </div>
            </td>

            {/* Status */}
            <td className="px-3 py-3">
              {hasActiveExecution && executionPhase ? (
                <Badge
                  variant="outline"
                  className={cn(
                    'text-[10px] px-1.5 py-0.5 flex items-center gap-1 w-fit',
                    EXECUTION_PHASE_BADGE_COLORS[executionPhase]
                  )}
                >
                  <Loader2 className="h-2.5 w-2.5 animate-spin" />
                  {EXECUTION_PHASE_LABELS[executionPhase]}
                </Badge>
              ) : (
                <Badge
                  variant="outline"
                  className={cn('text-[10px] px-1.5 py-0.5 w-fit', getStatusBadgeClass(task.status))}
                >
                  {t(TASK_STATUS_LABELS[task.status] || 'status.backlog')}
                </Badge>
              )}
            </td>

            {/* Category/Type */}
            <td className="px-3 py-3">
              {task.metadata?.category && (
                <Badge
                  variant="outline"
                  className={cn('text-[10px] px-1.5 py-0 w-fit', TASK_CATEGORY_COLORS[task.metadata.category])}
                >
                  {CategoryIcon[task.metadata.category] && (
                    (() => {
                      const Icon = CategoryIcon[task.metadata.category!];
                      return <Icon className="h-2.5 w-2.5 mr-0.5" />;
                    })()
                  )}
                  {TASK_CATEGORY_LABELS[task.metadata.category]}
                </Badge>
              )}
            </td>

            {/* Progress */}
            <td className="px-3 py-3 min-w-[120px]">
              {(task.subtasks.length > 0 || hasActiveExecution || isRunning) && (
                <div className="w-full max-w-[150px]">
                  <PhaseProgressIndicator
                    phase={executionPhase}
                    subtasks={task.subtasks}
                    phaseProgress={task.executionProgress?.phaseProgress}
                    isStuck={false}
                    isRunning={isRunning}
                  />
                </div>
              )}
            </td>

            {/* Updated */}
            <td className="px-3 py-3 text-xs text-muted-foreground whitespace-nowrap">
              <div className="flex items-center gap-1">
                <Clock className="h-3 w-3" />
                <span>{relativeTime}</span>
              </div>
            </td>

            {/* Actions */}
            <td className="px-3 py-3">
              <div className="flex items-center gap-1" onClick={(e) => e.stopPropagation()}>
                {task.metadata?.prUrl && (
                  <Button
                    variant="ghost"
                    size="sm"
                    className="h-7 w-7 p-0"
                    onClick={handleViewPR}
                    title={t('tooltips.viewPR')}
                  >
                    <GitPullRequest className="h-3.5 w-3.5" />
                  </Button>
                )}
                {statusMenuItems && (
                  <DropdownMenu>
                    <DropdownMenuTrigger asChild>
                      <Button
                        variant="ghost"
                        size="sm"
                        className="h-7 w-7 p-0"
                        aria-label={t('actions.taskActions')}
                      >
                        <MoreVertical className="h-4 w-4" />
                      </Button>
                    </DropdownMenuTrigger>
                    <DropdownMenuContent align="end">
                      <DropdownMenuLabel>{t('actions.moveTo')}</DropdownMenuLabel>
                      <DropdownMenuSeparator />
                      {statusMenuItems}
                    </DropdownMenuContent>
                  </DropdownMenu>
                )}
              </div>
            </td>
          </tr>
        </CollapsibleTrigger>

        {/* Expanded content row */}
        <CollapsibleContent asChild>
          <tr className="bg-muted/10 border-b border-border/50">
            <td colSpan={7} className="p-0">
              <div className="px-6 py-4 space-y-4">
                {/* Description */}
                {sanitizedDescription && (
                  <div>
                    <h4 className="text-xs font-medium text-muted-foreground mb-1.5">
                      {t('form.description')}
                    </h4>
                    <p className="text-sm text-foreground leading-relaxed">
                      {sanitizedDescription}
                    </p>
                  </div>
                )}

                {/* Metadata badges */}
                <div className="flex flex-wrap gap-2">
                  {/* PR Status */}
                  {task.metadata?.prStatus && (
                    <PRStatusBadge status={task.metadata.prStatus} />
                  )}

                  {/* Archived indicator */}
                  {isArchived && (
                    <Badge
                      variant="outline"
                      className="text-[10px] px-1.5 py-0.5 flex items-center gap-1 bg-muted text-muted-foreground border-border"
                    >
                      <Archive className="h-2.5 w-2.5" />
                      {t('status.archived')}
                    </Badge>
                  )}

                  {/* Complexity */}
                  {task.metadata?.complexity && (
                    <Badge
                      variant="outline"
                      className={cn('text-[10px] px-1.5 py-0', TASK_COMPLEXITY_COLORS[task.metadata.complexity])}
                    >
                      {TASK_COMPLEXITY_LABELS[task.metadata.complexity]}
                    </Badge>
                  )}

                  {/* Impact */}
                  {task.metadata?.impact && (
                    <Badge
                      variant="outline"
                      className={cn('text-[10px] px-1.5 py-0', TASK_IMPACT_COLORS[task.metadata.impact])}
                    >
                      {TASK_IMPACT_LABELS[task.metadata.impact]}
                    </Badge>
                  )}

                  {/* Priority */}
                  {task.metadata?.priority && (task.metadata.priority === 'urgent' || task.metadata.priority === 'high') && (
                    <Badge
                      variant="outline"
                      className={cn('text-[10px] px-1.5 py-0', TASK_PRIORITY_COLORS[task.metadata.priority])}
                    >
                      {TASK_PRIORITY_LABELS[task.metadata.priority]}
                    </Badge>
                  )}
                </div>

                {/* Subtasks list */}
                {task.subtasks.length > 0 && (
                  <div>
                    <h4 className="text-xs font-medium text-muted-foreground mb-2">
                      Subtasks ({task.subtasks.filter(s => s.status === 'completed').length}/{task.subtasks.length})
                    </h4>
                    <ul className="space-y-1.5">
                      {task.subtasks.slice(0, 5).map((subtask) => (
                        <li
                          key={subtask.id}
                          className="flex items-center gap-2 text-sm"
                        >
                          <div
                            className={cn(
                              'w-2 h-2 rounded-full shrink-0',
                              subtask.status === 'completed' && 'bg-success',
                              subtask.status === 'in_progress' && 'bg-info',
                              subtask.status === 'failed' && 'bg-destructive',
                              subtask.status === 'pending' && 'bg-muted'
                            )}
                          />
                          <span className={cn(
                            'truncate',
                            subtask.status === 'completed' && 'text-muted-foreground line-through'
                          )}>
                            {subtask.title || t('subtasks.untitled')}
                          </span>
                        </li>
                      ))}
                      {task.subtasks.length > 5 && (
                        <li className="text-xs text-muted-foreground pl-4">
                          +{task.subtasks.length - 5} more...
                        </li>
                      )}
                    </ul>
                  </div>
                )}

                {/* View details button */}
                <div className="pt-2">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={(e) => {
                      e.stopPropagation();
                      onClick();
                    }}
                    className="text-xs"
                  >
                    <ExternalLink className="h-3 w-3 mr-1.5" />
                    {t('actions.view')}
                  </Button>
                </div>
              </div>
            </td>
          </tr>
        </CollapsibleContent>
      </div>
    </Collapsible>
  );
}, taskTableRowPropsAreEqual);

export default TaskTableRow;
