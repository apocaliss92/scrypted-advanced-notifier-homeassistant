import Link from 'next/link';

const CARDS = [
  {
    href: '/docs/installation',
    title: 'Install it',
    body: 'Add the repository to HACS, restart, and run the two-step config flow.',
  },
  {
    href: '/docs/architecture',
    title: 'Understand it',
    body: 'How the Scrypted plugin pushes state into Home Assistant and how commands travel back.',
  },
  {
    href: '/docs/reference',
    title: 'Look it up',
    body: 'Configuration fields, entity platforms, events and endpoints — generated from the source, never hand-typed.',
  },
];

export default function HomePage() {
  return (
    <main className="flex flex-1 flex-col">
      <section className="flex flex-col items-center justify-center px-4 py-20 text-center">
        <h1 className="max-w-3xl text-4xl font-bold tracking-tight md:text-5xl">
          Scrypted Advanced Notifier for Home Assistant
        </h1>
        <p className="mt-5 max-w-2xl text-lg text-fd-muted-foreground">
          A custom integration that imports your Scrypted cameras, detection sensors and
          plugin controls into Home Assistant — pushed live, no polling, no MQTT broker.
        </p>
        <div className="mt-8 flex flex-wrap items-center justify-center gap-3">
          <Link
            href="/docs"
            className="rounded-lg bg-fd-primary px-5 py-2.5 font-medium text-fd-primary-foreground"
          >
            Read the docs
          </Link>
          <Link
            href="/docs/installation"
            className="rounded-lg border border-fd-border px-5 py-2.5 font-medium"
          >
            Installation
          </Link>
        </div>
      </section>

      <section className="mx-auto grid w-full max-w-5xl gap-4 px-4 pb-24 md:grid-cols-3">
        {CARDS.map((card) => (
          <Link
            key={card.href}
            href={card.href}
            className="rounded-xl border border-fd-border bg-fd-card p-5 transition-colors hover:bg-fd-accent"
          >
            <h2 className="font-semibold">{card.title}</h2>
            <p className="mt-2 text-sm text-fd-muted-foreground">{card.body}</p>
          </Link>
        ))}
      </section>
    </main>
  );
}
