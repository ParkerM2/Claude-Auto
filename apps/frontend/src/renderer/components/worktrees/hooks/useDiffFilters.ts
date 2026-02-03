import { useMemo, useState, useCallback } from 'react';
import type { WorktreeDiffFile } from '../../../../shared/types';

export type ChangeTypeFilter = 'all' | 'added' | 'modified' | 'deleted' | 'renamed';

export interface DiffFilterState {
  changeType: ChangeTypeFilter;
  fileExtensions: string[]; // e.g., ['ts', 'tsx', 'js']
  searchQuery: string;
}

const DEFAULT_FILTERS: DiffFilterState = {
  changeType: 'all',
  fileExtensions: [],
  searchQuery: '',
};

/**
 * Extract file extension from path
 */
function getFileExtension(path: string): string {
  const parts = path.split('.');
  return parts.length > 1 ? parts[parts.length - 1].toLowerCase() : '';
}

/**
 * Custom hook for filtering diff files by change type, file extension, and search query
 *
 * @param files Array of diff files to filter
 * @returns Filtered files and filter controls
 */
export function useDiffFilters(files: WorktreeDiffFile[]) {
  const [filters, setFiltersState] = useState<DiffFilterState>(DEFAULT_FILTERS);

  // Derive unique file extensions from files
  const availableExtensions = useMemo(() => {
    const extensionSet = new Set<string>();
    files.forEach(file => {
      const ext = getFileExtension(file.path);
      if (ext) {
        extensionSet.add(ext);
      }
    });
    return Array.from(extensionSet).sort((a, b) =>
      a.toLowerCase().localeCompare(b.toLowerCase())
    );
  }, [files]);

  // Compute totals for each change type
  const changeTypeTotals = useMemo(() => {
    return {
      all: files.length,
      added: files.filter(f => f.status === 'added').length,
      modified: files.filter(f => f.status === 'modified').length,
      deleted: files.filter(f => f.status === 'deleted').length,
      renamed: files.filter(f => f.status === 'renamed').length,
    };
  }, [files]);

  // Filter files based on current filters
  const filteredFiles = useMemo(() => {
    return files.filter(file => {
      // Change type filter
      if (filters.changeType !== 'all' && file.status !== filters.changeType) {
        return false;
      }

      // File extension filter (multi-select)
      if (filters.fileExtensions.length > 0) {
        const ext = getFileExtension(file.path);
        if (!ext || !filters.fileExtensions.includes(ext)) {
          return false;
        }
      }

      // Search query filter - matches file path
      if (filters.searchQuery) {
        const query = filters.searchQuery.toLowerCase();
        const matchesPath = file.path.toLowerCase().includes(query);
        if (!matchesPath) {
          return false;
        }
      }

      return true;
    });
  }, [files, filters]);

  // Filter setters
  const setChangeType = useCallback((changeType: ChangeTypeFilter) => {
    setFiltersState(prev => ({ ...prev, changeType }));
  }, []);

  const setFileExtensions = useCallback((extensions: string[]) => {
    setFiltersState(prev => ({ ...prev, fileExtensions: extensions }));
  }, []);

  const setSearchQuery = useCallback((query: string) => {
    setFiltersState(prev => ({ ...prev, searchQuery: query }));
  }, []);

  const clearFilters = useCallback(() => {
    setFiltersState(DEFAULT_FILTERS);
  }, []);

  const hasActiveFilters = useMemo(() => {
    return (
      filters.changeType !== 'all' ||
      filters.fileExtensions.length > 0 ||
      filters.searchQuery !== ''
    );
  }, [filters]);

  return {
    filteredFiles,
    filters,
    setChangeType,
    setFileExtensions,
    setSearchQuery,
    clearFilters,
    hasActiveFilters,
    availableExtensions,
    changeTypeTotals,
  };
}
