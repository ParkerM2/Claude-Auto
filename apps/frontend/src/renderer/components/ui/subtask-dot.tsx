import { cn } from '../../lib/utils';

type SubtaskStatus = 'pending' | 'in_progress' | 'completed' | 'failed';

interface SubtaskDotProps {
  status: SubtaskStatus;
  size?: 'sm' | 'md';
  className?: string;
  title?: string;
}

/**
 * Single subtask status indicator dot.
 * Color-coded based on status with hover scale effect.
 */
export function SubtaskDot({ status, size = 'sm', className, title }: SubtaskDotProps) {
  return (
    <div
      className={cn(
        'rounded-full transition-transform hover:scale-150',
        size === 'sm' ? 'h-2 w-2' : 'h-2.5 w-2.5',
        status === 'completed' && 'bg-success',
        status === 'in_progress' && 'bg-info',
        status === 'failed' && 'bg-destructive',
        status === 'pending' && 'bg-muted-foreground/30',
        className
      )}
      title={title}
    />
  );
}
