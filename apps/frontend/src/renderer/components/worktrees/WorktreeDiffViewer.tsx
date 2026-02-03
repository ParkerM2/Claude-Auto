import { useEffect, useState, useCallback } from 'react';
import { useTranslation } from 'react-i18next';
import { Loader2, AlertCircle, X, Keyboard } from 'lucide-react';
import { Button } from '../ui/button';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../ui/card';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle
} from '../ui/dialog';
import { DiffFileTree } from './DiffFileTree';
import { SideBySideDiff } from './SideBySideDiff';
import { useDiffNavigation } from './hooks/useDiffNavigation';
import { useDiffFilters } from './hooks/useDiffFilters';
import type { WorktreeDiff, WorktreeDiffFile } from '../../../shared/types';

interface WorktreeDiffViewerProps {
  taskId: string;
  open: boolean;
  onClose: () => void;
}

/**
 * Main worktree diff viewer component
 * Shows file tree on left and side-by-side diff on right
 * Supports keyboard navigation and filtering
 */
export function WorktreeDiffViewer({ taskId, open, onClose }: WorktreeDiffViewerProps) {
  const { t } = useTranslation(['common', 'dialogs']);

  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [diff, setDiff] = useState<WorktreeDiff | null>(null);
  const [selectedFilePath, setSelectedFilePath] = useState<string | null>(null);
  const [showKeyboardHelp, setShowKeyboardHelp] = useState(false);

  // Load detailed diff data
  const loadDiff = useCallback(async () => {
    if (!taskId || !open) return;

    setIsLoading(true);
    setError(null);

    try {
      const result = await window.electronAPI.getDetailedWorktreeDiff(taskId);

      if (result.success && result.data) {
        setDiff(result.data);
        // Auto-select first file if available
        if (result.data.files && result.data.files.length > 0) {
          setSelectedFilePath(result.data.files[0].path);
        }
      } else {
        setError(result.error || 'Failed to load diff');
      }
    } catch (err) {
      console.error('[WorktreeDiffViewer] Error loading diff:', err);
      setError(err instanceof Error ? err.message : 'Failed to load diff');
    } finally {
      setIsLoading(false);
    }
  }, [taskId, open]);

  // Load diff when dialog opens
  useEffect(() => {
    if (open) {
      loadDiff();
    } else {
      // Reset state when dialog closes
      setDiff(null);
      setSelectedFilePath(null);
      setError(null);
    }
  }, [open, loadDiff]);

  // Use diff filters hook
  const {
    filteredFiles,
    filters,
    setChangeType,
    setFileExtensions,
    setSearchQuery,
    clearFilters,
    hasActiveFilters,
    availableExtensions,
    changeTypeTotals,
  } = useDiffFilters(diff?.files || []);

  // Use diff navigation hook
  const {
    currentFileIndex,
    currentHunkIndex,
    goToNextFile,
    goToPrevFile,
    goToNextHunk,
    goToPrevHunk,
    goToFile,
    goToHunk,
  } = useDiffNavigation({
    files: filteredFiles,
    onFileChange: setSelectedFilePath,
    onClose,
    enabled: open && !showKeyboardHelp, // Disable when keyboard help is shown
  });

  // Handle file selection from tree
  const handleFileSelect = useCallback((filePath: string) => {
    setSelectedFilePath(filePath);
    // Update navigation to match selected file
    const fileIndex = filteredFiles.findIndex(f => f.path === filePath);
    if (fileIndex !== -1) {
      goToFile(fileIndex);
    }
  }, [filteredFiles, goToFile]);

  // Get currently selected file object
  const selectedFile = diff?.files.find(f => f.path === selectedFilePath) || null;

  // Render loading state
  if (isLoading) {
    return (
      <Dialog open={open} onOpenChange={onClose}>
        <DialogContent className="max-w-7xl h-[90vh]">
          <DialogHeader>
            <DialogTitle>{t('dialogs:worktreeDiff.title')}</DialogTitle>
            <DialogDescription>{t('dialogs:worktreeDiff.description')}</DialogDescription>
          </DialogHeader>
          <div className="flex items-center justify-center py-12">
            <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
          </div>
        </DialogContent>
      </Dialog>
    );
  }

  // Render error state
  if (error) {
    return (
      <Dialog open={open} onOpenChange={onClose}>
        <DialogContent className="max-w-7xl h-[90vh]">
          <DialogHeader>
            <DialogTitle>{t('dialogs:worktreeDiff.title')}</DialogTitle>
            <DialogDescription>{t('dialogs:worktreeDiff.description')}</DialogDescription>
          </DialogHeader>
          <div className="flex flex-col items-center justify-center py-12">
            <AlertCircle className="h-8 w-8 text-destructive mb-4" />
            <p className="text-sm text-muted-foreground mb-4">{error}</p>
            <Button onClick={loadDiff} variant="outline">
              {t('common:actions.retry')}
            </Button>
          </div>
        </DialogContent>
      </Dialog>
    );
  }

  // Render empty state
  if (!diff || diff.files.length === 0) {
    return (
      <Dialog open={open} onOpenChange={onClose}>
        <DialogContent className="max-w-7xl h-[90vh]">
          <DialogHeader>
            <DialogTitle>{t('dialogs:worktreeDiff.title')}</DialogTitle>
            <DialogDescription>{t('dialogs:worktreeDiff.description')}</DialogDescription>
          </DialogHeader>
          <div className="flex flex-col items-center justify-center py-12">
            <AlertCircle className="h-8 w-8 text-muted-foreground mb-4" />
            <p className="text-sm text-muted-foreground">
              {t('common:labels.noData')}
            </p>
          </div>
        </DialogContent>
      </Dialog>
    );
  }

  return (
    <>
      <Dialog open={open} onOpenChange={onClose}>
        <DialogContent className="max-w-7xl h-[90vh] flex flex-col p-0">
          <DialogHeader className="px-6 pt-6 pb-4 border-b">
            <div className="flex items-center justify-between">
              <div className="flex-1">
                <DialogTitle>{t('dialogs:worktreeDiff.title')}</DialogTitle>
                <DialogDescription>
                  {diff.summary || t('dialogs:worktreeDiff.description')}
                </DialogDescription>
              </div>
              <div className="flex items-center gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setShowKeyboardHelp(true)}
                >
                  <Keyboard className="h-4 w-4 mr-2" />
                  Shortcuts
                </Button>
                <Button variant="ghost" size="sm" onClick={onClose}>
                  <X className="h-4 w-4" />
                </Button>
              </div>
            </div>
          </DialogHeader>

          {/* Main content area */}
          <div className="flex-1 flex overflow-hidden">
            {/* Left panel - File tree */}
            <div className="w-80 border-r flex flex-col">
              <DiffFileTree
                files={filteredFiles}
                selectedFile={selectedFilePath}
                onFileSelect={handleFileSelect}
                isLoading={false}
              />
            </div>

            {/* Right panel - Diff viewer */}
            <div className="flex-1 flex flex-col overflow-hidden">
              {selectedFile ? (
                <SideBySideDiff file={selectedFile} />
              ) : (
                <div className="flex-1 flex items-center justify-center p-8">
                  <div className="text-center">
                    <p className="text-sm text-muted-foreground">
                      Select a file to view diff
                    </p>
                  </div>
                </div>
              )}
            </div>
          </div>

          {/* Footer with navigation info */}
          <div className="px-6 py-3 border-t bg-muted/30">
            <div className="flex items-center justify-between text-xs text-muted-foreground">
              <div>
                Viewing {currentFileIndex + 1} of {filteredFiles.length} files
                {hasActiveFilters && (
                  <span className="ml-2">
                    ({changeTypeTotals.all} total)
                  </span>
                )}
              </div>
              <div className="flex items-center gap-4">
                <span>
                  <kbd className="px-1.5 py-0.5 rounded bg-muted border text-xs">N</kbd> Next file
                </span>
                <span>
                  <kbd className="px-1.5 py-0.5 rounded bg-muted border text-xs">P</kbd> Prev file
                </span>
                <span>
                  <kbd className="px-1.5 py-0.5 rounded bg-muted border text-xs">J</kbd> Next hunk
                </span>
                <span>
                  <kbd className="px-1.5 py-0.5 rounded bg-muted border text-xs">K</kbd> Prev hunk
                </span>
              </div>
            </div>
          </div>
        </DialogContent>
      </Dialog>

      {/* Keyboard shortcuts help dialog */}
      <Dialog open={showKeyboardHelp} onOpenChange={setShowKeyboardHelp}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Keyboard Shortcuts</DialogTitle>
            <DialogDescription>
              Navigate through the diff viewer efficiently
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="flex items-center justify-between">
              <span className="text-sm">Next file</span>
              <kbd className="px-2 py-1 rounded bg-muted border text-sm font-mono">N</kbd>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-sm">Previous file</span>
              <kbd className="px-2 py-1 rounded bg-muted border text-sm font-mono">P</kbd>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-sm">Next hunk</span>
              <kbd className="px-2 py-1 rounded bg-muted border text-sm font-mono">J</kbd>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-sm">Previous hunk</span>
              <kbd className="px-2 py-1 rounded bg-muted border text-sm font-mono">K</kbd>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-sm">Close viewer</span>
              <kbd className="px-2 py-1 rounded bg-muted border text-sm font-mono">Escape</kbd>
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </>
  );
}
