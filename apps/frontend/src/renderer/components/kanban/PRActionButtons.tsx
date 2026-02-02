import { useCallback } from 'react';
import { useTranslation } from 'react-i18next';
import { CheckCircle, AlertTriangle, GitMerge, ExternalLink } from 'lucide-react';
import { Button } from '../ui/button';

export interface PRActionButtonsProps {
  prNumber: number;
  prState: string;
  prHtmlUrl: string;
  projectId: string;
  isApproved?: boolean;
  isMergeable?: boolean;
  onApprove?: () => void;
  onRequestChanges?: () => void;
  onMerge?: () => void;
  disabled?: boolean;
  className?: string;
}

export function PRActionButtons({
  prNumber,
  prState,
  prHtmlUrl,
  projectId,
  isApproved = false,
  isMergeable = false,
  onApprove,
  onRequestChanges,
  onMerge,
  disabled = false,
  className,
}: PRActionButtonsProps) {
  const { t } = useTranslation('common');

  // Handle approve PR
  const handleApprove = useCallback(
    (e: React.MouseEvent) => {
      e.stopPropagation();
      onApprove?.();
    },
    [onApprove]
  );

  // Handle request changes
  const handleRequestChanges = useCallback(
    (e: React.MouseEvent) => {
      e.stopPropagation();
      onRequestChanges?.();
    },
    [onRequestChanges]
  );

  // Handle merge PR
  const handleMerge = useCallback(
    (e: React.MouseEvent) => {
      e.stopPropagation();
      onMerge?.();
    },
    [onMerge]
  );

  // Handle open in GitHub
  const handleOpenInGitHub = useCallback(
    (e: React.MouseEvent) => {
      e.stopPropagation();
      if (window.electronAPI?.openExternal) {
        window.electronAPI.openExternal(prHtmlUrl);
      } else {
        window.open(prHtmlUrl, '_blank');
      }
    },
    [prHtmlUrl]
  );

  // Only show buttons for open PRs
  if (prState !== 'open') {
    return null;
  }

  return (
    <div className={`flex items-center gap-2 ${className || ''}`}>
      {/* Approve button - show if not already approved and callback provided */}
      {!isApproved && onApprove && (
        <Button
          variant="success"
          size="sm"
          onClick={handleApprove}
          disabled={disabled}
          title={t('prReview.approve')}
        >
          <CheckCircle className="h-3.5 w-3.5 mr-1.5" />
          {t('prReview.approve')}
        </Button>
      )}

      {/* Request changes button - show if callback provided */}
      {onRequestChanges && (
        <Button
          variant="warning"
          size="sm"
          onClick={handleRequestChanges}
          disabled={disabled}
          title={t('prReview.actions.requestChanges')}
        >
          <AlertTriangle className="h-3.5 w-3.5 mr-1.5" />
          {t('prReview.actions.requestChanges')}
        </Button>
      )}

      {/* Merge button - show if approved, mergeable, and callback provided */}
      {isApproved && isMergeable && onMerge && (
        <Button
          variant="default"
          size="sm"
          onClick={handleMerge}
          disabled={disabled}
          title={t('prReview.merge')}
        >
          <GitMerge className="h-3.5 w-3.5 mr-1.5" />
          {t('prReview.merge')}
        </Button>
      )}

      {/* View on GitHub button - always show */}
      <Button
        variant="ghost"
        size="sm"
        onClick={handleOpenInGitHub}
        disabled={disabled}
        title={t('prReview.viewOnGitHub')}
      >
        <ExternalLink className="h-3.5 w-3.5 mr-1.5" />
        {t('prReview.viewOnGitHub')}
      </Button>
    </div>
  );
}
