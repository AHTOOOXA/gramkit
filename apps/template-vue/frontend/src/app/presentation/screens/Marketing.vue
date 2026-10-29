<script setup lang="ts">
import { computed } from 'vue';
import { useI18n } from 'vue-i18n';
import {
  ArrowRight,
  Atom,
  Bell,
  Check,
  Code2,
  CreditCard,
  Database,
  FileCode2,
  FlaskConical,
  Globe,
  Laptop,
  Layers,
  LayoutDashboard,
  LayoutGrid,
  Palette,
  Radio,
  Shield,
  Smartphone,
  Sparkles,
  Terminal,
  Users,
  Zap,
  type LucideIcon,
} from '@lucide/vue';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import ScrollReveal from '@/components/ui/animation/ScrollReveal.vue';
import { cn } from '@/lib/utils';
import { GITHUB_URL, REACT_DEMO_URL } from '@/config/constants';
import { PRODUCTION_SITE } from '@/config/showcase';
import ArchitectureDiagram from '@app/presentation/components/home/ArchitectureDiagram.vue';
import BrandIcon from '@app/presentation/components/home/BrandIcon.vue';
import CommandBlock from '@app/presentation/components/home/CommandBlock.vue';
import CopyPrompt from '@app/presentation/components/home/CopyPrompt.vue';
import { useMessageList } from '@app/presentation/components/home/useMessageList';

// Mirrors template-react's app/[locale]/(marketing)/page.tsx; copy lives in homePage.* (en + ru).
const { t } = useI18n();
const { list } = useMessageList();

// Design system: consistent hover patterns
// Feature cards (above fold): interactive, draw attention
const cardFeature =
  'group relative overflow-hidden transition-all duration-300 ease-out hover:shadow-xl hover:shadow-primary/10 hover:-translate-y-1.5 hover:border-primary/30';
// Info cards (below fold): subtle, for reading
const cardInfo = 'transition-all duration-300 hover:shadow-lg hover:shadow-primary/5 hover:border-primary/20';
// Buttons: consistent press/lift feedback
const btnPrimary =
  'group active:scale-[0.98] hover:-translate-y-0.5 hover:shadow-lg hover:shadow-primary/25 transition-all duration-150';
const btnSecondary = 'active:scale-[0.98] hover:-translate-y-0.5 transition-all duration-150';

const featureItems: { key: string; icon: LucideIcon; highlighted?: boolean }[] = [
  { key: 'authentication', icon: Shield, highlighted: true },
  { key: 'rbac', icon: Users },
  { key: 'realtime', icon: Radio, highlighted: true },
  { key: 'mobile', icon: Smartphone },
  { key: 'typeSafe', icon: Code2, highlighted: true },
  { key: 'i18n', icon: Palette },
  { key: 'tanstack', icon: Database },
  { key: 'dx', icon: Terminal },
];

const pillarItems: { key: 'admin' | 'payments' | 'bot'; icon: LucideIcon }[] = [
  { key: 'admin', icon: LayoutDashboard },
  { key: 'payments', icon: CreditCard },
  { key: 'bot', icon: Bell },
];

const highlightsLeft: { key: string; icon: LucideIcon }[] = [
  { key: 'endToEnd', icon: FileCode2 },
  { key: 'make', icon: Terminal },
  { key: 'shared', icon: Layers },
];
const highlightsRight: { key: string; icon: LucideIcon }[] = [
  { key: 'hotReload', icon: Zap },
  { key: 'repo', icon: Database },
  { key: 'tanstackPatterns', icon: Radio },
];

const testingLeft: { key: string; icon: LucideIcon }[] = [
  { key: 'realPostgres', icon: Database },
  { key: 'parallel', icon: Zap },
];
const testingRight: { key: string; icon: LucideIcon }[] = [
  { key: 'incremental', icon: Terminal },
  { key: 'isolated', icon: Shield },
];


// Typed list (generic calls can't live in the template); computed so it follows the locale
const devServerHighlights = computed(() =>
  list<{ title: string; description: string }>('homePage.workflow.devServer.highlights'),
);

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
</script>

