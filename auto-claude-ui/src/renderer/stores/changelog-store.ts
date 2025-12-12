import { create } from 'zustand';
import type {
  ChangelogTask,
  TaskSpecContent,
  ChangelogFormat,
  ChangelogAudience,
  ChangelogGenerationProgress,
  ChangelogGenerationResult,
  ExistingChangelog,
  Task
} from '../../shared/types';
import { useTaskStore } from './task-store';

interface ChangelogState {
  // Data
  doneTasks: ChangelogTask[];
  selectedTaskIds: string[];
  loadedSpecs: TaskSpecContent[];
  existingChangelog: ExistingChangelog | null;

  // Generation config
  version: string;
  date: string;
  format: ChangelogFormat;
  audience: ChangelogAudience;
  customInstructions: string;

  // Generation state
  generationProgress: ChangelogGenerationProgress | null;
  generatedChangelog: string;
  isGenerating: boolean;
  error: string | null;

  // Actions
  setDoneTasks: (tasks: ChangelogTask[]) => void;
  setSelectedTaskIds: (ids: string[]) => void;
  toggleTaskSelection: (taskId: string) => void;
  selectAllTasks: () => void;
  deselectAllTasks: () => void;
  setLoadedSpecs: (specs: TaskSpecContent[]) => void;
  setExistingChangelog: (changelog: ExistingChangelog | null) => void;

  // Config actions
  setVersion: (version: string) => void;
  setDate: (date: string) => void;
  setFormat: (format: ChangelogFormat) => void;
  setAudience: (audience: ChangelogAudience) => void;
  setCustomInstructions: (instructions: string) => void;

  // Generation actions
  setGenerationProgress: (progress: ChangelogGenerationProgress | null) => void;
  setGeneratedChangelog: (changelog: string) => void;
  setIsGenerating: (isGenerating: boolean) => void;
  setError: (error: string | null) => void;

  // Compound actions
  reset: () => void;
  updateGeneratedChangelog: (changelog: string) => void;
}

const getDefaultDate = (): string => {
  return new Date().toISOString().split('T')[0];
};

const initialState = {
  doneTasks: [],
  selectedTaskIds: [],
  loadedSpecs: [],
  existingChangelog: null,

  version: '1.0.0',
  date: getDefaultDate(),
  format: 'keep-a-changelog' as ChangelogFormat,
  audience: 'user-facing' as ChangelogAudience,
  customInstructions: '',

  generationProgress: null,
  generatedChangelog: '',
  isGenerating: false,
  error: null
};

export const useChangelogStore = create<ChangelogState>((set, get) => ({
  ...initialState,

  // Data actions
  setDoneTasks: (tasks) => set({ doneTasks: tasks }),

  setSelectedTaskIds: (ids) => set({ selectedTaskIds: ids }),

  toggleTaskSelection: (taskId) =>
    set((state) => ({
      selectedTaskIds: state.selectedTaskIds.includes(taskId)
        ? state.selectedTaskIds.filter((id) => id !== taskId)
        : [...state.selectedTaskIds, taskId]
    })),

  selectAllTasks: () =>
    set((state) => ({
      selectedTaskIds: state.doneTasks.map((task) => task.id)
    })),

  deselectAllTasks: () => set({ selectedTaskIds: [] }),

  setLoadedSpecs: (specs) => set({ loadedSpecs: specs }),

  setExistingChangelog: (changelog) => {
    set({ existingChangelog: changelog });
    // Auto-suggest next version if we found a previous version
    if (changelog?.lastVersion) {
      const parts = changelog.lastVersion.split('.').map(Number);
      if (parts.length === 3 && !parts.some(isNaN)) {
        const [major, minor, patch] = parts;
        set({ version: `${major}.${minor}.${patch + 1}` });
      }
    }
  },

  // Config actions
  setVersion: (version) => set({ version }),
  setDate: (date) => set({ date }),
  setFormat: (format) => set({ format }),
  setAudience: (audience) => set({ audience }),
  setCustomInstructions: (instructions) => set({ customInstructions: instructions }),

  // Generation actions
  setGenerationProgress: (progress) => set({ generationProgress: progress }),
  setGeneratedChangelog: (changelog) => set({ generatedChangelog: changelog }),
  setIsGenerating: (isGenerating) => set({ isGenerating }),
  setError: (error) => set({ error }),

  // Compound actions
  reset: () => set({ ...initialState, date: getDefaultDate() }),

  updateGeneratedChangelog: (changelog) => set({ generatedChangelog: changelog })
}));

