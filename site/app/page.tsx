"use client";

import { useEffect, useRef, useState } from "react";

/* ─── Intersection fade-in ─── */
function FadeIn({
  children,
  delay = 0,
  className = "",
}: {
  children: React.ReactNode;
  delay?: number;
  className?: string;
}) {
  const ref = useRef<HTMLDivElement>(null);
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const obs = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          setVisible(true);
          obs.unobserve(el);
        }
      },
      { threshold: 0.06, rootMargin: "0px 0px -60px 0px" }
    );
    obs.observe(el);
    return () => obs.disconnect();
  }, []);

  return (
    <div
      ref={ref}
      className={className}
      style={{
        opacity: visible ? 1 : 0,
        transform: visible ? "translateY(0)" : "translateY(28px)",
        transition: `opacity 700ms cubic-bezier(0.22, 1, 0.36, 1) ${delay}ms, transform 700ms cubic-bezier(0.22, 1, 0.36, 1) ${delay}ms`,
      }}
    >
      {children}
    </div>
  );
}

/* ─── Copy button ─── */
function CopyButton({ text }: { text: string }) {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      /* noop */
    }
  };

  return (
    <button
      onClick={handleCopy}
      className="ml-3 inline-flex shrink-0 items-center justify-center rounded border border-base-300 bg-base-100 h-6 w-6 text-base-600 transition-colors hover:bg-base-200 hover:text-base-950"
      aria-label="Copy to clipboard"
      title={copied ? "Copied" : "Copy"}
    >
      {copied ? (
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <polyline points="20 6 9 17 4 12" />
        </svg>
      ) : (
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <rect x="9" y="9" width="13" height="13" rx="2" ry="2" />
          <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1" />
        </svg>
      )}
    </button>
  );
}

/* ─── Nav ─── */
function Nav() {
  return (
    <nav className="sticky top-0 z-50 border-b border-base-300/40 bg-background/90 backdrop-blur-xl">
      <div className="mx-auto flex h-14 max-w-6xl items-center justify-between px-4 sm:px-6 lg:px-8">
        <a href="/" className="text-[1.125rem] font-bold tracking-tight text-base-950">
          Seam
        </a>
        <div className="flex items-center gap-8 text-sm font-medium">
          <a
            href="https://github.com/Aditya190803/seam"
            target="_blank"
            rel="noopener noreferrer"
            className="hidden text-base-600 transition-colors hover:text-base-950 sm:block"
          >
            GitHub
          </a>
          <a
            href="#install"
            className="inline-flex h-9 items-center justify-center rounded bg-base-950 px-4 text-sm font-medium text-base-100 transition-colors hover:bg-base-900"
          >
            Get Started
          </a>
        </div>
      </div>
    </nav>
  );
}

/* ─── Rule ─── */
function Rule() {
  return <div className="h-px w-full bg-base-300" />;
}

/* ─── Dot grid background pattern ─── */
function DotGrid() {
  return (
    <div
      className="pointer-events-none absolute inset-0 opacity-[0.35]"
      style={{
        backgroundImage: `radial-gradient(circle, var(--base-400) 1px, transparent 1px)`,
        backgroundSize: "24px 24px",
      }}
    />
  );
}

