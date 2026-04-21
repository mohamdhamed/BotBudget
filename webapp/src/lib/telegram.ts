import { useEffect, useState } from 'react';

/** Minimal Telegram WebApp typing (we avoid deep SDK coupling). */
declare global {
  interface Window {
    Telegram?: {
      WebApp?: {
        initData: string;
        initDataUnsafe: { user?: TelegramUser };
        ready: () => void;
        expand: () => void;
        colorScheme: 'light' | 'dark';
        themeParams: Record<string, string>;
        onEvent: (event: string, cb: () => void) => void;
      };
    };
  }
}

export interface TelegramUser {
  id: number;
  first_name?: string;
  last_name?: string;
  username?: string;
  language_code?: string;
}

export function initTelegram() {
  const wa = window.Telegram?.WebApp;
  if (!wa) return;
  wa.ready();
  wa.expand();
  applyTheme(wa.themeParams);
  wa.onEvent('themeChanged', () => applyTheme(wa.themeParams));
}

function applyTheme(params: Record<string, string>) {
  const root = document.documentElement;
  const map: Record<string, string> = {
    bg_color: '--tg-theme-bg-color',
    text_color: '--tg-theme-text-color',
    hint_color: '--tg-theme-hint-color',
    link_color: '--tg-theme-link-color',
    button_color: '--tg-theme-button-color',
    button_text_color: '--tg-theme-button-text-color',
    secondary_bg_color: '--tg-theme-secondary-bg-color',
  };
  for (const [k, cssVar] of Object.entries(map)) {
    const v = params[k];
    if (v) root.style.setProperty(cssVar, v);
  }
}

export function getInitDataRaw(): string {
  return window.Telegram?.WebApp?.initData || '';
}

export function useUser(): TelegramUser | null {
  const [user, setUser] = useState<TelegramUser | null>(
    () => window.Telegram?.WebApp?.initDataUnsafe?.user ?? null,
  );
  useEffect(() => {
    if (!user) {
      const u = window.Telegram?.WebApp?.initDataUnsafe?.user ?? null;
      if (u) setUser(u);
    }
  }, [user]);
  return user;
}
