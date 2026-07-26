import type { BaseLayoutProps } from 'fumadocs-ui/layouts/shared';
import { Github } from 'lucide-react';

export const gitConfig = {
  user: 'apocaliss92',
  repo: 'scrypted-advanced-notifier-homeassistant',
  branch: 'main',
};

export function baseOptions(): BaseLayoutProps {
  return {
    nav: {
      title: 'Scrypted Advanced Notifier · HA',
      url: '/',
    },
    links: [
      {
        type: 'main',
        url: '/docs',
        text: 'Docs',
        on: 'nav',
      },
      {
        type: 'main',
        url: '/docs/reference',
        text: 'Reference',
        on: 'nav',
      },
      {
        type: 'main',
        url: 'https://github.com/apocaliss92/scrypted-advanced-notifier',
        text: 'Scrypted plugin',
        on: 'all',
        external: true,
      },
      {
        type: 'icon',
        url: `https://github.com/${gitConfig.user}/${gitConfig.repo}`,
        label: 'GitHub',
        icon: <Github className="h-5 w-5" />,
        text: 'GitHub',
        external: true,
        on: 'nav',
      },
    ],
  };
}
