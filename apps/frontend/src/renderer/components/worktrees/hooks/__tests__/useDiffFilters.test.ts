/**
 * Unit tests for useDiffFilters hook
 *
 * @vitest-environment jsdom
 */
import { describe, it, expect } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { useDiffFilters } from '../useDiffFilters';
import type { WorktreeDiffFile } from '../../../../../shared/types';

describe('useDiffFilters', () => {
  const mockFiles: WorktreeDiffFile[] = [
    {
      path: 'src/components/App.tsx',
      status: 'modified',
      additions: 10,
      deletions: 5,
    },
    {
      path: 'src/utils/helper.ts',
      status: 'added',
      additions: 20,
      deletions: 0,
    },
    {
      path: 'src/old-file.js',
      status: 'deleted',
      additions: 0,
      deletions: 15,
    },
    {
      path: 'README.md',
      status: 'modified',
      additions: 3,
      deletions: 1,
    },
  ];

  it('should initialize with default filters', () => {
    const { result } = renderHook(() => useDiffFilters(mockFiles));

    expect(result.current.filters.changeType).toBe('all');
    expect(result.current.filters.fileExtensions).toEqual([]);
    expect(result.current.filters.searchQuery).toBe('');
    expect(result.current.hasActiveFilters).toBe(false);
  });

  it('should return all files when no filters applied', () => {
    const { result } = renderHook(() => useDiffFilters(mockFiles));

    expect(result.current.filteredFiles).toHaveLength(4);
    expect(result.current.filteredFiles).toEqual(mockFiles);
  });

  it('should filter by change type', () => {
    const { result } = renderHook(() => useDiffFilters(mockFiles));

    act(() => {
      result.current.setChangeType('added');
    });

    expect(result.current.filteredFiles).toHaveLength(1);
    expect(result.current.filteredFiles[0].status).toBe('added');
    expect(result.current.hasActiveFilters).toBe(true);
  });

  it('should filter by file extension', () => {
    const { result } = renderHook(() => useDiffFilters(mockFiles));

    act(() => {
      result.current.setFileExtensions(['tsx', 'ts']);
    });

    expect(result.current.filteredFiles).toHaveLength(2);
    expect(result.current.filteredFiles.every(f =>
      f.path.endsWith('.tsx') || f.path.endsWith('.ts')
    )).toBe(true);
  });

  it('should filter by search query', () => {
    const { result } = renderHook(() => useDiffFilters(mockFiles));

    act(() => {
      result.current.setSearchQuery('components');
    });

    expect(result.current.filteredFiles).toHaveLength(1);
    expect(result.current.filteredFiles[0].path).toContain('components');
  });

  it('should apply multiple filters simultaneously', () => {
    const { result } = renderHook(() => useDiffFilters(mockFiles));

    act(() => {
      result.current.setChangeType('modified');
      result.current.setFileExtensions(['tsx']);
    });

    expect(result.current.filteredFiles).toHaveLength(1);
    expect(result.current.filteredFiles[0].path).toBe('src/components/App.tsx');
  });

  it('should clear all filters', () => {
    const { result } = renderHook(() => useDiffFilters(mockFiles));

    act(() => {
      result.current.setChangeType('added');
      result.current.setFileExtensions(['ts']);
      result.current.setSearchQuery('helper');
    });

    expect(result.current.hasActiveFilters).toBe(true);

    act(() => {
      result.current.clearFilters();
    });

    expect(result.current.filters.changeType).toBe('all');
    expect(result.current.filters.fileExtensions).toEqual([]);
    expect(result.current.filters.searchQuery).toBe('');
    expect(result.current.hasActiveFilters).toBe(false);
    expect(result.current.filteredFiles).toHaveLength(4);
  });

  it('should derive available extensions from files', () => {
    const { result } = renderHook(() => useDiffFilters(mockFiles));

    expect(result.current.availableExtensions).toContain('tsx');
    expect(result.current.availableExtensions).toContain('ts');
    expect(result.current.availableExtensions).toContain('js');
    expect(result.current.availableExtensions).toContain('md');
    expect(result.current.availableExtensions).toHaveLength(4);
  });

  it('should compute correct change type totals', () => {
    const { result } = renderHook(() => useDiffFilters(mockFiles));

    expect(result.current.changeTypeTotals.all).toBe(4);
    expect(result.current.changeTypeTotals.added).toBe(1);
    expect(result.current.changeTypeTotals.modified).toBe(2);
    expect(result.current.changeTypeTotals.deleted).toBe(1);
    expect(result.current.changeTypeTotals.renamed).toBe(0);
  });

  it('should handle empty file list', () => {
    const { result } = renderHook(() => useDiffFilters([]));

    expect(result.current.filteredFiles).toEqual([]);
    expect(result.current.availableExtensions).toEqual([]);
    expect(result.current.changeTypeTotals.all).toBe(0);
  });

  it('should handle case-insensitive search', () => {
    const { result } = renderHook(() => useDiffFilters(mockFiles));

    act(() => {
      result.current.setSearchQuery('COMPONENTS');
    });

    expect(result.current.filteredFiles).toHaveLength(1);
    expect(result.current.filteredFiles[0].path).toContain('components');
  });
});
