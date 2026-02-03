import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { cn } from '../../lib/utils';

interface MarkdownContentProps {
  content: string;
  className?: string;
}

/**
 * Reusable markdown renderer with prose styling.
 * Uses react-markdown with GFM (GitHub Flavored Markdown) support.
 */
export function MarkdownContent({ content, className }: MarkdownContentProps) {
  return (
    <div className={cn(
      'prose prose-sm dark:prose-invert max-w-none',
      // Customize prose colors for the design system
      'prose-headings:text-foreground prose-headings:font-semibold',
      'prose-p:text-muted-foreground prose-p:leading-relaxed',
      'prose-a:text-primary prose-a:no-underline hover:prose-a:underline',
      'prose-code:text-accent-foreground prose-code:bg-secondary prose-code:px-1 prose-code:py-0.5 prose-code:rounded prose-code:text-xs',
      'prose-pre:bg-secondary prose-pre:border prose-pre:border-border',
      'prose-ul:text-muted-foreground prose-ol:text-muted-foreground',
      'prose-li:marker:text-muted-foreground',
      'prose-strong:text-foreground prose-strong:font-semibold',
      'prose-blockquote:border-l-primary prose-blockquote:text-muted-foreground',
      className
    )}>
      <ReactMarkdown remarkPlugins={[remarkGfm]}>{content}</ReactMarkdown>
    </div>
  );
}
