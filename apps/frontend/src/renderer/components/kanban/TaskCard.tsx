import { useState, useEffect, useRef, useCallback, memo, useMemo } from 'react';
import { useTranslation } from 'react-i18next';
import { Play, Square, Clock, Zap, Target, Shield, Gauge, Palette, FileCode, Bug, Wrench, Loader2, AlertTriangle, RotateCcw, Archive, GitPullRequest, MoreVertical, ExternalLink } from 'lucide-react';
import { PRStatusBadge } from './PRStatusBadge';
import { PRActionButtons } from './PRActionButtons';
import { PRConfirmDialog, type PRActionType } from './PRConfirmDialog';
import { Card, CardContent } from '../ui/card';
import { Badge } from '../ui/badge';
import { Button } from '../ui/button';
import { Checkbox } from '../ui/checkbox';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '../ui/dropdown-menu';
import { cn, formatRelativeTime, sanitizeMarkdownForDisplay } from '../../lib/utils';
import { useToast } from '../../hooks/use-toast';
import { PhaseProgressIndicator } from './PhaseProgressIndicator';
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
  JSON_ERROR_PREFIX,
  JSON_ERROR_TITLE_SUFFIX
} from '../../../shared/constants';
import { startTask, stopTask, checkTaskRunning, recoverStuckTask, isIncompleteHumanReview, archiveTasks } from '../../stores/task-store';
import { useProjectStore } from '../../stores/project-store';
import type { Task, TaskCategory, ReviewReason, TaskStatus } from '../../../shared/types';

