import { cn } from '../../lib/utils';
import type { DiffLine as DiffLineType } from '../../../shared/types';

interface DiffLineProps {
  line: DiffLineType;
  side: 'left' | 'right';
}

/**
 * Individual diff line component with syntax highlighting and line numbers
 */
export function DiffLine({ line, side }: DiffLineProps) {
  const { type, content, oldLineNumber, newLineNumber } = line;

  // Determine which line number to show based on side and line type
  const lineNumber = side === 'left' ? oldLineNumber : newLineNumber;

  // Don't render if this line doesn't belong to this side
  if (side === 'left' && type === 'added') {
    return (
      <div className="flex min-h-[20px] bg-muted/20">
        <div className="w-12 flex-shrink-0 px-2 text-right text-xs text-muted-foreground select-none" />
        <div className="flex-1 px-2 font-mono text-xs" />
      </div>
    );
  }

  if (side === 'right' && type === 'deleted') {
    return (
      <div className="flex min-h-[20px] bg-muted/20">
        <div className="w-12 flex-shrink-0 px-2 text-right text-xs text-muted-foreground select-none" />
        <div className="flex-1 px-2 font-mono text-xs" />
      </div>
    );
  }

  // Background colors based on line type
  const bgClass = cn(
    'flex min-h-[20px]',
    type === 'added' && 'bg-green-500/10 hover:bg-green-500/20',
    type === 'deleted' && 'bg-red-500/10 hover:bg-red-500/20',
    type === 'context' && 'bg-background hover:bg-muted/30'
  );

  // Line number gutter color
  const lineNumClass = cn(
    'w-12 flex-shrink-0 px-2 text-right text-xs select-none border-r',
    type === 'added' && 'text-green-600 dark:text-green-400 bg-green-500/5 border-green-500/20',
    type === 'deleted' && 'text-red-600 dark:text-red-400 bg-red-500/5 border-red-500/20',
    type === 'context' && 'text-muted-foreground bg-muted/10 border-border'
  );

  // Content styling
  const contentClass = cn(
    'flex-1 px-2 font-mono text-xs whitespace-pre overflow-x-auto',
    type === 'added' && 'text-foreground',
    type === 'deleted' && 'text-foreground',
    type === 'context' && 'text-muted-foreground'
  );

  return (
    <div className={bgClass}>
      <div className={lineNumClass}>
        {lineNumber !== undefined ? lineNumber : ''}
      </div>
      <div className={contentClass}>
        {content || '\n'}
      </div>
    </div>
  );
}
