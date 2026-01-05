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
  FlaskConical,
  type LucideIcon,
} from 'lucide-react';
import { SiVuedotjs } from 'react-icons/si';
import { useTranslations } from 'next-intl';

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
  const t = useTranslations('homePage');

  const featureItems: {
    key: string;
    icon: LucideIcon;
    highlighted?: boolean;
  }[] = [
    { key: 'authentication', icon: Shield, highlighted: true },
    { key: 'rbac', icon: Users },
    { key: 'realtime', icon: Radio, highlighted: true },
    { key: 'mobile', icon: Smartphone },
    { key: 'typeSafe', icon: Code2, highlighted: true },
    { key: 'i18n', icon: Palette },
    { key: 'tanstack', icon: Database },
    { key: 'dx', icon: Terminal },
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
          <span>{t('badge')}</span>
        </div>

        <h1 className="text-4xl md:text-6xl font-bold tracking-tight">{t('title')}</h1>

        <p className="text-xl md:text-2xl text-muted-foreground max-w-3xl mx-auto">
          {t('heroSubtitle')}
        </p>

        <div className="flex flex-col sm:flex-row gap-4 justify-center pt-4">
          <Button asChild size="lg" className={btnPrimary}>
            <Link href={isAuthenticated ? '/demo' : '/login'}>
              {isAuthenticated ? t('explorePatterns') : t('getStarted')}
              <ArrowRight className="w-4 h-4 ml-2 transition-transform duration-300 group-hover:translate-x-1" />
            </Link>
          </Button>
          <Button asChild variant="outline" size="lg" className={btnSecondary}>
            <a href="https://vue.antonchaynik.ru" target="_blank" rel="noopener noreferrer">
              <SiVuedotjs className="w-4 h-4 mr-2" />
              {t('tryVueVersion')}
            </a>
          </Button>
        </div>
      </section>

      {/* Key Features Section - Above fold, interactive cards */}
      <section className="space-y-6 md:space-y-8 motion-opacity-in-[0%] motion-translate-y-in-[30px] motion-blur-in-[4px] motion-duration-[0.5s] motion-delay-[0.3s] motion-ease-spring-smooth">
        <div className="text-center">
          <h2 className="text-3xl md:text-4xl font-bold mb-3">{t('features.title')}</h2>
          <p className="text-muted-foreground text-lg">
            {t('features.subtitle')}
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {featureItems.map((item, index) => (
            <Card
              key={item.key}
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
                <CardTitle className="text-base">{t(`features.items.${item.key}.name`)}</CardTitle>
              </CardHeader>
              <CardContent className="relative pt-0">
                <CardDescription className="text-sm">{t(`features.items.${item.key}.description`)}</CardDescription>
              </CardContent>
            </Card>
          ))}
        </div>
      </section>

      {/* Architecture Overview Section - Info cards */}
      <ScrollReveal delay={0}>
        <section className="space-y-6 md:space-y-8">
          <div className="text-center">
            <h2 className="text-3xl md:text-4xl font-bold mb-3">{t('architecture.title')}</h2>
            <p className="text-muted-foreground text-lg">{t('architecture.subtitle')}</p>
          </div>

          <div className="max-w-4xl mx-auto space-y-4 md:space-y-6">
            <Card className={cardInfo}>
              <CardHeader>
                <CardTitle className="text-xl">{t('architecture.monorepoTitle')}</CardTitle>
              </CardHeader>
              <CardContent>
                <ArchitectureDiagram />
              </CardContent>
            </Card>

            <Card className={cardInfo}>
              <CardHeader>
                <CardTitle className="text-xl">{t('architecture.highlightsTitle')}</CardTitle>
                <CardDescription>
                  {t('architecture.highlightsSubtitle')}
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
                        <p className="text-sm font-medium">{t('architecture.highlights.endToEnd.title')}</p>
                        <p className="text-xs text-muted-foreground">
                          {t('architecture.highlights.endToEnd.description')}
                        </p>
                      </div>
                    </div>
                    <div className="flex items-start gap-3">
                      <div className="p-1.5 rounded bg-primary/10 mt-0.5">
                        <Terminal className="w-3.5 h-3.5 text-primary" />
                      </div>
                      <div>
                        <p className="text-sm font-medium">{t('architecture.highlights.make.title')}</p>
                        <p className="text-xs text-muted-foreground">
                          {t('architecture.highlights.make.description')}
                        </p>
                      </div>
                    </div>
                    <div className="flex items-start gap-3">
                      <div className="p-1.5 rounded bg-primary/10 mt-0.5">
                        <Layers className="w-3.5 h-3.5 text-primary" />
                      </div>
                      <div>
                        <p className="text-sm font-medium">{t('architecture.highlights.shared.title')}</p>
                        <p className="text-xs text-muted-foreground">
                          {t('architecture.highlights.shared.description')}
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
                        <p className="text-sm font-medium">{t('architecture.highlights.hotReload.title')}</p>
                        <p className="text-xs text-muted-foreground">
                          {t('architecture.highlights.hotReload.description')}
                        </p>
                      </div>
                    </div>
                    <div className="flex items-start gap-3">
                      <div className="p-1.5 rounded bg-primary/10 mt-0.5">
                        <Database className="w-3.5 h-3.5 text-primary" />
                      </div>
                      <div>
                        <p className="text-sm font-medium">{t('architecture.highlights.repo.title')}</p>
                        <p className="text-xs text-muted-foreground">
                          {t('architecture.highlights.repo.description')}
                        </p>
                      </div>
                    </div>
                    <div className="flex items-start gap-3">
                      <div className="p-1.5 rounded bg-primary/10 mt-0.5">
                        <Radio className="w-3.5 h-3.5 text-primary" />
                      </div>
                      <div>
                        <p className="text-sm font-medium">{t('architecture.highlights.tanstackPatterns.title')}</p>
                        <p className="text-xs text-muted-foreground">
                          {t('architecture.highlights.tanstackPatterns.description')}
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
            <h2 className="text-3xl md:text-4xl font-bold mb-3">{t('workflow.title')}</h2>
            <p className="text-muted-foreground text-lg">
              {t('workflow.subtitle')}
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
                    <CardTitle className="text-lg">{t('workflow.localhost.title')}</CardTitle>
                    <span className="text-xs bg-primary/10 text-primary px-2 py-0.5 rounded-full">{t('workflow.localhost.recommended')}</span>
                  </div>
                  <CardDescription>
                    {t('workflow.localhost.subtitle')}
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-3">
                  <div className="bg-muted p-3 rounded font-mono text-xs">
                    <div className="text-foreground">{t('workflow.localhost.url')}</div>
                  </div>
                  <ul className="space-y-1.5 text-sm text-muted-foreground">
                    {(t.raw('workflow.localhost.benefits') as string[]).map((benefit, idx) => (
                      <li key={idx} className="flex items-center gap-2">
                        <span className="text-primary">✓</span> {benefit}
                      </li>
                    ))}
                  </ul>
                </CardContent>
              </Card>

              <Card className={cardInfo}>
                <CardHeader className="pb-3">
                  <div className="flex items-center gap-3 mb-2">
                    <div className="p-2 rounded-lg bg-primary/10">
                      <Globe className="w-4 h-4 text-primary" />
                    </div>
                    <CardTitle className="text-lg">{t('workflow.tunnel.title')}</CardTitle>
                  </div>
                  <CardDescription>
                    {t('workflow.tunnel.subtitle')}
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-3">
                  <div className="bg-muted p-3 rounded font-mono text-xs">
                    <div className="text-muted-foreground">{t('workflow.tunnel.url')}</div>
                  </div>
                  <ul className="space-y-1.5 text-sm text-muted-foreground">
                    {(t.raw('workflow.tunnel.benefits') as string[]).map((benefit, idx) => (
                      <li key={idx} className="flex items-center gap-2">
                        <span className="text-primary">✓</span> {benefit}
                      </li>
                    ))}
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
                  <CardTitle className="text-lg">{t('workflow.gateway.title')}</CardTitle>
                </div>
                <CardDescription>
                  {t('workflow.gateway.subtitle')}
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="grid md:grid-cols-3 gap-3 text-xs">
                  <div className="bg-muted p-3 rounded">
                    <code className="text-blue-400">{t('workflow.gateway.apps.react')}</code>
                    <div className="mt-1.5 space-y-1 text-muted-foreground">
                      <div>{t('workflow.gateway.appDetails')}</div>
                    </div>
                  </div>
                  <div className="bg-muted p-3 rounded">
                    <code className="text-green-400">{t('workflow.gateway.apps.vue')}</code>
                    <div className="mt-1.5 space-y-1 text-muted-foreground">
                      <div>{t('workflow.gateway.vueDetails')}</div>
                    </div>
                  </div>
                  <div className="bg-muted p-3 rounded">
                    <code className="text-primary">{t('workflow.gateway.apps.yourApp')}</code>
                    <div className="mt-1.5 space-y-1 text-muted-foreground">
                      <div>{t('workflow.gateway.yourAppDetails')}</div>
                    </div>
                  </div>
                </div>
                <p className="text-xs text-muted-foreground mt-3">
                  {t('workflow.gateway.description')}
                </p>
              </CardContent>
            </Card>

            <Card className={cn(cardInfo, 'border-primary/20 bg-gradient-to-br from-card to-primary/[0.02]')}>
              <CardHeader className="pb-3">
                <div className="flex items-center gap-3 mb-2">
                  <div className="p-2 rounded-lg bg-primary/15">
                    <Zap className="w-4 h-4 text-primary" />
                  </div>
                  <CardTitle className="text-lg">{t('workflow.turbopack.title')}</CardTitle>
                </div>
              </CardHeader>
              <CardContent>
                <div className="grid md:grid-cols-3 gap-4 text-sm">
                  {(t.raw('workflow.turbopack.highlights') as {title: string; description: string}[]).map((highlight, idx) => (
                    <div key={idx}>
                      <p className="font-medium">{highlight.title}</p>
                      <p className="text-xs text-muted-foreground">
                        {highlight.description}
                      </p>
                    </div>
                  ))}
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
            <h2 className="text-3xl md:text-4xl font-bold mb-3">{t('included.title')}</h2>
            <p className="text-muted-foreground text-lg">
              {t('included.subtitle')}
            </p>
          </div>

          <div className="grid md:grid-cols-3 gap-4 md:gap-6 max-w-5xl mx-auto">
            <Card className={cardInfo}>
              <CardHeader>
                <CardTitle className="text-lg">{t('included.pages.title')}</CardTitle>
                <CardDescription>{t('included.pages.subtitle')}</CardDescription>
              </CardHeader>
              <CardContent>
                <ul className="space-y-2 text-sm text-muted-foreground">
                  {(t.raw('included.pages.items') as string[]).map((item, idx) => (
                    <li key={idx}>• {item}</li>
                  ))}
                </ul>
              </CardContent>
            </Card>

            <Card className={cardInfo}>
              <CardHeader>
                <CardTitle className="text-lg">{t('included.demos.title')}</CardTitle>
                <CardDescription>{t('included.demos.subtitle')}</CardDescription>
              </CardHeader>
              <CardContent>
                <ul className="space-y-2 text-sm text-muted-foreground">
                  {(t.raw('included.demos.items') as string[]).map((item, idx) => (
                    <li key={idx}>• {item}</li>
                  ))}
                </ul>
              </CardContent>
            </Card>

            <Card className={cardInfo}>
              <CardHeader>
                <CardTitle className="text-lg">{t('included.auth.title')}</CardTitle>
                <CardDescription>{t('included.auth.subtitle')}</CardDescription>
              </CardHeader>
              <CardContent>
                <ul className="space-y-2 text-sm text-muted-foreground">
                  {(t.raw('included.auth.items') as string[]).map((item, idx) => (
                    <li key={idx}>• {item}</li>
                  ))}
                </ul>
              </CardContent>
            </Card>
          </div>
        </section>
      </ScrollReveal>

      {/* Testing Section */}
      <ScrollReveal delay={250}>
        <section className="space-y-6 md:space-y-8">
          <div className="text-center">
            <h2 className="text-3xl md:text-4xl font-bold mb-3">{t('testing.title')}</h2>
            <p className="text-muted-foreground text-lg">
              {t('testing.subtitle')}
            </p>
          </div>

          <div className="max-w-4xl mx-auto">
            <Card className={cn(cardInfo, 'border-primary/20 bg-gradient-to-br from-card to-primary/[0.02]')}>
              <CardHeader className="pb-3">
                <div className="flex items-center gap-3 mb-2">
                  <div className="p-2 rounded-lg bg-primary/15">
                    <FlaskConical className="w-4 h-4 text-primary" />
                  </div>
                  <CardTitle className="text-lg">{t('testing.title')}</CardTitle>
                </div>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid md:grid-cols-2 gap-4">
                  <div className="space-y-3">
                    <div className="flex items-start gap-3">
                      <div className="p-1.5 rounded bg-primary/10 mt-0.5">
                        <Database className="w-3.5 h-3.5 text-primary" />
                      </div>
                      <div>
                        <p className="text-sm font-medium">{t('testing.items.realPostgres.title')}</p>
                        <p className="text-xs text-muted-foreground">{t('testing.items.realPostgres.description')}</p>
                      </div>
                    </div>
                    <div className="flex items-start gap-3">
                      <div className="p-1.5 rounded bg-primary/10 mt-0.5">
                        <Zap className="w-3.5 h-3.5 text-primary" />
                      </div>
                      <div>
                        <p className="text-sm font-medium">{t('testing.items.parallel.title')}</p>
                        <p className="text-xs text-muted-foreground">{t('testing.items.parallel.description')}</p>
                      </div>
                    </div>
                  </div>
                  <div className="space-y-3">
                    <div className="flex items-start gap-3">
                      <div className="p-1.5 rounded bg-primary/10 mt-0.5">
                        <Terminal className="w-3.5 h-3.5 text-primary" />
                      </div>
                      <div>
                        <p className="text-sm font-medium">{t('testing.items.incremental.title')}</p>
                        <p className="text-xs text-muted-foreground">{t('testing.items.incremental.description')}</p>
                      </div>
                    </div>
                    <div className="flex items-start gap-3">
                      <div className="p-1.5 rounded bg-primary/10 mt-0.5">
                        <Shield className="w-3.5 h-3.5 text-primary" />
                      </div>
                      <div>
                        <p className="text-sm font-medium">{t('testing.items.isolated.title')}</p>
                        <p className="text-xs text-muted-foreground">{t('testing.items.isolated.description')}</p>
                      </div>
                    </div>
                  </div>
                </div>

                <div className="bg-muted p-4 rounded-lg font-mono text-xs space-y-2">
                  <div className="flex items-center gap-2">
                    <span className="text-primary">$</span>
                    <code className="text-foreground">{t('testing.commands.full')}</code>
                    <span className="text-muted-foreground ml-2"># {t('testing.commands.fullDesc')}</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="text-primary">$</span>
                    <code className="text-foreground">{t('testing.commands.quick')}</code>
                    <span className="text-muted-foreground ml-2"># {t('testing.commands.quickDesc')}</span>
                  </div>
                </div>
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
              {t('claudeCode.title')}
            </h2>
            <p className="text-muted-foreground text-lg">
              {t('claudeCode.subtitle')}
            </p>
          </div>

          <div className="max-w-5xl mx-auto space-y-4 md:space-y-6">
            {/* Architecture Overview */}
            <Card className={cardInfo}>
              <CardHeader>
                <CardTitle className="text-xl">{t('claudeCode.orchestration.title')}</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="bg-muted p-4 rounded-lg font-mono text-xs overflow-x-auto">
                  <div className="text-muted-foreground">
                    <span className="text-primary">Layer 0:</span> {t('claudeCode.orchestration.layer0')}
                  </div>
                  <div className="text-muted-foreground ml-4">
                    ├── <span className="text-primary">Layer 1:</span> {t('claudeCode.orchestration.layer1')}
                  </div>
                  <div className="text-muted-foreground ml-4">
                    ├── <span className="text-primary">Layer 2:</span> {t('claudeCode.orchestration.layer2')}
                  </div>
                  <div className="text-muted-foreground ml-4">
                    └── <span className="text-primary">Layer 3:</span> {t('claudeCode.orchestration.layer3')}
                  </div>
                </div>
              </CardContent>
            </Card>

            <div className="grid md:grid-cols-2 gap-4 md:gap-6">
              <Card className={cardInfo}>
                <CardHeader className="pb-3">
                  <CardTitle className="text-base">{t('claudeCode.slashCommands.title')}</CardTitle>
                </CardHeader>
                <CardContent className="space-y-2">
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-2 text-xs">
                    <div>
                      <code className="text-primary">{t('claudeCode.slashCommands.items.createTask.cmd')}</code>
                      <p className="text-muted-foreground">{t('claudeCode.slashCommands.items.createTask.desc')}</p>
                    </div>
                    <div>
                      <code className="text-primary">{t('claudeCode.slashCommands.items.executeTask.cmd')}</code>
                      <p className="text-muted-foreground">{t('claudeCode.slashCommands.items.executeTask.desc')}</p>
                    </div>
                    <div>
                      <code className="text-primary">{t('claudeCode.slashCommands.items.develop.cmd')}</code>
                      <p className="text-muted-foreground">{t('claudeCode.slashCommands.items.develop.desc')}</p>
                    </div>
                    <div>
                      <code className="text-primary">{t('claudeCode.slashCommands.items.design.cmd')}</code>
                      <p className="text-muted-foreground">{t('claudeCode.slashCommands.items.design.desc')}</p>
                    </div>
                    <div>
                      <code className="text-primary">{t('claudeCode.slashCommands.items.review.cmd')}</code>
                      <p className="text-muted-foreground">{t('claudeCode.slashCommands.items.review.desc')}</p>
                    </div>
                    <div>
                      <code className="text-primary">{t('claudeCode.slashCommands.items.addTesting.cmd')}</code>
                      <p className="text-muted-foreground">{t('claudeCode.slashCommands.items.addTesting.desc')}</p>
                    </div>
                  </div>
                </CardContent>
              </Card>

              <Card className={cardInfo}>
                <CardHeader className="pb-3">
                  <CardTitle className="text-base">{t('claudeCode.structuredTasks.title')}</CardTitle>
                </CardHeader>
                <CardContent className="space-y-3">
                  <p className="text-xs text-muted-foreground">
                    {t('claudeCode.structuredTasks.description')}
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
                  <CardTitle className="text-base">{t('claudeCode.developerAgent.title')}</CardTitle>
                </CardHeader>
                <CardContent className="space-y-2 text-xs text-muted-foreground">
                  <p>{t('claudeCode.developerAgent.intro')}</p>
                  <ul className="space-y-1">
                    {(t.raw('claudeCode.developerAgent.items') as string[]).map((item, idx) => (
                      <li key={idx}>
                        • <span className="text-foreground">{item}</span>
                      </li>
                    ))}
                  </ul>
                </CardContent>
              </Card>

              <Card className={cardInfo}>
                <CardHeader className="pb-3">
                  <CardTitle className="text-base">{t('claudeCode.patternDocs.title')}</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="flex flex-wrap gap-1.5">
                    {(t.raw('claudeCode.patternDocs.docs') as string[]).map((doc, idx) => (
                      <code key={idx} className="bg-muted px-1.5 py-0.5 rounded text-xs">{doc}</code>
                    ))}
                  </div>
                </CardContent>
              </Card>
            </div>

            {/* Workflow Example */}
            <Card className={cardInfo}>
              <CardHeader className="pb-3">
                <CardTitle className="text-base">{t('claudeCode.example.title')}</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="grid md:grid-cols-4 gap-3 text-xs">
                  <div className="bg-muted p-3 rounded">
                    <code className="text-primary">{t('claudeCode.example.createTask.cmd')}</code>
                    <p className="text-muted-foreground mt-1">
                      {t('claudeCode.example.createTask.desc')}
                    </p>
                    <p className="text-muted-foreground mt-1">
                      {t('claudeCode.example.createTask.result')}
                    </p>
                  </div>
                  <div className="bg-muted p-3 rounded">
                    <code className="text-primary">{t('claudeCode.example.executeTask.cmd')}</code>
                    <p className="text-muted-foreground mt-1">
                      {t('claudeCode.example.executeTask.desc')}
                    </p>
                    <p className="text-muted-foreground mt-1">
                      {t('claudeCode.example.executeTask.result')}
                    </p>
                  </div>
                  <div className="bg-muted p-3 rounded">
                    <code className="text-primary">{t('claudeCode.example.developerAgent.cmd')}</code>
                    <p className="text-muted-foreground mt-1">
                      {t('claudeCode.example.developerAgent.desc')}
                    </p>
                    <p className="text-muted-foreground mt-1">
                      {t('claudeCode.example.developerAgent.result')}
                    </p>
                  </div>
                  <div className="bg-muted p-3 rounded">
                    <code className="text-primary">{t('claudeCode.example.review.cmd')}</code>
                    <p className="text-muted-foreground mt-1">
                      {t('claudeCode.example.review.desc')}
                    </p>
                    <p className="text-muted-foreground mt-1">
                      {t('claudeCode.example.review.result')}
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
            <h2 className="text-3xl md:text-4xl font-bold mb-3">{t('quickStart.title')}</h2>
            <p className="text-muted-foreground text-lg">
              {t('quickStart.subtitle')}
            </p>
          </div>

          <div className="max-w-4xl mx-auto space-y-4 md:space-y-6">
            {/* Animated Terminal - Hero Visual */}
            <AnimatedTerminal />

            <div className="grid md:grid-cols-2 gap-4 md:gap-6">
              <Card className={cardInfo}>
                <CardHeader>
                  <CardTitle className="text-lg">{t('quickStart.run.title')}</CardTitle>
                  <CardDescription>{t('quickStart.run.subtitle')}</CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="space-y-3">
                    {(t.raw('quickStart.run.steps') as {num: number; title: string; code?: string; desc?: string}[]).map((step, idx) => (
                      <div key={idx} className="flex gap-3">
                        <span className={cn(
                          "flex-shrink-0 w-6 h-6 rounded-full text-xs flex items-center justify-center font-medium",
                          step.num === 0 ? "bg-muted text-muted-foreground" : "bg-primary/10 text-primary"
                        )}>
                          {step.num}
                        </span>
                        <div className="flex-1">
                          <p className="text-sm font-medium">{step.title}</p>
                          {step.code ? (
                            <code className="text-xs text-muted-foreground">{step.code}</code>
                          ) : (
                            <p className="text-xs text-muted-foreground">{step.desc}</p>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                  <div className="pt-2 border-t">
                    <p className="text-xs text-muted-foreground">
                      {t('quickStart.run.openAt')}
                    </p>
                  </div>
                </CardContent>
              </Card>

              <Card className={cardInfo}>
                <CardHeader>
                  <CardTitle className="text-lg">{t('quickStart.create.title')}</CardTitle>
                  <CardDescription>{t('quickStart.create.subtitle')}</CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="space-y-3">
                    {(t.raw('quickStart.create.steps') as {num: number; title: string; code: string}[]).map((step, idx) => (
                      <div key={idx} className="flex gap-3">
                        <span className="flex-shrink-0 w-6 h-6 rounded-full bg-primary/10 text-primary text-xs flex items-center justify-center font-medium">
                          {step.num}
                        </span>
                        <div className="flex-1">
                          <p className="text-sm font-medium">{step.title}</p>
                          <code className="text-xs text-muted-foreground">
                            {step.code}
                          </code>
                        </div>
                      </div>
                    ))}
                  </div>
                  <div className="pt-2 border-t">
                    <p className="text-xs text-muted-foreground">
                      {t('quickStart.create.seeDetails')}
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
              <h3 className="text-2xl font-bold">{t('cta.title')}</h3>
              <div className="flex flex-col sm:flex-row gap-3 justify-center pt-2">
                <Button asChild size="lg" className={btnPrimary}>
                  <Link href="/demo">
                    <span className="hidden sm:inline">{t('cta.tryDemos')}: {t('cta.demoSubtitle')}</span>
                    <span className="sm:hidden">{t('cta.tryDemos')}</span>
                    <ArrowRight className="w-4 h-4 ml-2 transition-transform duration-300 group-hover:translate-x-1" />
                  </Link>
                </Button>
                <Button asChild variant="outline" size="lg" className={btnSecondary}>
                  <Link href="/profile">
                    <span className="hidden sm:inline">{t('cta.testAuth')}: {t('cta.authSubtitle')}</span>
                    <span className="sm:hidden">{t('cta.testAuth')}</span>
                  </Link>
                </Button>
              </div>
            </div>
          </div>
        </section>
      </ScrollReveal>

      {/* Footer Credits */}
      <footer className="text-center py-6 text-sm text-muted-foreground">
        {t('footer.text')} •{' '}
        <a
          href="https://vue.antonchaynik.ru"
          target="_blank"
          rel="noopener noreferrer"
          className="text-primary hover:underline"
        >
          {t('footer.vueLink')}
        </a>
      </footer>
    </div>
  );
}
