import { useMemo } from 'react';
import { useTranslation } from 'react-i18next';
import { FileCode, Plus, Minus } from 'lucide-react';
import { cn } from '../../lib/utils';
import { Badge } from '../ui/badge';
import { ScrollArea } from '../ui/scroll-area';
import { DiffLine } from './DiffLine';
import type { WorktreeDiffFile, DiffHunk } from '../../../shared/types';

interface SideBySideDiffProps {
  file: WorktreeDiffFile;
  className?: string;
}

/**
 * Side-by-side diff viewer component with syntax highlighting and line numbers
 * Displays before/after views with color-coded additions, deletions, and context lines
 */
export function SideBySideDiff({ file, className }: SideBySideDiffProps) {
  const { t } = useTranslation(['dialogs']);
  const { path, status, additions, deletions, hunks = [] } = file;

  // Get file name from path
  const fileName = useMemo(() => path.split('/').pop() || path, [path]);

  // Status badge variant
  const statusBadgeClass = cn(
    'text-xs',
    status === 'added' && 'bg-green-500/10 text-green-600 dark:text-green-400',
    status === 'deleted' && 'bg-red-500/10 text-red-600 dark:text-red-400',
    status === 'modified' && 'bg-blue-500/10 text-blue-600 dark:text-blue-400',
    status === 'renamed' && 'bg-purple-500/10 text-purple-600 dark:text-purple-400'
  );

  return (
    <div className={cn('flex flex-col h-full', className)}>
      {/* File header */}
      <div className="flex items-center justify-between p-3 border-b bg-muted/30">
        <div className="flex items-center gap-2 min-w-0 flex-1">
          <FileCode className="h-4 w-4 text-muted-foreground flex-shrink-0" />
          <div className="min-w-0 flex-1">
            <div className="text-sm font-medium truncate">{fileName}</div>
            <div className="text-xs text-muted-foreground truncate font-mono">{path}</div>
          </div>
        </div>
        <div className="flex items-center gap-2 flex-shrink-0 ml-2">
          {additions > 0 && (
            <div className="flex items-center gap-0.5 text-green-600 dark:text-green-400">
              <Plus className="h-3 w-3" />
              <span className="text-xs font-medium">{additions}</span>
            </div>
          )}
          {deletions > 0 && (
            <div className="flex items-center gap-0.5 text-red-600 dark:text-red-400">
              <Minus className="h-3 w-3" />
              <span className="text-xs font-medium">{deletions}</span>
            </div>
          )}
          <Badge variant="secondary" className={statusBadgeClass}>
            {status}
          </Badge>
        </div>
      </div>

      {/* Diff content */}
      {hunks.length === 0 ? (
        <div className="flex-1 flex items-center justify-center p-8">
          <div className="text-center">
            <FileCode className="h-8 w-8 text-muted-foreground mx-auto mb-2" />
            <p className="text-sm text-muted-foreground">
              {status === 'added' ? t('dialogs:worktreeDiff.newFile') :
               status === 'deleted' ? t('dialogs:worktreeDiff.deletedFile') :
               t('dialogs:worktreeDiff.noDiff')}
            </p>
          </div>
        </div>
      ) : (
        <ScrollArea className="flex-1">
          <div className="grid grid-cols-2 divide-x">
            {/* Left side (before) */}
            <div className="flex flex-col">
              {/* Column header */}
              <div className="sticky top-0 z-10 px-3 py-2 text-xs font-medium text-muted-foreground bg-muted/50 border-b">
                {t('dialogs:worktreeDiff.before')}
              </div>
              {/* Lines */}
              <div className="flex flex-col">
                {hunks.map((hunk, hunkIdx) => (
                  <div key={hunkIdx} className="flex flex-col">
                    {/* Hunk header */}
                    <div className="px-3 py-1 text-xs font-mono text-muted-foreground bg-muted/30 border-y">
                      {hunk.header}
                    </div>
                    {/* Hunk lines */}
                    {hunk.lines.map((line, lineIdx) => (
                      <DiffLine
                        key={`${hunkIdx}-${lineIdx}-left`}
                        line={line}
                        side="left"
                      />
                    ))}
                  </div>
                ))}
              </div>
            </div>

            {/* Right side (after) */}
            <div className="flex flex-col">
              {/* Column header */}
              <div className="sticky top-0 z-10 px-3 py-2 text-xs font-medium text-muted-foreground bg-muted/50 border-b">
                {t('dialogs:worktreeDiff.after')}
              </div>
              {/* Lines */}
              <div className="flex flex-col">
                {hunks.map((hunk, hunkIdx) => (
                  <div key={hunkIdx} className="flex flex-col">
                    {/* Hunk header */}
                    <div className="px-3 py-1 text-xs font-mono text-muted-foreground bg-muted/30 border-y">
                      {hunk.header}
                    </div>
                    {/* Hunk lines */}
                    {hunk.lines.map((line, lineIdx) => (
                      <DiffLine
                        key={`${hunkIdx}-${lineIdx}-right`}
                        line={line}
                        side="right"
                      />
                    ))}
                  </div>
                ))}
              </div>
            </div>
          </div>
        </ScrollArea>
      )}
    </div>
  );
}
