import { useState, useMemo, useCallback } from 'react';
import { useTranslation } from 'react-i18next';
import { Ticket, RefreshCw, Settings, ExternalLink } from 'lucide-react';
import { useProjectStore } from '../../stores/project-store';
import { useJiraTickets } from './hooks';
import { TicketList, TicketFilterBar, TicketDetail } from './components';
import { Button } from '../ui/button';
import { ResizablePanels } from '../ui/resizable-panels';
import type { JiraIssue } from '../../../shared/types';

interface JiraTicketsProps {
  onOpenSettings?: () => void;
  isActive?: boolean;
}

function NotConnectedState({
  error,
  onOpenSettings,
  t,
}: {
  error: string | null;
  onOpenSettings?: () => void;
  t: (key: string) => string;
}) {
  return (
    <div className="flex-1 flex items-center justify-center p-8">
      <div className="text-center max-w-md">
        <Ticket className="h-12 w-12 mx-auto mb-4 text-muted-foreground opacity-50" />
        <h3 className="text-lg font-medium mb-2">{t('jira.notConnected')}</h3>
        <p className="text-sm text-muted-foreground mb-4">
          {error || t('jira.connectPrompt')}
        </p>
        {onOpenSettings && (
          <Button onClick={onOpenSettings} variant="outline">
            <Settings className="h-4 w-4 mr-2" />
            {t('jira.openSettings')}
          </Button>
        )}
      </div>
    </div>
  );
}

function EmptyState({ message }: { message: string }) {
  return (
    <div className="flex-1 flex items-center justify-center">
      <div className="text-center text-muted-foreground">
        <Ticket className="h-8 w-8 mx-auto mb-2 opacity-50" />
        <p>{message}</p>
      </div>
    </div>
  );
}

export function JiraTickets({ onOpenSettings, isActive = false }: JiraTicketsProps) {
  const { t } = useTranslation('common');
  const projects = useProjectStore((state) => state.projects);
  const selectedProjectId = useProjectStore((state) => state.selectedProjectId);
  const selectedProject = projects.find((p) => p.id === selectedProjectId);

  const [searchQuery, setSearchQuery] = useState('');

  const {
    tickets,
    isLoading,
    error,
    selectedTicket,
    isConnected,
    connectionStatus,
    selectTicket,
    refresh,
  } = useJiraTickets(selectedProject?.id, { isActive });

  // Filter tickets by search query
  const filteredTickets = useMemo(() => {
    if (!searchQuery.trim()) return tickets;

    const query = searchQuery.toLowerCase();
    return tickets.filter(
      (ticket) =>
        ticket.key.toLowerCase().includes(query) ||
        ticket.summary.toLowerCase().includes(query) ||
        ticket.labels.some((label) => label.toLowerCase().includes(query))
    );
  }, [tickets, searchQuery]);

  const hasActiveFilters = searchQuery.trim().length > 0;

  const clearFilters = useCallback(() => {
    setSearchQuery('');
  }, []);

  const handleSelectTicket = useCallback(
    (ticket: JiraIssue) => {
      selectTicket(ticket);
    },
    [selectTicket]
  );

  // Not connected state
  if (!isConnected) {
    return <NotConnectedState error={error} onOpenSettings={onOpenSettings} t={t} />;
  }

  return (
    <div className="flex-1 flex flex-col h-full">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-border">
        <div className="flex items-center gap-3">
          <h2 className="text-sm font-medium flex items-center gap-2">
            <Ticket className="h-4 w-4" />
            {t('jira.tickets')}
          </h2>
          {connectionStatus?.baseUrl && (
            <a
              href={connectionStatus.baseUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="text-xs text-muted-foreground hover:text-foreground flex items-center gap-1"
            >
              {connectionStatus.currentUser || 'Jira'}
              <ExternalLink className="h-3 w-3" />
            </a>
          )}
          <span className="text-xs text-muted-foreground">
            {tickets.length} {t('jira.assigned')}
          </span>
        </div>
        <Button variant="ghost" size="icon" onClick={refresh} disabled={isLoading}>
          <RefreshCw className={`h-4 w-4 ${isLoading ? 'animate-spin' : ''}`} />
        </Button>
      </div>

      {/* Content - Resizable split panels */}
      <ResizablePanels
        defaultLeftWidth={35}
        minLeftWidth={25}
        maxLeftWidth={50}
        storageKey="jira-tickets-panel-width"
        leftPanel={
          <div className="flex flex-col h-full">
            <TicketFilterBar
              searchQuery={searchQuery}
              onSearchChange={setSearchQuery}
              hasActiveFilters={hasActiveFilters}
              onClearFilters={clearFilters}
            />
            <TicketList
              tickets={filteredTickets}
              selectedTicketKey={selectedTicket?.key || null}
              isLoading={isLoading}
              error={error}
              onSelectTicket={handleSelectTicket}
            />
          </div>
        }
        rightPanel={
          selectedTicket ? (
            <TicketDetail
              ticket={selectedTicket}
              projectId={selectedProjectId || ''}
            />
          ) : (
            <EmptyState message={t('jira.selectTicketToView')} />
          )
        }
      />
    </div>
  );
}
