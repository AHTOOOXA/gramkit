'use client';

import { type ReactNode } from 'react';
import {
  ArrowRight,
  Code2,
  Palette,
  Zap,
  Database,
  Sparkles,
  Users,
  Radio,
  Smartphone,
  Terminal,
  Shield,
  Layers,
  FileCode2,
  Globe,
  Laptop,
  LayoutGrid,
  type LucideIcon,
} from 'lucide-react';
import { SiVuedotjs } from 'react-icons/si';

import { Link } from '@/i18n/navigation';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { useAuth, useScrollReveal } from '@/hooks';
import { ArchitectureDiagram } from '@/components/home/ArchitectureDiagram';
import { AnimatedTerminal } from '@/components/home/AnimatedTerminal';
import { cn } from '@/lib/utils';

// =============================================================================
// DESIGN SYSTEM - Consistent hover patterns
// =============================================================================

// Feature cards (above fold) - interactive, draw attention
const cardFeature = 'group relative overflow-hidden transition-all duration-300 ease-out hover:shadow-xl hover:shadow-primary/10 hover:-translate-y-1.5 hover:border-primary/30';

// Info cards (below fold) - subtle, for reading
const cardInfo = 'transition-all duration-300 hover:shadow-lg hover:shadow-primary/5 hover:border-primary/20';

// Buttons - consistent press/lift feedback
const btnPrimary = 'group active:scale-[0.98] hover:-translate-y-0.5 hover:shadow-lg hover:shadow-primary/25 transition-all duration-150';
const btnSecondary = 'active:scale-[0.98] hover:-translate-y-0.5 transition-all duration-150';

// =============================================================================

// Scroll reveal wrapper component
function ScrollReveal({
  children,
  className,
  delay = 0,
}: {
  children: ReactNode;
  className?: string;
  delay?: number;
}) {
  const { ref, isVisible } = useScrollReveal();

  return (
    <div
      ref={ref}
      className={cn(
        'transition-all duration-700 ease-out',
        isVisible
          ? 'opacity-100 translate-y-0 blur-0'
          : 'opacity-0 translate-y-8 blur-[2px]',
        className
      )}
      style={{ transitionDelay: isVisible ? `${String(delay)}ms` : '0ms' }}
    >
      {children}
    </div>
  );
}

