import { useMemo, useCallback, memo } from 'react';
import { useTranslation } from 'react-i18next';
import { Inbox } from 'lucide-react';
import { ScrollArea } from './ui/scroll-area';
import { TaskTableRow } from './TaskTableRow';
import { cn } from '../lib/utils';
import { persistTaskStatus } from '../stores/task-store';
import type { Task, TaskStatus } from '../../shared/types';

export interface TaskTableViewProps {
  tasks: Task[];
  onTaskClick: (task: Task) => void;
}

/**
 * Compare two tasks arrays for meaningful changes.
 * Returns true if tasks are equivalent (should skip re-render).
 */
function tasksAreEquivalent(prevTasks: Task[], nextTasks: Task[]): boolean {
  if (prevTasks.length !== nextTasks.length) return false;
  if (prevTasks === nextTasks) return true;

  // Compare by ID and fields that affect rendering
  for (let i = 0; i < prevTasks.length; i++) {
    const prev = prevTasks[i];
    const next = nextTasks[i];
    if (
      prev.id !== next.id ||
      prev.status !== next.status ||
      prev.title !== next.title ||
      prev.updatedAt !== next.updatedAt ||
      prev.executionProgress?.phase !== next.executionProgress?.phase ||
      prev.metadata?.category !== next.metadata?.category ||
      prev.metadata?.archivedAt !== next.metadata?.archivedAt
    ) {
      return false;
    }
  }
  return true;
}

/**
 * Custom comparator for TaskTableView memo.
 */
function taskTableViewPropsAreEqual(
  prevProps: TaskTableViewProps,
  nextProps: TaskTableViewProps
): boolean {
  if (prevProps.onTaskClick !== nextProps.onTaskClick) return false;
  return tasksAreEquivalent(prevProps.tasks, nextProps.tasks);
}

/**
 * TaskTableView - A Jira-style table view component for displaying tasks.
 * Features expandable rows (using TaskTableRow) that show full task details inline.
 * Supports multiple rows being expanded simultaneously.
 */
export const TaskTableView = memo(function TaskTableView({
  tasks,
  onTaskClick,
}: TaskTableViewProps) {
  const { t } = useTranslation(['tasks', 'common']);

  // Handle status change for a task
  const handleStatusChange = useCallback(async (taskId: string, newStatus: TaskStatus) => {
    await persistTaskStatus(taskId, newStatus);
  }, []);

  // Create stable onClick handlers for each task to prevent unnecessary re-renders
  const onClickHandlers = useMemo(() => {
    const handlers = new Map<string, () => void>();
    tasks.forEach((task) => {
      handlers.set(task.id, () => onTaskClick(task));
    });
    return handlers;
  }, [tasks, onTaskClick]);

  // Create stable onStatusChange handlers for each task
  const onStatusChangeHandlers = useMemo(() => {
    const handlers = new Map<string, (newStatus: TaskStatus) => void>();
    tasks.forEach((task) => {
      handlers.set(task.id, (newStatus: TaskStatus) => handleStatusChange(task.id, newStatus));
    });
    return handlers;
  }, [tasks, handleStatusChange]);

  // Memoize table rows to prevent recreation on every render
  const tableRows = useMemo(() => {
    if (tasks.length === 0) return null;
    return tasks.map((task) => (
      <TaskTableRow
        key={task.id}
        task={task}
        onClick={onClickHandlers.get(task.id)!}
        onStatusChange={onStatusChangeHandlers.get(task.id)}
      />
    ));
  }, [tasks, onClickHandlers, onStatusChangeHandlers]);

  return (
    <div className="flex h-full flex-col">
      <ScrollArea className="flex-1">
        <div className="p-6">
          <div className="rounded-xl border border-border bg-card/50 backdrop-blur-sm overflow-hidden">
            <table className="w-full">
              <thead>
                <tr className="border-b border-border bg-muted/30">
                  {/* Expand/Collapse column */}
                  <th className="w-10 px-3 py-3 text-left">
                    <span className="sr-only">{t('common:accessibility.expand')}</span>
                  </th>
                  {/* Title */}
                  <th className="px-3 py-3 text-left">
                    <span className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
                      {t('table.columns.title')}
                    </span>
                  </th>
                  {/* Status */}
                  <th className="px-3 py-3 text-left">
                    <span className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
                      {t('table.columns.status')}
                    </span>
                  </th>
                  {/* Category/Type */}
                  <th className="px-3 py-3 text-left">
                    <span className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
                      {t('table.columns.category')}
                    </span>
                  </th>
                  {/* Progress */}
                  <th className="px-3 py-3 text-left">
                    <span className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
                      {t('execution.labels.progress')}
                    </span>
                  </th>
                  {/* Updated */}
                  <th className="px-3 py-3 text-left">
                    <span className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
                      {t('table.columns.updatedAt')}
                    </span>
                  </th>
                  {/* Actions */}
                  <th className="px-3 py-3 text-left">
                    <span className="sr-only">{t('common:accessibility.actions')}</span>
                  </th>
                </tr>
              </thead>
              <tbody>
                {tasks.length === 0 ? (
                  <tr>
                    <td colSpan={7} className="px-6 py-16">
                      <div className="flex flex-col items-center justify-center text-center">
                        <Inbox className="h-10 w-10 text-muted-foreground/50 mb-3" />
                        <h3 className="text-sm font-medium text-foreground mb-1">
                          {t('table.empty.title')}
                        </h3>
                        <p className="text-xs text-muted-foreground">
                          {t('table.empty.description')}
                        </p>
                      </div>
                    </td>
                  </tr>
                ) : (
                  tableRows
                )}
              </tbody>
            </table>
          </div>
        </div>
      </ScrollArea>
    </div>
  );
}, taskTableViewPropsAreEqual);

export default TaskTableView;
