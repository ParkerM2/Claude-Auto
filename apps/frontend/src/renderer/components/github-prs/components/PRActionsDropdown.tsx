import { useState, useCallback } from 'react';
import { useTranslation } from 'react-i18next';
import {
  MoreVertical,
  Bot,
  Play,
  GitBranch,
  ExternalLink,
  Link2,
  Copy,
  GitMerge,
  RefreshCw,
  MessageSquare,
  AlertTriangle,
  FileText,
  CheckCircle,
  Loader2,
  FolderOpen,
} from 'lucide-react';
import { Button } from '../../ui/button';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
  DropdownMenuSub,
  DropdownMenuSubContent,
  DropdownMenuSubTrigger,
} from '../../ui/dropdown-menu';
import { useToast } from '../../../hooks/use-toast';
import type { PRData } from '../hooks/useGitHubPRs';
import type { Task } from '../../../../shared/types';
import type { PRWorktreeInfo } from '../../../../shared/types/integrations';

export interface PRActionsDropdownProps {
  pr: PRData;
  projectId: string;
  linkedTask?: Task;
  onRunReview?: () => void;
  onRunFollowupReview?: () => void;
  onMergePR?: (method: 'merge' | 'squash' | 'rebase') => Promise<boolean>;
  onPostComment?: (body: string) => Promise<boolean>;
  onRequestChanges?: (comment: string) => Promise<boolean>;
  triggerVariant?: 'icon' | 'button';
  align?: 'start' | 'center' | 'end';
  disabled?: boolean;
  className?: string;
  isReviewing?: boolean;
  worktreeStatus?: PRWorktreeInfo | null;
  onCheckoutWorktree?: () => Promise<void>;
}