<template>
  <div class="space-y-8 md:space-y-16">
    <!-- Hero Section -->
    <section
      class="space-y-6 py-6 text-center motion-blur-in-[10px] motion-scale-in-[0.95] motion-opacity-in-[0%] motion-duration-[0.7s] motion-ease-spring-smooth md:py-12"
    >
      <div class="inline-flex items-center gap-2 rounded-full bg-primary/10 px-4 py-2 text-sm font-medium text-primary">
        <Sparkles class="h-4 w-4" />
        <span>{{ t('homePage.badge') }}</span>
      </div>

      <h1 class="text-4xl font-bold tracking-tight md:text-6xl">{{ t('homePage.title') }}</h1>

      <p class="mx-auto max-w-3xl text-xl text-muted-foreground md:text-2xl">
        {{ t('homePage.heroSubtitle') }}
      </p>

      <div class="flex flex-col justify-center gap-4 pt-4 sm:flex-row">
        <Button as-child size="lg" :class="btnPrimary">
          <a href="#get-started">
            {{ t('homePage.getStarted') }}
            <ArrowRight class="ml-2 h-4 w-4 transition-transform duration-300 group-hover:translate-x-1" />
          </a>
        </Button>
        <Button as-child variant="outline" size="lg" :class="btnSecondary">
          <a :href="GITHUB_URL" target="_blank" rel="noopener noreferrer">
            <BrandIcon name="github" class="mr-2 h-4 w-4" />
            {{ t('homePage.github') }}
          </a>
        </Button>
        <Button as-child variant="outline" size="lg" :class="btnSecondary">
          <a :href="REACT_DEMO_URL" target="_blank" rel="noopener noreferrer">
            <Atom class="mr-2 h-4 w-4" />
            {{ t('homePage.tryReactVersion') }}
          </a>
        </Button>
      </div>

      <p class="text-sm text-muted-foreground">
        {{ t('homePage.inProduction') }}
        <a :href="PRODUCTION_SITE.url" target="_blank" rel="noopener noreferrer" class="text-primary hover:underline">
          {{ PRODUCTION_SITE.label }}
        </a>
      </p>
    </section>

    <!-- Key Features Section: above fold, interactive cards -->
    <section
      class="space-y-6 motion-opacity-in-[0%] motion-translate-y-in-[30px] motion-blur-in-[4px] motion-duration-[0.5s] motion-delay-[0.3s] motion-ease-spring-smooth md:space-y-8"
    >
      <div class="text-center">
        <h2 class="mb-3 text-3xl font-bold md:text-4xl">{{ t('homePage.features.title') }}</h2>
        <p class="text-lg text-muted-foreground">{{ t('homePage.features.subtitle') }}</p>
      </div>

      <div class="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-4">
        <Card
          v-for="(item, index) in featureItems"
          :key="item.key"
          :class="
            cn(
              cardFeature,
              'gap-3 py-4',
              'motion-opacity-in-[0%] motion-translate-y-in-[20px] motion-blur-in-[3px] motion-duration-[0.4s] motion-ease-spring-smooth',
              featureDelays[index],
              item.highlighted && 'border-primary/20 bg-gradient-to-br from-card to-primary/[0.02]',
            )
          "
        >
          <!-- Hover gradient overlay -->
          <div
            class="pointer-events-none absolute inset-0 bg-gradient-to-br from-primary/0 via-primary/[0.03] to-primary/0 opacity-0 transition-opacity duration-300 group-hover:opacity-100"
          />

          <CardHeader class="relative pb-0">
            <div class="mb-1 flex items-center gap-3">
              <div
                :class="
                  cn(
                    'rounded-lg p-2 transition-all duration-300',
                    item.highlighted ? 'bg-primary/15 group-hover:bg-primary/25' : 'bg-primary/10 group-hover:bg-primary/20',
                  )
                "
              >
                <component :is="item.icon" class="h-4 w-4 text-primary transition-transform duration-300 group-hover:scale-110" />
              </div>
            </div>
            <CardTitle class="text-base">{{ t(`homePage.features.items.${item.key}.name`) }}</CardTitle>
          </CardHeader>
          <CardContent class="relative pt-0">
            <CardDescription class="text-sm">{{ t(`homePage.features.items.${item.key}.description`) }}</CardDescription>
          </CardContent>
        </Card>
      </div>
    </section>

    <!-- Admin, payments, bot: what a paid Mini App needs -->
    <ScrollReveal :delay="0">
      <section class="space-y-6 md:space-y-8">
        <div class="text-center">
          <h2 class="mb-3 text-3xl font-bold md:text-4xl">{{ t('homePage.pillars.title') }}</h2>
          <p class="text-lg text-muted-foreground">{{ t('homePage.pillars.subtitle') }}</p>
        </div>

        <div class="grid gap-4 md:gap-6 lg:grid-cols-3">
          <Card
            v-for="pillar in pillarItems"
            :key="pillar.key"
            :class="cn(cardInfo, 'border-primary/20 bg-gradient-to-br from-card to-primary/[0.02]')"
          >
            <CardHeader class="pb-3">
              <div class="mb-2 flex items-center gap-3">
                <div class="rounded-lg bg-primary/15 p-2">
                  <component :is="pillar.icon" class="h-4 w-4 text-primary" />
                </div>
                <CardTitle class="text-lg">{{ t(`homePage.pillars.${pillar.key}.title`) }}</CardTitle>
              </div>
              <CardDescription>{{ t(`homePage.pillars.${pillar.key}.lead`) }}</CardDescription>
            </CardHeader>
            <CardContent>
              <ul class="space-y-2 text-sm text-muted-foreground">
                <li v-for="(item, idx) in list(`homePage.pillars.${pillar.key}.items`)" :key="idx" class="flex gap-2">
                  <Check class="mt-0.5 h-4 w-4 shrink-0 text-primary" />
                  <span>{{ item }}</span>
                </li>
              </ul>
            </CardContent>
          </Card>
        </div>
      </section>
    </ScrollReveal>

    <!-- Architecture Overview Section: info cards -->
    <ScrollReveal :delay="0">
      <section class="space-y-6 md:space-y-8">
        <div class="text-center">
          <h2 class="mb-3 text-3xl font-bold md:text-4xl">{{ t('homePage.architecture.title') }}</h2>
          <p class="text-lg text-muted-foreground">{{ t('homePage.architecture.subtitle') }}</p>
        </div>

        <div class="mx-auto max-w-4xl space-y-4 md:space-y-6">
          <Card :class="cardInfo">
            <CardHeader>
              <CardTitle class="text-xl">{{ t('homePage.architecture.monorepoTitle') }}</CardTitle>
            </CardHeader>
            <CardContent>
              <ArchitectureDiagram />
            </CardContent>
          </Card>

          <Card :class="cardInfo">
            <CardHeader>
              <CardTitle class="text-xl">{{ t('homePage.architecture.highlightsTitle') }}</CardTitle>
              <CardDescription>{{ t('homePage.architecture.highlightsSubtitle') }}</CardDescription>
            </CardHeader>
            <CardContent>
              <div class="grid gap-4 md:grid-cols-2">
                <div v-for="(column, ci) in [highlightsLeft, highlightsRight]" :key="ci" class="space-y-3">
                  <div v-for="item in column" :key="item.key" class="flex items-start gap-3">
                    <div class="mt-0.5 rounded bg-primary/10 p-1.5">
                      <component :is="item.icon" class="h-3.5 w-3.5 text-primary" />
                    </div>
                    <div>
                      <p class="text-sm font-medium">{{ t(`homePage.architecture.highlights.${item.key}.title`) }}</p>
                      <p class="text-xs text-muted-foreground">
                        {{ t(`homePage.architecture.highlights.${item.key}.description`) }}
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

    <!-- Development Workflow Section -->
    <ScrollReveal :delay="100">
      <section class="space-y-6 md:space-y-8">
        <div class="text-center">
          <h2 class="mb-3 text-3xl font-bold md:text-4xl">{{ t('homePage.workflow.title') }}</h2>
          <p class="text-lg text-muted-foreground">{{ t('homePage.workflow.subtitle') }}</p>
        </div>

        <div class="mx-auto max-w-5xl space-y-4 md:space-y-6">
          <div class="grid gap-4 md:grid-cols-2 md:gap-6">
            <Card :class="cn(cardInfo, 'border-primary/20 bg-gradient-to-br from-card to-primary/[0.02]')">
              <CardHeader class="pb-3">
                <div class="mb-2 flex items-center gap-3">
                  <div class="rounded-lg bg-primary/15 p-2">
                    <Laptop class="h-4 w-4 text-primary" />
                  </div>
                  <CardTitle class="text-lg">{{ t('homePage.workflow.localhost.title') }}</CardTitle>
                  <span class="rounded-full bg-primary/10 px-2 py-0.5 text-xs text-primary">
                    {{ t('homePage.workflow.localhost.recommended') }}
                  </span>
                </div>
                <CardDescription>{{ t('homePage.workflow.localhost.subtitle') }}</CardDescription>
              </CardHeader>
              <CardContent class="space-y-3">
                <div class="rounded bg-muted p-3 font-mono text-xs">
                  <div class="text-foreground">{{ t('homePage.workflow.localhost.url') }}</div>
                </div>
                <ul class="space-y-1.5 text-sm text-muted-foreground">
                  <li v-for="(benefit, idx) in list('homePage.workflow.localhost.benefits')" :key="idx" class="flex items-center gap-2">
                    <span class="text-primary">✓</span> {{ benefit }}
                  </li>
                </ul>
              </CardContent>
            </Card>

            <Card :class="cardInfo">
              <CardHeader class="pb-3">
                <div class="mb-2 flex items-center gap-3">
                  <div class="rounded-lg bg-primary/10 p-2">
                    <Globe class="h-4 w-4 text-primary" />
                  </div>
                  <CardTitle class="text-lg">{{ t('homePage.workflow.tunnel.title') }}</CardTitle>
                </div>
                <CardDescription>{{ t('homePage.workflow.tunnel.subtitle') }}</CardDescription>
              </CardHeader>
              <CardContent class="space-y-3">
                <div class="rounded bg-muted p-3 font-mono text-xs">
                  <div class="text-muted-foreground">{{ t('homePage.workflow.tunnel.url') }}</div>
                </div>
                <ul class="space-y-1.5 text-sm text-muted-foreground">
                  <li v-for="(benefit, idx) in list('homePage.workflow.tunnel.benefits')" :key="idx" class="flex items-center gap-2">
                    <span class="text-primary">✓</span> {{ benefit }}
                  </li>
                </ul>
              </CardContent>
            </Card>
          </div>

          <Card :class="cardInfo">
            <CardHeader class="pb-3">
              <div class="mb-2 flex items-center gap-3">
                <div class="rounded-lg bg-primary/10 p-2">
                  <LayoutGrid class="h-4 w-4 text-primary" />
                </div>
                <CardTitle class="text-lg">{{ t('homePage.workflow.gateway.title') }}</CardTitle>
              </div>
              <CardDescription>{{ t('homePage.workflow.gateway.subtitle') }}</CardDescription>
            </CardHeader>
            <CardContent>
              <div class="grid gap-3 text-xs md:grid-cols-3">
                <div class="rounded bg-muted p-3">
                  <code class="text-blue-400">{{ t('homePage.workflow.gateway.apps.react') }}</code>
                  <div class="mt-1.5 space-y-1 text-muted-foreground">
                    <div>{{ t('homePage.workflow.gateway.appDetails') }}</div>
                  </div>
                </div>
                <div class="rounded bg-muted p-3">
                  <code class="text-green-400">{{ t('homePage.workflow.gateway.apps.vue') }}</code>
                  <div class="mt-1.5 space-y-1 text-muted-foreground">
                    <div>{{ t('homePage.workflow.gateway.vueDetails') }}</div>
                  </div>
                </div>
                <div class="rounded bg-muted p-3">
                  <code class="text-primary">{{ t('homePage.workflow.gateway.apps.yourApp') }}</code>
                  <div class="mt-1.5 space-y-1 text-muted-foreground">
                    <div>{{ t('homePage.workflow.gateway.yourAppDetails') }}</div>
                  </div>
                </div>
              </div>
              <p class="mt-3 text-xs text-muted-foreground">{{ t('homePage.workflow.gateway.description') }}</p>
            </CardContent>
          </Card>

          <Card :class="cn(cardInfo, 'border-primary/20 bg-gradient-to-br from-card to-primary/[0.02]')">
            <CardHeader class="pb-3">
              <div class="mb-2 flex items-center gap-3">
                <div class="rounded-lg bg-primary/15 p-2">
                  <Zap class="h-4 w-4 text-primary" />
                </div>
                <CardTitle class="text-lg">{{ t('homePage.workflow.devServer.title') }}</CardTitle>
              </div>
            </CardHeader>
            <CardContent>
              <div class="grid gap-4 text-sm md:grid-cols-3">
                <div
                  v-for="(highlight, idx) in devServerHighlights"
                  :key="idx"
                >
                  <p class="font-medium">{{ highlight.title }}</p>
                  <p class="text-xs text-muted-foreground">{{ highlight.description }}</p>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      </section>
    </ScrollReveal>

    <!-- What's Included Section: info cards -->
    <ScrollReveal :delay="200">
      <section class="space-y-6 md:space-y-8">
        <div class="text-center">
          <h2 class="mb-3 text-3xl font-bold md:text-4xl">{{ t('homePage.included.title') }}</h2>
          <p class="text-lg text-muted-foreground">{{ t('homePage.included.subtitle') }}</p>
        </div>

        <div class="mx-auto grid max-w-5xl gap-4 md:grid-cols-3 md:gap-6">
          <Card v-for="block in ['pages', 'demos', 'auth']" :key="block" :class="cardInfo">
            <CardHeader>
              <CardTitle class="text-lg">{{ t(`homePage.included.${block}.title`) }}</CardTitle>
              <CardDescription>{{ t(`homePage.included.${block}.subtitle`) }}</CardDescription>
            </CardHeader>
            <CardContent>
              <ul class="space-y-2 text-sm text-muted-foreground">
                <li v-for="(item, idx) in list(`homePage.included.${block}.items`)" :key="idx">• {{ item }}</li>
              </ul>
            </CardContent>
          </Card>
        </div>
      </section>
    </ScrollReveal>

    <!-- Testing Section -->
    <ScrollReveal :delay="250">
      <section class="space-y-6 md:space-y-8">
        <div class="text-center">
          <h2 class="mb-3 text-3xl font-bold md:text-4xl">{{ t('homePage.testing.title') }}</h2>
          <p class="text-lg text-muted-foreground">{{ t('homePage.testing.subtitle') }}</p>
        </div>

        <div class="mx-auto max-w-4xl">
          <Card :class="cn(cardInfo, 'border-primary/20 bg-gradient-to-br from-card to-primary/[0.02]')">
            <CardHeader class="pb-3">
              <div class="mb-2 flex items-center gap-3">
                <div class="rounded-lg bg-primary/15 p-2">
                  <FlaskConical class="h-4 w-4 text-primary" />
                </div>
                <CardTitle class="text-lg">{{ t('homePage.testing.title') }}</CardTitle>
              </div>
            </CardHeader>
            <CardContent class="space-y-4">
              <div class="grid gap-4 md:grid-cols-2">
                <div v-for="(column, ci) in [testingLeft, testingRight]" :key="ci" class="space-y-3">
                  <div v-for="item in column" :key="item.key" class="flex items-start gap-3">
                    <div class="mt-0.5 rounded bg-primary/10 p-1.5">
                      <component :is="item.icon" class="h-3.5 w-3.5 text-primary" />
                    </div>
                    <div>
                      <p class="text-sm font-medium">{{ t(`homePage.testing.items.${item.key}.title`) }}</p>
                      <p class="text-xs text-muted-foreground">{{ t(`homePage.testing.items.${item.key}.description`) }}</p>
                    </div>
                  </div>
                </div>
              </div>

              <div class="space-y-2 rounded-lg bg-muted p-4 font-mono text-xs">
                <div class="flex items-center gap-2">
                  <span class="text-primary">$</span>
                  <code class="text-foreground">{{ t('homePage.testing.commands.full') }}</code>
                  <span class="ml-2 text-muted-foreground"># {{ t('homePage.testing.commands.fullDesc') }}</span>
                </div>
                <div class="flex items-center gap-2">
                  <span class="text-primary">$</span>
                  <code class="text-foreground">{{ t('homePage.testing.commands.quick') }}</code>
                  <span class="ml-2 text-muted-foreground"># {{ t('homePage.testing.commands.quickDesc') }}</span>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      </section>
    </ScrollReveal>

    <!-- Claude Code & Agents Section: info cards -->
    <ScrollReveal :delay="300">
      <section class="space-y-6 md:space-y-8">
        <div class="text-center">
          <h2 class="mb-3 text-3xl font-bold md:text-4xl">{{ t('homePage.claudeCode.title') }}</h2>
          <p class="text-lg text-muted-foreground">{{ t('homePage.claudeCode.subtitle') }}</p>
        </div>

        <div class="mx-auto max-w-4xl">
          <Card :class="cardInfo">
            <CardHeader>
              <CardTitle class="text-xl">{{ t('homePage.claudeCode.orchestration.title') }}</CardTitle>
            </CardHeader>
            <CardContent class="space-y-4">
              <div class="space-y-0.5 overflow-x-auto rounded-lg bg-muted p-4 font-mono text-xs text-muted-foreground">
                <div>{{ t('homePage.claudeCode.orchestration.layer0') }}</div>
                <div class="ml-4">├── {{ t('homePage.claudeCode.orchestration.layer1') }}</div>
                <div class="ml-4">├── {{ t('homePage.claudeCode.orchestration.layer2') }}</div>
                <div class="ml-4">└── {{ t('homePage.claudeCode.orchestration.layer3') }}</div>
              </div>
              <div class="space-y-2">
                <p class="text-sm font-medium">{{ t('homePage.claudeCode.patternDocs.title') }}</p>
                <div class="flex flex-wrap gap-1.5">
                  <code v-for="doc in list('homePage.claudeCode.patternDocs.docs')" :key="doc" class="rounded bg-muted px-1.5 py-0.5 text-xs">
                    {{ doc }}
                  </code>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      </section>
    </ScrollReveal>

    <!-- Get Started: run the template, or copy it into your own app -->
    <ScrollReveal :delay="400">
      <section id="get-started" class="scroll-mt-24 space-y-6 md:space-y-8">
        <div class="text-center">
          <h2 class="mb-3 text-3xl font-bold md:text-4xl">{{ t('homePage.quickStart.title') }}</h2>
          <p class="text-lg text-muted-foreground">{{ t('homePage.quickStart.subtitle') }}</p>
        </div>

        <div class="mx-auto grid max-w-5xl gap-4 md:grid-cols-2 md:gap-6">
          <Card
            v-for="block in ['run', 'create']"
            :key="block"
            :class="cn('min-w-0', cardInfo, block === 'create' && 'border-primary/30 bg-gradient-to-br from-card to-primary/[0.03]')"
          >
            <CardHeader>
              <CardTitle class="text-lg">{{ t(`homePage.quickStart.${block}.title`) }}</CardTitle>
            </CardHeader>
            <CardContent class="space-y-4">
              <CommandBlock :commands="list(`homePage.quickStart.${block}.commands`)" />
              <p class="text-xs text-muted-foreground">{{ t(`homePage.quickStart.${block}.note`) }}</p>
              <CopyPrompt :prompt="t(`homePage.quickStart.${block}.prompt`)" />
            </CardContent>
          </Card>
        </div>
      </section>
    </ScrollReveal>

    <!-- Footer Credits -->
    <footer class="py-6 text-center text-sm text-muted-foreground">
      {{ t('homePage.footer.text') }} •
      <a :href="GITHUB_URL" target="_blank" rel="noopener noreferrer" class="text-primary hover:underline">
        {{ t('homePage.footer.githubLink') }}
      </a>
      •
      <a :href="REACT_DEMO_URL" target="_blank" rel="noopener noreferrer" class="text-primary hover:underline">
        {{ t('homePage.footer.reactLink') }}
      </a>
    </footer>
  </div>
</template>
