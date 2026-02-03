import { motion, AnimatePresence } from 'motion/react';
import { useTranslation } from 'react-i18next';
import { memo } from 'react';
import { cn } from '../../lib/utils';
import { usePhaseProgress, PHASE_COLORS } from './hooks/usePhaseProgress';
import { SubtaskDot } from '../ui/subtask-dot';
import type { ExecutionPhase, TaskLogs, Subtask } from '../../../shared/types';

interface PhaseProgressIndicatorProps {
  phase?: ExecutionPhase;
  subtasks: Subtask[];
  phaseLogs?: TaskLogs | null;
  /** Fallback progress percentage (0-100) when phaseLogs unavailable */
  phaseProgress?: number;
  isStuck?: boolean;
  isRunning?: boolean;
  className?: string;
}

/**
 * Smart progress indicator that adapts based on execution phase:
 * - Planning/Validation: Shows animated activity bar with entry count
 * - Coding: Shows subtask-based percentage progress
 * - Stuck: Shows warning state with interrupted animation
 *
 * Performance: Uses IntersectionObserver to pause animations when not visible
 *
 * Layout: Progress label | Subtask dots | Percentage + overflow
 */
export const PhaseProgressIndicator = memo(function PhaseProgressIndicator({
  phase: rawPhase,
  subtasks,
  phaseLogs,
  phaseProgress,
  isStuck = false,
  isRunning = false,
  className,
}: PhaseProgressIndicatorProps) {
  const { t } = useTranslation('tasks');

  const presenter = usePhaseProgress({
    phase: rawPhase,
    subtasks,
    phaseLogs,
    phaseProgress,
    isStuck,
    isRunning,
  });

  return (
    <div ref={presenter.containerRef} className={cn('space-y-1.5', className)}>
      {/* Progress row - aligned layout: Label | Dots | Percentage */}
      <div className="flex items-center justify-between gap-2">
        {/* Left: Progress label */}
        <div className="flex items-center gap-2 shrink-0">
          <span className="text-xs text-muted-foreground">
            {isStuck ? t('execution.labels.interrupted') : presenter.showSubtaskProgress ? t('execution.labels.progress') : presenter.phaseLabel}
          </span>
          {/* Activity indicator dot for non-coding phases - only animate when visible */}
          {isRunning && !isStuck && presenter.isIndeterminatePhase && (
            <motion.div
              className={cn('h-1.5 w-1.5 rounded-full', presenter.colors.color)}
              animate={presenter.shouldAnimate ? {
                scale: [1, 1.5, 1],
                opacity: [1, 0.5, 1],
              } : { scale: 1, opacity: 1 }}
              transition={presenter.shouldAnimate ? {
                duration: 1,
                repeat: Infinity,
                ease: 'easeInOut',
              } : undefined}
            />
          )}
        </div>

        {/* Center: Subtask dots in a row (only show when subtasks exist) */}
        {presenter.totalCount > 0 && (
          <div className="flex items-center gap-1 flex-1 justify-center min-w-0">
            <div className="flex items-center gap-1">
              {presenter.visibleDots.map((subtask, index) => {
                const isInProgress = subtask.status === 'in_progress';
                const shouldPulse = isInProgress && presenter.isVisible;

                return (
                  <motion.div
                    key={subtask.id}
                    initial={{ scale: 0, opacity: 0 }}
                    animate={{
                      scale: 1,
                      opacity: 1,
                      ...(shouldPulse && {
                        boxShadow: [
                          '0 0 0 0 rgba(var(--info), 0.4)',
                          '0 0 0 4px rgba(var(--info), 0)',
                        ],
                      }),
                    }}
                    transition={{
                      scale: { delay: index * 0.03, duration: 0.2 },
                      opacity: { delay: index * 0.03, duration: 0.2 },
                      boxShadow: shouldPulse
                        ? { duration: 1, repeat: Infinity, ease: 'easeOut' }
                        : undefined,
                    }}
                  >
                    <SubtaskDot
                      status={subtask.status}
                      size="sm"
                      title={`${subtask.title || subtask.id}: ${subtask.status}`}
                    />
                  </motion.div>
                );
              })}
            </div>
            {/* Overflow count */}
            {presenter.overflowCount > 0 && (
              <span className="text-[10px] text-muted-foreground font-medium ml-0.5">
                +{presenter.overflowCount}
              </span>
            )}
          </div>
        )}

        {/* Right: Percentage */}
        <span className="text-xs font-medium text-foreground shrink-0">
          {presenter.showSubtaskProgress ? (
            `${presenter.percentage}%`
          ) : presenter.activeEntries > 0 ? (
            <span className="text-muted-foreground">
              {presenter.activeEntries} {presenter.activeEntries === 1 ? t('execution.labels.entry') : t('execution.labels.entries')}
            </span>
          ) : isRunning && presenter.isIndeterminatePhase && (phaseProgress ?? 0) > 0 ? (
            `${Math.round(Math.min(phaseProgress!, 100))}%`
          ) : (
            '—'
          )}
        </span>
      </div>

      {/* Progress bar */}
      <div
        className={cn(
          'relative h-1.5 w-full overflow-hidden rounded-full',
          isStuck ? 'bg-warning/20' : 'bg-border'
        )}
      >
        <AnimatePresence mode="wait">
          {isStuck ? (
            // Stuck/Interrupted state - pulsing warning bar (only animate when visible)
            <motion.div
              key="stuck"
              className="absolute inset-0 bg-warning/40"
              initial={{ opacity: 0 }}
              animate={presenter.isVisible ? { opacity: [0.3, 0.6, 0.3] } : { opacity: 0.45 }}
              transition={presenter.isVisible ? { duration: 2, repeat: Infinity, ease: 'easeInOut' } : undefined}
            />
          ) : presenter.showSubtaskProgress ? (
            // Determinate progress for coding phase
            <motion.div
              key="determinate"
              className={cn('h-full rounded-full', presenter.colors.color)}
              initial={{ width: 0 }}
              animate={{ width: `${presenter.percentage}%` }}
              transition={{ duration: 0.5, ease: 'easeOut' }}
            />
          ) : presenter.shouldAnimate && presenter.isIndeterminatePhase ? (
            // Indeterminate animated progress for planning/validation (only when visible)
            <motion.div
              key="indeterminate"
              className={cn('absolute h-full w-1/3 rounded-full', presenter.colors.color)}
              animate={{
                x: ['-100%', '400%'],
              }}
              transition={{
                duration: 1.5,
                repeat: Infinity,
                ease: 'easeInOut',
              }}
            />
          ) : isRunning && presenter.isIndeterminatePhase && !presenter.isVisible ? (
            // Static placeholder when not visible but running
            <motion.div
              key="indeterminate-static"
              className={cn('absolute h-full w-1/3 rounded-full left-1/3', presenter.colors.color)}
            />
          ) : null}
        </AnimatePresence>
      </div>

      {/* Phase steps indicator (shows overall flow) */}
      {(isRunning || presenter.phase !== 'idle') && (
        <PhaseStepsIndicator currentPhase={presenter.phase} isStuck={isStuck} isVisible={presenter.isVisible} />
      )}
    </div>
  );
});