/* ───────────────────────── PAGE ───────────────────────── */
export default function Home() {
  const curlCmd = `curl -fsSL https://seam.adityamer.dev/install.sh | bash`;

  return (
    <div className="min-h-screen bg-background">
      <Nav />

      {/* ═══════ HERO ═══════ */}
      <section className="relative overflow-hidden px-4 pt-10 pb-8 sm:px-6 md:px-8 md:pt-16 md:pb-12 lg:pt-20 lg:pb-16">
        <DotGrid />

        <div className="relative mx-auto max-w-6xl">
          <div className="flex flex-col items-center text-center">
            <FadeIn>
              <h1 className="max-w-4xl text-[clamp(2rem,6.5vw,5rem)] font-bold leading-[1.02] tracking-[-0.035em] text-base-950">
                Your codebase,
                <br />
                indexed once.
                <br />
                <span className="text-accent-600">Queried by any agent, instantly.</span>
              </h1>
            </FadeIn>

            <FadeIn delay={80}>
              <p className="mt-7 max-w-xl text-lg leading-relaxed text-base-600">
                Seam is a local-first CLI and MCP server that gives coding agents
                semantic access to your repository. No more re-reading the entire
                codebase on every task.
              </p>
            </FadeIn>

            <FadeIn delay={160}>
              {/* Curl command bar */}
              <div className="mt-10 w-full max-w-2xl">
                <div className="flex items-center justify-between">
                  <span className="text-[10px] font-bold uppercase tracking-[0.15em] text-base-500">
                    Install
                  </span>
                    <span className="text-[10px] font-bold uppercase tracking-[0.15em] text-base-500">
                      macOS / Linux
                    </span>
                  </div>
                <div className="mt-2 flex items-center justify-between gap-3 overflow-x-auto rounded-lg border border-base-300 bg-base-100 px-3 py-1.5">
                  <code className="whitespace-nowrap font-mono text-[11px] text-base-950 sm:text-[13px]">
                    <span className="text-accent-600">$</span> {curlCmd}
                  </code>
                  <CopyButton text={curlCmd} />
                </div>
              </div>
            </FadeIn>

            <FadeIn delay={240}>
              <div className="mt-5 flex w-full flex-col gap-3 text-sm sm:w-auto sm:flex-row sm:gap-4">
                <a
                  href="#install"
                  className="inline-flex h-11 w-full items-center justify-center rounded bg-base-950 px-5 text-sm font-medium text-base-100 transition-colors hover:bg-base-900 sm:w-auto"
                >
                  Get Started
                </a>
                <a
                  href="https://github.com/Aditya190803/seam"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex h-11 w-full items-center justify-center rounded border border-base-300 bg-transparent px-5 text-sm font-medium text-base-950 transition-colors hover:bg-base-200 sm:w-auto"
                >
                  View on GitHub
                </a>
              </div>
            </FadeIn>
          </div>
        </div>
      </section>

      <Rule />

      {/* ═══════ HOW IT WORKS ═══════ */}
      <section className="px-4 py-14 sm:px-6 md:px-8 md:py-20 lg:py-28">
        <div className="mx-auto max-w-6xl">
          <FadeIn>
            <div className="flex items-baseline gap-3">
              <span className="text-[10px] font-bold uppercase tracking-[0.15em] text-accent-600">
                01
              </span>
              <h2 className="text-[clamp(1.75rem,4.5vw,2.75rem)] font-semibold leading-[1.1] tracking-[-0.02em] text-base-950">
                How it works
              </h2>
            </div>
          </FadeIn>

          <div className="mt-14 grid gap-10 md:grid-cols-3 md:gap-6">
            {[
              {
                num: "01",
                title: "Index",
                desc: "Run seam init . Seam walks your repo, chunks files with tree-sitter, computes embeddings, and stores everything in a local vector database.",
              },
              {
                num: "02",
                title: "Search",
                desc: "Query with natural language. Hybrid vector + keyword ranking surfaces the most relevant code across your entire codebase in milliseconds.",
              },
              {
                num: "03",
                title: "Context",
                desc: "seam context generates formatted code blocks your agent can paste directly. XML, markdown, or JSON. Ready for Claude, Codex, Cursor.",
              },
            ].map((step, i) => (
              <FadeIn key={step.num} delay={i * 130}>
                <div>
                  <div className="font-mono text-[3.5rem] font-bold leading-none text-base-200">
                    {step.num}
                  </div>
                  <h3 className="mt-4 text-xl font-semibold text-base-950">
                    {step.title}
                  </h3>
                  <p className="mt-2 text-base leading-relaxed text-base-600">
                    {step.desc}
                  </p>
                </div>
              </FadeIn>
            ))}
          </div>
        </div>
      </section>

      <Rule />

      {/* ═══════ FEATURES ═══════ */}
      <section className="bg-base-200/15 px-4 py-14 sm:px-6 md:px-8 md:py-20 lg:py-28">
        <div className="mx-auto max-w-6xl">
          <FadeIn>
            <div className="flex items-baseline gap-3">
              <span className="text-[10px] font-bold uppercase tracking-[0.15em] text-accent-600">
                02
              </span>
              <h2 className="text-[clamp(1.75rem,4.5vw,2.75rem)] font-semibold leading-[1.1] tracking-[-0.02em] text-base-950">
                Built for agents
              </h2>
            </div>
          </FadeIn>

          {/* Asymmetric feature stack */}
          <div className="mt-14 space-y-0">
            <FadeIn delay={100}>
              <div className="grid gap-6 border-b border-base-300 py-8 md:gap-8 md:py-10 lg:grid-cols-[1fr_1.5fr]">
                <div>
                  <div className="font-mono text-[10px] font-bold uppercase tracking-[0.15em] text-accent-600">
                    Local-first
                  </div>
                  <h3 className="mt-2 text-xl font-semibold leading-tight text-base-950 md:text-2xl">
                    Your code never leaves your machine
                  </h3>
                </div>
                <p className="text-base leading-relaxed text-base-600 lg:pt-6">
                  Offline embeddings, local vector store, zero external dependencies. Privacy by design, not by policy. No API keys, no rate limits, no network required.
                </p>
              </div>
            </FadeIn>

            <FadeIn delay={180}>
              <div className="grid gap-6 border-b border-base-300 py-8 md:gap-8 md:py-10 lg:grid-cols-[1.5fr_1fr]">
                <p className="order-2 text-base leading-relaxed text-base-600 lg:order-1 lg:pt-6">
                  SQLite backend, deterministic embeddings, automatic file watching. Works the moment you install. No yaml to write, no daemons to manage.
                </p>
                <div className="order-1 lg:order-2 lg:text-right">
                  <div className="font-mono text-[10px] font-bold uppercase tracking-[0.15em] text-accent-600">
                    Zero-config
                  </div>
                  <h3 className="mt-2 text-xl font-semibold leading-tight text-base-950 md:text-2xl">
                    Sensible defaults
                  </h3>
                </div>
              </div>
            </FadeIn>

            <FadeIn delay={260}>
              <div className="grid gap-6 border-b border-base-300 py-8 md:gap-8 md:py-10 lg:grid-cols-[1fr_1.5fr]">
                <div>
                  <div className="font-mono text-[10px] font-bold uppercase tracking-[0.15em] text-accent-600">
                    Incremental
                  </div>
                  <h3 className="mt-2 text-xl font-semibold leading-tight text-base-950 md:text-2xl">
                    Smart indexing
                  </h3>
                </div>
                <p className="text-base leading-relaxed text-base-600 lg:pt-6">
                  File hashing and tree-sitter chunking. Only re-index what changed. Merkle tree tracks state. Watch mode keeps it fresh automatically.
                </p>
              </div>
            </FadeIn>

            <FadeIn delay={340}>
              <div className="grid gap-6 border-b border-base-300 py-8 md:gap-8 md:py-10 lg:grid-cols-[1.5fr_1fr]">
                <p className="order-2 text-base leading-relaxed text-base-600 lg:order-1 lg:pt-6">
                  FastMCP server with search_code, list_files, get_chunk tools. Works with Claude, Codex, Cursor, and any MCP client out of the box.
                </p>
                <div className="order-1 lg:order-2 lg:text-right">
                  <div className="font-mono text-[10px] font-bold uppercase tracking-[0.15em] text-accent-600">
                    MCP ready
                  </div>
                  <h3 className="mt-2 text-xl font-semibold leading-tight text-base-950 md:text-2xl">
                    FastMCP server
                  </h3>
                </div>
              </div>
            </FadeIn>

            <FadeIn delay={420}>
              <div className="grid gap-6 py-8 md:gap-8 md:py-10 lg:grid-cols-[1fr_1.5fr]">
                <div>
                  <div className="font-mono text-[10px] font-bold uppercase tracking-[0.15em] text-accent-600">
                    Portable
                  </div>
                  <h3 className="mt-2 text-xl font-semibold leading-tight text-base-950 md:text-2xl">
                    Export / Import
                  </h3>
                </div>
                <p className="text-base leading-relaxed text-base-600 lg:pt-6">
                  Move your index between machines. Share with teammates. No re-indexing. Archive and restore with a single command.
                </p>
              </div>
            </FadeIn>
          </div>
        </div>
      </section>

      {/* ═══════ BACKENDS ═══════ */}
      <section className="px-4 py-14 sm:px-6 md:px-8 md:py-20 lg:py-28">
        <div className="mx-auto max-w-6xl">
          <FadeIn>
            <div className="flex items-baseline gap-3">
              <span className="text-[10px] font-bold uppercase tracking-[0.15em] text-accent-600">
                03
              </span>
              <h2 className="text-[clamp(1.75rem,4.5vw,2.75rem)] font-semibold leading-[1.1] tracking-[-0.02em] text-base-950">
                Backends & Providers
              </h2>
            </div>
            <p className="mt-4 max-w-2xl text-lg text-base-600">
              Pick what works for your stack. Default is local SQLite + deterministic embeddings for zero-config, offline operation.
            </p>
          </FadeIn>

          <FadeIn delay={100}>
            <div className="mt-10 grid gap-px bg-base-300 md:mt-12 md:grid-cols-3">
              {/* SQLite */}
              <div className="bg-background p-5 md:p-7">
                <div className="font-mono text-xs font-semibold text-accent-600">Default</div>
                <h3 className="mt-2 text-xl font-semibold text-base-950">SQLite</h3>
                <p className="mt-2 text-sm leading-relaxed text-base-600">
                  Local vector store with no dependencies. Ships with Seam. Zero setup.
                </p>
                <div className="mt-4 overflow-x-auto font-mono text-xs text-base-500">
                  seam config set backend sqlite
                </div>
              </div>

              {/* LanceDB */}
              <div className="bg-background p-5 md:p-7">
                <div className="font-mono text-xs font-semibold text-accent-600">Local</div>
                <h3 className="mt-2 text-xl font-semibold text-base-950">LanceDB</h3>
                <p className="mt-2 text-sm leading-relaxed text-base-600">
                  Disk-based vector DB for larger codebases. Efficient columnar storage.
                </p>
                <div className="mt-4 overflow-x-auto font-mono text-xs text-base-500">
                  seam config set backend lancedb
                </div>
              </div>

              {/* Qdrant */}
              <div className="bg-background p-5 md:p-7">
                <div className="font-mono text-xs font-semibold text-accent-600">Remote</div>
                <h3 className="mt-2 text-xl font-semibold text-base-950">Qdrant</h3>
                <p className="mt-2 text-sm leading-relaxed text-base-600">
                  Remote vector backend with metadata-only payloads. Source stays local.
                </p>
                <div className="mt-4 overflow-x-auto font-mono text-xs text-base-500">
                  seam config set backend qdrant
                </div>
              </div>
            </div>
          </FadeIn>

          <FadeIn delay={200}>
            <div className="mt-6 grid gap-px bg-base-300 md:mt-8 md:grid-cols-3">
              {/* Local embeddings */}
              <div className="bg-background p-5 md:p-7">
                <div className="font-mono text-xs font-semibold text-accent-600">Default</div>
                <h3 className="mt-2 text-xl font-semibold text-base-950">Local</h3>
                <p className="mt-2 text-sm leading-relaxed text-base-600">
                  Deterministic offline embeddings. No network, no API keys, no quotas.
                </p>
              </div>

              {/* OpenAI */}
              <div className="bg-background p-5 md:p-7">
                <div className="font-mono text-xs font-semibold text-accent-600">Cloud</div>
                <h3 className="mt-2 text-xl font-semibold text-base-950">OpenAI</h3>
                <p className="mt-2 text-sm leading-relaxed text-base-600">
                  OpenAI-compatible API. text-embedding-3-small or any compatible model.
                </p>
              </div>

              {/* Ollama */}
              <div className="bg-background p-5 md:p-7">
                <div className="font-mono text-xs font-semibold text-accent-600">Local AI</div>
                <h3 className="mt-2 text-xl font-semibold text-base-950">Ollama</h3>
                <p className="mt-2 text-sm leading-relaxed text-base-600">
                  Self-hosted embedding models. nomic-embed-text or any Ollama model.
                </p>
              </div>
            </div>
          </FadeIn>
        </div>
      </section>

      <Rule />

      {/* ═══════ INSTALL ═══════ */}
      <section id="install" className="bg-base-200/15 px-4 py-14 sm:px-6 md:px-8 md:py-20 lg:py-28">
        <div className="mx-auto max-w-6xl">
          <FadeIn>
            <div className="flex items-baseline gap-3">
              <span className="text-[10px] font-bold uppercase tracking-[0.15em] text-accent-600">
                04
              </span>
              <h2 className="text-[clamp(1.75rem,4.5vw,2.75rem)] font-semibold leading-[1.1] tracking-[-0.02em] text-base-950">
                Install
              </h2>
            </div>
            <p className="mt-4 max-w-2xl text-lg text-base-600">
              One command. Zero configuration. Works offline.
            </p>
          </FadeIn>

          <FadeIn delay={100}>
            <div className="mt-10 space-y-8 md:mt-12">
              {/* Quick install — full width */}
              <div>
                <div className="mb-2 text-sm font-semibold text-base-950">Quick install</div>
                <div className="flex items-center justify-between gap-3 overflow-x-auto rounded-lg border border-base-300 bg-base-100 px-3 py-1.5">
                  <code className="whitespace-nowrap font-mono text-[11px] text-base-950 sm:text-[13px]">
                    <span className="text-accent-600">$</span> {curlCmd}
                  </code>
                  <CopyButton text={curlCmd} />
                </div>
              </div>

              {/* uv / pipx */}
              <div className="grid gap-4 sm:grid-cols-2">
                <div>
                  <div className="mb-2 text-sm font-semibold text-base-950">uv</div>
                  <div className="overflow-x-auto rounded-lg border border-base-300 bg-base-100 px-4 py-3">
                    <code className="font-mono text-sm text-base-950">uv tool install seam-index</code>
                  </div>
                </div>
                <div>
                  <div className="mb-2 text-sm font-semibold text-base-950">pipx</div>
                  <div className="overflow-x-auto rounded-lg border border-base-300 bg-base-100 px-4 py-3">
                    <code className="font-mono text-sm text-base-950">pipx install seam-index</code>
                  </div>
                </div>
              </div>

              {/* Index and search */}
              <div>
                <div className="mb-2 text-sm font-semibold text-base-950">Index and search</div>
                <pre className="overflow-x-auto rounded-lg border border-base-300 bg-base-100 p-5">
                  <code className="font-mono text-sm text-base-950">
{`# Index your repo
$ seam init .

# Search instantly
$ seam search "JWT validation"

# Generate context for agents
$ seam context "database pooling"`}
                  </code>
                </pre>
              </div>
            </div>
          </FadeIn>
        </div>
      </section>

      <Rule />

      {/* ═══════ WHY SEAM ═══════ */}
      <section className="px-4 py-14 sm:px-6 md:px-8 md:py-20 lg:py-28">
        <div className="mx-auto max-w-6xl">
          <FadeIn>
            <div className="flex items-baseline gap-3">
              <span className="text-[10px] font-bold uppercase tracking-[0.15em] text-accent-600">
                05
              </span>
              <h2 className="text-[clamp(1.75rem,4.5vw,2.75rem)] font-semibold leading-[1.1] tracking-[-0.02em] text-base-950">
                Why Seam?
              </h2>
            </div>
          </FadeIn>

          <div className="mt-14 grid gap-10 lg:grid-cols-2">
            <FadeIn>
              <div className="border-l-2 border-base-300 pl-6">
                <div className="mb-5 text-[10px] font-bold uppercase tracking-[0.15em] text-base-500">
                  Without Seam
                </div>
                <ul className="space-y-3 text-base text-base-600">
                  {[
                    "Agent re-reads thousands of files on every task",
                    "Context window fills with irrelevant code",
                    "Slow responses, repeated questions",
                    "Cannot work offline or with rate limits",
                  ].map((item) => (
                    <li key={item} className="flex items-start gap-3">
                      <span className="mt-2 h-1 w-1 shrink-0 rounded-full bg-base-400" />
                      <span>{item}</span>
                    </li>
                  ))}
                </ul>
              </div>
            </FadeIn>

            <FadeIn delay={120}>
              <div className="border-l-2 border-accent-500 pl-6">
                <div className="mb-5 text-[10px] font-bold uppercase tracking-[0.15em] text-accent-600">
                  With Seam
                </div>
                <ul className="space-y-3 text-base text-base-950">
                  {[
                    "Semantic search finds relevant code instantly",
                    "Context stays focused and precise",
                    "Fast, accurate responses every time",
                    "Works completely offline, no API calls",
                  ].map((item) => (
                    <li key={item} className="flex items-start gap-3">
                      <span className="mt-2 h-1 w-1 shrink-0 rounded-full bg-accent-500" />
                      <span>{item}</span>
                    </li>
                  ))}
                </ul>
              </div>
            </FadeIn>
          </div>
        </div>
      </section>

      <Rule />

      {/* ═══════ CTA ═══════ */}
      <section className="bg-neutral-950 px-4 py-14 sm:px-6 md:px-8 md:py-20 lg:py-28">
        <div className="mx-auto max-w-6xl">
          <FadeIn>
            <h2 className="max-w-3xl text-[clamp(2.25rem,5.5vw,3.75rem)] font-bold leading-[1.05] tracking-[-0.03em] text-white">
              Stop feeding your agent the entire repo
            </h2>
            <p className="mt-6 max-w-xl text-lg leading-relaxed text-neutral-400">
              Index once. Query forever. Give your AI coding agent the context
              it actually needs, without the noise.
            </p>
            <div className="mt-10 flex flex-col gap-4 sm:flex-row">
              <a
                href="#install"
                className="inline-flex h-12 w-full items-center justify-center rounded bg-accent-500 px-6 text-base font-semibold text-neutral-950 transition-colors hover:bg-accent-400 sm:w-auto"
              >
                Get Started
              </a>
              <a
                href="https://github.com/Aditya190803/seam"
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex h-12 w-full items-center justify-center rounded border border-neutral-700 bg-transparent px-6 text-base font-medium text-neutral-300 transition-colors hover:bg-neutral-800 sm:w-auto"
              >
                View on GitHub
              </a>
            </div>
          </FadeIn>
        </div>
      </section>

      <Rule />

      {/* ═══════ FOOTER ═══════ */}
      <footer className="px-4 py-8 sm:px-6 md:px-8 md:py-10">
        <div className="mx-auto max-w-6xl">
          <div className="flex flex-col items-start justify-between gap-6 sm:flex-row sm:items-center">
            <div>
              <div className="text-lg font-bold tracking-tight text-base-950">
                Seam
              </div>
              <p className="mt-1 text-sm text-base-500">
                Local-first semantic code search
              </p>
            </div>
            <div className="flex gap-8 text-sm font-medium">
              <a
                href="https://github.com/Aditya190803/seam"
                target="_blank"
                rel="noopener noreferrer"
                className="text-base-600 transition-colors hover:text-base-950"
              >
                GitHub
              </a>
              <a
                href="https://github.com/Aditya190803/seam/blob/main/README.md"
                target="_blank"
                rel="noopener noreferrer"
                className="text-base-600 transition-colors hover:text-base-950"
              >
                Documentation
              </a>
              <a
                href="https://github.com/Aditya190803/seam/blob/main/LICENSE"
                target="_blank"
                rel="noopener noreferrer"
                className="text-base-600 transition-colors hover:text-base-950"
              >
                License
              </a>
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
}
