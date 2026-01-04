interface TelegramWebApp {
  initData: string;
  initDataUnsafe: {
    user?: {
      id: number;
      first_name: string;
      last_name?: string;
      username?: string;
      language_code?: string;
    };
  };
  ready: () => void;
  expand: () => void;
  close: () => void;
  openInvoice: (
    url: string,
    callback?: (status: 'paid' | 'cancelled' | 'failed' | 'pending') => void
  ) => void;
}

interface Window {
  Telegram?: {
    WebApp: TelegramWebApp;
  };
}
