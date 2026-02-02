import { useState, useCallback } from 'react';
import { useTranslation } from 'react-i18next';
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '../ui/alert-dialog';
import { Textarea } from '../ui/textarea';
import { Label } from '../ui/label';

export type PRActionType = 'approve' | 'merge' | 'request_changes';

export interface PRConfirmDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  actionType: PRActionType;
  prNumber: number;
  prTitle: string;
  onConfirm: (comment?: string) => void;
  mergeMethod?: 'merge' | 'squash' | 'rebase';
}

/**
 * Confirmation dialog for PR actions (approve, merge, request changes)
 * For 'request_changes' action, includes a textarea for comment input
 */
export function PRConfirmDialog({
  open,
  onOpenChange,
  actionType,
  prNumber,
  prTitle,
  onConfirm,
  mergeMethod = 'merge',
}: PRConfirmDialogProps) {
  const { t } = useTranslation('common');
  const [comment, setComment] = useState('');

  const handleConfirm = useCallback(() => {
    if (actionType === 'request_changes') {
      onConfirm(comment);
    } else {
      onConfirm();
    }
    setComment('');
    onOpenChange(false);
  }, [actionType, comment, onConfirm, onOpenChange]);

  const handleCancel = useCallback(() => {
    setComment('');
    onOpenChange(false);
  }, [onOpenChange]);

  const getTitle = () => {
    switch (actionType) {
      case 'approve':
        return t('prReview.approve');
      case 'merge':
        return t('prReview.merge');
      case 'request_changes':
        return t('prReview.actions.requestChanges');
      default:
        return '';
    }
  };

  const getDescription = () => {
    switch (actionType) {
      case 'approve':
        return `${t('prReview.approve')} PR #${prNumber}: ${prTitle}`;
      case 'merge':
        const methodLabel = mergeMethod === 'squash'
          ? t('prReview.actions.squashAndMerge')
          : mergeMethod === 'rebase'
          ? t('prReview.actions.rebaseAndMerge')
          : t('prReview.actions.createMergeCommit');
        return `${methodLabel} PR #${prNumber}: ${prTitle}`;
      case 'request_changes':
        return `${t('prReview.actions.requestChanges')} for PR #${prNumber}: ${prTitle}`;
      default:
        return '';
    }
  };

  return (
    <AlertDialog open={open} onOpenChange={onOpenChange}>
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle>{getTitle()}</AlertDialogTitle>
          <AlertDialogDescription>{getDescription()}</AlertDialogDescription>
        </AlertDialogHeader>

        {actionType === 'request_changes' && (
          <div className="flex flex-col gap-2 mt-4">
            <Label htmlFor="comment">{t('prReview.actions.commentPlaceholder')}</Label>
            <Textarea
              id="comment"
              value={comment}
              onChange={(e) => setComment(e.target.value)}
              placeholder={t('prReview.actions.commentPlaceholder')}
              rows={4}
              className="resize-y"
            />
          </div>
        )}

        <AlertDialogFooter>
          <AlertDialogCancel onClick={handleCancel}>
            {t('buttons.cancel')}
          </AlertDialogCancel>
          <AlertDialogAction onClick={handleConfirm}>
            {t('buttons.confirm')}
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  );
}
