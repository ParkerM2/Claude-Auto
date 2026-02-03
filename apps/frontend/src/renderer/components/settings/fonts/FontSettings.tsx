import { useCallback } from 'react';
import { FontFamilyCard } from './FontFamilyCard';
import { LetterSpacingCard } from './LetterSpacingCard';
import { useSettingsStore } from '../../../stores/settings-store';
import type { AppSettings, FontSettings as FontSettingsType } from '../../../../shared/types';

interface FontSettingsProps {
  settings: AppSettings;
  onSettingsChange: (settings: AppSettings) => void;
}

export function FontSettings({ settings, onSettingsChange }: FontSettingsProps) {
  const fontSettings = settings.fontSettings || {};
  const updateAndPersist = useSettingsStore((state) => state.updateAndPersist);

  // Handle font family changes
  const handleFontChange = useCallback(
    (key: keyof FontSettingsType, value: string) => {
      const newFontSettings: FontSettingsType = {
        ...fontSettings,
        [key]: value,
      };
      // Update local draft state (for save)
      onSettingsChange({
        ...settings,
        fontSettings: newFontSettings,
      });
      // Persist immediately so fonts survive HMR/refresh
      updateAndPersist({ fontSettings: newFontSettings });
    },
    [settings, fontSettings, onSettingsChange, updateAndPersist]
  );

  // Handle letter spacing changes
  const handleLetterSpacingChange = useCallback(
    (value: number) => {
      const newFontSettings: FontSettingsType = {
        ...fontSettings,
        letterSpacing: value,
      };
      // Update local draft state (for save)
      onSettingsChange({
        ...settings,
        fontSettings: newFontSettings,
      });
      // Persist immediately so letter spacing survives HMR/refresh
      updateAndPersist({ fontSettings: newFontSettings });
    },
    [settings, fontSettings, onSettingsChange, updateAndPersist]
  );

  return (
    <div className="space-y-6">
      <FontFamilyCard
        fontSettings={fontSettings}
        onFontChange={handleFontChange}
      />
      <LetterSpacingCard
        fontSettings={fontSettings}
        onLetterSpacingChange={handleLetterSpacingChange}
      />
    </div>
  );
}
