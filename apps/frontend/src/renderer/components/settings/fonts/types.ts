/**
 * Font settings types
 */

export type FontCategory = 'sans-serif' | 'serif' | 'monospace';

export interface GoogleFont {
  family: string;
  category: string;
  variants: string[];
  subsets: string[];
}

export interface GoogleFontsResponse {
  items: GoogleFont[];
}

export interface FontOption {
  value: string;
  label: string;
  isLoaded?: boolean;
}

export interface FontSettingsProps {
  onSettingsChange: (settings: import('../../../../shared/types').AppSettings) => void;
  settings: import('../../../../shared/types').AppSettings;
}
