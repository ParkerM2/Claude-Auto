import { useEffect } from 'react';
import { useSettingsStore } from '../stores/settings-store';
import {
  DEFAULT_FONT_SANS_SERIF,
  DEFAULT_FONT_SERIF,
  DEFAULT_FONT_MONO,
  LETTER_SPACING_DEFAULT,
} from '../../shared/constants';

/**
 * Hook to apply font settings to the document root
 * This allows dynamic font customization throughout the app
 */
export function useFontSettings() {
  const fontSettings = useSettingsStore((state) => state.settings.fontSettings);

  useEffect(() => {
    const root = document.documentElement;

    // Apply font families
    const sansSerif = fontSettings?.sansSerif || DEFAULT_FONT_SANS_SERIF;
    const serif = fontSettings?.serif || DEFAULT_FONT_SERIF;
    const mono = fontSettings?.mono || DEFAULT_FONT_MONO;
    const letterSpacing = fontSettings?.letterSpacing ?? LETTER_SPACING_DEFAULT;

    // Set CSS custom properties
    root.style.setProperty('--app-font-sans', `'${sansSerif}'`);
    root.style.setProperty('--app-font-serif', `'${serif}'`);
    root.style.setProperty('--app-font-mono', `'${mono}'`);
    root.style.setProperty('--app-letter-spacing', `${letterSpacing}em`);

    // Load fonts if they're Google Fonts
    const fontsToLoad = [sansSerif, serif, mono].filter(
      (font) => font && font !== 'system-ui' && font !== 'ui-monospace' && font !== 'Georgia'
    );

    fontsToLoad.forEach((font) => {
      // Check if font is already loaded
      const existingLink = document.querySelector(`link[href*="${encodeURIComponent(font).replace(/%20/g, '+')}"]`);
      if (!existingLink) {
        const link = document.createElement('link');
        link.href = `https://fonts.googleapis.com/css2?family=${encodeURIComponent(font).replace(/%20/g, '+')}:wght@400;500;600;700&display=swap`;
        link.rel = 'stylesheet';
        document.head.appendChild(link);
      }
    });
  }, [fontSettings]);
}
