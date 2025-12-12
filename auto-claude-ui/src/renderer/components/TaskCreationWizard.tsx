import { useState } from 'react';
import { Loader2, ChevronDown, ChevronUp } from 'lucide-react';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle
} from './ui/dialog';
import { Button } from './ui/button';
import { Input } from './ui/input';
import { Textarea } from './ui/textarea';
import { Label } from './ui/label';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue
} from './ui/select';
import { createTask } from '../stores/task-store';
import { cn } from '../lib/utils';
import type { TaskCategory, TaskPriority, TaskComplexity, TaskImpact, TaskMetadata } from '../../shared/types';
import {
  TASK_CATEGORY_LABELS,
  TASK_PRIORITY_LABELS,
  TASK_COMPLEXITY_LABELS,
  TASK_IMPACT_LABELS
} from '../../shared/constants';

interface TaskCreationWizardProps {
  projectId: string;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function TaskCreationWizard({
  projectId,
  open,
  onOpenChange
}: TaskCreationWizardProps) {
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [isCreating, setIsCreating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showAdvanced, setShowAdvanced] = useState(false);

  // Metadata fields
  const [category, setCategory] = useState<TaskCategory | ''>('');
  const [priority, setPriority] = useState<TaskPriority | ''>('');
  const [complexity, setComplexity] = useState<TaskComplexity | ''>('');
  const [impact, setImpact] = useState<TaskImpact | ''>('');

  const handleCreate = async () => {
    if (!title.trim() || !description.trim()) {
      setError('Please provide both a title and description');
      return;
    }

    setIsCreating(true);
    setError(null);

    try {
      // Build metadata from selected values
      const metadata: TaskMetadata = {
        sourceType: 'manual'
      };

      if (category) metadata.category = category;
      if (priority) metadata.priority = priority;
      if (complexity) metadata.complexity = complexity;
      if (impact) metadata.impact = impact;

      const task = await createTask(projectId, title.trim(), description.trim(), metadata);
      if (task) {
        // Reset form and close
        resetForm();
        onOpenChange(false);
      } else {
        setError('Failed to create task. Please try again.');
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setIsCreating(false);
    }
  };

  const resetForm = () => {
    setTitle('');
    setDescription('');
    setCategory('');
    setPriority('');
    setComplexity('');
    setImpact('');
    setError(null);
    setShowAdvanced(false);
  };

  const handleClose = () => {
    if (!isCreating) {
      resetForm();
      onOpenChange(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent className="sm:max-w-[550px]">
        <DialogHeader>
          <DialogTitle className="text-foreground">Create New Task</DialogTitle>
          <DialogDescription>
            Describe what you want to build. The AI will analyze your request and
            create a detailed specification.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-5 py-4">
          {/* Title */}
          <div className="space-y-2">
            <Label htmlFor="title" className="text-sm font-medium text-foreground">
              Task Title
            </Label>
            <Input
              id="title"
              placeholder="e.g., Add user authentication"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              disabled={isCreating}
            />
          </div>

          {/* Description */}
          <div className="space-y-2">
            <Label htmlFor="description" className="text-sm font-medium text-foreground">
              Description
            </Label>
            <Textarea
              id="description"
              placeholder="Describe the feature, bug fix, or improvement you want to implement. Be as specific as possible about requirements, constraints, and expected behavior."
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              rows={5}
              disabled={isCreating}
            />
            <p className="text-xs text-muted-foreground">
              Tip: Include details about UI changes, API endpoints, data models,
              and any technical requirements.
            </p>
          </div>

          {/* Advanced Options Toggle */}
          <button
            type="button"
            onClick={() => setShowAdvanced(!showAdvanced)}
            className={cn(
              'flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground transition-colors',
              'w-full justify-between py-2 px-3 rounded-md hover:bg-muted/50'
            )}
            disabled={isCreating}
          >
            <span>Classification (optional)</span>
            {showAdvanced ? (
              <ChevronUp className="h-4 w-4" />
            ) : (
              <ChevronDown className="h-4 w-4" />
            )}
          </button>

          {/* Advanced Options */}
          {showAdvanced && (
            <div className="space-y-4 p-4 rounded-lg border border-border bg-muted/30">
              <div className="grid grid-cols-2 gap-4">
                {/* Category */}
                <div className="space-y-2">
                  <Label htmlFor="category" className="text-xs font-medium text-muted-foreground">
                    Category
                  </Label>
                  <Select
                    value={category}
                    onValueChange={(value) => setCategory(value as TaskCategory)}
                    disabled={isCreating}
                  >
                    <SelectTrigger id="category" className="h-9">
                      <SelectValue placeholder="Select category" />
                    </SelectTrigger>
                    <SelectContent>
                      {Object.entries(TASK_CATEGORY_LABELS).map(([value, label]) => (
                        <SelectItem key={value} value={value}>
                          {label}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>

                {/* Priority */}
                <div className="space-y-2">
                  <Label htmlFor="priority" className="text-xs font-medium text-muted-foreground">
                    Priority
                  </Label>
                  <Select
                    value={priority}
                    onValueChange={(value) => setPriority(value as TaskPriority)}
                    disabled={isCreating}
                  >
                    <SelectTrigger id="priority" className="h-9">
                      <SelectValue placeholder="Select priority" />
                    </SelectTrigger>
                    <SelectContent>
                      {Object.entries(TASK_PRIORITY_LABELS).map(([value, label]) => (
                        <SelectItem key={value} value={value}>
                          {label}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>

                {/* Complexity */}
                <div className="space-y-2">
                  <Label htmlFor="complexity" className="text-xs font-medium text-muted-foreground">
                    Complexity
                  </Label>
                  <Select
                    value={complexity}
                    onValueChange={(value) => setComplexity(value as TaskComplexity)}
                    disabled={isCreating}
                  >
                    <SelectTrigger id="complexity" className="h-9">
                      <SelectValue placeholder="Select complexity" />
                    </SelectTrigger>
                    <SelectContent>
                      {Object.entries(TASK_COMPLEXITY_LABELS).map(([value, label]) => (
                        <SelectItem key={value} value={value}>
                          {label}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>

                {/* Impact */}
                <div className="space-y-2">
                  <Label htmlFor="impact" className="text-xs font-medium text-muted-foreground">
                    Impact
                  </Label>
                  <Select
                    value={impact}
                    onValueChange={(value) => setImpact(value as TaskImpact)}
                    disabled={isCreating}
                  >
                    <SelectTrigger id="impact" className="h-9">
                      <SelectValue placeholder="Select impact" />
                    </SelectTrigger>
                    <SelectContent>
                      {Object.entries(TASK_IMPACT_LABELS).map(([value, label]) => (
                        <SelectItem key={value} value={value}>
                          {label}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              </div>

              <p className="text-xs text-muted-foreground">
                These labels help organize and prioritize tasks. They&apos;re optional but useful for filtering.
              </p>
            </div>
          )}

          {/* Error */}
          {error && (
            <div className="rounded-lg bg-[var(--error-light)] border border-[var(--error)]/30 p-3 text-sm text-[var(--error)]">
              {error}
            </div>
          )}
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={handleClose} disabled={isCreating}>
            Cancel
          </Button>
          <Button onClick={handleCreate} disabled={isCreating || !title.trim() || !description.trim()}>
            {isCreating ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Creating...
              </>
            ) : (
              'Create Task'
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
