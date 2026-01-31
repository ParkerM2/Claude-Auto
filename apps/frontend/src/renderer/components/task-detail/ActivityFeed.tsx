import { memo, useRef, useEffect, useMemo } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import { useTranslation } from 'react-i18next';
import {
  FileText,
  Pencil,
  Terminal,
  Search,
  FolderSearch,
  Wrench,
  FileCode,
  Brain,
  CheckCircle2,
  PlayCircle,
  ArrowRight,
  Activity
} from 'lucide-react';
import { cn } from '../../lib/utils';
import type { RecentAction, RecentActionType } from '../../../shared/types';

interface ActivityFeedProps {
  /** Array of recent actions to display (will show last 10) */
  actions: RecentAction[];
  /** Maximum number of actions to display (default: 10) */
  maxActions?: number;
  /** Whether the task is currently running (for styling) */
  isRunning?: boolean;
  /** Optional className for styling */
  className?: string;
}

// Action type display configuration
interface ActionTypeConfig {
  icon: typeof FileText;
  color: string;
  bgColor: string;
}

// Map tool names to their display configuration (matches TaskLogs.tsx)
const getToolConfig = (toolName: string): ActionTypeConfig => {
  switch (toolName) {
    case 'Read':
      return {
        icon: FileText,
        color: 'text-blue-500',
        bgColor: 'bg-blue-500/10'
      };
    case 'Glob':
      return {
        icon: FolderSearch,
        color: 'text-amber-500',
        bgColor: 'bg-amber-500/10'
      };
    case 'Grep':
      return {
        icon: Search,
        color: 'text-green-500',
        bgColor: 'bg-green-500/10'
      };
    case 'Edit':
      return {
        icon: Pencil,
        color: 'text-purple-500',
        bgColor: 'bg-purple-500/10'
      };
    case 'Write':
      return {
        icon: FileCode,
        color: 'text-cyan-500',
        bgColor: 'bg-cyan-500/10'
      };
    case 'Bash':
      return {
        icon: Terminal,
        color: 'text-orange-500',
        bgColor: 'bg-orange-500/10'
      };
    default:
      return {
        icon: Wrench,
        color: 'text-muted-foreground',
        bgColor: 'bg-muted'
      };
  }
};

// Map action types to their display configuration
const getActionTypeConfig = (type: RecentActionType, toolName?: string): ActionTypeConfig => {
  // For tool_use, use the specific tool configuration
  if (type === 'tool_use' && toolName) {
    return getToolConfig(toolName);
  }

  switch (type) {
    case 'file_edit':
      return {
        icon: Pencil,
        color: 'text-purple-500',
        bgColor: 'bg-purple-500/10'
      };
    case 'file_create':
      return {
        icon: FileCode,
        color: 'text-cyan-500',
        bgColor: 'bg-cyan-500/10'
      };
    case 'command':
      return {
        icon: Terminal,
        color: 'text-orange-500',
        bgColor: 'bg-orange-500/10'
      };
    case 'thinking':
      return {
        icon: Brain,
        color: 'text-violet-500',
        bgColor: 'bg-violet-500/10'
      };
    case 'subtask_start':
      return {
        icon: PlayCircle,
        color: 'text-info',
        bgColor: 'bg-info/10'
      };
    case 'subtask_complete':
      return {
        icon: CheckCircle2,
        color: 'text-success',
        bgColor: 'bg-success/10'
      };
    case 'phase_change':
      return {
        icon: ArrowRight,
        color: 'text-amber-500',
        bgColor: 'bg-amber-500/10'
      };
    default:
      return {
        icon: Wrench,
        color: 'text-muted-foreground',
        bgColor: 'bg-muted'
      };
  }
};

// Format timestamp to compact time string (HH:MM:SS)
const formatTime = (timestamp: Date | string): string => {
  try {
    const date = timestamp instanceof Date ? timestamp : new Date(timestamp);
    return date.toLocaleTimeString('en-US', {
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
      hour12: false
    });
  } catch {
    return '';
  }
};

// Individual activity item component
interface ActivityItemProps {
  action: RecentAction;
  isLatest: boolean;
}

