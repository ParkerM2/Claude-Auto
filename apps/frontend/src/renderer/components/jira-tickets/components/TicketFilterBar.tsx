import { Search, X } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { Input } from '../../ui/input';
import { Button } from '../../ui/button';

interface TicketFilterBarProps {
  searchQuery: string;
  onSearchChange: (query: string) => void;
  hasActiveFilters: boolean;
  onClearFilters: () => void;
}

export function TicketFilterBar({
  searchQuery,
  onSearchChange,
  hasActiveFilters,
  onClearFilters,
}: TicketFilterBarProps) {
  const { t } = useTranslation('common');

  return (
    <div className="p-2 border-b border-border">
      <div className="relative">
        <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
        <Input
          placeholder={t('jira.searchPlaceholder')}
          value={searchQuery}
          onChange={(e) => onSearchChange(e.target.value)}
          className="pl-8 pr-8 h-9"
        />
        {hasActiveFilters && (
          <Button
            variant="ghost"
            size="icon"
            className="absolute right-1 top-1 h-7 w-7"
            onClick={onClearFilters}
          >
            <X className="h-3 w-3" />
          </Button>
        )}
      </div>
    </div>
  );
}
