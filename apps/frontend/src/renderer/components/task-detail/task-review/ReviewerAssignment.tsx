import { useTranslation } from 'react-i18next';
import { UserCheck, User, CheckCircle, X, Plus } from 'lucide-react';
import { cn } from '../../../lib/utils';
import { Button } from '../../ui/button';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue
} from '../../ui/select';
import type { ReviewerAssignment as ReviewerAssignmentType, ReviewerInfo } from '../../../../shared/types';

interface ReviewerAssignmentProps {
  /** Reviewer assignment data */
  assignment?: ReviewerAssignmentType;
  /** Available reviewers to assign (name/email list) */
  availableReviewers?: Array<{ id: string; name: string; email?: string }>;
  /** Callback when a reviewer is added */
  onAddReviewer?: (reviewerId: string) => void;
  /** Callback when a reviewer is removed */
  onRemoveReviewer?: (reviewerId: string) => void;
  /** Callback when a reviewer approves */
  onApprove?: (reviewerId: string) => void;
  /** Disable interaction */
  disabled?: boolean;
}

/**
 * Displays reviewer assignment status with interactive controls for adding/removing reviewers
 * Shows approval status indicators for each assigned reviewer
 */
export function ReviewerAssignment({
  assignment,
  availableReviewers = [],
  onAddReviewer,
  onRemoveReviewer,
  onApprove,
  disabled = false
}: ReviewerAssignmentProps) {
  const { t } = useTranslation(['common']);

  // Don't render anything if no assignment provided
  if (!assignment) {
    return null;
  }

  const { required, actual, allApproved } = assignment;

  // Determine if a reviewer is required
  const isRequired = (reviewerId: string): boolean => {
    return required.some(r => r.id === reviewerId);
  };

  // Get reviewers who are not yet assigned
  const unassignedReviewers = availableReviewers.filter(
    av => !actual.some(a => a.id === av.id)
  );

  return (
    <div className="rounded-xl border border-border bg-background/50 p-4">
      {/* Header */}
      <div className="flex items-center justify-between mb-3">
        <h3 className="font-medium text-sm text-foreground flex items-center gap-2">
          {allApproved ? (
            <CheckCircle className="h-4 w-4 text-success" />
          ) : (
            <UserCheck className="h-4 w-4 text-muted-foreground" />
          )}
          {t('common:review.reviewers.title')}
        </h3>
        {/* Approval Status */}
        <span
          className={cn(
            'text-xs font-medium',
            allApproved ? 'text-success' : 'text-muted-foreground'
          )}
        >
          {allApproved
            ? t('common:review.reviewers.allApproved')
            : t('common:review.reviewers.requiresApproval', {
                count: required.filter(r => !r.approved).length
              })}
        </span>
      </div>

      {/* Assigned Reviewers List */}
      {actual.length > 0 ? (
        <div className="space-y-2 mb-3">
          {actual.map((reviewer) => (
            <div
              key={reviewer.id}
              className={cn(
                'flex items-center justify-between p-2.5 rounded-lg border transition-colors',
                reviewer.approved
                  ? 'border-success/30 bg-success/5'
                  : 'border-border bg-background/50'
              )}
            >
              <div className="flex items-center gap-2.5 flex-1 min-w-0">
                {/* Approval Status Icon */}
                {reviewer.approved ? (
                  <CheckCircle className="h-4 w-4 text-success flex-shrink-0" />
                ) : (
                  <User className="h-4 w-4 text-muted-foreground flex-shrink-0" />
                )}

                {/* Reviewer Info */}
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-1.5">
                    <span
                      className={cn(
                        'text-sm font-medium truncate',
                        reviewer.approved
                          ? 'text-foreground'
                          : 'text-foreground'
                      )}
                    >
                      {reviewer.name}
                    </span>
                    {isRequired(reviewer.id) && (
                      <span
                        className="text-xs text-warning flex-shrink-0"
                        title="Required reviewer"
                      >
                        *
                      </span>
                    )}
                  </div>
                  {reviewer.email && (
                    <span className="text-xs text-muted-foreground truncate block">
                      {reviewer.email}
                    </span>
                  )}
                  {reviewer.comment && (
                    <p className="text-xs text-muted-foreground italic mt-1 line-clamp-2">
                      {reviewer.comment}
                    </p>
                  )}
                </div>
              </div>

              {/* Remove Button */}
              {!disabled && onRemoveReviewer && (
                <Button
                  variant="ghost"
                  size="sm"
                  className="h-7 w-7 p-0 ml-2 flex-shrink-0"
                  onClick={() => onRemoveReviewer(reviewer.id)}
                  aria-label={t('common:review.reviewers.removeReviewer')}
                >
                  <X className="h-4 w-4" />
                </Button>
              )}
            </div>
          ))}
        </div>
      ) : (
        <div className="flex items-center gap-2 p-3 mb-3 text-sm text-muted-foreground bg-muted/20 rounded-lg">
          <User className="h-4 w-4" />
          {t('common:review.reviewers.noReviewers')}
        </div>
      )}

      {/* Add Reviewer Section */}
      {!disabled && onAddReviewer && unassignedReviewers.length > 0 && (
        <div className="flex items-center gap-2 pt-2 border-t border-border">
          <Select
            onValueChange={(value) => onAddReviewer(value)}
          >
            <SelectTrigger className="h-9 flex-1">
              <SelectValue placeholder={t('common:review.reviewers.assignPlaceholder')} />
            </SelectTrigger>
            <SelectContent>
              {unassignedReviewers.map((reviewer) => (
                <SelectItem key={reviewer.id} value={reviewer.id}>
                  <div className="flex flex-col items-start">
                    <span className="font-medium">{reviewer.name}</span>
                    {reviewer.email && (
                      <span className="text-xs text-muted-foreground">
                        {reviewer.email}
                      </span>
                    )}
                  </div>
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <Button
            variant="ghost"
            size="sm"
            className="h-9 px-2 flex-shrink-0"
            aria-label={t('common:review.reviewers.addReviewer')}
          >
            <Plus className="h-4 w-4" />
          </Button>
        </div>
      )}
    </div>
  );
}
