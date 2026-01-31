import { useTranslation } from 'react-i18next';
import { Clock, BarChart, AlertCircle } from 'lucide-react';
import { cn } from '../../../lib/utils';
import type { ReviewMetrics as ReviewMetricsType } from '../../../../shared/types';

interface ReviewMetricsProps {
  /** Review metrics data */
  metrics?: ReviewMetricsType;
  /** Optional className for styling */
  className?: string;
}

/**
 * Displays review cycle time metrics including cycle time, iterations,
 * time to approval, and reviewer response time
 */
export function ReviewMetrics({ metrics, className }: ReviewMetricsProps) {
  const { t } = useTranslation(['common']);

  /**
   * Format duration in milliseconds to human-readable format
   * @param ms Duration in milliseconds
   * @returns Formatted duration string
   */
  const formatDuration = (ms: number | undefined): string => {
    if (!ms || ms <= 0) return t('common:review.metrics.noData');

    const days = Math.floor(ms / (1000 * 60 * 60 * 24));
    const hours = Math.floor((ms % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60));
    const minutes = Math.floor((ms % (1000 * 60 * 60)) / (1000 * 60));

    if (days > 0) {
      return t('common:review.metrics.days', { count: days });
    } else if (hours > 0) {
      return t('common:review.metrics.hours', { count: hours });
    } else if (minutes > 0) {
      return t('common:review.metrics.minutes', { count: minutes });
    }
    return t('common:review.metrics.minutes', { count: 1 });
  };

  // Don't render anything if no metrics provided
  if (!metrics) {
    return null;
  }

  // Check if review is in progress or completed
  const isInProgress = metrics.reviewStartedAt && !metrics.approvedAt;
  const hasData =
    metrics.cycleTime ||
    metrics.iterationCount > 0 ||
    metrics.timeToApproval ||
    metrics.reviewerResponseTime;

  return (
    <div className={cn('rounded-xl border border-border bg-background/50 p-4', className)}>
      {/* Header */}
      <div className="flex items-center gap-2 mb-3">
        <BarChart className="h-4 w-4 text-info" />
        <h3 className="font-medium text-sm text-foreground">
          {t('common:review.metrics.title')}
        </h3>
      </div>

      {/* Metrics Grid */}
      {hasData ? (
        <div className="space-y-3">
          {/* Cycle Time */}
          {(metrics.cycleTime || isInProgress) && (
            <div className="flex items-center justify-between p-2.5 rounded-lg border border-border bg-background/50">
              <div className="flex items-center gap-2">
                <Clock className="h-4 w-4 text-muted-foreground" />
                <span className="text-sm text-foreground">
                  {t('common:review.metrics.cycleTime')}
                </span>
              </div>
              <span className="text-sm font-medium text-foreground tabular-nums">
                {isInProgress && !metrics.cycleTime
                  ? t('common:review.metrics.inProgress')
                  : formatDuration(metrics.cycleTime)}
              </span>
            </div>
          )}

          {/* Iteration Count */}
          {metrics.iterationCount > 0 && (
            <div className="flex items-center justify-between p-2.5 rounded-lg border border-border bg-background/50">
              <div className="flex items-center gap-2">
                <BarChart className="h-4 w-4 text-muted-foreground" />
                <span className="text-sm text-foreground">
                  {t('common:review.metrics.iterations')}
                </span>
              </div>
              <span className="text-sm font-medium text-foreground tabular-nums">
                {metrics.iterationCount}
              </span>
            </div>
          )}

          {/* Time to Approval */}
          {metrics.timeToApproval && (
            <div className="flex items-center justify-between p-2.5 rounded-lg border border-border bg-background/50">
              <div className="flex items-center gap-2">
                <Clock className="h-4 w-4 text-muted-foreground" />
                <span className="text-sm text-foreground">
                  {t('common:review.metrics.timeToApproval')}
                </span>
              </div>
              <span className="text-sm font-medium text-success tabular-nums">
                {formatDuration(metrics.timeToApproval)}
              </span>
            </div>
          )}

          {/* Reviewer Response Time */}
          {metrics.reviewerResponseTime && (
            <div className="flex items-center justify-between p-2.5 rounded-lg border border-border bg-background/50">
              <div className="flex items-center gap-2">
                <Clock className="h-4 w-4 text-muted-foreground" />
                <span className="text-sm text-foreground">
                  {t('common:review.metrics.reviewerResponseTime')}
                </span>
              </div>
              <span className="text-sm font-medium text-foreground tabular-nums">
                {formatDuration(metrics.reviewerResponseTime)}
              </span>
            </div>
          )}
        </div>
      ) : (
        <div className="flex items-center gap-2 p-3 text-sm text-muted-foreground bg-muted/20 rounded-lg">
          <AlertCircle className="h-4 w-4" />
          {t('common:review.metrics.noData')}
        </div>
      )}
    </div>
  );
}
