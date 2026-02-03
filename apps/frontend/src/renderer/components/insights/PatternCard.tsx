import { memo } from 'react';
import { useTranslation } from 'react-i18next';
import { CheckCircle2, X, TrendingUp } from 'lucide-react';
import { Card, CardContent } from '../ui/card';
import { Badge } from '../ui/badge';
import { Button } from '../ui/button';
import { cn, formatRelativeTime } from '../../lib/utils';

interface PatternCardProps {
  /** Pattern content/description */
  content: string;
  /** Number of times this pattern has been observed */
  frequency: number;
  /** ISO timestamp of when pattern was last seen */
  lastSeen: string;
  /** Callback when user confirms this pattern is useful */
  onConfirm?: () => void;
  /** Callback when user dismisses this pattern */
  onDismiss?: () => void;
  /** Whether actions are in progress */
  isActionPending?: boolean;
}

/**
 * Card component displaying a recognized code pattern.
 *
 * Shows pattern content, frequency count, recency, and allows users to
 * confirm (mark as useful) or dismiss patterns.
 *
 * @example
 * ```tsx
 * <PatternCard
 *   content="Use React hooks for state management"
 *   frequency={5}
 *   lastSeen="2024-01-15T10:30:00Z"
 *   onConfirm={() => console.log('confirmed')}
 *   onDismiss={() => console.log('dismissed')}
 * />
 * ```
 */
export const PatternCard = memo(function PatternCard({
  content,
  frequency,
  lastSeen,
  onConfirm,
  onDismiss,
  isActionPending = false
}: PatternCardProps) {
  const { t } = useTranslation(['insights', 'common']);

  const relativeTime = formatRelativeTime(lastSeen);

  return (
    <Card className="hover:shadow-md transition-shadow">
      <CardContent className="p-4">
        <div className="flex items-start gap-3">
          {/* Icon */}
          <div className="flex-shrink-0 mt-1">
            <div className="w-8 h-8 rounded-full bg-primary/10 flex items-center justify-center">
              <TrendingUp className="w-4 h-4 text-primary" />
            </div>
          </div>

          {/* Content */}
          <div className="flex-1 min-w-0">
            <p className="text-sm text-foreground mb-2 leading-relaxed">
              {content}
            </p>

            {/* Metadata */}
            <div className="flex items-center gap-2 flex-wrap">
              <Badge variant="secondary" className="text-xs">
                {t('insights:patterns.seenCount', { count: frequency })}
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
                  aria-label={t('insights:patterns.confirm')}
                  title={t('insights:patterns.confirm')}
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
                  aria-label={t('insights:patterns.dismiss')}
                  title={t('insights:patterns.dismiss')}
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
