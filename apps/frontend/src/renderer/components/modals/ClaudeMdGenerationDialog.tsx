import { useState, useEffect, useCallback } from 'react';
import { useTranslation } from 'react-i18next';
import { FileText, Sparkles, Check, AlertCircle, Loader2 } from 'lucide-react';
import { Button } from '../ui/button';
import { Progress } from '../ui/progress';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle
} from '../ui/dialog';
import { cn } from '../../lib/utils';
import type { ClaudeMdProgressEvent, ClaudeMdGenerationResult } from '../../../preload/api/modules/claude-md-api';

type DialogState = 'prompt' | 'generating' | 'success' | 'error';

interface ClaudeMdGenerationDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  projectPath: string;
  onGenerate?: () => void;
  onSkip?: () => void;
  onRemindLater?: () => void;
}

export function ClaudeMdGenerationDialog({
  open,
  onOpenChange,
  projectPath,
  onGenerate,
  onSkip,
  onRemindLater
}: ClaudeMdGenerationDialogProps) {
  const { t } = useTranslation('dialogs');
  const [state, setState] = useState<DialogState>('prompt');
  const [progress, setProgress] = useState(0);
  const [progressMessage, setProgressMessage] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [outputPath, setOutputPath] = useState<string | null>(null);

  // Reset state when dialog opens
  useEffect(() => {
    if (open) {
      setState('prompt');
      setProgress(0);
      setProgressMessage('');
      setError(null);
      setOutputPath(null);
    }
  }, [open]);

  // Handle progress events
  const handleProgress = useCallback((eventProjectPath: string, progressEvent: ClaudeMdProgressEvent) => {
    if (eventProjectPath !== projectPath) return;
    setProgress(progressEvent.percent);
    setProgressMessage(progressEvent.message);
  }, [projectPath]);

  // Handle completion
  const handleComplete = useCallback((eventProjectPath: string, result: ClaudeMdGenerationResult) => {
    if (eventProjectPath !== projectPath) return;
    if (result.success && result.outputPath) {
      setOutputPath(result.outputPath);
      setState('success');
    } else {
      setError(result.error || t('claudeMd.error'));
      setState('error');
    }
  }, [projectPath, t]);

  // Handle error
  const handleError = useCallback((eventProjectPath: string, errorMessage: string) => {
    if (eventProjectPath !== projectPath) return;
    setError(errorMessage);
    setState('error');
  }, [projectPath]);

  // Subscribe to events
  useEffect(() => {
    if (!open || state !== 'generating') return;

    const cleanupProgress = window.electronAPI.claudeMd.onProgress(handleProgress);
    const cleanupComplete = window.electronAPI.claudeMd.onComplete(handleComplete);
    const cleanupError = window.electronAPI.claudeMd.onError(handleError);

    return () => {
      cleanupProgress();
      cleanupComplete();
      cleanupError();
    };
  }, [open, state, handleProgress, handleComplete, handleError]);

  const handleGenerate = () => {
    setState('generating');
    setProgress(0);
    setProgressMessage(t('claudeMd.analyzingProject'));
    window.electronAPI.claudeMd.generateClaudeMd(projectPath);
    onGenerate?.();
  };

  const handleSkip = () => {
    onSkip?.();
    onOpenChange(false);
  };

  const handleRemindLater = () => {
    onRemindLater?.();
    onOpenChange(false);
  };

  const handleClose = () => {
    if (state === 'generating') {
      // Don't allow closing while generating
      return;
    }
    onOpenChange(false);
  };

  const handleViewFile = () => {
    if (outputPath) {
      // Open the file in the default editor or reveal in explorer
      window.electronAPI.openExternal(`file://${outputPath}`);
    }
    onOpenChange(false);
  };

  const renderPrompt = () => (
    <>
      <DialogHeader>
        <DialogTitle className="flex items-center gap-2">
          <FileText className="h-5 w-5 text-primary" />
          {t('claudeMd.title')}
        </DialogTitle>
        <DialogDescription>
          {t('claudeMd.description')}
        </DialogDescription>
      </DialogHeader>

      <div className="py-4 space-y-4">
        {/* What is CLAUDE.md */}
        <div className="space-y-2">
          <h4 className="text-sm font-medium text-foreground">{t('claudeMd.whatIs')}</h4>
          <p className="text-sm text-muted-foreground">
            {t('claudeMd.explanation')}
          </p>
        </div>

        {/* Benefits */}
        <div className="space-y-2">
          <h4 className="text-sm font-medium text-foreground">{t('claudeMd.benefits')}</h4>
          <ul className="space-y-1.5">
            {[1, 2, 3, 4].map((i) => (
              <li key={i} className="flex items-start gap-2 text-sm text-muted-foreground">
                <Check className="h-4 w-4 text-success mt-0.5 shrink-0" />
                <span>{t(`claudeMd.benefit${i}`)}</span>
              </li>
            ))}
          </ul>
        </div>
      </div>

      <DialogFooter className="flex-col sm:flex-row gap-2">
        <Button variant="ghost" onClick={handleRemindLater} className="w-full sm:w-auto">
          {t('claudeMd.remindLater')}
        </Button>
        <Button variant="outline" onClick={handleSkip} className="w-full sm:w-auto">
          {t('claudeMd.skip')}
        </Button>
        <Button onClick={handleGenerate} className="w-full sm:w-auto">
          <Sparkles className="h-4 w-4 mr-2" />
          {t('claudeMd.generate')}
        </Button>
      </DialogFooter>
    </>
  );

  const renderGenerating = () => (
    <>
      <DialogHeader>
        <DialogTitle className="flex items-center gap-2">
          <Loader2 className="h-5 w-5 text-primary animate-spin" />
          {t('claudeMd.generating')}
        </DialogTitle>
      </DialogHeader>

      <div className="py-6 space-y-4">
        <Progress value={progress} className="w-full" />
        <p className="text-sm text-center text-muted-foreground">
          {progressMessage || t('claudeMd.analyzingProject')}
        </p>
      </div>
    </>
  );

  const renderSuccess = () => (
    <>
      <DialogHeader>
        <DialogTitle className="flex items-center gap-2 text-success">
          <Check className="h-5 w-5" />
          {t('claudeMd.complete')}
        </DialogTitle>
      </DialogHeader>

      <div className="py-6 text-center">
        <div className={cn(
          'mx-auto w-16 h-16 rounded-full flex items-center justify-center',
          'bg-success/10 mb-4'
        )}>
          <FileText className="h-8 w-8 text-success" />
        </div>
        <p className="text-sm text-muted-foreground">
          {t('claudeMd.success')}
        </p>
        {outputPath && (
          <p className="text-xs text-muted-foreground/70 mt-2 font-mono truncate max-w-full px-4">
            {outputPath}
          </p>
        )}
      </div>

      <DialogFooter>
        <Button variant="outline" onClick={() => onOpenChange(false)}>
          {t('common:buttons.close')}
        </Button>
        <Button onClick={handleViewFile}>
          {t('claudeMd.viewFile')}
        </Button>
      </DialogFooter>
    </>
  );

  const renderError = () => (
    <>
      <DialogHeader>
        <DialogTitle className="flex items-center gap-2 text-destructive">
          <AlertCircle className="h-5 w-5" />
          {t('claudeMd.error')}
        </DialogTitle>
      </DialogHeader>

      <div className="py-6">
        <div className={cn(
          'mx-auto w-16 h-16 rounded-full flex items-center justify-center',
          'bg-destructive/10 mb-4'
        )}>
          <AlertCircle className="h-8 w-8 text-destructive" />
        </div>
        {error && (
          <p className="text-sm text-center text-muted-foreground px-4">
            {error}
          </p>
        )}
      </div>

      <DialogFooter>
        <Button variant="outline" onClick={() => onOpenChange(false)}>
          {t('common:buttons.close')}
        </Button>
        <Button onClick={() => setState('prompt')}>
          {t('common:buttons.retry')}
        </Button>
      </DialogFooter>
    </>
  );

  const renderContent = () => {
    switch (state) {
      case 'prompt':
        return renderPrompt();
      case 'generating':
        return renderGenerating();
      case 'success':
        return renderSuccess();
      case 'error':
        return renderError();
    }
  };

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent className="sm:max-w-md">
        {renderContent()}
      </DialogContent>
    </Dialog>
  );
}