/**
 * Mini phase steps indicator showing the overall flow
 */
const PhaseStepsIndicator = memo(function PhaseStepsIndicator({
  currentPhase,
  isStuck,
  isVisible = true,
}: {
  currentPhase: ExecutionPhase;
  isStuck: boolean;
  isVisible?: boolean;
}) {
  const { t } = useTranslation('tasks');

  const phases: { key: ExecutionPhase; labelKey: string }[] = [
    { key: 'planning', labelKey: 'execution.shortPhases.plan' },
    { key: 'coding', labelKey: 'execution.shortPhases.code' },
    { key: 'qa_review', labelKey: 'execution.shortPhases.qa' },
  ];

  const getPhaseState = (phaseKey: ExecutionPhase) => {
    const phaseOrder = ['planning', 'coding', 'qa_review', 'qa_fixing', 'complete'];
    const currentIndex = phaseOrder.indexOf(currentPhase);
    const phaseIndex = phaseOrder.indexOf(phaseKey);

    if (currentPhase === 'failed') return 'failed';
    if (currentPhase === 'complete') return 'complete';
    if (phaseKey === currentPhase || (phaseKey === 'qa_review' && currentPhase === 'qa_fixing')) {
      return isStuck ? 'stuck' : 'active';
    }
    if (phaseIndex < currentIndex) return 'complete';
    return 'pending';
  };

  return (
    <div className="flex items-center gap-1 mt-2">
      {phases.map((phase, index) => {
        const state = getPhaseState(phase.key);
        const shouldAnimate = state === 'active' && !isStuck && isVisible;

        return (
          <div key={phase.key} className="flex items-center">
            <motion.div
              className={cn(
                'flex items-center gap-1 px-1.5 py-0.5 rounded text-[9px] font-medium',
                state === 'complete' && 'bg-success/10 text-success',
                state === 'active' && 'bg-primary/10 text-primary',
                state === 'stuck' && 'bg-warning/10 text-warning',
                state === 'failed' && 'bg-destructive/10 text-destructive',
                state === 'pending' && 'bg-muted text-muted-foreground'
              )}
              animate={shouldAnimate ? { opacity: [1, 0.6, 1] } : { opacity: 1 }}
              transition={shouldAnimate ? { duration: 1.5, repeat: Infinity, ease: 'easeInOut' } : undefined}
            >
              {state === 'complete' && (
                <svg className="h-2.5 w-2.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" />
                </svg>
              )}
              {t(phase.labelKey)}
            </motion.div>
            {index < phases.length - 1 && (
              <div
                className={cn(
                  'w-2 h-px mx-0.5',
                  getPhaseState(phases[index + 1].key) !== 'pending' ? 'bg-success/50' : 'bg-border'
                )}
              />
            )}
          </div>
        );
      })}
    </div>
  );
});