// Helper functions for loading data
export async function loadChangelogData(projectId: string): Promise<void> {
  const store = useChangelogStore.getState();

  try {
    // Get tasks from the task store (which has the correct UI status)
    // This is necessary because the Kanban board updates task status in the Zustand store,
    // but the backend reads from the filesystem which doesn't reflect UI-only changes
    const taskStore = useTaskStore.getState();
    const tasks = taskStore.tasks;

    // Load done tasks - pass the renderer's task list to get correct status
    const tasksResult = await window.electronAPI.getChangelogDoneTasks(projectId, tasks);
    if (tasksResult.success && tasksResult.data) {
      store.setDoneTasks(tasksResult.data);
    }

    // Load existing changelog
    const changelogResult = await window.electronAPI.readExistingChangelog(projectId);
    if (changelogResult.success && changelogResult.data) {
      store.setExistingChangelog(changelogResult.data);
    }
  } catch (error) {
    store.setError(error instanceof Error ? error.message : 'Failed to load changelog data');
  }
}

export async function loadTaskSpecs(projectId: string, taskIds: string[]): Promise<void> {
  const store = useChangelogStore.getState();

  try {
    const result = await window.electronAPI.loadTaskSpecs(projectId, taskIds);
    if (result.success && result.data) {
      store.setLoadedSpecs(result.data);
    }
  } catch (error) {
    store.setError(error instanceof Error ? error.message : 'Failed to load task specs');
  }
}

export function generateChangelog(projectId: string): void {
  const store = useChangelogStore.getState();

  if (store.selectedTaskIds.length === 0) {
    store.setError('Please select at least one task to include in the changelog');
    return;
  }

  store.setIsGenerating(true);
  store.setError(null);
  store.setGenerationProgress({
    stage: 'loading_specs',
    progress: 0,
    message: 'Starting changelog generation...'
  });

  window.electronAPI.generateChangelog({
    projectId,
    taskIds: store.selectedTaskIds,
    version: store.version,
    date: store.date,
    format: store.format,
    audience: store.audience,
    customInstructions: store.customInstructions || undefined
  });
}

export async function saveChangelog(
  projectId: string,
  mode: 'prepend' | 'overwrite' | 'append' = 'prepend'
): Promise<boolean> {
  const store = useChangelogStore.getState();

  if (!store.generatedChangelog) {
    store.setError('No changelog to save');
    return false;
  }

  try {
    const result = await window.electronAPI.saveChangelog({
      projectId,
      content: store.generatedChangelog,
      mode
    });

    if (result.success) {
      return true;
    } else {
      store.setError(result.error || 'Failed to save changelog');
      return false;
    }
  } catch (error) {
    store.setError(error instanceof Error ? error.message : 'Failed to save changelog');
    return false;
  }
}

export function copyChangelogToClipboard(): boolean {
  const store = useChangelogStore.getState();

  if (!store.generatedChangelog) {
    store.setError('No changelog to copy');
    return false;
  }

  try {
    navigator.clipboard.writeText(store.generatedChangelog);
    return true;
  } catch (error) {
    store.setError('Failed to copy to clipboard');
    return false;
  }
}

// Selectors
export function getSelectedTasks(): ChangelogTask[] {
  const store = useChangelogStore.getState();
  return store.doneTasks.filter((task) => store.selectedTaskIds.includes(task.id));
}

export function getTasksWithSpecs(): ChangelogTask[] {
  const store = useChangelogStore.getState();
  return store.doneTasks.filter((task) => task.hasSpecs);
}

export function canGenerate(): boolean {
  const store = useChangelogStore.getState();
  return store.selectedTaskIds.length > 0 && !store.isGenerating;
}

export function canSave(): boolean {
  const store = useChangelogStore.getState();
  return store.generatedChangelog.length > 0 && !store.isGenerating;
}
