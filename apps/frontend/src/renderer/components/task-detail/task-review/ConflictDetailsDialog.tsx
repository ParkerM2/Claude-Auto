import { useState } from 'react';
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
  onMerge: () => void;
}

/**
 * Dialog displaying detailed information about merge conflicts
 */
export function ConflictDetailsDialog({
  open,
  mergePreview,
  stageOnly,
  onOpenChange,
  onMerge
}: ConflictDetailsDialogProps) {
  // Track selected strategy for each conflict (indexed by conflict index)
  const [selectedStrategies, setSelectedStrategies] = useState<Record<number, string>>({});

  return (
    <AlertDialog open={open} onOpenChange={onOpenChange}>
      <AlertDialogContent className="max-w-2xl max-h-[80vh] overflow-hidden flex flex-col">
        <AlertDialogHeader>
          <AlertDialogTitle className="flex items-center gap-2">
            <AlertTriangle className="h-5 w-5 text-warning" />
            Merge Conflicts Preview
          </AlertDialogTitle>
          <AlertDialogDescription>
            {mergePreview?.conflicts.length || 0} potential conflict{(mergePreview?.conflicts.length || 0) !== 1 ? 's' : ''} detected.
            {mergePreview && mergePreview.summary.autoMergeable > 0 && (
              <span className="text-success ml-1">
                {mergePreview.summary.autoMergeable} can be auto-merged.
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
                          auto-merge
                        </Badge>
                      )}
                    </div>
                  </div>
                  <div className="text-xs text-muted-foreground space-y-1">
                    {conflict.location && (
                      <div><span className="text-foreground/70">Location:</span> {conflict.location}</div>
                    )}
                    {conflict.reason && (
                      <div><span className="text-foreground/70">Reason:</span> {conflict.reason}</div>
                    )}
                    {/* Display AI-suggested resolution strategies with selection */}
                    {conflict.resolutionStrategies && conflict.resolutionStrategies.length > 0 && (
                      <div className="mt-2 pt-2 border-t border-border/50">
                        <div className="text-foreground/70 mb-1.5 font-medium">AI-Suggested Strategies:</div>
                        <RadioGroup
                          value={selectedStrategies[idx] || ''}
                          onValueChange={(value) => {
                            setSelectedStrategies(prev => ({ ...prev, [idx]: value }));
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
                      <div><span className="text-foreground/70">Strategy:</span> {conflict.strategy}</div>
                    )}
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="text-center py-8 text-muted-foreground">
              No conflicts detected
            </div>
          )}
        </div>
        <AlertDialogFooter className="mt-4">
          <AlertDialogCancel>Close</AlertDialogCancel>
          <AlertDialogAction
            onClick={(e) => {
              e.preventDefault();
              onOpenChange(false);
              onMerge();
            }}
            className="bg-warning text-warning-foreground hover:bg-warning/90"
          >
            <GitMerge className="mr-2 h-4 w-4" />
            {stageOnly ? 'Stage with AI Merge' : 'Merge with AI'}
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  );
}
