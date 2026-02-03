import { useMemo, useRef, useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import type { ExecutionPhase, TaskLogs, Subtask } from '../../../../shared/types';

// Phase display configuration (colors only - labels are translated)
export const PHASE_COLORS: Record<ExecutionPhase, { color: string; bgColor: string }> = {
  idle: { color: 'bg-muted-foreground', bgColor: 'bg-muted' },
  planning: { color: 'bg-amber-500', bgColor: 'bg-amber-500/20' },
  coding: { color: 'bg-info', bgColor: 'bg-info/20' },
  qa_review: { color: 'bg-purple-500', bgColor: 'bg-purple-500/20' },
  qa_fixing: { color: 'bg-orange-500', bgColor: 'bg-orange-500/20' },
  complete: { color: 'bg-success', bgColor: 'bg-success/20' },
  failed: { color: 'bg-destructive', bgColor: 'bg-destructive/20' },
};

// Phase label translation keys
export const PHASE_LABEL_KEYS: Record<ExecutionPhase, string> = {
  idle: 'execution.phases.idle',
  planning: 'execution.phases.planning',
  coding: 'execution.phases.coding',
  qa_review: 'execution.phases.reviewing',
  qa_fixing: 'execution.phases.fixing',
  complete: 'execution.phases.complete',
  failed: 'execution.phases.failed',
};

interface UsePhaseProgressProps {
  phase?: ExecutionPhase;
  subtasks: Subtask[];
  phaseLogs?: TaskLogs | null;
  phaseProgress?: number;
  isStuck?: boolean;
  isRunning?: boolean;
}

interface VisibleSubtask {
  id: string;
  status: 'pending' | 'in_progress' | 'completed' | 'failed';
  title?: string;
}

interface PhaseProgressPresenter {
  // Computed values
  phase: ExecutionPhase;
  completedCount: number;
  totalCount: number;
  percentage: number;
  visibleDots: VisibleSubtask[];
  overflowCount: number;

  // Display helpers
  phaseLabel: string;
  colors: { color: string; bgColor: string };
  activeEntries: number;

  // State flags
  isIndeterminatePhase: boolean;
  showSubtaskProgress: boolean;
  shouldAnimate: boolean;
  isVisible: boolean;

  // Refs
  containerRef: React.RefObject<HTMLDivElement | null>;
}

/**
 * Presenter hook for PhaseProgressIndicator.
 * Contains all logic, state, and computed values.
 */
export function usePhaseProgress({
  phase: rawPhase,
  subtasks,
  phaseLogs,
  phaseProgress,
  isStuck = false,
  isRunning = false,
}: UsePhaseProgressProps): PhaseProgressPresenter {
  const { t } = useTranslation('tasks');
  const phase = rawPhase || 'idle';
  const containerRef = useRef<HTMLDivElement | null>(null);
  const [isVisible, setIsVisible] = useState(true);
  const prevVisibleRef = useRef(true);

  // Use IntersectionObserver to pause animations when component is not visible
  useEffect(() => {
    const element = containerRef.current;
    if (!element) return;

    const observer = new IntersectionObserver(
      ([entry]) => {
        const nowVisible = entry.isIntersecting;

        if (prevVisibleRef.current !== nowVisible && window.DEBUG) {
          console.log(`[PhaseProgress] Visibility changed: ${prevVisibleRef.current} -> ${nowVisible}, animations ${nowVisible ? 'resumed' : 'paused'}`);
        }

        prevVisibleRef.current = nowVisible;
        setIsVisible(nowVisible);
      },
      { threshold: 0.1 }
    );

    observer.observe(element);
    return () => observer.disconnect();
  }, []);

  // Calculate subtask-based progress
  const completedCount = useMemo(
    () => subtasks.filter((s) => s.status === 'completed').length,
    [subtasks]
  );

  const totalCount = subtasks.length;

  const percentage = useMemo(
    () => (totalCount > 0 ? Math.round((completedCount / totalCount) * 100) : 0),
    [completedCount, totalCount]
  );

  // Get visible dots (limited to 10) and overflow count
  const visibleDots = useMemo(
    () => subtasks.slice(0, 10).map((s) => ({
      id: s.id || `subtask-${subtasks.indexOf(s)}`,
      status: s.status,
      title: s.title,
    })),
    [subtasks]
  );

  const overflowCount = totalCount > 10 ? totalCount - 10 : 0;

  // Get log entry counts for activity indication
  const activeEntries = useMemo(() => {
    const planningEntries = phaseLogs?.phases?.planning?.entries?.length || 0;
    const codingEntries = phaseLogs?.phases?.coding?.entries?.length || 0;
    const validationEntries = phaseLogs?.phases?.validation?.entries?.length || 0;

    if (phase === 'planning') return planningEntries;
    if (phase === 'qa_review' || phase === 'qa_fixing') return validationEntries;
    return codingEntries;
  }, [phase, phaseLogs]);

  // Display helpers
  const isIndeterminatePhase = phase === 'planning' || phase === 'qa_review' || phase === 'qa_fixing';
  const showSubtaskProgress = totalCount > 0;
  const shouldAnimate = isVisible && isRunning && !isStuck;
  const colors = PHASE_COLORS[phase] || PHASE_COLORS.idle;
  const phaseLabel = t(PHASE_LABEL_KEYS[phase] || PHASE_LABEL_KEYS.idle);

  return {
    phase,
    completedCount,
    totalCount,
    percentage,
    visibleDots,
    overflowCount,
    phaseLabel,
    colors,
    activeEntries,
    isIndeterminatePhase,
    showSubtaskProgress,
    shouldAnimate,
    isVisible,
    containerRef,
  };
}
