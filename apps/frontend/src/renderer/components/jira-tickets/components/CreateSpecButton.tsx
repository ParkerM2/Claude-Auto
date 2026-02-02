import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { FileText, Loader2, CheckCircle2 } from 'lucide-react';
import { Button } from '../../ui/button';
import type { JiraIssue } from '../../../../shared/types';

interface CreateSpecButtonProps {
  ticket: JiraIssue;
  projectId: string;
}

export function CreateSpecButton({ ticket, projectId }: CreateSpecButtonProps) {
  const { t } = useTranslation('common');
  const [isCreating, setIsCreating] = useState(false);
  const [isSuccess, setIsSuccess] = useState(false);

  const handleCreateSpec = async () => {
    try {
      setIsCreating(true);
      setIsSuccess(false);

      const result = await window.electronAPI.jira.importAsSpec(projectId, ticket.key);

      if (result.success) {
        setIsSuccess(true);
        // Reset success state after 3 seconds
        setTimeout(() => setIsSuccess(false), 3000);
      } else {
        console.error('Failed to create spec:', result.error);
      }
    } catch (error) {
      console.error('Error creating spec from Jira ticket:', error);
    } finally {
      setIsCreating(false);
    }
  };

  if (isSuccess) {
    return (
      <Button variant="success" size="sm" disabled>
        <CheckCircle2 className="h-4 w-4 mr-1" />
        {t('jira.specCreated')}
      </Button>
    );
  }

  return (
    <Button
      variant="default"
      size="sm"
      onClick={handleCreateSpec}
      disabled={isCreating}
    >
      {isCreating ? (
        <>
          <Loader2 className="h-4 w-4 mr-1 animate-spin" />
          {t('jira.creatingSpec')}
        </>
      ) : (
        <>
          <FileText className="h-4 w-4 mr-1" />
          {t('jira.createSpec')}
        </>
      )}
    </Button>
  );
}
