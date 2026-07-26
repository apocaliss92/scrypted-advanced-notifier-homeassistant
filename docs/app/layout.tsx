import { RootProvider } from 'fumadocs-ui/provider/next';
import './global.css';
import { Inter } from 'next/font/google';
import type { Metadata } from 'next';

const inter = Inter({
  subsets: ['latin'],
});

export const metadata: Metadata = {
  title: {
    default: 'Scrypted Advanced Notifier for Home Assistant',
    template: '%s — Scrypted Advanced Notifier for Home Assistant',
  },
  description:
    'Official documentation for the Home Assistant custom integration that brings Scrypted Advanced Notifier cameras, sensors and controls into Home Assistant.',
};

export default function Layout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={inter.className} suppressHydrationWarning>
      <body className="flex flex-col min-h-screen">
        <RootProvider>{children}</RootProvider>
      </body>
    </html>
  );
}
