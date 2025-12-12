import { useState, useMemo } from 'react';
import {
  DndContext,
  DragOverlay,
  closestCorners,
  KeyboardSensor,
  PointerSensor,
  useSensor,
  useSensors,
  useDroppable,
  type DragStartEvent,
  type DragEndEvent,
  type DragOverEvent
} from '@dnd-kit/core';
import {
  SortableContext,
  sortableKeyboardCoordinates,
  verticalListSortingStrategy
} from '@dnd-kit/sortable';
import { Plus } from 'lucide-react';
import { ScrollArea } from './ui/scroll-area';
import { Button } from './ui/button';
import { TaskCard } from './TaskCard';
import { SortableTaskCard } from './SortableTaskCard';
import { TASK_STATUS_COLUMNS, TASK_STATUS_LABELS } from '../../shared/constants';
import { cn } from '../lib/utils';
import { persistTaskStatus } from '../stores/task-store';
import type { Task, TaskStatus } from '../../shared/types';

interface KanbanBoardProps {
  tasks: Task[];
  onTaskClick: (task: Task) => void;
  onNewTaskClick?: () => void;
}

interface DroppableColumnProps {
  status: TaskStatus;
  tasks: Task[];
  onTaskClick: (task: Task) => void;
  isOver: boolean;
  onAddClick?: () => void;
}

function DroppableColumn({ status, tasks, onTaskClick, isOver, onAddClick }: DroppableColumnProps) {
  const { setNodeRef } = useDroppable({
    id: status
  });

  const taskIds = tasks.map((t) => t.id);

  const getColumnBorderColor = (): string => {
    switch (status) {
      case 'backlog':
        return 'column-backlog';
      case 'in_progress':
        return 'column-in-progress';
      case 'ai_review':
        return 'column-ai-review';
      case 'human_review':
        return 'column-human-review';
      case 'done':
        return 'column-done';
      default:
        return 'border-t-muted-foreground/30';
    }
  };

  return (
    <div
      className={cn(
        'flex w-72 shrink-0 flex-col rounded-xl border border-white/5 bg-linear-to-b from-secondary/30 to-transparent backdrop-blur-sm transition-all duration-200',
        getColumnBorderColor(),
        'border-t-2',
        isOver && 'bg-accent/10'
      )}
    >
      {/* Column header */}
      <div className="flex items-center justify-between p-4">
        <div className="flex items-center gap-2">
          <h2 className="font-semibold text-sm text-foreground">
            {TASK_STATUS_LABELS[status]}
          </h2>
          <span className="flex h-6 w-6 items-center justify-center rounded-full bg-secondary text-xs font-medium text-muted-foreground">
            {tasks.length}
          </span>
        </div>
        {status === 'backlog' && onAddClick && (
          <Button
            variant="ghost"
            size="icon"
            className="h-6 w-6"
            onClick={onAddClick}
          >
            <Plus className="h-4 w-4" />
          </Button>
        )}
      </div>

      {/* Droppable task list */}
      <div ref={setNodeRef} className="flex-1 min-h-0">
        <ScrollArea className="h-full px-3 pb-3">
          <SortableContext
            items={taskIds}
            strategy={verticalListSortingStrategy}
          >
            <div className="space-y-3 min-h-[100px]">
              {tasks.length === 0 ? (
                <div
                  className={cn(
                    'rounded-lg border border-dashed border-border p-4 text-center text-sm text-muted-foreground transition-all duration-200',
                    isOver && 'border-primary/50 bg-accent/30'
                  )}
                >
                  {isOver ? 'Drop here' : 'No tasks'}
                </div>
              ) : (
                tasks.map((task) => (
                  <SortableTaskCard
                    key={task.id}
                    task={task}
                    onClick={() => onTaskClick(task)}
                  />
                ))
              )}
            </div>
          </SortableContext>
        </ScrollArea>
      </div>
    </div>
  );
}

export function KanbanBoard({ tasks, onTaskClick, onNewTaskClick }: KanbanBoardProps) {
  const [activeTask, setActiveTask] = useState<Task | null>(null);
  const [overColumnId, setOverColumnId] = useState<string | null>(null);

  const sensors = useSensors(
    useSensor(PointerSensor, {
      activationConstraint: {
        distance: 8 // 8px movement required before drag starts
      }
    }),
    useSensor(KeyboardSensor, {
      coordinateGetter: sortableKeyboardCoordinates
    })
  );

  const tasksByStatus = useMemo(() => {
    const grouped: Record<TaskStatus, Task[]> = {
      backlog: [],
      in_progress: [],
      ai_review: [],
      human_review: [],
      done: []
    };

    tasks.forEach((task) => {
      if (grouped[task.status]) {
        grouped[task.status].push(task);
      }
    });

    return grouped;
  }, [tasks]);

  const handleDragStart = (event: DragStartEvent) => {
    const { active } = event;
    const task = tasks.find((t) => t.id === active.id);
    if (task) {
      setActiveTask(task);
    }
  };

  const handleDragOver = (event: DragOverEvent) => {
    const { over } = event;

    if (!over) {
      setOverColumnId(null);
      return;
    }

    const overId = over.id as string;

    // Check if over a column
    if (TASK_STATUS_COLUMNS.includes(overId as TaskStatus)) {
      setOverColumnId(overId);
      return;
    }

    // Check if over a task - get its column
    const overTask = tasks.find((t) => t.id === overId);
    if (overTask) {
      setOverColumnId(overTask.status);
    }
  };

  const handleDragEnd = (event: DragEndEvent) => {
    const { active, over } = event;
    setActiveTask(null);
    setOverColumnId(null);

    if (!over) return;

    const activeTaskId = active.id as string;
    const overId = over.id as string;

    // Check if dropped on a column
    if (TASK_STATUS_COLUMNS.includes(overId as TaskStatus)) {
      const newStatus = overId as TaskStatus;
      const task = tasks.find((t) => t.id === activeTaskId);

      if (task && task.status !== newStatus) {
        // Persist status change to file and update local state
        persistTaskStatus(activeTaskId, newStatus);
      }
      return;
    }

    // Check if dropped on another task - move to that task's column
    const overTask = tasks.find((t) => t.id === overId);
    if (overTask) {
      const task = tasks.find((t) => t.id === activeTaskId);
      if (task && task.status !== overTask.status) {
        // Persist status change to file and update local state
        persistTaskStatus(activeTaskId, overTask.status);
      }
    }
  };

  return (
    <DndContext
      sensors={sensors}
      collisionDetection={closestCorners}
      onDragStart={handleDragStart}
      onDragOver={handleDragOver}
      onDragEnd={handleDragEnd}
    >
      <div className="flex h-full gap-4 overflow-x-auto p-6">
        {TASK_STATUS_COLUMNS.map((status) => (
          <DroppableColumn
            key={status}
            status={status}
            tasks={tasksByStatus[status]}
            onTaskClick={onTaskClick}
            isOver={overColumnId === status}
            onAddClick={status === 'backlog' ? onNewTaskClick : undefined}
          />
        ))}
      </div>

      {/* Drag overlay - shows the card being dragged */}
      <DragOverlay>
        {activeTask ? (
          <div className="opacity-95 rotate-2 scale-105 cursor-grabbing">
            <TaskCard task={activeTask} onClick={() => {}} />
          </div>
        ) : null}
      </DragOverlay>
    </DndContext>
  );
}