export function PRActionsDropdown({
  pr,
  projectId,
  linkedTask,
  onRunReview,
  onRunFollowupReview,
  onMergePR,
  onPostComment,
  onRequestChanges,
  triggerVariant = 'icon',
  align = 'end',
  disabled = false,
  className,
  isReviewing = false,
  worktreeStatus,
  onCheckoutWorktree,
}: PRActionsDropdownProps) {
  const { t } = useTranslation('common');
  const { toast } = useToast();

  // Local state for async operations
  const [isCheckingOut, setIsCheckingOut] = useState(false);
  const [isStartingPreview, setIsStartingPreview] = useState(false);
  const [isMerging, setIsMerging] = useState(false);
  const [isUpdatingBranch, setIsUpdatingBranch] = useState(false);

  // Quick comment dialog state
  const [showCommentDialog, setShowCommentDialog] = useState(false);
  const [showRequestChangesDialog, setShowRequestChangesDialog] = useState(false);

  // Copy to clipboard helper
  const copyToClipboard = useCallback(async (text: string, successMessage: string) => {
    try {
      await navigator.clipboard.writeText(text);
      toast({
        title: successMessage,
        duration: 2000,
      });
    } catch (err) {
      toast({
        title: t('errors.generic'),
        variant: 'destructive',
        duration: 2000,
      });
    }
  }, [toast, t]);

  // Handle copy PR URL
  const handleCopyPRUrl = useCallback((e: React.MouseEvent) => {
    e.stopPropagation();
    copyToClipboard(pr.htmlUrl, t('prReview.actions.copiedUrl'));
  }, [pr.htmlUrl, copyToClipboard, t]);

  // Handle copy branch name
  const handleCopyBranch = useCallback((e: React.MouseEvent) => {
    e.stopPropagation();
    copyToClipboard(pr.headRefName, t('prReview.actions.copiedBranch'));
  }, [pr.headRefName, copyToClipboard, t]);

  // Handle open in GitHub
  const handleOpenInGitHub = useCallback((e: React.MouseEvent) => {
    e.stopPropagation();
    if (window.electronAPI?.openExternal) {
      window.electronAPI.openExternal(pr.htmlUrl);
    } else {
      window.open(pr.htmlUrl, '_blank');
    }
  }, [pr.htmlUrl]);

  // Handle run AI review
  const handleRunReview = useCallback((e: React.MouseEvent) => {
    e.stopPropagation();
    onRunReview?.();
  }, [onRunReview]);

  // Handle run follow-up review
  const handleRunFollowupReview = useCallback((e: React.MouseEvent) => {
    e.stopPropagation();
    onRunFollowupReview?.();
  }, [onRunFollowupReview]);

  // Handle checkout to worktree
  const handleCheckoutWorktree = useCallback(async (e: React.MouseEvent) => {
    e.stopPropagation();
    if (!onCheckoutWorktree) return;

    setIsCheckingOut(true);
    try {
      await onCheckoutWorktree();
      toast({
        title: t('prReview.worktree.worktreeCreated', { path: worktreeStatus?.worktreePath || '' }),
        duration: 3000,
      });
    } catch (err) {
      toast({
        title: t('prReview.worktree.worktreeFailed'),
        variant: 'destructive',
        duration: 3000,
      });
    } finally {
      setIsCheckingOut(false);
    }
  }, [onCheckoutWorktree, worktreeStatus?.worktreePath, toast, t]);

  // Handle view preview (dev server)
  const handleViewPreview = useCallback(async (e: React.MouseEvent) => {
    e.stopPropagation();
    if (!projectId || !worktreeStatus?.worktreePath) return;

    setIsStartingPreview(true);
    try {
      const result = await window.electronAPI.github.spawnPRDevServer(projectId, pr.number);
      if (result.success && result.data) {
        toast({
          title: t('prReview.actions.previewStarted', { port: result.data.port }),
          duration: 3000,
        });
      } else {
        toast({
          title: result.error || t('prReview.actions.previewFailed'),
          variant: 'destructive',
          duration: 3000,
        });
      }
    } catch (err) {
      toast({
        title: t('prReview.actions.previewFailed'),
        variant: 'destructive',
        duration: 3000,
      });
    } finally {
      setIsStartingPreview(false);
    }
  }, [projectId, pr.number, worktreeStatus?.worktreePath, toast, t]);

  // Handle merge PR
  const handleMerge = useCallback(async (method: 'merge' | 'squash' | 'rebase', e: React.MouseEvent) => {
    e.stopPropagation();
    if (!onMergePR) return;

    setIsMerging(true);
    try {
      const success = await onMergePR(method);
      if (success) {
        toast({
          title: t('prReview.actions.merged'),
          duration: 3000,
        });
      }
    } finally {
      setIsMerging(false);
    }
  }, [onMergePR, toast, t]);

  // Handle update branch
  const handleUpdateBranch = useCallback(async (e: React.MouseEvent) => {
    e.stopPropagation();
    setIsUpdatingBranch(true);
    try {
      const result = await window.electronAPI.github.updatePRBranch(projectId, pr.number);
      if (result.success) {
        toast({
          title: t('prReview.branchUpdated'),
          duration: 3000,
        });
      } else {
        toast({
          title: result.error || t('prReview.branchUpdateFailed'),
          variant: 'destructive',
          duration: 3000,
        });
      }
    } catch (err) {
      toast({
        title: t('prReview.branchUpdateFailed'),
        variant: 'destructive',
        duration: 3000,
      });
    } finally {
      setIsUpdatingBranch(false);
    }
  }, [projectId, pr.number, toast, t]);

  // Handle assign for review (move Kanban card + trigger AI review)
  const handleAssignForReview = useCallback(async (e: React.MouseEvent) => {
    e.stopPropagation();
    if (!linkedTask) return;

    // TODO: Implement when Kanban integration is available
    // 1. Move task to 'human_review' column via persistTaskStatus
    // 2. Trigger AI review
    onRunReview?.();
    toast({
      title: t('prReview.actions.movedToReview'),
      duration: 3000,
    });
  }, [linkedTask, onRunReview, toast, t]);

  // Determine if worktree exists
  const hasWorktree = worktreeStatus?.hasWorktree ?? false;

  return (
    <>
      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <Button
            variant={triggerVariant === 'button' ? 'outline' : 'ghost'}
            size="sm"
            className={triggerVariant === 'icon' ? 'h-8 w-8 p-0' : className}
            disabled={disabled}
            onClick={(e) => e.stopPropagation()}
            aria-label={t('prReview.actions.title')}
          >
            <MoreVertical className="h-4 w-4" />
          </Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align={align} onClick={(e) => e.stopPropagation()}>
          {/* Review Section */}
          <DropdownMenuLabel>{t('prReview.actions.review')}</DropdownMenuLabel>

          {linkedTask && (
            <DropdownMenuItem onClick={handleAssignForReview}>
              <Bot className="mr-2 h-4 w-4" />
              <div className="flex flex-col">
                <span>{t('prReview.actions.assignForReview')}</span>
                <span className="text-xs text-muted-foreground">{t('prReview.actions.assignForReviewDesc')}</span>
              </div>
            </DropdownMenuItem>
          )}

          <DropdownMenuItem onClick={handleRunReview} disabled={isReviewing}>
            {isReviewing ? (
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
            ) : (
              <Bot className="mr-2 h-4 w-4" />
            )}
            {t('prReview.runAIReview')}
          </DropdownMenuItem>

          {onRunFollowupReview && (
            <DropdownMenuItem onClick={handleRunFollowupReview} disabled={isReviewing}>
              {isReviewing ? (
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              ) : (
                <RefreshCw className="mr-2 h-4 w-4" />
              )}
              {t('prReview.runFollowup')}
            </DropdownMenuItem>
          )}

          <DropdownMenuItem onClick={() => setShowRequestChangesDialog(true)}>
            <AlertTriangle className="mr-2 h-4 w-4" />
            {t('prReview.actions.requestChanges')}
          </DropdownMenuItem>

          <DropdownMenuItem onClick={() => setShowCommentDialog(true)}>
            <MessageSquare className="mr-2 h-4 w-4" />
            {t('prReview.actions.addComment')}
          </DropdownMenuItem>

          <DropdownMenuSeparator />

          {/* Development Section */}
          <DropdownMenuLabel>{t('prReview.actions.development')}</DropdownMenuLabel>

          {hasWorktree ? (
            <>
              <DropdownMenuItem onClick={handleViewPreview} disabled={isStartingPreview}>
                {isStartingPreview ? (
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                ) : (
                  <Play className="mr-2 h-4 w-4" />
                )}
                <div className="flex flex-col">
                  <span>{t('prReview.actions.viewPreview')}</span>
                  <span className="text-xs text-muted-foreground">{t('prReview.actions.viewPreviewDesc')}</span>
                </div>
              </DropdownMenuItem>

              <DropdownMenuItem onClick={(e) => {
                e.stopPropagation();
                // Open worktree in terminal/IDE
                if (worktreeStatus?.worktreePath && window.electronAPI?.openTerminal) {
                  window.electronAPI.openTerminal(worktreeStatus.worktreePath);
                }
              }}>
                <FolderOpen className="mr-2 h-4 w-4" />
                {t('prReview.actions.openWorktree')}
              </DropdownMenuItem>
            </>
          ) : (
            <DropdownMenuItem onClick={handleCheckoutWorktree} disabled={isCheckingOut}>
              {isCheckingOut ? (
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              ) : (
                <GitBranch className="mr-2 h-4 w-4" />
              )}
              {t('prReview.actions.checkoutToWorktree')}
            </DropdownMenuItem>
          )}

          <DropdownMenuItem onClick={(e) => {
            e.stopPropagation();
            // View diff - this would open a diff dialog
            // For now, just navigate to GitHub diff
            if (window.electronAPI?.openExternal) {
              window.electronAPI.openExternal(`${pr.htmlUrl}/files`);
            }
          }}>
            <FileText className="mr-2 h-4 w-4" />
            {t('prReview.actions.viewDiff')}
          </DropdownMenuItem>

          <DropdownMenuSeparator />

          {/* Status Section */}
          <DropdownMenuLabel>{t('prReview.actions.status')}</DropdownMenuLabel>

          <DropdownMenuItem onClick={(e) => {
            e.stopPropagation();
            // View CI status - open checks page
            if (window.electronAPI?.openExternal) {
              window.electronAPI.openExternal(`${pr.htmlUrl}/checks`);
            }
          }}>
            <CheckCircle className="mr-2 h-4 w-4" />
            {t('prReview.actions.viewCIStatus')}
          </DropdownMenuItem>

          <DropdownMenuItem onClick={handleUpdateBranch} disabled={isUpdatingBranch}>
            {isUpdatingBranch ? (
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
            ) : (
              <RefreshCw className="mr-2 h-4 w-4" />
            )}
            {t('prReview.updateBranch')}
          </DropdownMenuItem>

          <DropdownMenuSeparator />

          {/* Links Section */}
          <DropdownMenuLabel>{t('prReview.actions.links')}</DropdownMenuLabel>

          <DropdownMenuItem onClick={handleOpenInGitHub}>
            <ExternalLink className="mr-2 h-4 w-4" />
            {t('prReview.actions.openInGitHub')}
          </DropdownMenuItem>

          <DropdownMenuItem onClick={handleCopyPRUrl}>
            <Link2 className="mr-2 h-4 w-4" />
            {t('prReview.actions.copyPRUrl')}
          </DropdownMenuItem>

          <DropdownMenuItem onClick={handleCopyBranch}>
            <Copy className="mr-2 h-4 w-4" />
            {t('prReview.actions.copyBranchName')}
          </DropdownMenuItem>

          <DropdownMenuSeparator />

          {/* Merge Section */}
          <DropdownMenuLabel>{t('prReview.actions.merge')}</DropdownMenuLabel>

          <DropdownMenuSub>
            <DropdownMenuSubTrigger disabled={isMerging}>
              {isMerging ? (
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              ) : (
                <GitMerge className="mr-2 h-4 w-4" />
              )}
              {t('prReview.actions.mergePR')}
            </DropdownMenuSubTrigger>
            <DropdownMenuSubContent>
              <DropdownMenuItem onClick={(e) => handleMerge('merge', e)}>
                {t('prReview.actions.createMergeCommit')}
              </DropdownMenuItem>
              <DropdownMenuItem onClick={(e) => handleMerge('squash', e)}>
                {t('prReview.actions.squashAndMerge')}
              </DropdownMenuItem>
              <DropdownMenuItem onClick={(e) => handleMerge('rebase', e)}>
                {t('prReview.actions.rebaseAndMerge')}
              </DropdownMenuItem>
            </DropdownMenuSubContent>
          </DropdownMenuSub>
        </DropdownMenuContent>
      </DropdownMenu>

      {/* Quick Comment Dialog would be rendered here when showCommentDialog is true */}
      {/* Quick Request Changes Dialog would be rendered here when showRequestChangesDialog is true */}
    </>
  );
}
