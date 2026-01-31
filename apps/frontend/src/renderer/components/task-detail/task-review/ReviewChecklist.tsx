import { useTranslation } from 'react-i18next';
import { CheckCircle, Circle, AlertCircle } from 'lucide-react';
import { Checkbox } from '../../ui/checkbox';
import { cn } from '../../../lib/utils';
import type { ReviewChecklist as ReviewChecklistType } from '../../../../shared/types';

interface ReviewChecklistProps {
  /** Review checklist data */
  checklist?: ReviewChecklistType;
  /** Callback when checklist item completion changes */
  onItemChange?: (itemId: string, completed: boolean) => void;
  /** Disable interaction with checkboxes */
  disabled?: boolean;
}

/**
 * Displays a review checklist with interactive checkboxes for each item
 * Shows completion status and allows marking items as complete/incomplete
 */
export function ReviewChecklist({
  checklist,
  onItemChange,
  disabled = false
}: ReviewChecklistProps) {
  const { t } = useTranslation(['common']);

  // Don't render anything if no checklist provided
  if (!checklist) {
    return null;
  }

  const { items, allComplete } = checklist;

  // Count remaining items
  const remainingCount = items.filter(item => item.required && !item.completed).length;
  const hasItems = items.length > 0;

  return (
    <div className="rounded-xl border border-border bg-background/50 p-4">
      {/* Header */}
      <div className="flex items-center justify-between mb-3">
        <h3 className="font-medium text-sm text-foreground flex items-center gap-2">
          {allComplete ? (
            <CheckCircle className="h-4 w-4 text-success" />
          ) : (
            <Circle className="h-4 w-4 text-muted-foreground" />
          )}
          {t('common:review.checklist.title')}
        </h3>
        {/* Completion Status */}
        {hasItems && (
          <span
            className={cn(
              'text-xs font-medium',
              allComplete ? 'text-success' : 'text-muted-foreground'
            )}
          >
            {allComplete
              ? t('common:review.checklist.allComplete')
              : t('common:review.checklist.incomplete', { count: remainingCount })}
          </span>
        )}
      </div>

      {/* Checklist Items */}
      {hasItems ? (
        <div className="space-y-2">
          {items.map((item) => (
            <label
              key={item.id}
              className={cn(
                'flex items-start gap-3 p-2.5 rounded-lg border transition-colors cursor-pointer',
                'hover:bg-muted/30',
                item.completed
                  ? 'border-success/30 bg-success/5'
                  : 'border-border bg-background/50',
                disabled && 'cursor-not-allowed opacity-60'
              )}
            >
              <Checkbox
                checked={item.completed}
                onCheckedChange={(checked) => {
                  if (!disabled && onItemChange) {
                    onItemChange(item.id, checked === true);
                  }
                }}
                disabled={disabled}
                className={cn(
                  'mt-0.5',
                  item.completed && 'border-success data-[state=checked]:bg-success'
                )}
                aria-label={
                  item.completed
                    ? t('common:review.checklist.itemComplete')
                    : t('common:review.checklist.itemIncomplete')
                }
              />
              <div className="flex-1 min-w-0">
                <span
                  className={cn(
                    'text-sm',
                    item.completed
                      ? 'text-muted-foreground line-through'
                      : 'text-foreground'
                  )}
                >
                  {item.label}
                </span>
                {item.required && !item.completed && (
                  <span
                    className="ml-1.5 text-xs text-warning"
                    title="Required"
                  >
                    *
                  </span>
                )}
              </div>
            </label>
          ))}
        </div>
      ) : (
        <div className="flex items-center gap-2 p-3 text-sm text-muted-foreground bg-muted/20 rounded-lg">
          <AlertCircle className="h-4 w-4" />
          {t('common:review.checklist.noItems')}
        </div>
      )}
    </div>
  );
}
