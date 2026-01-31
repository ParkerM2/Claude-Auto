import { memo, useRef, useState, useEffect, useCallback } from 'react';
import { motion } from 'motion/react';
import { useTranslation } from 'react-i18next';
import { Clock, CheckCircle2 } from 'lucide-react';
import { cn } from '../../lib/utils';
import { estimateRemainingTime, formatRemainingTime } from '../../../shared/progress';

interface EstimatedTimeRemainingProps {
  /** Start time of the execution */
  startTime?: Date | null;
  /** Current progress percentage (0-100) */
  progress: number;
  /** Whether the task is currently running */
  isRunning?: boolean;
  /** Whether the task is completed */
  isCompleted?: boolean;
  /** Optional className for styling */
  className?: string;
  /** Update interval in milliseconds (default: 1000ms) */
  updateInterval?: number;
}

/**
 * EstimatedTimeRemaining displays the estimated time to completion
 * using the existing estimateRemainingTime function, with live updates.
 *
 * Features:
 * - Calculates remaining time based on elapsed time and progress
 * - Updates live while task is running
 * - Uses IntersectionObserver to pause updates when not visible (performance)
 * - Smooth transitions between time estimates
 * - i18n support for all labels
 */
export const EstimatedTimeRemaining = memo(function EstimatedTimeRemaining({
  startTime,
  progress,
  isRunning = false,
  isCompleted = false,
  className,
  updateInterval = 1000
}: EstimatedTimeRemainingProps) {
  const { t } = useTranslation('tasks');
  const containerRef = useRef<HTMLDivElement>(null);
  const [isVisible, setIsVisible] = useState(true);
  const [remainingTime, setRemainingTime] = useState<number | null>(null);

  // Calculate remaining time
  const calculateRemaining = useCallback(() => {
    if (!startTime || progress <= 0 || progress >= 100 || isCompleted) {
      return null;
    }
    return estimateRemainingTime(new Date(startTime), progress);
  }, [startTime, progress, isCompleted]);

  // Use IntersectionObserver to pause updates when component is not visible
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

  // Update remaining time periodically when visible and running
  useEffect(() => {
    // Initial calculation
    setRemainingTime(calculateRemaining());

    // Only update periodically if visible, running, and not completed
    if (!isVisible || !isRunning || isCompleted) {
      return;
    }

    const intervalId = setInterval(() => {
      setRemainingTime(calculateRemaining());
    }, updateInterval);

    return () => clearInterval(intervalId);
  }, [isVisible, isRunning, isCompleted, calculateRemaining, updateInterval]);

  // Format the remaining time for display
  const getDisplayText = (): string => {
    // Show completed state
    if (isCompleted || progress >= 100) {
      return t('execution.estimatedTime.completed');
    }

    // Show calculating state when no start time or progress is 0
    if (!startTime || progress <= 0) {
      return t('execution.estimatedTime.calculating');
    }

    // Format the remaining time
    const formatted = formatRemainingTime(remainingTime);
    if (!formatted) {
      return t('execution.estimatedTime.unknown');
    }

    return formatted;
  };

  // Determine icon and colors based on state
  const getStateStyles = () => {
    if (isCompleted || progress >= 100) {
      return {
        icon: CheckCircle2,
        iconColor: 'text-success',
        bgColor: 'bg-success/10',
        borderColor: 'border-success/20'
      };
    }

    if (!isRunning) {
      return {
        icon: Clock,
        iconColor: 'text-muted-foreground',
        bgColor: 'bg-muted',
        borderColor: 'border-muted'
      };
    }

    return {
      icon: Clock,
      iconColor: 'text-info',
      bgColor: 'bg-info/10',
      borderColor: 'border-info/20'
    };
  };

  const { icon: Icon, iconColor, bgColor, borderColor } = getStateStyles();
  const displayText = getDisplayText();

  return (
    <div ref={containerRef} className={cn('flex items-center gap-2', className)}>
      <motion.div
        className={cn(
          'flex items-center gap-2 px-3 py-1.5 rounded-lg border text-sm',
          bgColor,
          borderColor
        )}
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ duration: 0.2 }}
      >
        {/* Animated clock icon when running */}
        <motion.div
          animate={
            isRunning && isVisible && !isCompleted
              ? { rotate: [0, 10, -10, 0] }
              : { rotate: 0 }
          }
          transition={
            isRunning && isVisible && !isCompleted
              ? { duration: 2, repeat: Infinity, ease: 'easeInOut' }
              : undefined
          }
        >
          <Icon className={cn('h-4 w-4', iconColor)} />
        </motion.div>

        {/* Label */}
        <span className="text-xs text-muted-foreground">
          {t('execution.estimatedTime.label')}:
        </span>

        {/* Time estimate with smooth transitions */}
        <motion.span
          key={displayText}
          className={cn(
            'font-medium tabular-nums',
            isCompleted || progress >= 100 ? 'text-success' : 'text-foreground'
          )}
          initial={{ opacity: 0, y: -5 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.15 }}
        >
          {displayText}
        </motion.span>

        {/* Pulse indicator when actively calculating */}
        {isRunning && isVisible && !isCompleted && progress > 0 && (
          <motion.div
            className="h-1.5 w-1.5 rounded-full bg-info"
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
    </div>
  );
});
