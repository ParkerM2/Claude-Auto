import { useEffect, useCallback, useState, useRef } from 'react';
import type { WorktreeDiffFile } from '../../../../shared/types';

interface UseDiffNavigationOptions {
  files: WorktreeDiffFile[];
  onFileChange?: (filePath: string) => void;
  onClose?: () => void;
  enabled?: boolean; // Allow disabling keyboard shortcuts
}

interface UseDiffNavigationReturn {
  currentFileIndex: number;
  currentHunkIndex: number;
  goToNextFile: () => void;
  goToPrevFile: () => void;
  goToNextHunk: () => void;
  goToPrevHunk: () => void;
  goToFile: (index: number) => void;
  goToHunk: (index: number) => void;
}

/**
 * Custom hook for keyboard navigation through diff files and hunks
 *
 * Keyboard shortcuts:
 * - n: next file
 * - p: previous file
 * - j: next hunk
 * - k: previous hunk
 * - Escape: close diff viewer
 *
 * @param options Configuration options
 * @returns Navigation state and functions
 */
export function useDiffNavigation({
  files,
  onFileChange,
  onClose,
  enabled = true,
}: UseDiffNavigationOptions): UseDiffNavigationReturn {
  const [currentFileIndex, setCurrentFileIndex] = useState(0);
  const [currentHunkIndex, setCurrentHunkIndex] = useState(0);

  // Use refs to track latest values for event handlers
  const filesRef = useRef(files);
  const currentFileIndexRef = useRef(currentFileIndex);
  const currentHunkIndexRef = useRef(currentHunkIndex);

  // Update refs when state changes
  useEffect(() => {
    filesRef.current = files;
    currentFileIndexRef.current = currentFileIndex;
    currentHunkIndexRef.current = currentHunkIndex;
  }, [files, currentFileIndex, currentHunkIndex]);

  // Navigate to next file
  const goToNextFile = useCallback(() => {
    const newIndex = Math.min(currentFileIndexRef.current + 1, filesRef.current.length - 1);
    setCurrentFileIndex(newIndex);
    setCurrentHunkIndex(0); // Reset hunk index when changing files

    if (newIndex !== currentFileIndexRef.current && filesRef.current[newIndex]) {
      onFileChange?.(filesRef.current[newIndex].path);
    }
  }, [onFileChange]);

  // Navigate to previous file
  const goToPrevFile = useCallback(() => {
    const newIndex = Math.max(currentFileIndexRef.current - 1, 0);
    setCurrentFileIndex(newIndex);
    setCurrentHunkIndex(0); // Reset hunk index when changing files

    if (newIndex !== currentFileIndexRef.current && filesRef.current[newIndex]) {
      onFileChange?.(filesRef.current[newIndex].path);
    }
  }, [onFileChange]);

  // Navigate to next hunk within current file
  const goToNextHunk = useCallback(() => {
    const currentFile = filesRef.current[currentFileIndexRef.current];
    if (!currentFile?.hunks || currentFile.hunks.length === 0) {
      return;
    }

    const maxHunkIndex = currentFile.hunks.length - 1;
    const newIndex = Math.min(currentHunkIndexRef.current + 1, maxHunkIndex);
    setCurrentHunkIndex(newIndex);
  }, []);

  // Navigate to previous hunk within current file
  const goToPrevHunk = useCallback(() => {
    const newIndex = Math.max(currentHunkIndexRef.current - 1, 0);
    setCurrentHunkIndex(newIndex);
  }, []);

  // Navigate to specific file by index
  const goToFile = useCallback((index: number) => {
    const clampedIndex = Math.max(0, Math.min(index, filesRef.current.length - 1));
    setCurrentFileIndex(clampedIndex);
    setCurrentHunkIndex(0);

    if (filesRef.current[clampedIndex]) {
      onFileChange?.(filesRef.current[clampedIndex].path);
    }
  }, [onFileChange]);

  // Navigate to specific hunk by index
  const goToHunk = useCallback((index: number) => {
    const currentFile = filesRef.current[currentFileIndexRef.current];
    if (!currentFile?.hunks) {
      return;
    }

    const clampedIndex = Math.max(0, Math.min(index, currentFile.hunks.length - 1));
    setCurrentHunkIndex(clampedIndex);
  }, []);

  // Keyboard event handler
  useEffect(() => {
    if (!enabled) {
      return;
    }

    const handleKeyDown = (e: KeyboardEvent) => {
      // Don't interfere with input fields
      const target = e.target as HTMLElement;
      if (
        target.tagName === 'INPUT' ||
        target.tagName === 'TEXTAREA' ||
        target.isContentEditable
      ) {
        return;
      }

      switch (e.key.toLowerCase()) {
        case 'n':
          e.preventDefault();
          goToNextFile();
          break;
        case 'p':
          e.preventDefault();
          goToPrevFile();
          break;
        case 'j':
          e.preventDefault();
          goToNextHunk();
          break;
        case 'k':
          e.preventDefault();
          goToPrevHunk();
          break;
        case 'escape':
          e.preventDefault();
          onClose?.();
          break;
        default:
          // No action for other keys
          break;
      }
    };

    window.addEventListener('keydown', handleKeyDown);

    return () => {
      window.removeEventListener('keydown', handleKeyDown);
    };
  }, [enabled, goToNextFile, goToPrevFile, goToNextHunk, goToPrevHunk, onClose]);

  // Reset indices when files array changes
  useEffect(() => {
    if (currentFileIndex >= files.length) {
      setCurrentFileIndex(Math.max(0, files.length - 1));
      setCurrentHunkIndex(0);
    }
  }, [files, currentFileIndex]);

  return {
    currentFileIndex,
    currentHunkIndex,
    goToNextFile,
    goToPrevFile,
    goToNextHunk,
    goToPrevHunk,
    goToFile,
    goToHunk,
  };
}