// Category icon mapping
const CategoryIcon: Record<TaskCategory, typeof Zap> = {
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

// Phases where stuck detection should be skipped (terminal states + initial planning)
// Defined outside component to avoid recreation on every render
const STUCK_CHECK_SKIP_PHASES = ['complete', 'failed', 'planning'] as const;

function shouldSkipStuckCheck(phase: string | undefined): boolean {
  return STUCK_CHECK_SKIP_PHASES.includes(phase as typeof STUCK_CHECK_SKIP_PHASES[number]);
}

interface TaskCardProps {
  task: Task;
  onClick: () => void;
  onStatusChange?: (newStatus: TaskStatus) => unknown;
  // Optional selectable mode props for multi-selection
  isSelectable?: boolean;
  isSelected?: boolean;
  onToggleSelect?: () => void;
  // Compact mode - shows minimal info (title, status, category, progress, menu)
  compact?: boolean;
}

// Custom comparator for React.memo - only re-render when relevant task data changes
function taskCardPropsAreEqual(prevProps: TaskCardProps, nextProps: TaskCardProps): boolean {
  const prevTask = prevProps.task;
  const nextTask = nextProps.task;

  // Fast path: same reference (include selectable and compact props)
  if (
    prevTask === nextTask &&
    prevProps.onClick === nextProps.onClick &&
    prevProps.onStatusChange === nextProps.onStatusChange &&
    prevProps.isSelectable === nextProps.isSelectable &&
    prevProps.isSelected === nextProps.isSelected &&
    prevProps.onToggleSelect === nextProps.onToggleSelect &&
    prevProps.compact === nextProps.compact
  ) {
    return true;
  }

  // Check selectable and compact props first (cheap comparison)
  if (
    prevProps.isSelectable !== nextProps.isSelectable ||
    prevProps.isSelected !== nextProps.isSelected ||
    prevProps.compact !== nextProps.compact
  ) {
    return false;
  }

  // Compare only the fields that affect rendering
  const isEqual = (
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
    prevTask.metadata?.archivedAt === nextTask.metadata?.archivedAt &&
    prevTask.metadata?.prUrl === nextTask.metadata?.prUrl &&
    prevTask.metadata?.prStatus?.state === nextTask.metadata?.prStatus?.state &&
    prevTask.metadata?.prStatus?.reviewDecision === nextTask.metadata?.prStatus?.reviewDecision &&
    prevTask.metadata?.prStatus?.ciStatus === nextTask.metadata?.prStatus?.ciStatus &&
    prevTask.metadata?.prStatus?.mergeable === nextTask.metadata?.prStatus?.mergeable &&
    // Check if any subtask statuses changed (compare all subtasks)
    prevTask.subtasks.every((s, i) => s.status === nextTask.subtasks[i]?.status)
  );

  // Only log when actually re-rendering (reduces noise significantly)
  if (window.DEBUG && !isEqual) {
    const changes: string[] = [];
    if (prevTask.status !== nextTask.status) changes.push(`status: ${prevTask.status} -> ${nextTask.status}`);
    if (prevTask.executionProgress?.phase !== nextTask.executionProgress?.phase) {
      changes.push(`phase: ${prevTask.executionProgress?.phase} -> ${nextTask.executionProgress?.phase}`);
    }
    if (prevTask.subtasks.length !== nextTask.subtasks.length) {
      changes.push(`subtasks: ${prevTask.subtasks.length} -> ${nextTask.subtasks.length}`);
    }
    console.log(`[TaskCard] Re-render: ${prevTask.id} | ${changes.join(', ') || 'other fields'}`);
  }

  return isEqual;
}

export const TaskCard = memo(function TaskCard({
  task,
  onClick,
  onStatusChange,
  isSelectable,
  isSelected,
  onToggleSelect,
  compact
}: TaskCardProps) {
  const { t } = useTranslation(['tasks', 'errors']);
  const { toast } = useToast();
  const selectedProjectId = useProjectStore((state) => state.selectedProjectId);
  const [isStuck, setIsStuck] = useState(false);
  const [isRecovering, setIsRecovering] = useState(false);
  const stuckCheckRef = useRef<{ timeout: NodeJS.Timeout | null; interval: NodeJS.Timeout | null }>({
    timeout: null,
    interval: null
  });

  // PR action dialog state
  const [showPRDialog, setShowPRDialog] = useState(false);
  const [prActionType, setPRActionType] = useState<PRActionType>('approve');
  const [isApprovingPR, setIsApprovingPR] = useState(false);
  const [isRequestingChanges, setIsRequestingChanges] = useState(false);
  const [isMergingPR, setIsMergingPR] = useState(false);

  const isRunning = task.status === 'in_progress';
  const executionPhase = task.executionProgress?.phase;
  const hasActiveExecution = executionPhase && executionPhase !== 'idle' && executionPhase !== 'complete' && executionPhase !== 'failed';

  // Check if task is in human_review but has no completed subtasks (crashed/incomplete)
  const isIncomplete = isIncompleteHumanReview(task);

  // Memoize expensive computations to avoid running on every render
  // Truncate description for card display - full description shown in modal
  // Handle JSON error tasks with i18n
  const sanitizedDescription = useMemo(() => {
    if (!task.description) return null;
    // Check for JSON error marker and use i18n
    if (task.description.startsWith(JSON_ERROR_PREFIX)) {
      const errorMessage = task.description.slice(JSON_ERROR_PREFIX.length);
      const translatedDesc = t('errors:task.jsonError.description', { error: errorMessage });
      return sanitizeMarkdownForDisplay(translatedDesc, 120);
    }
    return sanitizeMarkdownForDisplay(task.description, 120);
  }, [task.description, t]);

  // Memoize title with JSON error suffix handling
  const displayTitle = useMemo(() => {
    if (task.title.endsWith(JSON_ERROR_TITLE_SUFFIX)) {
      const baseName = task.title.slice(0, -JSON_ERROR_TITLE_SUFFIX.length);
      return `${baseName} ${t('errors:task.jsonError.titleSuffix')}`;
    }
    return task.title;
  }, [task.title, t]);

  // Memoize relative time (recalculates only when updatedAt changes)
  const relativeTime = useMemo(
    () => formatRelativeTime(task.updatedAt),
    [task.updatedAt]
  );

  // Memoize status menu items to avoid recreating on every render
  const statusMenuItems = useMemo(() => {
    if (!onStatusChange) return null;
    return TASK_STATUS_COLUMNS.filter(status => status !== task.status).map((status) => (
      <DropdownMenuItem
        key={status}
        onClick={() => onStatusChange(status)}
      >
        {t(TASK_STATUS_LABELS[status])}
      </DropdownMenuItem>
    ));
  }, [task.status, onStatusChange, t]);

  // Memoized stuck check function to avoid recreating on every render
  const performStuckCheck = useCallback(() => {
    const currentPhase = task.executionProgress?.phase;
    if (shouldSkipStuckCheck(currentPhase)) {
      if (window.DEBUG) {
        console.log(`[TaskCard] Stuck check skipped for ${task.id} - phase is '${currentPhase}' (planning/terminal phases don't need process verification)`);
      }
      setIsStuck(false);
      return;
    }

    // Use requestIdleCallback for non-blocking check when available
    const doCheck = () => {
      checkTaskRunning(task.id).then((actuallyRunning) => {
        // Double-check the phase again in case it changed while waiting
        const latestPhase = task.executionProgress?.phase;
        if (shouldSkipStuckCheck(latestPhase)) {
          setIsStuck(false);
        } else {
          setIsStuck(!actuallyRunning);
        }
      });
    };

    if ('requestIdleCallback' in window) {
      (window as Window & { requestIdleCallback: (cb: () => void) => void }).requestIdleCallback(doCheck);
    } else {
      doCheck();
    }
  }, [task.id, task.executionProgress?.phase]);

  // Check if task is stuck (status says in_progress but no actual process)
  // Add a longer grace period to avoid false positives during process spawn
  useEffect(() => {
    if (!isRunning) {
      setIsStuck(false);
      // Clear any pending checks
      if (stuckCheckRef.current.timeout) {
        clearTimeout(stuckCheckRef.current.timeout);
        stuckCheckRef.current.timeout = null;
      }
      if (stuckCheckRef.current.interval) {
        clearInterval(stuckCheckRef.current.interval);
        stuckCheckRef.current.interval = null;
      }
      return;
    }

    // Initial check after 5s grace period (increased from 2s)
    stuckCheckRef.current.timeout = setTimeout(performStuckCheck, 5000);

    // Periodic re-check every 30 seconds (reduced frequency from 15s)
    stuckCheckRef.current.interval = setInterval(performStuckCheck, 30000);

    return () => {
      if (stuckCheckRef.current.timeout) {
        clearTimeout(stuckCheckRef.current.timeout);
      }
      if (stuckCheckRef.current.interval) {
        clearInterval(stuckCheckRef.current.interval);
      }
    };
  }, [task.id, isRunning, performStuckCheck]);

  // Add visibility change handler to re-validate on focus (debounced)
  useEffect(() => {
    let debounceTimeout: NodeJS.Timeout | null = null;

    const handleVisibilityChange = () => {
      if (document.visibilityState === 'visible' && isRunning) {
        // Debounce visibility checks to avoid rapid re-checks
        if (debounceTimeout) clearTimeout(debounceTimeout);
        debounceTimeout = setTimeout(performStuckCheck, 500);
      }
    };

    document.addEventListener('visibilitychange', handleVisibilityChange);
    return () => {
      document.removeEventListener('visibilitychange', handleVisibilityChange);
      if (debounceTimeout) clearTimeout(debounceTimeout);
    };
  }, [isRunning, performStuckCheck]);

  const handleStartStop = (e: React.MouseEvent) => {
    e.stopPropagation();
    if (isRunning && !isStuck) {
      stopTask(task.id);
    } else {
      startTask(task.id);
    }
  };

  const handleRecover = async (e: React.MouseEvent) => {
    e.stopPropagation();
    setIsRecovering(true);
    // Auto-restart the task after recovery (no need to click Start again)
    const result = await recoverStuckTask(task.id, { autoRestart: true });
    if (result.success) {
      setIsStuck(false);
    }
    setIsRecovering(false);
  };

  const handleArchive = async (e: React.MouseEvent) => {
    e.stopPropagation();
    const result = await archiveTasks(task.projectId, [task.id]);
    if (!result.success) {
      console.error('[TaskCard] Failed to archive task:', task.id, result.error);
    }
  };

  const handleViewPR = (e: React.MouseEvent) => {
    e.stopPropagation();
    if (task.metadata?.prUrl && window.electronAPI?.openExternal) {
      window.electronAPI.openExternal(task.metadata.prUrl);
    }
  };

  // PR action handlers - show confirmation dialogs
  const handleApprovePR = useCallback(() => {
    if (!selectedProjectId || !task.metadata?.prStatus?.prNumber) return;
    setPRActionType('approve');
    setShowPRDialog(true);
  }, [selectedProjectId, task.metadata?.prStatus?.prNumber]);

  const handleRequestChangesPR = useCallback(() => {
    if (!selectedProjectId || !task.metadata?.prStatus?.prNumber) return;
    setPRActionType('request_changes');
    setShowPRDialog(true);
  }, [selectedProjectId, task.metadata?.prStatus?.prNumber]);

  const handleMergePR = useCallback(() => {
    if (!selectedProjectId || !task.metadata?.prStatus?.prNumber) return;
    setPRActionType('merge');
    setShowPRDialog(true);
  }, [selectedProjectId, task.metadata?.prStatus?.prNumber]);

  // Confirmed PR action handlers - actual API calls with error handling
  const handleConfirmPRAction = useCallback(async (comment?: string) => {
    if (!selectedProjectId || !task.metadata?.prStatus?.prNumber) return;

    const prNumber = task.metadata.prStatus.prNumber;

    try {
      if (prActionType === 'approve') {
        setIsApprovingPR(true);
        const result = await window.electronAPI.github.postPRReview(
          selectedProjectId,
          prNumber,
          undefined, // selectedFindingIds - approve all
          { forceApprove: true } // Force approve without findings
        );

        if (result) {
          toast({
            title: t('common:prReview.approved'),
            duration: 3000,
          });
        } else {
          toast({
            title: t('errors:generic'),
            variant: 'destructive',
            duration: 3000,
          });
        }
      } else if (prActionType === 'request_changes') {
        setIsRequestingChanges(true);
        const result = await window.electronAPI.github.requestChanges(
          selectedProjectId,
          prNumber,
          comment || t('common:prReview.actions.requestChanges')
        );

        if (result.success) {
          toast({
            title: t('common:prReview.actions.changesRequested'),
            duration: 3000,
          });
        } else {
          toast({
            title: result.error || t('errors:generic'),
            variant: 'destructive',
            duration: 3000,
          });
        }
      } else if (prActionType === 'merge') {
        setIsMergingPR(true);
        const result = await window.electronAPI.github.mergePR(
          selectedProjectId,
          prNumber,
          'squash' // Default merge method
        );

        if (result) {
          toast({
            title: t('common:prReview.actions.merged'),
            duration: 3000,
          });
        } else {
          toast({
            title: t('errors:generic'),
            variant: 'destructive',
            duration: 3000,
          });
        }
      }
    } catch (error) {
      console.error('[TaskCard] Failed to perform PR action:', prActionType, error);
      toast({
        title: t('errors:generic'),
        variant: 'destructive',
        duration: 3000,
      });
    } finally {
      setIsApprovingPR(false);
      setIsRequestingChanges(false);
      setIsMergingPR(false);
    }
  }, [selectedProjectId, task.metadata?.prStatus?.prNumber, prActionType, toast, t]);

  const getStatusBadgeVariant = (status: string) => {
    switch (status) {
      case 'in_progress':
        return 'info';
      case 'ai_review':
        return 'warning';
      case 'human_review':
        return 'purple';
      case 'done':
        return 'success';
      default:
        return 'secondary';
    }
  };

  const getStatusLabel = (status: string) => {
    switch (status) {
      case 'in_progress':
        return t('labels.running');
      case 'ai_review':
        return t('labels.aiReview');
      case 'human_review':
        return t('labels.needsReview');
      case 'done':
        return t('status.complete');
      default:
        return t('labels.pending');
    }
  };

  const getReviewReasonLabel = (reason?: ReviewReason): { label: string; variant: 'success' | 'destructive' | 'warning' } | null => {
    if (!reason) return null;
    switch (reason) {
      case 'completed':
        return { label: t('reviewReason.completed'), variant: 'success' };
      case 'errors':
        return { label: t('reviewReason.hasErrors'), variant: 'destructive' };
      case 'qa_rejected':
        return { label: t('reviewReason.qaIssues'), variant: 'warning' };
      case 'plan_review':
        return { label: t('reviewReason.approvePlan'), variant: 'warning' };
      default:
        return null;
    }
  };

  const reviewReasonInfo = task.status === 'human_review' ? getReviewReasonLabel(task.reviewReason) : null;

  const isArchived = !!task.metadata?.archivedAt;

  return (
    <Card
      className={cn(
        'card-surface task-card-enhanced cursor-pointer',
        isRunning && !isStuck && 'ring-2 ring-primary border-primary task-running-pulse',
        isStuck && 'ring-2 ring-warning border-warning task-stuck-pulse',
        isArchived && 'opacity-60 hover:opacity-80',
        isSelectable && isSelected && 'ring-2 ring-ring border-ring bg-accent/10'
      )}
      onClick={onClick}
    >
      <CardContent className={cn('p-4', compact && 'p-3')}>
        <div className={isSelectable ? 'flex gap-3' : undefined}>
          {/* Checkbox for selectable mode - stops event propagation */}
          {isSelectable && (
            <div className="flex-shrink-0 pt-0.5">
              <Checkbox
                checked={isSelected}
                onCheckedChange={onToggleSelect}
                onClick={(e) => e.stopPropagation()}
                aria-label={t('tasks:actions.selectTask', { title: displayTitle })}
              />
            </div>
          )}

          <div className={isSelectable ? 'flex-1 min-w-0' : undefined}>
            {/* Compact mode: Header with title and menu button in same row */}
            {compact ? (
              <div className="flex items-start justify-between gap-2">
                <h3
                  className="font-semibold text-sm text-foreground line-clamp-1 leading-snug flex-1 min-w-0"
                  title={displayTitle}
                >
                  {displayTitle}
                </h3>
                {/* Menu button at top-right in compact mode */}
                {statusMenuItems && (
                  <DropdownMenu>
                    <DropdownMenuTrigger asChild>
                      <Button
                        variant="ghost"
                        size="sm"
                        className="h-6 w-6 p-0 flex-shrink-0 -mt-0.5 -mr-1"
                        onClick={(e) => e.stopPropagation()}
                        aria-label={t('actions.taskActions')}
                      >
                        <MoreVertical className="h-3.5 w-3.5" />
                      </Button>
                    </DropdownMenuTrigger>
                    <DropdownMenuContent align="end" onClick={(e) => e.stopPropagation()}>
                      <DropdownMenuLabel>{t('actions.moveTo')}</DropdownMenuLabel>
                      <DropdownMenuSeparator />
                      {statusMenuItems}
                    </DropdownMenuContent>
                  </DropdownMenu>
                )}
              </div>
            ) : (
              /* Full mode: Title only, menu in footer */
              <h3
                className="font-semibold text-sm text-foreground line-clamp-2 leading-snug"
                title={displayTitle}
              >
                {displayTitle}
              </h3>
            )}

        {/* Description - sanitized to handle markdown content (memoized) - hidden in compact mode */}
        {!compact && sanitizedDescription && (
          <p className="mt-2 text-xs text-muted-foreground line-clamp-2">
            {sanitizedDescription}
          </p>
        )}

        {/* Metadata badges - in compact mode show only essential badges */}
        {(task.metadata || isStuck || isIncomplete || hasActiveExecution || reviewReasonInfo) && (
          <div className={cn('mt-2.5 flex flex-wrap gap-1.5', compact && 'mt-2')}>
            {/* Stuck indicator - highest priority - show in both modes */}
            {isStuck && (
              <Badge
                variant="outline"
                className="text-[10px] px-1.5 py-0.5 flex items-center gap-1 bg-warning/10 text-warning border-warning/30 badge-priority-urgent"
              >
                <AlertTriangle className="h-2.5 w-2.5" />
                {t('labels.stuck')}
              </Badge>
            )}
            {/* Incomplete indicator - task in human_review but no subtasks completed - show in both modes */}
            {isIncomplete && !isStuck && (
              <Badge
                variant="outline"
                className="text-[10px] px-1.5 py-0.5 flex items-center gap-1 bg-orange-500/10 text-orange-400 border-orange-500/30"
              >
                <AlertTriangle className="h-2.5 w-2.5" />
                {t('labels.incomplete')}
              </Badge>
            )}
            {/* Archived indicator - task has been released - hidden in compact mode */}
            {!compact && task.metadata?.archivedAt && (
              <Badge
                variant="outline"
                className="text-[10px] px-1.5 py-0.5 flex items-center gap-1 bg-muted text-muted-foreground border-border"
              >
                <Archive className="h-2.5 w-2.5" />
                {t('status.archived')}
              </Badge>
            )}
            {/* PR status badge - shown when task has a linked PR with status - hidden in compact mode */}
            {!compact && task.metadata?.prStatus && (
              <PRStatusBadge status={task.metadata.prStatus} compact />
            )}
            {/* Execution phase badge - shown when actively running - show in both modes */}
            {hasActiveExecution && executionPhase && !isStuck && !isIncomplete && (
              <Badge
                variant="outline"
                className={cn(
                  'text-[10px] px-1.5 py-0.5 flex items-center gap-1',
                  EXECUTION_PHASE_BADGE_COLORS[executionPhase]
                )}
              >
                <Loader2 className="h-2.5 w-2.5 animate-spin" />
                {EXECUTION_PHASE_LABELS[executionPhase]}
              </Badge>
            )}
             {/* Status badge - hide when execution phase badge is showing - show in both modes */}
             {!hasActiveExecution && (
               <>
                  {task.status === 'done' ? (
                    <Badge
                      variant={getStatusBadgeVariant(task.status)}
                      className="text-[10px] px-1.5 py-0.5"
                    >
                      {getStatusLabel(task.status)}
                    </Badge>
                  ) : (
                   <Badge
                     variant={isStuck ? 'warning' : isIncomplete ? 'warning' : getStatusBadgeVariant(task.status)}
                     className="text-[10px] px-1.5 py-0.5"
                   >
                     {isStuck ? t('labels.needsRecovery') : isIncomplete ? t('labels.needsResume') : getStatusLabel(task.status)}
                   </Badge>
                 )}
               </>
             )}
            {/* Review reason badge - explains why task needs human review - hidden in compact mode */}
            {!compact && reviewReasonInfo && !isStuck && !isIncomplete && (
              <Badge
                variant={reviewReasonInfo.variant}
                className="text-[10px] px-1.5 py-0.5"
              >
                {reviewReasonInfo.label}
              </Badge>
            )}
            {/* Category badge with icon - show in both modes (type tag) */}
            {task.metadata?.category && (
              <Badge
                variant="outline"
                className={cn('text-[10px] px-1.5 py-0', TASK_CATEGORY_COLORS[task.metadata.category])}
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
            {/* Impact badge - high visibility for important tasks - hidden in compact mode */}
            {!compact && task.metadata?.impact && (task.metadata.impact === 'high' || task.metadata.impact === 'critical') && (
              <Badge
                variant="outline"
                className={cn('text-[10px] px-1.5 py-0', TASK_IMPACT_COLORS[task.metadata.impact])}
              >
                {TASK_IMPACT_LABELS[task.metadata.impact]}
              </Badge>
            )}
            {/* Complexity badge - hidden in compact mode */}
            {!compact && task.metadata?.complexity && (
              <Badge
                variant="outline"
                className={cn('text-[10px] px-1.5 py-0', TASK_COMPLEXITY_COLORS[task.metadata.complexity])}
              >
                {TASK_COMPLEXITY_LABELS[task.metadata.complexity]}
              </Badge>
            )}
            {/* Priority badge - only show urgent/high - hidden in compact mode */}
            {!compact && task.metadata?.priority && (task.metadata.priority === 'urgent' || task.metadata.priority === 'high') && (
              <Badge
                variant="outline"
                className={cn('text-[10px] px-1.5 py-0', TASK_PRIORITY_COLORS[task.metadata.priority])}
              >
                {TASK_PRIORITY_LABELS[task.metadata.priority]}
              </Badge>
            )}
            {/* Security severity - always show - hidden in compact mode */}
            {!compact && task.metadata?.securitySeverity && (
              <Badge
                variant="outline"
                className={cn('text-[10px] px-1.5 py-0', TASK_IMPACT_COLORS[task.metadata.securitySeverity])}
              >
                {task.metadata.securitySeverity} {t('metadata.severity')}
              </Badge>
            )}
          </div>
        )}

        {/* Progress section - Phase-aware with animations - show in both modes */}
        {(task.subtasks.length > 0 || hasActiveExecution || isRunning || isStuck) && (
          <div className={cn('mt-4', compact && 'mt-2.5')}>
            <PhaseProgressIndicator
              phase={executionPhase}
              subtasks={task.subtasks}
              phaseProgress={task.executionProgress?.phaseProgress}
              isStuck={isStuck}
              isRunning={isRunning}
            />
          </div>
        )}

        {/* Footer - hidden in compact mode (menu is at top-right) */}
        {!compact && (
          <div className="mt-4 flex items-center justify-between">
            <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
              <Clock className="h-3 w-3" />
              <span>{relativeTime}</span>
            </div>

          <div className="flex items-center gap-1.5">
            {/* Action buttons */}
            {isStuck ? (
              <Button
                variant="warning"
                size="sm"
                className="h-7 px-2.5"
                onClick={handleRecover}
                disabled={isRecovering}
              >
                {isRecovering ? (
                  <>
                    <Loader2 className="mr-1.5 h-3 w-3 animate-spin" />
                    {t('labels.recovering')}
                  </>
                ) : (
                  <>
                    <RotateCcw className="mr-1.5 h-3 w-3" />
                    {t('actions.recover')}
                  </>
                )}
              </Button>
            ) : isIncomplete ? (
              <Button
                variant="default"
                size="sm"
                className="h-7 px-2.5"
                onClick={handleStartStop}
              >
                <Play className="mr-1.5 h-3 w-3" />
                {t('actions.resume')}
              </Button>
            ) : task.metadata?.prStatus && task.metadata?.prUrl && selectedProjectId ? (
              <div className="flex gap-1 items-center">
                <PRActionButtons
                  prNumber={task.metadata.prStatus.prNumber}
                  prState={task.metadata.prStatus.state}
                  prHtmlUrl={task.metadata.prUrl}
                  projectId={selectedProjectId}
                  isApproved={task.metadata.prStatus.reviewDecision === 'approved'}
                  isMergeable={task.metadata.prStatus.mergeable === 'MERGEABLE'}
                  onApprove={handleApprovePR}
                  onRequestChanges={handleRequestChangesPR}
                  onMerge={handleMergePR}
                  disabled={isApprovingPR || isRequestingChanges || isMergingPR}
                  className="text-xs"
                />
                {!task.metadata?.archivedAt && (
                  <Button
                    variant="ghost"
                    size="sm"
                    className="h-7 px-2 cursor-pointer"
                    onClick={handleArchive}
                    title={t('tooltips.archiveTask')}
                  >
                    <Archive className="h-3 w-3" />
                  </Button>
                )}
              </div>
            ) : task.status === 'done' && task.metadata?.prUrl ? (
              <div className="flex gap-1">
                {task.metadata?.prUrl && (
                  <Button
                    variant="ghost"
                    size="sm"
                    className="h-7 px-2 cursor-pointer"
                    onClick={handleViewPR}
                    title={t('tooltips.viewPR')}
                  >
                    <GitPullRequest className="h-3 w-3" />
                  </Button>
                )}
                {!task.metadata?.archivedAt && (
                  <Button
                    variant="ghost"
                    size="sm"
                    className="h-7 px-2 cursor-pointer"
                    onClick={handleArchive}
                    title={t('tooltips.archiveTask')}
                  >
                    <Archive className="h-3 w-3" />
                  </Button>
                )}
              </div>
            ) : task.status === 'done' && !task.metadata?.archivedAt ? (
              <Button
                variant="ghost"
                size="sm"
                className="h-7 px-2.5 hover:bg-muted-foreground/10"
                onClick={handleArchive}
                title={t('tooltips.archiveTask')}
              >
                <Archive className="mr-1.5 h-3 w-3" />
                {t('actions.archive')}
              </Button>
            ) : (task.status === 'backlog' || task.status === 'in_progress') && (
              <Button
                variant={isRunning ? 'destructive' : 'default'}
                size="sm"
                className="h-7 px-2.5"
                onClick={handleStartStop}
              >
                {isRunning ? (
                  <>
                    <Square className="mr-1.5 h-3 w-3" />
                    {t('actions.stop')}
                  </>
                ) : (
                  <>
                    <Play className="mr-1.5 h-3 w-3" />
                    {t('actions.start')}
                  </>
                )}
              </Button>
            )}

              {/* Move to menu for keyboard accessibility */}
              {statusMenuItems && (
                <DropdownMenu>
                  <DropdownMenuTrigger asChild>
                    <Button
                      variant="ghost"
                      size="sm"
                      className="h-7 w-7 p-0"
                      onClick={(e) => e.stopPropagation()}
                      aria-label={t('actions.taskActions')}
                    >
                      <MoreVertical className="h-4 w-4" />
                    </Button>
                  </DropdownMenuTrigger>
                  <DropdownMenuContent align="end" onClick={(e) => e.stopPropagation()}>
                    <DropdownMenuLabel>{t('actions.moveTo')}</DropdownMenuLabel>
                    <DropdownMenuSeparator />
                    {statusMenuItems}
                  </DropdownMenuContent>
                </DropdownMenu>
              )}
            </div>
          </div>
        )}
        {/* Close content wrapper for selectable mode */}
        </div>
        {/* Close flex container for selectable mode */}
        </div>
      </CardContent>

      {/* PR Confirmation Dialog */}
      {task.metadata?.prStatus?.prNumber && (
        <PRConfirmDialog
          open={showPRDialog}
          onOpenChange={setShowPRDialog}
          actionType={prActionType}
          prNumber={task.metadata.prStatus.prNumber}
          prTitle={task.title}
          onConfirm={handleConfirmPRAction}
          mergeMethod="squash"
        />
      )}
    </Card>
  );
}, taskCardPropsAreEqual);
