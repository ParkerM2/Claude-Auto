import { memo, useRef, useState, useEffect } from 'react';
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
  Loader2
} from 'lucide-react';
import { cn } from '../../lib/utils';
import type { RecentAction, RecentActionType, ExecutionPhase } from '../../../shared/types';

interface CurrentActionIndicatorProps {
  /** The current/most recent action being performed */
  currentAction?: RecentAction | null;
  /** Current execution phase for context-aware display */
  phase?: ExecutionPhase;
  /** Whether the task is currently running */
  isRunning?: boolean;
  /** Whether the task is stuck/interrupted */
  isStuck?: boolean;
  /** Optional className for styling */
  className?: string;
}

// Action type display configuration
interface ActionTypeConfig {
  icon: typeof FileText;
  label: string;
  color: string;
  bgColor: string;
}

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
        label: 'editingFile',
        color: 'text-purple-500',
        bgColor: 'bg-purple-500/10'
      };
    case 'file_create':
      return {
        icon: FileCode,
        label: 'creatingFile',
        color: 'text-cyan-500',
        bgColor: 'bg-cyan-500/10'
      };
    case 'command':
      return {
        icon: Terminal,
        label: 'executingCommand',
        color: 'text-orange-500',
        bgColor: 'bg-orange-500/10'
      };
    case 'thinking':
      return {
        icon: Brain,
        label: 'analyzing',
        color: 'text-violet-500',
        bgColor: 'bg-violet-500/10'
      };
    case 'subtask_start':
      return {
        icon: PlayCircle,
        label: 'startingSubtask',
        color: 'text-info',
        bgColor: 'bg-info/10'
      };
    case 'subtask_complete':
      return {
        icon: CheckCircle2,
        label: 'completedSubtask',
        color: 'text-success',
        bgColor: 'bg-success/10'
      };
    case 'phase_change':
      return {
        icon: ArrowRight,
        label: 'changingPhase',
        color: 'text-amber-500',
        bgColor: 'bg-amber-500/10'
      };
    default:
      return {
        icon: Wrench,
        label: 'working',
        color: 'text-muted-foreground',
        bgColor: 'bg-muted'
      };
  }
};

// Map tool names to their display configuration (similar to TaskLogs.tsx)
const getToolConfig = (toolName: string): ActionTypeConfig => {
  switch (toolName) {
    case 'Read':
      return {
        icon: FileText,
        label: 'readingFile',
        color: 'text-blue-500',
        bgColor: 'bg-blue-500/10'
      };
    case 'Glob':
      return {
        icon: FolderSearch,
        label: 'searchingFiles',
        color: 'text-amber-500',
        bgColor: 'bg-amber-500/10'
      };
    case 'Grep':
      return {
        icon: Search,
        label: 'searchingCode',
        color: 'text-green-500',
        bgColor: 'bg-green-500/10'
      };
    case 'Edit':
      return {
        icon: Pencil,
        label: 'editingFile',
        color: 'text-purple-500',
        bgColor: 'bg-purple-500/10'
      };
    case 'Write':
      return {
        icon: FileCode,
        label: 'writingFile',
        color: 'text-cyan-500',
        bgColor: 'bg-cyan-500/10'
      };
    case 'Bash':
      return {
        icon: Terminal,
        label: 'runningCommand',
        color: 'text-orange-500',
        bgColor: 'bg-orange-500/10'
      };
    default:
      return {
        icon: Wrench,
        label: 'usingTool',
        color: 'text-muted-foreground',
        bgColor: 'bg-muted'
      };
  }
};

// Translation key mapping for action labels
const ACTION_LABEL_KEYS: Record<string, string> = {
  readingFile: 'execution.activity.actions.readingFile',
  writingFile: 'execution.activity.actions.writingFile',
  editingFile: 'execution.activity.actions.writingFile',
  creatingFile: 'execution.activity.actions.writingFile',
  searchingFiles: 'execution.activity.actions.analyzingCode',
  searchingCode: 'execution.activity.actions.analyzingCode',
  runningCommand: 'execution.activity.actions.executingCommand',
  executingCommand: 'execution.activity.actions.executingCommand',
  analyzing: 'execution.activity.actions.analyzingCode',
  startingSubtask: 'execution.activity.actions.analyzingCode',
  completedSubtask: 'execution.activity.actions.reviewingChanges',
  changingPhase: 'execution.activity.actions.creatingPlan',
  working: 'execution.activity.actions.waiting',
  usingTool: 'execution.activity.actions.analyzingCode'
};

/**
 * CurrentActionIndicator displays the current agent action prominently
 * with appropriate icon and animation.
 *
 * Features:
 * - Shows what the agent is currently doing (e.g., 'Reading file X', 'Running tests')
 * - Uses action-specific icons and colors
 * - Animated pulse effect when actively working
 * - IntersectionObserver to pause animations when not visible (performance)
 */