export default function HomePage() {
  const { isAuthenticated } = useAuth();

  const featureItems: {
    name: string;
    description: string;
    icon: LucideIcon;
    highlighted?: boolean;
  }[] = [
    {
      name: 'Authentication',
      description: 'Email + OTP verification, Telegram OAuth, password reset flows',
      icon: Shield,
      highlighted: true,
    },
    {
      name: 'Role-Based Access',
      description: 'Admin/Owner/User roles, protected routes, permission checks',
      icon: Users,
    },
    {
      name: 'Real-Time Data',
      description: 'WebSocket, polling, AI streaming, optimistic updates',
      icon: Radio,
      highlighted: true,
    },
    {
      name: 'Mobile-First Design',
      description: 'Responsive layouts, bottom nav, Telegram Mini App detection',
      icon: Smartphone,
    },
    {
      name: 'Type-Safe API',
      description: 'Auto-generated TypeScript hooks from OpenAPI schema',
      icon: Code2,
      highlighted: true,
    },
    {
      name: 'i18n + Theming',
      description: 'Multi-language support, dark/light mode out of the box',
      icon: Palette,
    },
    {
      name: 'TanStack Query Patterns',
      description: '17 interactive demos: caching, mutations, infinite scroll, suspense',
      icon: Database,
    },
    {
      name: 'Developer Experience',
      description: 'Hot reload, Make commands, organized monorepo structure',
      icon: Terminal,
    },
  ];

  // Staggered delays for feature cards
  const featureDelays = [
    'motion-delay-[0.4s]',
    'motion-delay-[0.45s]',
    'motion-delay-[0.5s]',
    'motion-delay-[0.55s]',
    'motion-delay-[0.6s]',
    'motion-delay-[0.65s]',
    'motion-delay-[0.7s]',
    'motion-delay-[0.75s]',
  ];

  return (
    <div className="space-y-8 md:space-y-16">
      {/* Hero Section */}
      <section className="text-center space-y-6 py-6 md:py-12 motion-blur-in-[10px] motion-scale-in-[0.95] motion-opacity-in-[0%] motion-duration-[0.7s] motion-ease-spring-smooth">
        <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-primary/10 text-primary text-sm font-medium">
          <Sparkles className="w-4 h-4" />
          <span>Production-Ready Template</span>
        </div>

        <h1 className="text-4xl md:text-6xl font-bold tracking-tight">React Template</h1>

        <p className="text-xl md:text-2xl text-muted-foreground max-w-3xl mx-auto">
          Production-ready web app template with mobile-first design and Telegram Mini App support
        </p>

        <div className="flex flex-col sm:flex-row gap-4 justify-center pt-4">
          <Button asChild size="lg" className={btnPrimary}>
            <Link href={isAuthenticated ? '/demo' : '/login'}>
              {isAuthenticated ? 'Explore Patterns' : 'Get Started'}
              <ArrowRight className="w-4 h-4 ml-2 transition-transform duration-300 group-hover:translate-x-1" />
            </Link>
          </Button>
          <Button asChild variant="outline" size="lg" className={btnSecondary}>
            <a href="https://vue.antonchaynik.ru" target="_blank" rel="noopener noreferrer">
              <SiVuedotjs className="w-4 h-4 mr-2" />
              Try Vue Version
            </a>
          </Button>
        </div>
      </section>

      {/* Key Features Section - Above fold, interactive cards */}
      <section className="space-y-6 md:space-y-8 motion-opacity-in-[0%] motion-translate-y-in-[30px] motion-blur-in-[4px] motion-duration-[0.5s] motion-delay-[0.3s] motion-ease-spring-smooth">
        <div className="text-center">
          <h2 className="text-3xl md:text-4xl font-bold mb-3">What You Get</h2>
          <p className="text-muted-foreground text-lg">
            Battle-tested features, not boilerplate
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {featureItems.map((item, index) => (
            <Card
              key={item.name}
              className={cn(
                cardFeature,
                'py-4 gap-3', // Tighter spacing for feature cards
                'motion-opacity-in-[0%] motion-translate-y-in-[20px] motion-blur-in-[3px] motion-duration-[0.4s] motion-ease-spring-smooth',
                featureDelays[index],
                item.highlighted && 'border-primary/20 bg-gradient-to-br from-card to-primary/[0.02]'
              )}
            >
              {/* Hover gradient overlay */}
              <div className="absolute inset-0 bg-gradient-to-br from-primary/0 via-primary/[0.03] to-primary/0 opacity-0 group-hover:opacity-100 transition-opacity duration-300 pointer-events-none" />

              <CardHeader className="pb-0 relative">
                <div className="flex items-center gap-3 mb-1">
                  <div className={cn(
                    'p-2 rounded-lg transition-all duration-300',
                    item.highlighted
                      ? 'bg-primary/15 group-hover:bg-primary/25'
                      : 'bg-primary/10 group-hover:bg-primary/20'
                  )}>
                    <item.icon className="w-4 h-4 text-primary transition-transform duration-300 group-hover:scale-110" />
                  </div>
                </div>
                <CardTitle className="text-base">{item.name}</CardTitle>
              </CardHeader>
              <CardContent className="relative pt-0">
                <CardDescription className="text-sm">{item.description}</CardDescription>
              </CardContent>
            </Card>
          ))}
        </div>
      </section>

      {/* Architecture Overview Section - Info cards */}
      <ScrollReveal delay={0}>
        <section className="space-y-6 md:space-y-8">
          <div className="text-center">
            <h2 className="text-3xl md:text-4xl font-bold mb-3">Modern Stack, Clean Architecture</h2>
            <p className="text-muted-foreground text-lg">End-to-end type safety from database to UI</p>
          </div>

          <div className="max-w-4xl mx-auto space-y-4 md:space-y-6">
            <Card className={cardInfo}>
              <CardHeader>
                <CardTitle className="text-xl">Monorepo Structure</CardTitle>
              </CardHeader>
              <CardContent>
                <ArchitectureDiagram />
              </CardContent>
            </Card>

            <Card className={cardInfo}>
              <CardHeader>
                <CardTitle className="text-xl">Technical Highlights</CardTitle>
                <CardDescription>
                  Not just a stack — solutions to real problems
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="grid md:grid-cols-2 gap-4">
                  <div className="space-y-3">
                    <div className="flex items-start gap-3">
                      <div className="p-1.5 rounded bg-primary/10 mt-0.5">
                        <FileCode2 className="w-3.5 h-3.5 text-primary" />
                      </div>
                      <div>
                        <p className="text-sm font-medium">End-to-End Type Safety</p>
                        <p className="text-xs text-muted-foreground">
                          OpenAPI schema → Kubb generates TypeScript hooks. Change backend, frontend types update automatically.
                        </p>
                      </div>
                    </div>
                    <div className="flex items-start gap-3">
                      <div className="p-1.5 rounded bg-primary/10 mt-0.5">
                        <Terminal className="w-3.5 h-3.5 text-primary" />
                      </div>
                      <div>
                        <p className="text-sm font-medium">Unified Make Commands</p>
                        <p className="text-xs text-muted-foreground">
                          One interface for all apps:{' '}
                          <code className="bg-muted px-1 rounded">make test APP=x</code>,{' '}
                          <code className="bg-muted px-1 rounded">make migration</code>. No Docker/pytest directly.
                        </p>
                      </div>
                    </div>
                    <div className="flex items-start gap-3">
                      <div className="p-1.5 rounded bg-primary/10 mt-0.5">
                        <Layers className="w-3.5 h-3.5 text-primary" />
                      </div>
                      <div>
                        <p className="text-sm font-medium">Shared Core Logic</p>
                        <p className="text-xs text-muted-foreground">
                          Auth, users, payments, email in core/ — import into any app. No copy-paste between projects.
                        </p>
                      </div>
                    </div>
                  </div>
                  <div className="space-y-3">
                    <div className="flex items-start gap-3">
                      <div className="p-1.5 rounded bg-primary/10 mt-0.5">
                        <Zap className="w-3.5 h-3.5 text-primary" />
                      </div>
                      <div>
                        <p className="text-sm font-medium">Hot Reload Everywhere</p>
                        <p className="text-xs text-muted-foreground">
                          Edit Python or TypeScript, see changes instantly. No container restarts, no manual rebuilds.
                        </p>
                      </div>
                    </div>
                    <div className="flex items-start gap-3">
                      <div className="p-1.5 rounded bg-primary/10 mt-0.5">
                        <Database className="w-3.5 h-3.5 text-primary" />
                      </div>
                      <div>
                        <p className="text-sm font-medium">Repository Pattern + Flush</p>
                        <p className="text-xs text-muted-foreground">
                          Clean data access layer. Repositories use flush(), services control transactions. Testable, predictable.
                        </p>
                      </div>
                    </div>
                    <div className="flex items-start gap-3">
                      <div className="p-1.5 rounded bg-primary/10 mt-0.5">
                        <Radio className="w-3.5 h-3.5 text-primary" />
                      </div>
                      <div>
                        <p className="text-sm font-medium">TanStack Query Patterns</p>
                        <p className="text-xs text-muted-foreground">
                          17 demos showing caching, optimistic updates, infinite scroll, real-time — copy patterns directly.
                        </p>
                      </div>
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>
        </section>
      </ScrollReveal>

      {/* Development Workflow Section */}
      <ScrollReveal delay={100}>
        <section className="space-y-6 md:space-y-8">
          <div className="text-center">
            <h2 className="text-3xl md:text-4xl font-bold mb-3">Two Ways to Develop</h2>
            <p className="text-muted-foreground text-lg">
              Localhost for speed, tunnel for Telegram testing
            </p>
          </div>

          <div className="max-w-5xl mx-auto space-y-4 md:space-y-6">
            <div className="grid md:grid-cols-2 gap-4 md:gap-6">
              <Card className={cn(cardInfo, 'border-primary/20 bg-gradient-to-br from-card to-primary/[0.02]')}>
                <CardHeader className="pb-3">
                  <div className="flex items-center gap-3 mb-2">
                    <div className="p-2 rounded-lg bg-primary/15">
                      <Laptop className="w-4 h-4 text-primary" />
                    </div>
                    <CardTitle className="text-lg">Direct Localhost</CardTitle>
                    <span className="text-xs bg-primary/10 text-primary px-2 py-0.5 rounded-full">Recommended</span>
                  </div>
                  <CardDescription>
                    Native Turbopack — fastest iteration, no Docker overhead
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-3">
                  <div className="bg-muted p-3 rounded font-mono text-xs">
                    <div className="text-foreground">http://localhost:3001/template-react</div>
                  </div>
                  <ul className="space-y-1.5 text-sm text-muted-foreground">
                    <li className="flex items-center gap-2">
                      <span className="text-primary">✓</span> ~10x faster warm starts with Turbopack cache
                    </li>
                    <li className="flex items-center gap-2">
                      <span className="text-primary">✓</span> Direct API calls (CORS enabled in dev)
                    </li>
                    <li className="flex items-center gap-2">
                      <span className="text-primary">✓</span> Frontend runs natively on macOS
                    </li>
                  </ul>
                </CardContent>
              </Card>

              <Card className={cardInfo}>
                <CardHeader className="pb-3">
                  <div className="flex items-center gap-3 mb-2">
                    <div className="p-2 rounded-lg bg-primary/10">
                      <Globe className="w-4 h-4 text-primary" />
                    </div>
                    <CardTitle className="text-lg">Tunnel Mode</CardTitle>
                  </div>
                  <CardDescription>
                    Via nginx + Cloudflare tunnel — for Telegram Mini App testing
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-3">
                  <div className="bg-muted p-3 rounded font-mono text-xs">
                    <div className="text-muted-foreground">https://local.yourdomain.com/template-react</div>
                  </div>
                  <ul className="space-y-1.5 text-sm text-muted-foreground">
                    <li className="flex items-center gap-2">
                      <span className="text-primary">✓</span> HTTPS with valid certificate
                    </li>
                    <li className="flex items-center gap-2">
                      <span className="text-primary">✓</span> Telegram WebApp authentication
                    </li>
                    <li className="flex items-center gap-2">
                      <span className="text-primary">✓</span> Production-like environment
                    </li>
                  </ul>
                </CardContent>
              </Card>
            </div>

            <Card className={cardInfo}>
              <CardHeader className="pb-3">
                <div className="flex items-center gap-3 mb-2">
                  <div className="p-2 rounded-lg bg-primary/10">
                    <LayoutGrid className="w-4 h-4 text-primary" />
                  </div>
                  <CardTitle className="text-lg">Gateway Hub</CardTitle>
                </div>
                <CardDescription>
                  nginx landing page with quick access to all apps
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="grid md:grid-cols-3 gap-3 text-xs">
                  <div className="bg-muted p-3 rounded">
                    <code className="text-blue-400">template-react</code>
                    <div className="mt-1.5 space-y-1 text-muted-foreground">
                      <div>tunnel • :3001 • api</div>
                    </div>
                  </div>
                  <div className="bg-muted p-3 rounded">
                    <code className="text-green-400">template-vue</code>
                    <div className="mt-1.5 space-y-1 text-muted-foreground">
                      <div>tunnel • :5174 • api</div>
                    </div>
                  </div>
                  <div className="bg-muted p-3 rounded">
                    <code className="text-primary">your-app</code>
                    <div className="mt-1.5 space-y-1 text-muted-foreground">
                      <div>tunnel • :1234 • api</div>
                    </div>
                  </div>
                </div>
                <p className="text-xs text-muted-foreground mt-3">
                  Access at{' '}
                  <code className="bg-muted px-1.5 py-0.5 rounded">https://local.yourdomain.com/</code>
                  {' '}— one hub for tunnel links, localhost ports, and API docs
                </p>
              </CardContent>
            </Card>

            <Card className={cn(cardInfo, 'border-primary/20 bg-gradient-to-br from-card to-primary/[0.02]')}>
              <CardHeader className="pb-3">
                <div className="flex items-center gap-3 mb-2">
                  <div className="p-2 rounded-lg bg-primary/15">
                    <Zap className="w-4 h-4 text-primary" />
                  </div>
                  <CardTitle className="text-lg">Next.js 16.1 + Turbopack</CardTitle>
                </div>
              </CardHeader>
              <CardContent>
                <div className="grid md:grid-cols-3 gap-4 text-sm">
                  <div>
                    <p className="font-medium">Persistent Cache</p>
                    <p className="text-xs text-muted-foreground">
                      Turbopack cache survives restarts — cold start becomes warm start
                    </p>
                  </div>
                  <div>
                    <p className="font-medium">Native Performance</p>
                    <p className="text-xs text-muted-foreground">
                      Frontends run locally on macOS, not in Docker containers
                    </p>
                  </div>
                  <div>
                    <p className="font-medium">React 19 Ready</p>
                    <p className="text-xs text-muted-foreground">
                      Server Components, Actions, and latest React features
                    </p>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>
        </section>
      </ScrollReveal>

      {/* What's Included Section - Info cards */}
      <ScrollReveal delay={200}>
        <section className="space-y-6 md:space-y-8">
          <div className="text-center">
            <h2 className="text-3xl md:text-4xl font-bold mb-3">Everything Wired Up</h2>
            <p className="text-muted-foreground text-lg">
              Not just scaffolding — real, working features
            </p>
          </div>

          <div className="grid md:grid-cols-3 gap-4 md:gap-6 max-w-5xl mx-auto">
            <Card className={cardInfo}>
              <CardHeader>
                <CardTitle className="text-lg">5 Pages</CardTitle>
                <CardDescription>Production-ready routes</CardDescription>
              </CardHeader>
              <CardContent>
                <ul className="space-y-2 text-sm text-muted-foreground">
                  <li>• Home marketing page</li>
                  <li>• Tech demos (17 patterns)</li>
                  <li>• Profile management</li>
                  <li>• Admin dashboard</li>
                  <li>• Extensible structure</li>
                </ul>
              </CardContent>
            </Card>

            <Card className={cardInfo}>
              <CardHeader>
                <CardTitle className="text-lg">17 Tech Demos</CardTitle>
                <CardDescription>Reference implementations</CardDescription>
              </CardHeader>
              <CardContent>
                <ul className="space-y-2 text-sm text-muted-foreground">
                  <li>• Loading & error states</li>
                  <li>• Caching strategies</li>
                  <li>• Mutations & optimistic UI</li>
                  <li>• Streaming & real-time</li>
                  <li>• Infinite scroll & more</li>
                </ul>
              </CardContent>
            </Card>

            <Card className={cardInfo}>
              <CardHeader>
                <CardTitle className="text-lg">Full Auth System</CardTitle>
                <CardDescription>Complete authentication flows</CardDescription>
              </CardHeader>
              <CardContent>
                <ul className="space-y-2 text-sm text-muted-foreground">
                  <li>• Email + OTP verification</li>
                  <li>• Telegram OAuth</li>
                  <li>• Password reset flow</li>
                  <li>• Account linking</li>
                  <li>• Session management</li>
                </ul>
              </CardContent>
            </Card>
          </div>
        </section>
      </ScrollReveal>

      {/* Claude Code & Agents Section - Info cards */}
      <ScrollReveal delay={300}>
        <section className="space-y-6 md:space-y-8">
          <div className="text-center">
            <h2 className="text-3xl md:text-4xl font-bold mb-3">
              Built for Claude Code
            </h2>
            <p className="text-muted-foreground text-lg">
              4-layer orchestration architecture — context-efficient, parallel-ready
            </p>
          </div>

          <div className="max-w-5xl mx-auto space-y-4 md:space-y-6">
            {/* Architecture Overview */}
            <Card className={cardInfo}>
              <CardHeader>
                <CardTitle className="text-xl">Orchestration-First Architecture</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="bg-muted p-4 rounded-lg font-mono text-xs overflow-x-auto">
                  <div className="text-muted-foreground">
                    <span className="text-primary">Layer 0:</span> CLAUDE.md → orchestration rules, quick reference
                  </div>
                  <div className="text-muted-foreground ml-4">
                    ├── <span className="text-primary">Layer 1:</span> commands/ → /develop, /create-task, /execute-task, /review
                  </div>
                  <div className="text-muted-foreground ml-4">
                    ├── <span className="text-primary">Layer 2:</span> skills/ → auto-invoked procedures (task creation, execution)
                  </div>
                  <div className="text-muted-foreground ml-4">
                    └── <span className="text-primary">Layer 3:</span> agents/ → developer-agent, testing-polish-agent
                  </div>
                </div>
              </CardContent>
            </Card>

            <div className="grid md:grid-cols-2 gap-4 md:gap-6">
              <Card className={cardInfo}>
                <CardHeader className="pb-3">
                  <CardTitle className="text-base">Slash Commands</CardTitle>
                </CardHeader>
                <CardContent className="space-y-2">
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-2 text-xs">
                    <div>
                      <code className="text-primary">/create-task</code>
                      <p className="text-muted-foreground">PRD → phases → parallel enrichment</p>
                    </div>
                    <div>
                      <code className="text-primary">/execute-task</code>
                      <p className="text-muted-foreground">Phase-by-phase with auto-commits</p>
                    </div>
                    <div>
                      <code className="text-primary">/develop</code>
                      <p className="text-muted-foreground">Quick delegation to developer-agent</p>
                    </div>
                    <div>
                      <code className="text-primary">/design</code>
                      <p className="text-muted-foreground">Research approaches, compare options</p>
                    </div>
                    <div>
                      <code className="text-primary">/review</code>
                      <p className="text-muted-foreground">Deep code review with questions</p>
                    </div>
                    <div>
                      <code className="text-primary">/add-testing</code>
                      <p className="text-muted-foreground">Add test phases to existing task</p>
                    </div>
                  </div>
                </CardContent>
              </Card>

              <Card className={cardInfo}>
                <CardHeader className="pb-3">
                  <CardTitle className="text-base">Structured Task System</CardTitle>
                </CardHeader>
                <CardContent className="space-y-3">
                  <p className="text-xs text-muted-foreground">
                    Auto-detects difficulty. Simple tasks: inline enrichment. Hard tasks: hub-and-spoke
                    parallel agents with shared ARCHITECTURE.md to prevent conflicts.
                  </p>
                  <div className="bg-muted p-3 rounded text-xs font-mono">
                    <div className="text-muted-foreground">docs/tasks/user-settings/</div>
                    <div className="text-muted-foreground ml-2">├── README.md <span className="text-primary"># PRD</span></div>
                    <div className="text-muted-foreground ml-2">├── ARCHITECTURE.md <span className="text-primary"># Contracts</span></div>
                    <div className="text-muted-foreground ml-2">├── CONTEXT.md <span className="text-primary"># State</span></div>
                    <div className="text-muted-foreground ml-2">├── 01-models.md <span className="text-primary"># file:line refs</span></div>
                    <div className="text-muted-foreground ml-2">└── 02-api.md</div>
                  </div>
                </CardContent>
              </Card>

              <Card className={cardInfo}>
                <CardHeader className="pb-3">
                  <CardTitle className="text-base">Developer Agent</CardTitle>
                </CardHeader>
                <CardContent className="space-y-2 text-xs text-muted-foreground">
                  <p>Reads pattern docs before every task. Returns summaries, not code dumps.</p>
                  <ul className="space-y-1">
                    <li>
                      • <span className="text-foreground">Mandatory reads:</span> critical-rules.md + domain-specific doc
                    </li>
                    <li>
                      • <span className="text-foreground">After changes:</span> make test, make lint, make schema
                    </li>
                    <li>
                      • <span className="text-foreground">Commits:</span> follows conventional format per phase
                    </li>
                  </ul>
                </CardContent>
              </Card>

              <Card className={cardInfo}>
                <CardHeader className="pb-3">
                  <CardTitle className="text-base">10 Pattern Docs in .claude/shared/</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="flex flex-wrap gap-1.5">
                    <code className="bg-muted px-1.5 py-0.5 rounded text-xs">backend-patterns.md</code>
                    <code className="bg-muted px-1.5 py-0.5 rounded text-xs">react-frontend.md</code>
                    <code className="bg-muted px-1.5 py-0.5 rounded text-xs">vue-frontend.md</code>
                    <code className="bg-muted px-1.5 py-0.5 rounded text-xs">testing-patterns.md</code>
                    <code className="bg-muted px-1.5 py-0.5 rounded text-xs">monorepo-structure.md</code>
                    <code className="bg-muted px-1.5 py-0.5 rounded text-xs">error-handling.md</code>
                    <code className="bg-muted px-1.5 py-0.5 rounded text-xs">critical-rules.md</code>
                    <code className="bg-muted px-1.5 py-0.5 rounded text-xs">playwright-testing.md</code>
                    <code className="bg-muted px-1.5 py-0.5 rounded text-xs">react-animations.md</code>
                    <code className="bg-muted px-1.5 py-0.5 rounded text-xs">adding-packages.md</code>
                  </div>
                </CardContent>
              </Card>
            </div>

            {/* Workflow Example */}
            <Card className={cardInfo}>
              <CardHeader className="pb-3">
                <CardTitle className="text-base">Example: Adding a Feature</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="grid md:grid-cols-4 gap-3 text-xs">
                  <div className="bg-muted p-3 rounded">
                    <code className="text-primary">/create-task</code>
                    <p className="text-muted-foreground mt-1">
                      "add user notifications"
                    </p>
                    <p className="text-muted-foreground mt-1">
                      → Creates PRD, detects HARD, launches parallel enrichment agents
                    </p>
                  </div>
                  <div className="bg-muted p-3 rounded">
                    <code className="text-primary">/execute-task</code>
                    <p className="text-muted-foreground mt-1">
                      Delegates each phase to developer-agent
                    </p>
                    <p className="text-muted-foreground mt-1">
                      → Reads CONTEXT.md, resumes if interrupted
                    </p>
                  </div>
                  <div className="bg-muted p-3 rounded">
                    <code className="text-primary">developer-agent</code>
                    <p className="text-muted-foreground mt-1">
                      Reads backend-patterns.md, implements, runs tests
                    </p>
                    <p className="text-muted-foreground mt-1">
                      → Returns summary with file:line refs
                    </p>
                  </div>
                  <div className="bg-muted p-3 rounded">
                    <code className="text-primary">/review</code>
                    <p className="text-muted-foreground mt-1">
                      Deep architectural review
                    </p>
                    <p className="text-muted-foreground mt-1">
                      → Questions design decisions, not just style
                    </p>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>
        </section>
      </ScrollReveal>

      {/* Quick Start Section - Info cards */}
      <ScrollReveal delay={400}>
        <section className="space-y-6 md:space-y-8">
          <div className="text-center">
            <h2 className="text-3xl md:text-4xl font-bold mb-3">Get Started</h2>
            <p className="text-muted-foreground text-lg">
              Prerequisites: Docker, pnpm, make
            </p>
          </div>

          <div className="max-w-4xl mx-auto space-y-4 md:space-y-6">
            {/* Animated Terminal - Hero Visual */}
            <AnimatedTerminal />

            <div className="grid md:grid-cols-2 gap-4 md:gap-6">
              <Card className={cardInfo}>
                <CardHeader>
                  <CardTitle className="text-lg">Run the Template</CardTitle>
                  <CardDescription>Start development in 3 steps</CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="space-y-3">
                    <div className="flex gap-3">
                      <span className="flex-shrink-0 w-6 h-6 rounded-full bg-muted text-muted-foreground text-xs flex items-center justify-center font-medium">
                        0
                      </span>
                      <div className="flex-1">
                        <p className="text-sm font-medium">Setup Cloudflare Tunnel</p>
                        <p className="text-xs text-muted-foreground">
                          Required for Telegram Mini App testing — exposes localhost via HTTPS
                        </p>
                      </div>
                    </div>
                    <div className="flex gap-3">
                      <span className="flex-shrink-0 w-6 h-6 rounded-full bg-primary/10 text-primary text-xs flex items-center justify-center font-medium">
                        1
                      </span>
                      <div className="flex-1">
                        <p className="text-sm font-medium">Clone & install</p>
                        <code className="text-xs text-muted-foreground">pnpm install</code>
                      </div>
                    </div>
                    <div className="flex gap-3">
                      <span className="flex-shrink-0 w-6 h-6 rounded-full bg-primary/10 text-primary text-xs flex items-center justify-center font-medium">
                        2
                      </span>
                      <div className="flex-1">
                        <p className="text-sm font-medium">Configure environment</p>
                        <code className="text-xs text-muted-foreground">
                          cp .env.example .env
                        </code>
                      </div>
                    </div>
                    <div className="flex gap-3">
                      <span className="flex-shrink-0 w-6 h-6 rounded-full bg-primary/10 text-primary text-xs flex items-center justify-center font-medium">
                        3
                      </span>
                      <div className="flex-1">
                        <p className="text-sm font-medium">Start everything</p>
                        <code className="text-xs text-muted-foreground">
                          make up APP=template-react
                        </code>
                      </div>
                    </div>
                  </div>
                  <div className="pt-2 border-t">
                    <p className="text-xs text-muted-foreground">
                      Open{' '}
                      <code className="bg-muted px-1.5 py-0.5 rounded">
                        http://localhost:3001/template-react
                      </code>
                    </p>
                  </div>
                </CardContent>
              </Card>

              <Card className={cardInfo}>
                <CardHeader>
                  <CardTitle className="text-lg">Create Your Own App</CardTitle>
                  <CardDescription>Use template as foundation</CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="space-y-3">
                    <div className="flex gap-3">
                      <span className="flex-shrink-0 w-6 h-6 rounded-full bg-primary/10 text-primary text-xs flex items-center justify-center font-medium">
                        1
                      </span>
                      <div className="flex-1">
                        <p className="text-sm font-medium">Copy template</p>
                        <code className="text-xs text-muted-foreground">
                          cp -r apps/template-react apps/your-app
                        </code>
                      </div>
                    </div>
                    <div className="flex gap-3">
                      <span className="flex-shrink-0 w-6 h-6 rounded-full bg-primary/10 text-primary text-xs flex items-center justify-center font-medium">
                        2
                      </span>
                      <div className="flex-1">
                        <p className="text-sm font-medium">Update configs</p>
                        <code className="text-xs text-muted-foreground">
                          package.json, docker-compose, .env
                        </code>
                      </div>
                    </div>
                    <div className="flex gap-3">
                      <span className="flex-shrink-0 w-6 h-6 rounded-full bg-primary/10 text-primary text-xs flex items-center justify-center font-medium">
                        3
                      </span>
                      <div className="flex-1">
                        <p className="text-sm font-medium">Create database</p>
                        <code className="text-xs text-muted-foreground">
                          make upgrade APP=your-app
                        </code>
                      </div>
                    </div>
                    <div className="flex gap-3">
                      <span className="flex-shrink-0 w-6 h-6 rounded-full bg-primary/10 text-primary text-xs flex items-center justify-center font-medium">
                        4
                      </span>
                      <div className="flex-1">
                        <p className="text-sm font-medium">Start building</p>
                        <code className="text-xs text-muted-foreground">
                          Remove demo code, add your features
                        </code>
                      </div>
                    </div>
                  </div>
                  <div className="pt-2 border-t">
                    <p className="text-xs text-muted-foreground">
                      See{' '}
                      <code className="bg-muted px-1.5 py-0.5 rounded">
                        .claude/shared/monorepo-structure.md
                      </code>{' '}
                      for details
                    </p>
                  </div>
                </CardContent>
              </Card>
            </div>
          </div>
        </section>
      </ScrollReveal>

      {/* Footer CTA */}
      <ScrollReveal delay={500}>
        <section>
          <div className="group relative overflow-hidden bg-muted/50 rounded-xl p-8 text-center transition-all duration-300 hover:bg-muted/70 hover:shadow-xl hover:shadow-primary/15">
            <div className="absolute inset-0 rounded-xl bg-gradient-to-r from-primary/0 via-primary/10 to-primary/0 opacity-0 group-hover:opacity-100 transition-opacity duration-500" />

            <div className="relative space-y-4">
              <h3 className="text-2xl font-bold">Ready to Explore?</h3>
              <div className="flex flex-col sm:flex-row gap-3 justify-center pt-2">
                <Button asChild size="lg" className={btnPrimary}>
                  <Link href="/demo">
                    <span className="hidden sm:inline">Try live demos: caching, WebSocket, AI streaming</span>
                    <span className="sm:hidden">Try Live Demos</span>
                    <ArrowRight className="w-4 h-4 ml-2 transition-transform duration-300 group-hover:translate-x-1" />
                  </Link>
                </Button>
                <Button asChild variant="outline" size="lg" className={btnSecondary}>
                  <Link href="/profile">
                    <span className="hidden sm:inline">Test auth flows & friend invites</span>
                    <span className="sm:hidden">Test Auth Flows</span>
                  </Link>
                </Button>
              </div>
            </div>
          </div>
        </section>
      </ScrollReveal>

      {/* Footer Credits */}
      <footer className="text-center py-6 text-sm text-muted-foreground">
        React Template •{' '}
        <a
          href="https://vue.antonchaynik.ru"
          target="_blank"
          rel="noopener noreferrer"
          className="text-primary hover:underline"
        >
          Vue version also available
        </a>
      </footer>
    </div>
  );
}
