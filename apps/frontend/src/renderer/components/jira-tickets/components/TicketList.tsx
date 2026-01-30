import { useTranslation } from 'react-i18next';
import { Ticket, Loader2 } from 'lucide-react';
import { cn } from '../../../lib/utils';
import type { JiraIssue } from '../../../../shared/types';
import { ScrollArea } from '../../ui/scroll-area';

interface TicketListProps {
  tickets: JiraIssue[];
  selectedTicketKey: string | null;
  isLoading: boolean;
  error: string | null;
  onSelectTicket: (ticket: JiraIssue) => void;
}

function getStatusColor(category: 'todo' | 'in_progress' | 'done'): string {
  switch (category) {
    case 'todo':
      return 'bg-slate-500';
    case 'in_progress':
      return 'bg-blue-500';
    case 'done':
      return 'bg-green-500';
    default:
      return 'bg-gray-500';
  }
}

export function TicketList({
  tickets,
  selectedTicketKey,
  isLoading,
  error,
  onSelectTicket,
}: TicketListProps) {
  const { t } = useTranslation('common');

  if (isLoading) {
    return (
      <div className="flex-1 flex items-center justify-center">
        <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex-1 flex items-center justify-center p-4">
        <p className="text-sm text-destructive text-center">{error}</p>
      </div>
    );
  }

  if (tickets.length === 0) {
    return (
      <div className="flex-1 flex items-center justify-center p-4">
        <div className="text-center text-muted-foreground">
          <Ticket className="h-8 w-8 mx-auto mb-2 opacity-50" />
          <p>{t('jira.noTickets')}</p>
        </div>
      </div>
    );
  }

  return (
    <ScrollArea className="flex-1">
      <div className="space-y-1 p-2">
        {tickets.map((ticket) => (
          <button
            key={ticket.key}
            onClick={() => onSelectTicket(ticket)}
            className={cn(
              'w-full text-left p-3 rounded-lg transition-colors',
              'hover:bg-accent',
              selectedTicketKey === ticket.key && 'bg-accent'
            )}
          >
            <div className="flex items-start gap-3">
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 mb-1">
                  <span className="text-xs font-mono text-muted-foreground">
                    {ticket.key}
                  </span>
                  <span
                    className={cn(
                      'w-2 h-2 rounded-full',
                      getStatusColor(ticket.status.category)
                    )}
                    title={ticket.status.name}
                  />
                </div>
                <p className="text-sm font-medium truncate">{ticket.summary}</p>
                <div className="flex items-center gap-2 mt-1">
                  {ticket.storyPoints !== undefined && ticket.storyPoints !== null && (
                    <span className="text-xs text-muted-foreground bg-secondary px-1.5 py-0.5 rounded">
                      {ticket.storyPoints} {t('jira.points')}
                    </span>
                  )}
                  {ticket.priority && (
                    <span className="text-xs text-muted-foreground">
                      {ticket.priority.name}
                    </span>
                  )}
                </div>
              </div>
              {ticket.assignee?.avatarUrl && (
                <img
                  src={ticket.assignee.avatarUrl}
                  alt={ticket.assignee.displayName}
                  className="w-6 h-6 rounded-full"
                />
              )}
            </div>
          </button>
        ))}
      </div>
    </ScrollArea>
  );
}