export const CurrentActionIndicator = memo(function CurrentActionIndicator({
  currentAction,
  phase,
  isRunning = false,
  isStuck = false,
  className
}: CurrentActionIndicatorProps) {
  const { t } = useTranslation('tasks');
  const containerRef = useRef<HTMLDivElement>(null);
  const [isVisible, setIsVisible] = useState(true);

  // Use IntersectionObserver to pause animations when component is not visible
  useEffect(() => {
    const element = containerRef.current;
    if (!element) return;

    const observer = new IntersectionObserver(
      ([entry]) => {
        setIsVisible(entry.isIntersecting);
      },
      { threshold: 0.1 }
    );

    observer.observe(element);
    return () => observer.disconnect();
  }, []);

  // Only animate when visible and running
  const shouldAnimate = isVisible && isRunning && !isStuck;

  // Get action configuration
  const actionConfig = currentAction
    ? getActionTypeConfig(currentAction.type, currentAction.toolName)
    : null;

  const Icon = actionConfig?.icon || Loader2;

  // Build the description text
  const getDescription = (): string => {
    if (!currentAction) {
      return t('execution.activity.actions.waiting');
    }

    // If action has a description, use it
    if (currentAction.description) {
      // Try to localize file-based actions
      if (currentAction.filePath) {
        const fileName = currentAction.filePath.split('/').pop() || currentAction.filePath;
        if (currentAction.type === 'file_edit' || currentAction.toolName === 'Edit') {
          return t('execution.activity.actions.writingFile', { file: fileName });
        }
        if (currentAction.type === 'file_create' || currentAction.toolName === 'Write') {
          return t('execution.activity.actions.writingFile', { file: fileName });
        }
        if (currentAction.toolName === 'Read') {
          return t('execution.activity.actions.readingFile', { file: fileName });
        }
      }
      return currentAction.description;
    }

    // Fall back to generic action label
    const labelKey = actionConfig ? ACTION_LABEL_KEYS[actionConfig.label] : null;
    return labelKey ? t(labelKey) : t('execution.activity.actions.waiting');
  };

  // Show waiting state when not running
  if (!isRunning && !currentAction) {
    return (
      <div ref={containerRef} className={cn('flex items-center gap-2 py-2', className)}>
        <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-muted text-muted-foreground">
          <Loader2 className="h-4 w-4" />
          <span className="text-sm">{t('execution.activity.actions.waiting')}</span>
        </div>
      </div>
    );
  }

  // Show interrupted state when stuck
  if (isStuck) {
    return (
      <div ref={containerRef} className={cn('flex items-center gap-2 py-2', className)}>
        <motion.div
          className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-warning/10 text-warning border border-warning/20"
          initial={{ opacity: 0 }}
          animate={isVisible ? { opacity: [0.6, 1, 0.6] } : { opacity: 0.8 }}
          transition={isVisible ? { duration: 2, repeat: Infinity, ease: 'easeInOut' } : undefined}
        >
          <Icon className="h-4 w-4" />
          <span className="text-sm font-medium">{t('execution.labels.interrupted')}</span>
        </motion.div>
      </div>
    );
  }

  return (
    <div ref={containerRef} className={cn('flex items-center gap-2 py-2', className)}>
      <AnimatePresence mode="wait">
        <motion.div
          key={currentAction?.id || 'loading'}
          className={cn(
            'flex items-center gap-2 px-3 py-1.5 rounded-lg border',
            actionConfig?.bgColor || 'bg-muted',
            actionConfig?.color || 'text-muted-foreground',
            'border-current/20'
          )}
          initial={{ opacity: 0, x: -10 }}
          animate={{ opacity: 1, x: 0 }}
          exit={{ opacity: 0, x: 10 }}
          transition={{ duration: 0.2 }}
        >
          {/* Animated icon */}
          <motion.div
            animate={shouldAnimate ? {
              scale: [1, 1.1, 1],
              opacity: [1, 0.7, 1]
            } : { scale: 1, opacity: 1 }}
            transition={shouldAnimate ? {
              duration: 1.5,
              repeat: Infinity,
              ease: 'easeInOut'
            } : undefined}
          >
            <Icon className="h-4 w-4" />
          </motion.div>

          {/* Action description */}
          <span className="text-sm font-medium truncate max-w-[280px]">
            {getDescription()}
          </span>

          {/* Activity pulse indicator */}
          {shouldAnimate && (
            <motion.div
              className={cn('h-2 w-2 rounded-full', actionConfig?.color?.replace('text-', 'bg-') || 'bg-info')}
              animate={{
                scale: [1, 1.5, 1],
                opacity: [0.5, 1, 0.5]
              }}
              transition={{
                duration: 1,
                repeat: Infinity,
                ease: 'easeInOut'
              }}
            />
          )}
        </motion.div>
      </AnimatePresence>

      {/* Phase context badge (optional) */}
      {phase && phase !== 'idle' && (
        <span className="text-[10px] text-muted-foreground/60 uppercase tracking-wider">
          {t(`execution.phases.${phase}`)}
        </span>
      )}
    </div>
  );
});
