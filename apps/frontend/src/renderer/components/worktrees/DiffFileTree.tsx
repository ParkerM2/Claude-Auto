import { useRef, useMemo, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useVirtualizer } from '@tanstack/react-virtual';
import {
  File,
  FileCode,
  FileJson,
  FileText,
  FileImage,
  Loader2,
  Plus,
  Minus,
  X,
  FilePlus,
  FileMinus,
  FileEdit
} from 'lucide-react';
import { cn } from '../../lib/utils';
import { Button } from '../ui/button';
import { Badge } from '../ui/badge';
import { ScrollArea } from '../ui/scroll-area';
import type { WorktreeDiffFile } from '../../../shared/types';

interface DiffFileTreeProps {
  files: WorktreeDiffFile[];
  selectedFile?: string | null;
  onFileSelect: (filePath: string) => void;
  isLoading?: boolean;
}

type ChangeTypeFilter = 'all' | 'added' | 'modified' | 'deleted' | 'renamed';

// Estimated height of each tree item in pixels
const ITEM_HEIGHT = 40;
// Number of items to render outside the visible area for smoother scrolling
const OVERSCAN = 10;

// Get appropriate icon based on file extension
function getFileIcon(name: string, status: WorktreeDiffFile['status']): React.ReactNode {
  const ext = name.split('.').pop()?.toLowerCase();

  // Use status-specific icons
  if (status === 'added') {
    return <FilePlus className="h-4 w-4 text-green-500" />;
  }
  if (status === 'deleted') {
    return <FileMinus className="h-4 w-4 text-red-500" />;
  }
  if (status === 'renamed') {
    return <FileEdit className="h-4 w-4 text-blue-500" />;
  }

  // For modified files, use extension-based icons
  switch (ext) {
    case 'ts':
    case 'tsx':
    case 'js':
    case 'jsx':
    case 'py':
    case 'rb':
    case 'go':
    case 'rs':
    case 'java':
    case 'c':
    case 'cpp':
    case 'h':
    case 'cs':
    case 'php':
    case 'swift':
    case 'kt':
      return <FileCode className="h-4 w-4 text-blue-400" />;
    case 'json':
    case 'yaml':
    case 'yml':
    case 'toml':
      return <FileJson className="h-4 w-4 text-yellow-400" />;
    case 'md':
    case 'txt':
    case 'rst':
      return <FileText className="h-4 w-4 text-gray-400" />;
    case 'png':
    case 'jpg':
    case 'jpeg':
    case 'gif':
    case 'svg':
    case 'webp':
    case 'ico':
      return <FileImage className="h-4 w-4 text-purple-400" />;
    case 'css':
    case 'scss':
    case 'sass':
    case 'less':
      return <FileCode className="h-4 w-4 text-pink-400" />;
    case 'html':
    case 'htm':
      return <FileCode className="h-4 w-4 text-orange-400" />;
    default:
      return <File className="h-4 w-4 text-muted-foreground" />;
  }
}

// Get badge variant for status
function getStatusBadgeVariant(status: WorktreeDiffFile['status']): 'default' | 'secondary' | 'destructive' | 'outline' {
  switch (status) {
    case 'added':
      return 'default';
    case 'modified':
      return 'secondary';
    case 'deleted':
      return 'destructive';
    case 'renamed':
      return 'outline';
    default:
      return 'secondary';
  }
}

