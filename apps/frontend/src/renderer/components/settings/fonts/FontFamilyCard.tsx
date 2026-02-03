import { useEffect } from 'react';
import { Type } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { Label } from '../../ui/label';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '../../ui/select';
import { SettingsSection } from '../SettingsSection';
import { useGoogleFonts } from './hooks/useGoogleFonts';
import { DEFAULT_FONT_SANS_SERIF, DEFAULT_FONT_SERIF, DEFAULT_FONT_MONO } from '../../../../shared/constants';
import type { FontSettings } from '../../../../shared/types';
import type { FontCategory } from './types';

interface FontFamilyCardProps {
  fontSettings: FontSettings;
  onFontChange: (key: keyof FontSettings, value: string) => void;
}

interface FontSelectorProps {
  category: FontCategory;
  label: string;
  description: string;
  value: string;
  onChange: (value: string) => void;
}

function FontSelector({ category, label, description, value, onChange }: FontSelectorProps) {
  const { fonts, isLoading, loadFont } = useGoogleFonts({ category });

  // Load the currently selected font
  useEffect(() => {
    if (value) {
      loadFont(value);
    }
  }, [value, loadFont]);

  // Handle font selection
  const handleChange = (newValue: string) => {
    loadFont(newValue);
    onChange(newValue);
  };

  return (
    <div className="space-y-2">
      <Label className="text-sm font-medium">{label}</Label>
      <p className="text-xs text-muted-foreground">{description}</p>
      <Select value={value} onValueChange={handleChange} disabled={isLoading}>
        <SelectTrigger className="w-full">
          <SelectValue placeholder={isLoading ? 'Loading fonts...' : 'Select a font'}>
            <span style={{ fontFamily: value }}>{value}</span>
          </SelectValue>
        </SelectTrigger>
        <SelectContent className="max-h-[300px]">
          {fonts.map((font, index) => (
            <SelectItem
              key={`${font.value}-${index}`}
              value={font.value}
              className="cursor-pointer"
            >
              <span
                style={{ fontFamily: font.value }}
                onMouseEnter={() => loadFont(font.value)}
              >
                {font.label}
              </span>
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
      {/* Preview */}
      <div
        className="p-3 rounded-md border border-border bg-muted/30 text-sm"
        style={{ fontFamily: value }}
      >
        The quick brown fox jumps over the lazy dog.
      </div>
    </div>
  );
}

export function FontFamilyCard({ fontSettings, onFontChange }: FontFamilyCardProps) {
  const { t } = useTranslation('settings');

  const sansSerifValue = fontSettings.sansSerif || DEFAULT_FONT_SANS_SERIF;
  const serifValue = fontSettings.serif || DEFAULT_FONT_SERIF;
  const monoValue = fontSettings.mono || DEFAULT_FONT_MONO;

  return (
    <SettingsSection
      title={t('sections.fonts.title', 'Font Family')}
      description={t('sections.fonts.description', 'Customize the fonts used throughout the application')}
    >
      <div className="space-y-6">
        <div className="flex items-center gap-2 text-sm text-muted-foreground">
          <Type className="h-4 w-4" />
          <span>{t('sections.fonts.googleFontsNote', 'Fonts are loaded from Google Fonts')}</span>
        </div>

        <div className="grid gap-6">
          <FontSelector
            category="sans-serif"
            label={t('sections.fonts.sansSerif', 'Sans-Serif Font')}
            description={t('sections.fonts.sansSerifDescription', 'Used for UI elements and body text')}
            value={sansSerifValue}
            onChange={(value) => onFontChange('sansSerif', value)}
          />

          <FontSelector
            category="serif"
            label={t('sections.fonts.serif', 'Serif Font')}
            description={t('sections.fonts.serifDescription', 'Used for headings and emphasis')}
            value={serifValue}
            onChange={(value) => onFontChange('serif', value)}
          />

          <FontSelector
            category="monospace"
            label={t('sections.fonts.mono', 'Monospace Font')}
            description={t('sections.fonts.monoDescription', 'Used for code and terminal output')}
            value={monoValue}
            onChange={(value) => onFontChange('mono', value)}
          />
        </div>
      </div>
    </SettingsSection>
  );
}
