import { useTranslation } from 'react-i18next';
import { Bot } from 'lucide-react';
import { Badge } from '../ui/badge';
import { cn } from '../../lib/utils';
import { useActiveAgents } from './hooks/useActiveAgents';

interface ActiveAgentsBadgeProps {
  className?: string;
}

/**
 * Badge component showing count of active (running) agents.
 * Features a pulsing border animation to draw attention.
 * Only renders when there are active agents.
 */
export function ActiveAgentsBadge({ className }: ActiveAgentsBadgeProps) {
  const { t } = useTranslation('tasks');
  const { activeCount, isActive } = useActiveAgents();

  if (!isActive) return null;

  return (
    <Badge
      variant="outline"
      className={cn(
        'text-sm px-3 py-1.5 gap-1.5',
        'animate-pulse-border',
        'bg-primary/5 text-primary border-primary',
        className
      )}
    >
      <Bot className="h-4 w-4" />
      <span className="font-medium">
        {activeCount} {t('labels.active')}
      </span>
    </Badge>
  );
}
