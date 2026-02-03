import { memo } from 'react';
import { useTranslation } from 'react-i18next';
import { AlertTriangle, X, CheckCircle2 } from 'lucide-react';
import { Card, CardContent } from '../ui/card';
import { Badge } from '../ui/badge';
import { Button } from '../ui/button';
import { cn, formatRelativeTime } from '../../lib/utils';

interface GotchaCardProps {
  /** Gotcha/pitfall description */
  content: string;
  /** Number of times this gotcha has been encountered */
  frequency: number;
  /** ISO timestamp of when gotcha was last encountered */
  lastSeen: string;
  /** Callback when user confirms they've noted this gotcha */
  onConfirm?: () => void;
  /** Callback when user dismisses this gotcha */
  onDismiss?: () => void;
  /** Whether actions are in progress */
  isActionPending?: boolean;
}

/**
 * Card component displaying a recognized gotcha or pitfall.
 *
 * Shows gotcha content, frequency count, recency, and allows users to
 * confirm (mark as useful) or dismiss gotchas.
 *
 * @example
 * ```tsx
 * <GotchaCard
 *   content="Remember to handle async errors with try-catch"
 *   frequency={3}
 *   lastSeen="2024-01-15T10:30:00Z"
 *   onConfirm={() => console.log('confirmed')}
 *   onDismiss={() => console.log('dismissed')}
 * />
 * ```
 */
export const GotchaCard = memo(function GotchaCard({
  content,
  frequency,
  lastSeen,
  onConfirm,
  onDismiss,
  isActionPending = false
}: GotchaCardProps) {
  const { t } = useTranslation(['insights', 'common']);

  const relativeTime = formatRelativeTime(new Date(lastSeen));

  return (
    <Card className="hover:shadow-md transition-shadow border-l-4 border-l-orange-500">
      <CardContent className="p-4">
        <div className="flex items-start gap-3">
          {/* Icon */}
          <div className="flex-shrink-0 mt-1">
            <div className="w-8 h-8 rounded-full bg-orange-100 dark:bg-orange-900/30 flex items-center justify-center">
              <AlertTriangle className="w-4 h-4 text-orange-600 dark:text-orange-400" />
            </div>
          </div>

          {/* Content */}
          <div className="flex-1 min-w-0">
            <p className="text-sm text-foreground mb-2 leading-relaxed">
              {content}
            </p>

            {/* Metadata */}
            <div className="flex items-center gap-2 flex-wrap">
              <Badge variant="secondary" className="text-xs bg-orange-100 text-orange-800 dark:bg-orange-900/30 dark:text-orange-400">
                {t('insights:gotchas.encounteredCount', { count: frequency })}
              </Badge>
              <span className="text-xs text-muted-foreground">
                {t('common:time.lastSeen')} {relativeTime}
              </span>
            </div>
          </div>

          {/* Actions */}
          {(onConfirm || onDismiss) && (
            <div className="flex-shrink-0 flex items-center gap-1">
              {onConfirm && (
                <Button
                  size="sm"
                  variant="ghost"
                  onClick={onConfirm}
                  disabled={isActionPending}
                  className="h-8 w-8 p-0"
                  aria-label={t('insights:gotchas.confirm')}
                  title={t('insights:gotchas.confirm')}
                >
                  <CheckCircle2 className="w-4 h-4 text-green-600" />
                </Button>
              )}
              {onDismiss && (
                <Button
                  size="sm"
                  variant="ghost"
                  onClick={onDismiss}
                  disabled={isActionPending}
                  className="h-8 w-8 p-0"
                  aria-label={t('insights:gotchas.dismiss')}
                  title={t('insights:gotchas.dismiss')}
                >
                  <X className="w-4 h-4 text-muted-foreground hover:text-foreground" />
                </Button>
              )}
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  );
});
