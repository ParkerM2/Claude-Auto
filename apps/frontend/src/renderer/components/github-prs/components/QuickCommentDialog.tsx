import { useState, useCallback } from 'react';
import { useTranslation } from 'react-i18next';
import { Loader2, MessageSquare, AlertTriangle } from 'lucide-react';
import { Button } from '../../ui/button';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '../../ui/dialog';
import { Textarea } from '../../ui/textarea';
import { useToast } from '../../../hooks/use-toast';

export interface QuickCommentDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  prNumber: number;
  prTitle: string;
  mode: 'comment' | 'request_changes';
  onSubmit: (comment: string) => Promise<boolean>;
}

export function QuickCommentDialog({
  open,
  onOpenChange,
  prNumber,
  prTitle,
  mode,
  onSubmit,
}: QuickCommentDialogProps) {
  const { t } = useTranslation('common');
  const { toast } = useToast();

  const [comment, setComment] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleSubmit = useCallback(async () => {
    if (!comment.trim()) return;

    setIsSubmitting(true);
    try {
      const success = await onSubmit(comment);
      if (success) {
        toast({
          title: mode === 'comment'
            ? t('prReview.actions.commentPosted')
            : t('prReview.actions.changesRequested'),
          duration: 3000,
        });
        setComment('');
        onOpenChange(false);
      } else {
        toast({
          title: t('errors.operationFailed'),
          variant: 'destructive',
          duration: 3000,
        });
      }
    } catch (err) {
      toast({
        title: t('errors.operationFailed'),
        variant: 'destructive',
        duration: 3000,
      });
    } finally {
      setIsSubmitting(false);
    }
  }, [comment, onSubmit, mode, toast, t, onOpenChange]);

  const handleClose = useCallback(() => {
    if (!isSubmitting) {
      setComment('');
      onOpenChange(false);
    }
  }, [isSubmitting, onOpenChange]);

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent className="sm:max-w-[500px]">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            {mode === 'comment' ? (
              <>
                <MessageSquare className="h-5 w-5" />
                {t('prReview.actions.addComment')}
              </>
            ) : (
              <>
                <AlertTriangle className="h-5 w-5 text-warning" />
                {t('prReview.actions.requestChanges')}
              </>
            )}
          </DialogTitle>
          <DialogDescription>
            PR #{prNumber}: {prTitle}
          </DialogDescription>
        </DialogHeader>

        <div className="py-4">
          <Textarea
            value={comment}
            onChange={(e) => setComment(e.target.value)}
            placeholder={t('prReview.actions.commentPlaceholder')}
            className="min-h-[150px] resize-none"
            disabled={isSubmitting}
            autoFocus
          />
        </div>

        <DialogFooter>
          <Button
            variant="outline"
            onClick={handleClose}
            disabled={isSubmitting}
          >
            {t('buttons.cancel')}
          </Button>
          <Button
            onClick={handleSubmit}
            disabled={isSubmitting || !comment.trim()}
            variant={mode === 'request_changes' ? 'destructive' : 'default'}
          >
            {isSubmitting ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                {t('prReview.posting')}
              </>
            ) : (
              t('prReview.actions.postComment')
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
