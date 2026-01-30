import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { ExternalLink, Tag, User } from 'lucide-react';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../../ui/tabs';
import { Badge } from '../../ui/badge';
import { Button } from '../../ui/button';
import { ScrollArea } from '../../ui/scroll-area';
import { cn } from '../../../lib/utils';
import type { JiraIssue } from '../../../../shared/types';
import { useLinkedPRs } from '../hooks';
import { LinkedPRSection } from './LinkedPRSection';

interface TicketDetailProps {
  ticket: JiraIssue;
  projectId: string;
}

function getStatusColor(category: 'todo' | 'in_progress' | 'done'): string {
  switch (category) {
    case 'todo':
      return 'bg-slate-500 text-white';
    case 'in_progress':
      return 'bg-blue-500 text-white';
    case 'done':
      return 'bg-green-500 text-white';
    default:
      return 'bg-gray-500 text-white';
  }
}

export function TicketDetail({ ticket, projectId }: TicketDetailProps) {
  const { t } = useTranslation('common');
  const [activeTab, setActiveTab] = useState('jira');

  const { linkedPRs, isLoading: isLoadingPRs } = useLinkedPRs(ticket.key, projectId);

  return (
    <div className="h-full flex flex-col">
      {/* Header */}
      <div className="px-4 py-3 border-b border-border">
        <div className="flex items-start justify-between gap-4">
          <div className="min-w-0 flex-1">
            <div className="flex items-center gap-2 mb-1">
              <span className="text-sm font-mono text-muted-foreground">
                {ticket.key}
              </span>
              <Badge className={cn('text-xs', getStatusColor(ticket.status.category))}>
                {ticket.status.name}
              </Badge>
            </div>
            <h2 className="text-lg font-medium">{ticket.summary}</h2>
          </div>
          <Button
            variant="ghost"
            size="sm"
            onClick={() => window.open(ticket.url, '_blank')}
            className="shrink-0"
          >
            <ExternalLink className="h-4 w-4 mr-1" />
            {t('jira.openInJira')}
          </Button>
        </div>
      </div>

      {/* Tabs */}
      <Tabs value={activeTab} onValueChange={setActiveTab} className="flex-1 flex flex-col">
        <TabsList className="mx-4 mt-3 justify-start">
          <TabsTrigger value="jira">{t('jira.tabs.jira')}</TabsTrigger>
          <TabsTrigger value="github">
            {t('jira.tabs.github')}
            {linkedPRs.length > 0 && (
              <Badge variant="secondary" className="ml-1.5 px-1.5 py-0 text-xs">
                {linkedPRs.length}
              </Badge>
            )}
          </TabsTrigger>
        </TabsList>

        <TabsContent value="jira" className="flex-1 mt-0">
          <ScrollArea className="h-full">
            <div className="p-4 space-y-6">
              {/* Metadata */}
              <div className="grid grid-cols-2 gap-4">
                {/* Story Points */}
                {ticket.storyPoints !== undefined && ticket.storyPoints !== null && (
                  <div>
                    <label className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
                      {t('jira.storyPoints')}
                    </label>
                    <p className="mt-1 text-sm font-medium">{ticket.storyPoints}</p>
                  </div>
                )}

                {/* Priority */}
                {ticket.priority && (
                  <div>
                    <label className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
                      {t('jira.priority')}
                    </label>
                    <div className="mt-1 flex items-center gap-2">
                      {ticket.priority.iconUrl && (
                        <img src={ticket.priority.iconUrl} alt="" className="w-4 h-4" />
                      )}
                      <span className="text-sm">{ticket.priority.name}</span>
                    </div>
                  </div>
                )}

                {/* Assignee */}
                {ticket.assignee && (
                  <div>
                    <label className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
                      {t('jira.assignee')}
                    </label>
                    <div className="mt-1 flex items-center gap-2">
                      {ticket.assignee.avatarUrl ? (
                        <img
                          src={ticket.assignee.avatarUrl}
                          alt=""
                          className="w-5 h-5 rounded-full"
                        />
                      ) : (
                        <User className="w-5 h-5 text-muted-foreground" />
                      )}
                      <span className="text-sm">{ticket.assignee.displayName}</span>
                    </div>
                  </div>
                )}

                {/* Reporter */}
                {ticket.reporter && (
                  <div>
                    <label className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
                      {t('jira.reporter')}
                    </label>
                    <div className="mt-1 flex items-center gap-2">
                      {ticket.reporter.avatarUrl ? (
                        <img
                          src={ticket.reporter.avatarUrl}
                          alt=""
                          className="w-5 h-5 rounded-full"
                        />
                      ) : (
                        <User className="w-5 h-5 text-muted-foreground" />
                      )}
                      <span className="text-sm">{ticket.reporter.displayName}</span>
                    </div>
                  </div>
                )}
              </div>

              {/* Labels */}
              {ticket.labels.length > 0 && (
                <div>
                  <label className="text-xs font-medium text-muted-foreground uppercase tracking-wide flex items-center gap-1">
                    <Tag className="h-3 w-3" />
                    {t('jira.labels')}
                  </label>
                  <div className="mt-2 flex flex-wrap gap-1.5">
                    {ticket.labels.map((label) => (
                      <Badge key={label} variant="secondary" className="text-xs">
                        {label}
                      </Badge>
                    ))}
                  </div>
                </div>
              )}

              {/* Description */}
              {ticket.description && (
                <div>
                  <label className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
                    {t('jira.description')}
                  </label>
                  <div className="mt-2 text-sm prose prose-sm dark:prose-invert max-w-none">
                    <pre className="whitespace-pre-wrap font-sans bg-muted p-3 rounded-lg">
                      {ticket.description}
                    </pre>
                  </div>
                </div>
              )}
            </div>
          </ScrollArea>
        </TabsContent>

        <TabsContent value="github" className="flex-1 mt-0">
          <ScrollArea className="h-full">
            <div className="p-4">
              <LinkedPRSection
                ticketKey={ticket.key}
                linkedPRs={linkedPRs}
                isLoading={isLoadingPRs}
                projectId={projectId}
              />
            </div>
          </ScrollArea>
        </TabsContent>
      </Tabs>
    </div>
  );
}
