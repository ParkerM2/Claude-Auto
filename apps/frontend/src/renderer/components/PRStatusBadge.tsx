/**
 * PR Status Badge Component
 *
 * Displays a compact badge showing the current status of a GitHub PR:
 * - PR state (merged, closed, draft, open)
 * - Review decision (approved, changes requested, pending review)
 * - CI status indicator
 */

import { memo, useMemo } from 'react';
import { useTranslation } from 'react-i18next';
import {
  GitMerge,
  GitPullRequestClosed,
  GitPullRequestDraft,
  CheckCircle2,
  XCircle,
  AlertCircle,
  Clock,
  Loader2
} from 'lucide-react';
import { Badge } from './ui/badge';
import { cn } from '../lib/utils';
import type { PRStatusInfo } from '../../shared/types/task';

interface PRStatusBadgeProps {
  status: PRStatusInfo;
  compact?: boolean;
  showCIStatus?: boolean;
}

/**
 * Get the primary status display info
 */
function getPrimaryStatus(status: PRStatusInfo): {
  label: string;
  icon: typeof GitMerge;
  className: string;
  priority: number;
} {
  // Merged state takes highest priority
  if (status.state === 'merged') {
    return {
      label: 'prStatus.merged',
      icon: GitMerge,
      className: 'bg-purple-500/10 text-purple-400 border-purple-500/30',
      priority: 100
    };
  }

  // Closed state
  if (status.state === 'closed') {
    return {
      label: 'prStatus.closed',
      icon: GitPullRequestClosed,
      className: 'bg-muted text-muted-foreground border-border',
      priority: 90
    };
  }

  // Draft state
  if (status.isDraft) {
    return {
      label: 'prStatus.draft',
      icon: GitPullRequestDraft,
      className: 'bg-muted text-muted-foreground border-border',
      priority: 80
    };
  }

  // Review decision states
  if (status.reviewDecision === 'approved') {
    return {
      label: 'prStatus.approved',
      icon: CheckCircle2,
      className: 'bg-green-500/10 text-green-400 border-green-500/30',
      priority: 70
    };
  }

  if (status.reviewDecision === 'changes_requested') {
    return {
      label: 'prStatus.changesRequested',
      icon: XCircle,
      className: 'bg-red-500/10 text-red-400 border-red-500/30',
      priority: 60
    };
  }

  // Default: pending review
  return {
    label: 'prStatus.pendingReview',
    icon: AlertCircle,
    className: 'bg-yellow-500/10 text-yellow-400 border-yellow-500/30',
    priority: 50
  };
}

/**
 * Get CI status display info
 */
function getCIStatus(ciStatus: PRStatusInfo['ciStatus']): {
  label: string;
  icon: typeof CheckCircle2;
  className: string;
} | null {
  switch (ciStatus) {
    case 'passing':
      return {
        label: 'prStatus.ciPassing',
        icon: CheckCircle2,
        className: 'text-green-400'
      };
    case 'failing':
      return {
        label: 'prStatus.ciFailing',
        icon: XCircle,
        className: 'text-red-400'
      };
    case 'pending':
      return {
        label: 'prStatus.ciPending',
        icon: Loader2,
        className: 'text-yellow-400 animate-spin'
      };
    default:
      return null;
  }
}

/**
 * PR Status Badge Component
 *
 * Displays a visual badge indicating the current status of a GitHub PR.
 */
export const PRStatusBadge = memo(function PRStatusBadge({
  status,
  compact = false,
  showCIStatus = true
}: PRStatusBadgeProps) {
  const { t } = useTranslation('common');

  const primaryStatus = useMemo(() => getPrimaryStatus(status), [status]);
  const ciStatus = useMemo(() => showCIStatus ? getCIStatus(status.ciStatus) : null, [status.ciStatus, showCIStatus]);

  const Icon = primaryStatus.icon;
  const CIIcon = ciStatus?.icon;

  if (compact) {
    // Compact mode: just icons
    return (
      <div className="flex items-center gap-1">
        <Badge
          variant="outline"
          className={cn('text-[10px] px-1.5 py-0.5 flex items-center gap-1', primaryStatus.className)}
          title={t(primaryStatus.label)}
        >
          <Icon className="h-3 w-3" />
        </Badge>
        {ciStatus && CIIcon && (
          <span title={t(ciStatus.label)}>
            <CIIcon className={cn('h-3 w-3', ciStatus.className)} />
          </span>
        )}
      </div>
    );
  }

  // Full mode: icon + label
  return (
    <div className="flex items-center gap-1.5">
      <Badge
        variant="outline"
        className={cn('text-[10px] px-1.5 py-0.5 flex items-center gap-1', primaryStatus.className)}
      >
        <Icon className="h-2.5 w-2.5" />
        {t(primaryStatus.label)}
      </Badge>
      {ciStatus && CIIcon && (
        <span
          className="flex items-center gap-1 text-[10px]"
          title={t(ciStatus.label)}
        >
          <CIIcon className={cn('h-3 w-3', ciStatus.className)} />
        </span>
      )}
    </div>
  );
});

export default PRStatusBadge;
