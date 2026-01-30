import { useTranslation } from 'react-i18next';
import {
  GitPullRequest,
  ExternalLink,
  Loader2,
  FileCode,
} from 'lucide-react';
import { Badge } from '../../ui/badge';
import { Button } from '../../ui/button';
import { cn } from '../../../lib/utils';
import type { PRData } from '../../../../preload/api/modules/github-api';

interface LinkedPRSectionProps {
  ticketKey: string;
  linkedPRs: PRData[];
  isLoading: boolean;
  projectId: string;
}

interface PRCardProps {
  pr: PRData;
}

function PRCard({ pr }: PRCardProps) {

  const prStatusColor = {
    open: 'bg-green-500',
    closed: 'bg-red-500',
    merged: 'bg-purple-500',
    OPEN: 'bg-green-500',
    CLOSED: 'bg-red-500',
    MERGED: 'bg-purple-500',
  }[pr.state] || 'bg-gray-500';

  return (
    <div className="border border-border rounded-lg p-4">
      {/* PR Header */}
      <div className="flex items-start gap-3">
        <GitPullRequest className="h-5 w-5 text-muted-foreground shrink-0 mt-0.5" />
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <span className="text-sm font-mono text-muted-foreground">
              #{pr.number}
            </span>
            <span className={cn('w-2 h-2 rounded-full', prStatusColor)} />
            <span className="text-xs text-muted-foreground capitalize">
              {pr.state.toLowerCase()}
            </span>
          </div>
          <p className="text-sm font-medium">{pr.title}</p>
          <p className="text-xs text-muted-foreground mt-1">
            {pr.headRefName} &rarr; {pr.baseRefName}
          </p>

          {/* PR Stats */}
          <div className="flex items-center gap-4 mt-3 text-xs text-muted-foreground">
            {pr.changedFiles !== undefined && (
              <span className="flex items-center gap-1">
                <FileCode className="h-3 w-3" />
                {pr.changedFiles} files
              </span>
            )}
            {pr.additions !== undefined && pr.deletions !== undefined && (
              <span>
                <span className="text-green-500">+{pr.additions}</span>
                {' / '}
                <span className="text-red-500">-{pr.deletions}</span>
              </span>
            )}
          </div>

          {/* Author */}
          {pr.author && (
            <div className="flex items-center gap-2 mt-3">
              <span className="text-xs text-muted-foreground">
                by {pr.author.login}
              </span>
            </div>
          )}
        </div>

        {/* Open in GitHub button */}
        <Button
          variant="ghost"
          size="sm"
          onClick={() => window.open(pr.htmlUrl, '_blank')}
          className="shrink-0"
        >
          <ExternalLink className="h-4 w-4" />
        </Button>
      </div>
    </div>
  );
}

export function LinkedPRSection({
  ticketKey,
  linkedPRs,
  isLoading,
}: LinkedPRSectionProps) {
  const { t } = useTranslation('common');

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-8">
        <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (linkedPRs.length === 0) {
    return (
      <div className="text-center py-8 text-muted-foreground">
        <GitPullRequest className="h-8 w-8 mx-auto mb-2 opacity-50" />
        <p>{t('jira.noLinkedPRs', { ticketKey })}</p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <h3 className="text-sm font-medium flex items-center gap-2">
        <GitPullRequest className="h-4 w-4" />
        {t('jira.linkedPRs')}
        <Badge variant="secondary">{linkedPRs.length}</Badge>
      </h3>
      <div className="space-y-3">
        {linkedPRs.map((pr) => (
          <PRCard key={pr.number} pr={pr} />
        ))}
      </div>
    </div>
  );
}