const ActivityItem = memo(function ActivityItem({ action, isLatest }: ActivityItemProps) {
  const config = getActionTypeConfig(action.type, action.toolName);
  const Icon = config.icon;

  return (
    <motion.div
      initial={{ opacity: 0, y: -5, height: 0 }}
      animate={{ opacity: 1, y: 0, height: 'auto' }}
      exit={{ opacity: 0, height: 0 }}
      transition={{ duration: 0.15 }}
      className={cn(
        'flex items-center gap-2 py-1.5 px-2 rounded-md transition-colors',
        isLatest ? config.bgColor : 'hover:bg-secondary/30',
        isLatest && 'border border-current/10'
      )}
    >
      {/* Timestamp */}
      <span className="text-[10px] text-muted-foreground/60 tabular-nums shrink-0 w-14">
        {formatTime(action.timestamp)}
      </span>

      {/* Action icon */}
      <div
        className={cn(
          'shrink-0 h-5 w-5 rounded-full flex items-center justify-center',
          config.bgColor
        )}
      >
        <Icon className={cn('h-3 w-3', config.color)} />
      </div>

      {/* Action description */}
      <span
        className={cn(
          'text-xs truncate flex-1',
          isLatest ? 'text-foreground font-medium' : 'text-muted-foreground'
        )}
        title={action.description}
      >
        {action.description}
      </span>

      {/* Latest indicator pulse */}
      {isLatest && (
        <motion.div
          className={cn('h-1.5 w-1.5 rounded-full shrink-0', config.color.replace('text-', 'bg-'))}
          animate={{
            scale: [1, 1.5, 1],
            opacity: [0.5, 1, 0.5]
          }}
          transition={{
            duration: 1.5,
            repeat: Infinity,
            ease: 'easeInOut'
          }}
        />
      )}
    </motion.div>
  );
});

/**
 * ActivityFeed displays a compact, scrollable list of recent agent actions
 * with timestamps and action-specific icons.
 *
 * Features:
 * - Shows the last N actions (default: 10)
 * - Auto-scrolls to latest action
 * - Compact vertical layout with timestamps
 * - Highlights the most recent action
 * - Smooth animations for new actions
 */
export const ActivityFeed = memo(function ActivityFeed({
  actions,
  maxActions = 10,
  isRunning = false,
  className
}: ActivityFeedProps) {
  const { t } = useTranslation('tasks');
  const scrollContainerRef = useRef<HTMLDivElement>(null);

  // Limit to maxActions and reverse to show newest at top
  const displayActions = useMemo(() => {
    const limited = actions.slice(-maxActions);
    // Return in reverse order (newest first) for top-to-bottom display
    return [...limited].reverse();
  }, [actions, maxActions]);

  // Auto-scroll to top when new actions arrive (newest is at top)
  useEffect(() => {
    if (scrollContainerRef.current && displayActions.length > 0) {
      scrollContainerRef.current.scrollTop = 0;
    }
  }, [displayActions.length]);

  // Empty state
  if (displayActions.length === 0) {
    return (
      <div className={cn('flex flex-col gap-2', className)}>
        <div className="flex items-center gap-2 text-xs text-muted-foreground">
          <Activity className="h-3.5 w-3.5" />
          <span className="font-medium">{t('execution.activity.title')}</span>
        </div>
        <div className="flex items-center justify-center py-4 px-2 rounded-lg border border-dashed border-border bg-secondary/20">
          <span className="text-xs text-muted-foreground">
            {t('execution.activity.noActivity')}
          </span>
        </div>
      </div>
    );
  }

  return (
    <div className={cn('flex flex-col gap-2', className)}>
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2 text-xs text-muted-foreground">
          <Activity className="h-3.5 w-3.5" />
          <span className="font-medium">{t('execution.activity.title')}</span>
          <span className="text-[10px] text-muted-foreground/60">
            ({displayActions.length})
          </span>
        </div>

        {/* Running indicator */}
        {isRunning && (
          <div className="flex items-center gap-1">
            <motion.div
              className="h-1.5 w-1.5 rounded-full bg-info"
              animate={{
                scale: [1, 1.2, 1],
                opacity: [0.7, 1, 0.7]
              }}
              transition={{
                duration: 1,
                repeat: Infinity,
                ease: 'easeInOut'
              }}
            />
            <span className="text-[10px] text-info">Live</span>
          </div>
        )}
      </div>

      {/* Scrollable feed container */}
      <div
        ref={scrollContainerRef}
        className={cn(
          'overflow-y-auto overflow-x-hidden',
          'scrollbar-thin scrollbar-thumb-border scrollbar-track-transparent',
          'rounded-lg border border-border bg-secondary/10',
          'max-h-[180px]'
        )}
      >
        <div className="p-1.5 space-y-0.5">
          <AnimatePresence mode="popLayout" initial={false}>
            {displayActions.map((action, index) => (
              <ActivityItem
                key={action.id}
                action={action}
                isLatest={index === 0 && isRunning}
              />
            ))}
          </AnimatePresence>
        </div>
      </div>
    </div>
  );
});