export function DiffFileTree({ files, selectedFile, onFileSelect, isLoading = false }: DiffFileTreeProps) {
  const { t } = useTranslation(['common', 'tasks', 'dialogs']);

  // Get status label with translations
  const getStatusLabel = (status: WorktreeDiffFile['status']): string => {
    switch (status) {
      case 'added':
        return t('dialogs:worktreeDiff.added');
      case 'modified':
        return t('dialogs:worktreeDiff.modified');
      case 'deleted':
        return t('dialogs:worktreeDiff.deleted');
      case 'renamed':
        return t('dialogs:worktreeDiff.renamed');
      default:
        return status;
    }
  };
  const parentRef = useRef<HTMLDivElement>(null);
  const [filter, setFilter] = useState<ChangeTypeFilter>('all');

  // Filter files based on selected filter
  const filteredFiles = useMemo(() => {
    if (filter === 'all') {
      return files;
    }
    return files.filter(file => file.status === filter);
  }, [files, filter]);

  // Set up the virtualizer
  const rowVirtualizer = useVirtualizer({
    count: filteredFiles.length,
    getScrollElement: () => parentRef.current,
    estimateSize: () => ITEM_HEIGHT,
    overscan: OVERSCAN,
  });

  // Calculate totals for filter badges
  const totals = useMemo(() => {
    return {
      all: files.length,
      added: files.filter(f => f.status === 'added').length,
      modified: files.filter(f => f.status === 'modified').length,
      deleted: files.filter(f => f.status === 'deleted').length,
      renamed: files.filter(f => f.status === 'renamed').length,
    };
  }, [files]);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-8">
        <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (files.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-8 px-4 text-center">
        <File className="h-6 w-6 text-muted-foreground mb-2" />
        <p className="text-xs text-muted-foreground">{t('common:labels.noData')}</p>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full">
      {/* Filter buttons */}
      <div className="flex flex-wrap gap-2 p-3 border-b">
        <Button
          variant={filter === 'all' ? 'default' : 'outline'}
          size="sm"
          onClick={() => setFilter('all')}
          className="h-7"
        >
          {t('dialogs:worktreeDiff.all')}
          <Badge variant="secondary" className="ml-1.5 px-1.5 py-0 text-xs">
            {totals.all}
          </Badge>
        </Button>
        {totals.added > 0 && (
          <Button
            variant={filter === 'added' ? 'default' : 'outline'}
            size="sm"
            onClick={() => setFilter('added')}
            className="h-7"
          >
            <Plus className="h-3 w-3 mr-1" />
            {t('dialogs:worktreeDiff.added')}
            <Badge variant="secondary" className="ml-1.5 px-1.5 py-0 text-xs">
              {totals.added}
            </Badge>
          </Button>
        )}
        {totals.modified > 0 && (
          <Button
            variant={filter === 'modified' ? 'default' : 'outline'}
            size="sm"
            onClick={() => setFilter('modified')}
            className="h-7"
          >
            <FileEdit className="h-3 w-3 mr-1" />
            {t('dialogs:worktreeDiff.modified')}
            <Badge variant="secondary" className="ml-1.5 px-1.5 py-0 text-xs">
              {totals.modified}
            </Badge>
          </Button>
        )}
        {totals.deleted > 0 && (
          <Button
            variant={filter === 'deleted' ? 'default' : 'outline'}
            size="sm"
            onClick={() => setFilter('deleted')}
            className="h-7"
          >
            <Minus className="h-3 w-3 mr-1" />
            {t('dialogs:worktreeDiff.deleted')}
            <Badge variant="secondary" className="ml-1.5 px-1.5 py-0 text-xs">
              {totals.deleted}
            </Badge>
          </Button>
        )}
        {totals.renamed > 0 && (
          <Button
            variant={filter === 'renamed' ? 'default' : 'outline'}
            size="sm"
            onClick={() => setFilter('renamed')}
            className="h-7"
          >
            <FileEdit className="h-3 w-3 mr-1" />
            {t('dialogs:worktreeDiff.renamed')}
            <Badge variant="secondary" className="ml-1.5 px-1.5 py-0 text-xs">
              {totals.renamed}
            </Badge>
          </Button>
        )}
      </div>

      {/* File list */}
      <div
        ref={parentRef}
        className="flex-1 overflow-auto"
      >
        {filteredFiles.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-8 px-4 text-center">
            <X className="h-6 w-6 text-muted-foreground mb-2" />
            <p className="text-xs text-muted-foreground">
              {t('dialogs:worktreeDiff.noFilteredFiles', { filter })}
            </p>
          </div>
        ) : (
          <div
            style={{
              height: `${rowVirtualizer.getTotalSize()}px`,
              width: '100%',
              position: 'relative',
            }}
          >
            {rowVirtualizer.getVirtualItems().map((virtualItem) => {
              const file = filteredFiles[virtualItem.index];
              if (!file) return null;

              const isSelected = selectedFile === file.path;
              const fileName = file.path.split('/').pop() || file.path;

              return (
                <div
                  key={file.path}
                  style={{
                    position: 'absolute',
                    top: 0,
                    left: 0,
                    width: '100%',
                    height: `${virtualItem.size}px`,
                    transform: `translateY(${virtualItem.start}px)`,
                  }}
                >
                  <div
                    role="button"
                    tabIndex={0}
                    className={cn(
                      'flex items-center gap-2 px-3 py-2 cursor-pointer transition-colors',
                      'hover:bg-accent/50',
                      isSelected && 'bg-accent border-l-2 border-primary'
                    )}
                    onClick={() => onFileSelect(file.path)}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter' || e.key === ' ') {
                        e.preventDefault();
                        onFileSelect(file.path);
                      }
                    }}
                  >
                    {/* File icon */}
                    {getFileIcon(fileName, file.status)}

                    {/* File name and path */}
                    <div className="flex-1 min-w-0">
                      <div className="text-sm font-medium truncate">
                        {fileName}
                      </div>
                      <div className="text-xs text-muted-foreground truncate">
                        {file.path}
                      </div>
                    </div>

                    {/* Change stats */}
                    <div className="flex items-center gap-2 flex-shrink-0">
                      {file.additions > 0 && (
                        <div className="flex items-center gap-0.5 text-green-600 dark:text-green-400">
                          <Plus className="h-3 w-3" />
                          <span className="text-xs font-medium">{file.additions}</span>
                        </div>
                      )}
                      {file.deletions > 0 && (
                        <div className="flex items-center gap-0.5 text-red-600 dark:text-red-400">
                          <Minus className="h-3 w-3" />
                          <span className="text-xs font-medium">{file.deletions}</span>
                        </div>
                      )}
                      <Badge variant={getStatusBadgeVariant(file.status)} className="text-xs">
                        {getStatusLabel(file.status)}
                      </Badge>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
