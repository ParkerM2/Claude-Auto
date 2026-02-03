import { useState, useEffect } from 'react';
import { useTaskStore } from '../../../stores/task-store';

interface UseActiveAgentsResult {
  activeCount: number;
  isActive: boolean;
}

/**
 * Presenter hook for tracking active (running) agent count.
 * Subscribes to task store to monitor tasks with status 'in_progress'.
 */
export function useActiveAgents(): UseActiveAgentsResult {
  const [activeCount, setActiveCount] = useState(0);

  // Subscribe to task store changes
  const tasks = useTaskStore((state) => state.tasks);

  useEffect(() => {
    // Count tasks that are actively running (in_progress status)
    const runningTasks = tasks.filter(
      (task) => task.status === 'in_progress' && !task.metadata?.archivedAt
    );
    setActiveCount(runningTasks.length);
  }, [tasks]);

  return {
    activeCount,
    isActive: activeCount > 0,
  };
}
