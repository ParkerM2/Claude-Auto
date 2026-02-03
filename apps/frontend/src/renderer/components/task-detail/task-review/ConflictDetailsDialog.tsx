import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { AlertTriangle, GitMerge } from 'lucide-react';
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '../../ui/alert-dialog';
import { Badge } from '../../ui/badge';
import { RadioGroup, RadioGroupItem } from '../../ui/radio-group';
import { Label } from '../../ui/label';
import { cn } from '../../../lib/utils';
import { getSeverityIcon, getSeverityVariant } from './utils';
import type { MergeConflict, MergeStats, GitConflictInfo } from '../../../../shared/types';

interface ConflictDetailsDialogProps {
  open: boolean;
  mergePreview: { files: string[]; conflicts: MergeConflict[]; summary: MergeStats; gitConflicts?: GitConflictInfo } | null;
  stageOnly: boolean;
  onOpenChange: (open: boolean) => void;
  onMerge: (conflictResolutions?: Record<string, string>) => void;
  onStrategiesChange?: (strategies: Record<string, string>) => void;
}

/**
 * Dialog displaying detailed information about merge conflicts
 */
export function ConflictDetailsDialog({
  open,
  mergePreview,
  stageOnly,
  onOpenChange,
  onMerge,
  onStrategiesChange
}: ConflictDetailsDialogProps) {
  const { t } = useTranslation(['dialogs']);
  // Track selected strategy for each conflict (indexed by conflict index)
  const [selectedStrategies, setSelectedStrategies] = useState<Record<number, string>>({});

  // Convert index-based strategies to file-path based for API
  const convertToConflictResolutions = (): Record<string, string> => {
    const resolutions: Record<string, string> = {};
    if (!mergePreview?.conflicts) return resolutions;

    Object.entries(selectedStrategies).forEach(([idxStr, strategy]) => {
      const idx = parseInt(idxStr, 10);
      const conflict = mergePreview.conflicts[idx];
      if (conflict && strategy) {
        resolutions[conflict.file] = strategy;
      }
    });

    return resolutions;
  };

  return (
    <AlertDialog open={open} onOpenChange={onOpenChange}>
      <AlertDialogContent className="max-w-2xl max-h-[80vh] overflow-hidden flex flex-col">
        <AlertDialogHeader>
          <AlertDialogTitle className="flex items-center gap-2">
            <AlertTriangle className="h-5 w-5 text-warning" />
            {t('dialogs:conflictDetails.title')}
          </AlertDialogTitle>
          <AlertDialogDescription>
            {t('dialogs:conflictDetails.conflictsDetected', {
              count: mergePreview?.conflicts.length || 0,
              plural: (mergePreview?.conflicts.length || 0) !== 1 ? 's' : ''
            })}
            {mergePreview && mergePreview.summary.autoMergeable > 0 && (
              <span className="text-success ml-1">
                {t('dialogs:conflictDetails.canAutoMerge', {
                  count: mergePreview.summary.autoMergeable
                })}
              </span>
            )}
          </AlertDialogDescription>
        </AlertDialogHeader>
        <div className="flex-1 overflow-auto min-h-0 -mx-6 px-6">
          {mergePreview?.conflicts && mergePreview.conflicts.length > 0 ? (
            <div className="space-y-3">
              {mergePreview.conflicts.map((conflict, idx) => (
                <div
                  key={idx}
                  className={cn(
                    "p-3 rounded-lg border",
                    conflict.canAutoMerge
                      ? "bg-secondary/30 border-border"
                      : conflict.severity === 'high' || conflict.severity === 'critical'
                        ? "bg-destructive/10 border-destructive/30"
                        : "bg-warning/10 border-warning/30"
                  )}
                >
                  <div className="flex items-start justify-between gap-2 mb-2">
                    <div className="flex items-center gap-2 min-w-0 flex-1">
                      {getSeverityIcon(conflict.severity)}
                      <span className="text-sm font-mono truncate">{conflict.file}</span>
                    </div>
                    <div className="flex items-center gap-2 shrink-0">
                      <Badge
                        variant="secondary"
                        className={cn('text-xs', getSeverityVariant(conflict.severity))}
                      >
                        {conflict.severity}
                      </Badge>
                      {conflict.canAutoMerge && (
                        <Badge variant="secondary" className="text-xs bg-success/10 text-success">
                          {t('dialogs:conflictDetails.autoMergeBadge')}
                        </Badge>
                      )}
                    </div>
                  </div>
                  <div className="text-xs text-muted-foreground space-y-1">
                    {conflict.location && (
                      <div><span className="text-foreground/70">{t('dialogs:conflictDetails.location')}</span> {conflict.location}</div>
                    )}
                    {conflict.reason && (
                      <div><span className="text-foreground/70">{t('dialogs:conflictDetails.reason')}</span> {conflict.reason}</div>
                    )}
                    {/* Display AI-suggested resolution strategies with selection */}
                    {conflict.resolutionStrategies && conflict.resolutionStrategies.length > 0 && (
                      <div className="mt-2 pt-2 border-t border-border/50">
                        <div className="text-foreground/70 mb-1.5 font-medium">{t('dialogs:conflictDetails.aiStrategies')}</div>
                        <RadioGroup
                          value={selectedStrategies[idx] || ''}
                          onValueChange={(value) => {
                            const newStrategies = { ...selectedStrategies, [idx]: value };
                            setSelectedStrategies(newStrategies);
                            // Notify parent of strategy changes
                            if (onStrategiesChange) {
                              const resolutions: Record<string, string> = {};
                              Object.entries(newStrategies).forEach(([i, s]) => {
                                const conflictIdx = parseInt(i, 10);
                                const c = mergePreview?.conflicts[conflictIdx];
                                if (c && s) resolutions[c.file] = s;
                              });
                              onStrategiesChange(resolutions);
                            }
                          }}
                          className="space-y-2"
                        >
                          {conflict.resolutionStrategies.map((strategy, strategyIdx) => (
                            <div key={strategyIdx} className="flex items-start gap-2">
                              <RadioGroupItem
                                value={strategy}
                                id={`strategy-${idx}-${strategyIdx}`}
                                className="mt-0.5"
                              />
                              <Label
                                htmlFor={`strategy-${idx}-${strategyIdx}`}
                                className="text-foreground/80 flex-1 cursor-pointer text-xs leading-relaxed"
                              >
                                {strategy}
                              </Label>
                            </div>
                          ))}
                        </RadioGroup>
                      </div>
                    )}
                    {/* Fallback to single strategy field if no resolutionStrategies */}
                    {!conflict.resolutionStrategies && conflict.strategy && (
                      <div><span className="text-foreground/70">{t('dialogs:conflictDetails.strategy')}</span> {conflict.strategy}</div>
                    )}
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="text-center py-8 text-muted-foreground">
              {t('dialogs:conflictDetails.noConflicts')}
            </div>
          )}
        </div>
        <AlertDialogFooter className="mt-4">
          <AlertDialogCancel>{t('dialogs:conflictDetails.close')}</AlertDialogCancel>
          <AlertDialogAction
            onClick={(e) => {
              e.preventDefault();
              onOpenChange(false);
              const resolutions = convertToConflictResolutions();
              onMerge(resolutions);
            }}
            className="bg-warning text-warning-foreground hover:bg-warning/90"
          >
            <GitMerge className="mr-2 h-4 w-4" />
            {stageOnly ? t('dialogs:conflictDetails.stageWithAI') : t('dialogs:conflictDetails.mergeWithAI')}
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  );
}
