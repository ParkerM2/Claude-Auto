export interface ContextProps {
  projectId: string;
  /** Register refresh function with parent */
  registerRefresh?: (fn: (() => void | Promise<void>) | null) => void;
}
