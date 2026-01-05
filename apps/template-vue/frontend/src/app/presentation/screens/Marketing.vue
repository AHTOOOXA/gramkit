<script setup lang="ts">
import { computed } from 'vue';
import { useI18n } from 'vue-i18n';
import { RouterLink } from 'vue-router';
import {
  ArrowRight,
  Atom,
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
} from 'lucide-vue-next';
import { Button } from '@/components/ui/button';
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import { useAuth } from '@app/composables/useAuth';
import ScrollReveal from '@/components/ui/animation/ScrollReveal.vue';
import AnimatedTerminal from '@app/presentation/components/home/AnimatedTerminal.vue';
import ArchitectureDiagram from '@app/presentation/components/home/ArchitectureDiagram.vue';

const { t, tm } = useI18n();
const { isAuthenticated } = useAuth();

// Design system constants
const cardFeature = 'group relative overflow-hidden transition-all duration-300 ease-out hover:shadow-xl hover:shadow-primary/10 hover:-translate-y-1.5 hover:border-primary/30';
const cardInfo = 'transition-all duration-300 hover:shadow-lg hover:shadow-primary/5 hover:border-primary/20';
const btnPrimary = 'group active:scale-[0.98] hover:-translate-y-0.5 hover:shadow-lg hover:shadow-primary/25 transition-all duration-150';
const btnSecondary = 'active:scale-[0.98] hover:-translate-y-0.5 transition-all duration-150';

interface FeatureItem {
  name: string;
  description: string;
  icon: LucideIcon;
  highlighted?: boolean;
}

const featureItems = computed<FeatureItem[]>(() => [
  {
    name: t('homePage.features.items.authentication.name'),
    description: t('homePage.features.items.authentication.description'),
    icon: Shield,
    highlighted: true,
  },
  {
    name: t('homePage.features.items.rbac.name'),
    description: t('homePage.features.items.rbac.description'),
    icon: Users,
  },
  {
    name: t('homePage.features.items.realtime.name'),
    description: t('homePage.features.items.realtime.description'),
    icon: Radio,
    highlighted: true,
  },
  {
    name: t('homePage.features.items.mobile.name'),
    description: t('homePage.features.items.mobile.description'),
    icon: Smartphone,
  },
  {
    name: t('homePage.features.items.typesat.name'),
    description: t('homePage.features.items.typesat.description'),
    icon: Code2,
    highlighted: true,
  },
  {
    name: t('homePage.features.items.i18n.name'),
    description: t('homePage.features.items.i18n.description'),
    icon: Palette,
  },
  {
    name: t('homePage.features.items.tanstack.name'),
    description: t('homePage.features.items.tanstack.description'),
    icon: Database,
  },
  {
    name: t('homePage.features.items.dx.name'),
    description: t('homePage.features.items.dx.description'),
    icon: Terminal,
  },
]);

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
    <section class="text-center space-y-6 py-6 md:py-12 motion-blur-in-[10px] motion-scale-in-[0.95] motion-opacity-in-[0%] motion-duration-[0.7s] motion-ease-spring-smooth">
      <div class="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-primary/10 text-primary text-sm font-medium">
        <Sparkles class="w-4 h-4" />
        <span>{{ t('homePage.badge') }}</span>
      </div>

      <h1 class="text-4xl md:text-6xl font-bold tracking-tight">{{ t('homePage.title') }}</h1>

      <p class="text-xl md:text-2xl text-muted-foreground max-w-3xl mx-auto">
        {{ t('homePage.subtitle') }}
      </p>

      <div class="flex flex-col sm:flex-row gap-4 justify-center pt-4">
        <Button
          :as-child="true"
          size="lg"
          :class="btnPrimary"
        >
          <RouterLink :to="isAuthenticated ? '/demo' : '/login'">
            {{ isAuthenticated ? t('homePage.explorePatterns') : t('homePage.getStarted') }}
            <ArrowRight class="w-4 h-4 ml-2 transition-transform duration-300 group-hover:translate-x-1" />
          </RouterLink>
        </Button>
        <Button
          :as-child="true"
          variant="outline"
          size="lg"
          :class="btnSecondary"
        >
          <a href="https://react.antonchaynik.ru" target="_blank" rel="noopener noreferrer">
            <Atom class="w-4 h-4 mr-2" />
            Try React Version
          </a>
        </Button>
      </div>
    </section>

    <!-- Key Features Section -->
    <section class="space-y-6 md:space-y-8 motion-opacity-in-[0%] motion-translate-y-in-[30px] motion-blur-in-[4px] motion-duration-[0.5s] motion-delay-[0.3s] motion-ease-spring-smooth">
      <div class="text-center">
        <h2 class="text-3xl md:text-4xl font-bold mb-3">{{ t('homePage.features.title') }}</h2>
        <p class="text-muted-foreground text-lg">
          {{ t('homePage.features.subtitle') }}
        </p>
      </div>

      <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <Card
          v-for="(item, index) in featureItems"
          :key="item.name"
          :class="[
            cardFeature,
            'py-4 gap-3',
            'motion-opacity-in-[0%] motion-translate-y-in-[20px] motion-blur-in-[3px] motion-duration-[0.4s] motion-ease-spring-smooth',
            featureDelays[index],
            item.highlighted && 'border-primary/20 bg-gradient-to-br from-card to-primary/[0.02]'
          ]"
        >
          <!-- Hover gradient overlay -->
          <div class="absolute inset-0 bg-gradient-to-br from-primary/0 via-primary/[0.03] to-primary/0 opacity-0 group-hover:opacity-100 transition-opacity duration-300 pointer-events-none" />

          <CardHeader class="pb-0 relative">
            <div class="flex items-center gap-3 mb-1">
              <div
:class="[
                'p-2 rounded-lg transition-all duration-300',
                item.highlighted
                  ? 'bg-primary/15 group-hover:bg-primary/25'
                  : 'bg-primary/10 group-hover:bg-primary/20'
              ]">
                <component :is="item.icon" class="w-4 h-4 text-primary transition-transform duration-300 group-hover:scale-110" />
              </div>
            </div>
            <CardTitle class="text-base">{{ item.name }}</CardTitle>
          </CardHeader>
          <CardContent class="relative pt-0">
            <CardDescription class="text-sm">{{ item.description }}</CardDescription>
          </CardContent>
        </Card>
      </div>
    </section>

    <!-- Architecture Overview Section -->
    <ScrollReveal :delay="0">
      <section class="space-y-6 md:space-y-8">
        <div class="text-center">
          <h2 class="text-3xl md:text-4xl font-bold mb-3">{{ t('homePage.architecture.title') }}</h2>
          <p class="text-muted-foreground text-lg">{{ t('homePage.architecture.subtitle') }}</p>
        </div>

        <div class="max-w-4xl mx-auto space-y-4 md:space-y-6">
          <Card :class="cardInfo">
            <CardHeader>
              <CardTitle class="text-xl">{{ t('homePage.architecture.title') }}</CardTitle>
            </CardHeader>
            <CardContent>
              <ArchitectureDiagram />
            </CardContent>
          </Card>

          <Card :class="cardInfo">
            <CardHeader>
              <CardTitle class="text-xl">{{ t('homePage.architecture.highlights.endToEnd.title') }}</CardTitle>
              <CardDescription>
                {{ t('homePage.architecture.subtitle') }}
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div class="grid md:grid-cols-2 gap-4">
                <div class="space-y-3">
                  <div class="flex items-start gap-3">
                    <div class="p-1.5 rounded bg-primary/10 mt-0.5">
                      <FileCode2 class="w-3.5 h-3.5 text-primary" />
                    </div>
                    <div>
                      <p class="text-sm font-medium">{{ t('homePage.architecture.highlights.endToEnd.title') }}</p>
                      <p class="text-xs text-muted-foreground">
                        {{ t('homePage.architecture.highlights.endToEnd.description') }}
                      </p>
                    </div>
                  </div>
                  <div class="flex items-start gap-3">
                    <div class="p-1.5 rounded bg-primary/10 mt-0.5">
                      <Terminal class="w-3.5 h-3.5 text-primary" />
                    </div>
                    <div>
                      <p class="text-sm font-medium">{{ t('homePage.architecture.highlights.make.title') }}</p>
                      <p class="text-xs text-muted-foreground">
                        {{ t('homePage.architecture.highlights.make.description') }}
                      </p>
                    </div>
                  </div>
                  <div class="flex items-start gap-3">
                    <div class="p-1.5 rounded bg-primary/10 mt-0.5">
                      <Layers class="w-3.5 h-3.5 text-primary" />
                    </div>
                    <div>
                      <p class="text-sm font-medium">{{ t('homePage.architecture.highlights.shared.title') }}</p>
                      <p class="text-xs text-muted-foreground">
                        {{ t('homePage.architecture.highlights.shared.description') }}
                      </p>
                    </div>
                  </div>
                </div>
                <div class="space-y-3">
                  <div class="flex items-start gap-3">
                    <div class="p-1.5 rounded bg-primary/10 mt-0.5">
                      <Zap class="w-3.5 h-3.5 text-primary" />
                    </div>
                    <div>
                      <p class="text-sm font-medium">{{ t('homePage.architecture.highlights.hotReload.title') }}</p>
                      <p class="text-xs text-muted-foreground">
                        {{ t('homePage.architecture.highlights.hotReload.description') }}
                      </p>
                    </div>
                  </div>
                  <div class="flex items-start gap-3">
                    <div class="p-1.5 rounded bg-primary/10 mt-0.5">
                      <Database class="w-3.5 h-3.5 text-primary" />
                    </div>
                    <div>
                      <p class="text-sm font-medium">{{ t('homePage.architecture.highlights.repo.title') }}</p>
                      <p class="text-xs text-muted-foreground">
                        {{ t('homePage.architecture.highlights.repo.description') }}
                      </p>
                    </div>
                  </div>
                  <div class="flex items-start gap-3">
                    <div class="p-1.5 rounded bg-primary/10 mt-0.5">
                      <Radio class="w-3.5 h-3.5 text-primary" />
                    </div>
                    <div>
                      <p class="text-sm font-medium">{{ t('homePage.architecture.highlights.tanstackPatterns.title') }}</p>
                      <p class="text-xs text-muted-foreground">
                        {{ t('homePage.architecture.highlights.tanstackPatterns.description') }}
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
          <h2 class="text-3xl md:text-4xl font-bold mb-3">{{ t('homePage.workflow.title') }}</h2>
          <p class="text-muted-foreground text-lg">
            {{ t('homePage.workflow.subtitle') }}
          </p>
        </div>

        <div class="max-w-5xl mx-auto space-y-4 md:space-y-6">
          <div class="grid md:grid-cols-2 gap-4 md:gap-6">
            <Card :class="[cardInfo, 'border-primary/20 bg-gradient-to-br from-card to-primary/[0.02]']">
              <CardHeader class="pb-3">
                <div class="flex items-center gap-3 mb-2">
                  <div class="p-2 rounded-lg bg-primary/15">
                    <Laptop class="w-4 h-4 text-primary" />
                  </div>
                  <CardTitle class="text-lg">{{ t('homePage.workflow.localhost.title') }}</CardTitle>
                  <span class="text-xs bg-primary/10 text-primary px-2 py-0.5 rounded-full">{{ t('homePage.workflow.localhost.recommended') }}</span>
                </div>
                <CardDescription>
                  {{ t('homePage.workflow.localhost.subtitle') }}
                </CardDescription>
              </CardHeader>
              <CardContent class="space-y-3">
                <div class="bg-muted p-3 rounded font-mono text-xs">
                  <div class="text-foreground">{{ t('homePage.workflow.localhost.url') }}</div>
                </div>
                <ul class="space-y-1.5 text-sm text-muted-foreground">
                  <li v-for="(benefit, idx) in (tm('homePage.workflow.localhost.benefits') as string[])" :key="idx" class="flex items-center gap-2">
                    <span class="text-primary">✓</span> {{ benefit }}
                  </li>
                </ul>
              </CardContent>
            </Card>

            <Card :class="cardInfo">
              <CardHeader class="pb-3">
                <div class="flex items-center gap-3 mb-2">
                  <div class="p-2 rounded-lg bg-primary/10">
                    <Globe class="w-4 h-4 text-primary" />
                  </div>
                  <CardTitle class="text-lg">{{ t('homePage.workflow.tunnel.title') }}</CardTitle>
                </div>
                <CardDescription>
                  {{ t('homePage.workflow.tunnel.subtitle') }}
                </CardDescription>
              </CardHeader>
              <CardContent class="space-y-3">
                <div class="bg-muted p-3 rounded font-mono text-xs">
                  <div class="text-muted-foreground">{{ t('homePage.workflow.tunnel.url') }}</div>
                </div>
                <ul class="space-y-1.5 text-sm text-muted-foreground">
                  <li v-for="(benefit, idx) in (tm('homePage.workflow.tunnel.benefits') as string[])" :key="idx" class="flex items-center gap-2">
                    <span class="text-primary">✓</span> {{ benefit }}
                  </li>
                </ul>
              </CardContent>
            </Card>
          </div>

          <Card :class="cardInfo">
            <CardHeader class="pb-3">
              <div class="flex items-center gap-3 mb-2">
                <div class="p-2 rounded-lg bg-primary/10">
                  <LayoutGrid class="w-4 h-4 text-primary" />
                </div>
                <CardTitle class="text-lg">{{ t('homePage.workflow.gateway.title') }}</CardTitle>
              </div>
              <CardDescription>
                {{ t('homePage.workflow.gateway.subtitle') }}
              </CardDescription>
            </CardHeader>
            <CardContent>
              <p class="text-xs text-muted-foreground">
                {{ t('homePage.workflow.gateway.description') }}
              </p>
            </CardContent>
          </Card>

          <Card :class="[cardInfo, 'border-primary/20 bg-gradient-to-br from-card to-primary/[0.02]']">
            <CardHeader class="pb-3">
              <div class="flex items-center gap-3 mb-2">
                <div class="p-2 rounded-lg bg-primary/15">
                  <Zap class="w-4 h-4 text-primary" />
                </div>
                <CardTitle class="text-lg">{{ t('homePage.workflow.turbopack.title') }}</CardTitle>
              </div>
            </CardHeader>
            <CardContent>
              <div class="grid md:grid-cols-3 gap-4 text-sm">
                <div v-for="(highlight, idx) in (tm('homePage.workflow.turbopack.highlights') as any[])" :key="idx">
                  <p class="font-medium">{{ highlight.title }}</p>
                  <p class="text-xs text-muted-foreground">{{ highlight.description }}</p>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      </section>
    </ScrollReveal>

    <!-- What's Included Section -->
    <ScrollReveal :delay="200">
      <section class="space-y-6 md:space-y-8">
        <div class="text-center">
          <h2 class="text-3xl md:text-4xl font-bold mb-3">{{ t('homePage.included.title') }}</h2>
          <p class="text-muted-foreground text-lg">
            {{ t('homePage.included.subtitle') }}
          </p>
        </div>

        <div class="grid md:grid-cols-3 gap-4 md:gap-6 max-w-5xl mx-auto">
          <Card :class="cardInfo">
            <CardHeader>
              <CardTitle class="text-lg">{{ t('homePage.included.pages.title') }}</CardTitle>
              <CardDescription>{{ t('homePage.included.pages.subtitle') }}</CardDescription>
            </CardHeader>
            <CardContent>
              <ul class="space-y-2 text-sm text-muted-foreground">
                <li v-for="(item, idx) in (tm('homePage.included.pages.items') as string[])" :key="idx">• {{ item }}</li>
              </ul>
            </CardContent>
          </Card>

          <Card :class="cardInfo">
            <CardHeader>
              <CardTitle class="text-lg">{{ t('homePage.included.demos.title') }}</CardTitle>
              <CardDescription>{{ t('homePage.included.demos.subtitle') }}</CardDescription>
            </CardHeader>
            <CardContent>
              <ul class="space-y-2 text-sm text-muted-foreground">
                <li v-for="(item, idx) in (tm('homePage.included.demos.items') as string[])" :key="idx">• {{ item }}</li>
              </ul>
            </CardContent>
          </Card>

          <Card :class="cardInfo">
            <CardHeader>
              <CardTitle class="text-lg">{{ t('homePage.included.auth.title') }}</CardTitle>
              <CardDescription>{{ t('homePage.included.auth.subtitle') }}</CardDescription>
            </CardHeader>
            <CardContent>
              <ul class="space-y-2 text-sm text-muted-foreground">
                <li v-for="(item, idx) in (tm('homePage.included.auth.items') as string[])" :key="idx">• {{ item }}</li>
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
          <h2 class="text-3xl md:text-4xl font-bold mb-3">{{ t('homePage.testing.title') }}</h2>
          <p class="text-muted-foreground text-lg">
            {{ t('homePage.testing.subtitle') }}
          </p>
        </div>

        <div class="max-w-4xl mx-auto">
          <Card :class="[cardInfo, 'border-primary/20 bg-gradient-to-br from-card to-primary/[0.02]']">
            <CardHeader class="pb-3">
              <div class="flex items-center gap-3 mb-2">
                <div class="p-2 rounded-lg bg-primary/15">
                  <FlaskConical class="w-4 h-4 text-primary" />
                </div>
                <CardTitle class="text-lg">{{ t('homePage.testing.title') }}</CardTitle>
              </div>
            </CardHeader>
            <CardContent class="space-y-4">
              <div class="grid md:grid-cols-2 gap-4">
                <div class="space-y-3">
                  <div class="flex items-start gap-3">
                    <div class="p-1.5 rounded bg-primary/10 mt-0.5">
                      <Database class="w-3.5 h-3.5 text-primary" />
                    </div>
                    <div>
                      <p class="text-sm font-medium">{{ t('homePage.testing.items.realPostgres.title') }}</p>
                      <p class="text-xs text-muted-foreground">{{ t('homePage.testing.items.realPostgres.description') }}</p>
                    </div>
                  </div>
                  <div class="flex items-start gap-3">
                    <div class="p-1.5 rounded bg-primary/10 mt-0.5">
                      <Zap class="w-3.5 h-3.5 text-primary" />
                    </div>
                    <div>
                      <p class="text-sm font-medium">{{ t('homePage.testing.items.parallel.title') }}</p>
                      <p class="text-xs text-muted-foreground">{{ t('homePage.testing.items.parallel.description') }}</p>
                    </div>
                  </div>
                </div>
                <div class="space-y-3">
                  <div class="flex items-start gap-3">
                    <div class="p-1.5 rounded bg-primary/10 mt-0.5">
                      <Terminal class="w-3.5 h-3.5 text-primary" />
                    </div>
                    <div>
                      <p class="text-sm font-medium">{{ t('homePage.testing.items.incremental.title') }}</p>
                      <p class="text-xs text-muted-foreground">{{ t('homePage.testing.items.incremental.description') }}</p>
                    </div>
                  </div>
                  <div class="flex items-start gap-3">
                    <div class="p-1.5 rounded bg-primary/10 mt-0.5">
                      <Shield class="w-3.5 h-3.5 text-primary" />
                    </div>
                    <div>
                      <p class="text-sm font-medium">{{ t('homePage.testing.items.isolated.title') }}</p>
                      <p class="text-xs text-muted-foreground">{{ t('homePage.testing.items.isolated.description') }}</p>
                    </div>
                  </div>
                </div>
              </div>

              <div class="bg-muted p-4 rounded-lg font-mono text-xs space-y-2">
                <div class="flex items-center gap-2">
                  <span class="text-primary">$</span>
                  <code class="text-foreground">{{ t('homePage.testing.commands.full') }}</code>
                  <span class="text-muted-foreground ml-2"># {{ t('homePage.testing.commands.fullDesc') }}</span>
                </div>
                <div class="flex items-center gap-2">
                  <span class="text-primary">$</span>
                  <code class="text-foreground">{{ t('homePage.testing.commands.quick') }}</code>
                  <span class="text-muted-foreground ml-2"># {{ t('homePage.testing.commands.quickDesc') }}</span>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      </section>
    </ScrollReveal>

    <!-- Claude Code Section -->
    <ScrollReveal :delay="300">
      <section class="space-y-6 md:space-y-8">
        <div class="text-center">
          <h2 class="text-3xl md:text-4xl font-bold mb-3">
            {{ t('homePage.claudeCode.title') }}
          </h2>
          <p class="text-muted-foreground text-lg">
            {{ t('homePage.claudeCode.subtitle') }}
          </p>
        </div>

        <div class="max-w-5xl mx-auto space-y-4 md:space-y-6">
          <Card :class="cardInfo">
            <CardHeader>
              <CardTitle class="text-xl">{{ t('homePage.claudeCode.orchestration.title') }}</CardTitle>
            </CardHeader>
            <CardContent>
              <div class="bg-muted p-4 rounded-lg font-mono text-xs overflow-x-auto">
                <div class="text-muted-foreground">
                  <span class="text-primary">Layer 0:</span> {{ t('homePage.claudeCode.orchestration.layer0') }}
                </div>
                <div class="text-muted-foreground ml-4">
                  ├── <span class="text-primary">Layer 1:</span> {{ t('homePage.claudeCode.orchestration.layer1') }}
                </div>
                <div class="text-muted-foreground ml-4">
                  ├── <span class="text-primary">Layer 2:</span> {{ t('homePage.claudeCode.orchestration.layer2') }}
                </div>
                <div class="text-muted-foreground ml-4">
                  └── <span class="text-primary">Layer 3:</span> {{ t('homePage.claudeCode.orchestration.layer3') }}
                </div>
              </div>
            </CardContent>
          </Card>

          <div class="grid md:grid-cols-2 gap-4 md:gap-6">
            <Card :class="cardInfo">
              <CardHeader class="pb-3">
                <CardTitle class="text-base">{{ t('homePage.claudeCode.slashCommands.title') }}</CardTitle>
              </CardHeader>
              <CardContent class="space-y-2">
                <div class="grid grid-cols-1 md:grid-cols-2 gap-2 text-xs">
                  <div v-for="(item, key) in (tm('homePage.claudeCode.slashCommands.items') as Record<string, any>)" :key="key">
                    <code class="text-primary">{{ item.cmd }}</code>
                    <p class="text-muted-foreground">{{ item.desc }}</p>
                  </div>
                </div>
              </CardContent>
            </Card>

            <Card :class="cardInfo">
              <CardHeader class="pb-3">
                <CardTitle class="text-base">{{ t('homePage.claudeCode.structuredTasks.title') }}</CardTitle>
              </CardHeader>
              <CardContent class="space-y-3">
                <p class="text-xs text-muted-foreground">
                  {{ t('homePage.claudeCode.structuredTasks.description') }}
                </p>
              </CardContent>
            </Card>

            <Card :class="cardInfo">
              <CardHeader class="pb-3">
                <CardTitle class="text-base">{{ t('homePage.claudeCode.developerAgent.title') }}</CardTitle>
              </CardHeader>
              <CardContent class="space-y-2 text-xs text-muted-foreground">
                <p>{{ (tm('homePage.claudeCode.developerAgent.items') as string[])[0] }}</p>
                <ul class="space-y-1">
                  <li v-for="(item, idx) in (tm('homePage.claudeCode.developerAgent.items') as string[]).slice(1)" :key="idx">
                    • <span class="text-foreground">{{ item }}</span>
                  </li>
                </ul>
              </CardContent>
            </Card>

            <Card :class="cardInfo">
              <CardHeader class="pb-3">
                <CardTitle class="text-base">{{ t('homePage.claudeCode.patternDocs.title') }}</CardTitle>
              </CardHeader>
              <CardContent>
                <div class="flex flex-wrap gap-1.5">
                  <code v-for="(doc, idx) in (tm('homePage.claudeCode.patternDocs.docs') as string[])" :key="idx" class="bg-muted px-1.5 py-0.5 rounded text-xs">{{ doc }}</code>
                </div>
              </CardContent>
            </Card>
          </div>
        </div>
      </section>
    </ScrollReveal>

    <!-- Quick Start Section -->
    <ScrollReveal :delay="400">
      <section class="space-y-6 md:space-y-8">
        <div class="text-center">
          <h2 class="text-3xl md:text-4xl font-bold mb-3">{{ t('homePage.quickStart.title') }}</h2>
          <p class="text-muted-foreground text-lg">
            {{ t('homePage.quickStart.subtitle') }}
          </p>
        </div>

        <div class="max-w-4xl mx-auto space-y-4 md:space-y-6">
          <AnimatedTerminal />

          <div class="grid md:grid-cols-2 gap-4 md:gap-6">
            <Card :class="cardInfo">
              <CardHeader>
                <CardTitle class="text-lg">{{ t('homePage.quickStart.run.title') }}</CardTitle>
                <CardDescription>{{ t('homePage.quickStart.run.subtitle') }}</CardDescription>
              </CardHeader>
              <CardContent class="space-y-4">
                <div class="space-y-3">
                  <div v-for="(step, idx) in (tm('homePage.quickStart.run.steps') as any[])" :key="idx" class="flex gap-3">
                    <span
class="flex-shrink-0 w-6 h-6 rounded-full text-xs flex items-center justify-center font-medium"
                      :class="step.num === 0 ? 'bg-muted text-muted-foreground' : 'bg-primary/10 text-primary'">
                      {{ step.num }}
                    </span>
                    <div class="flex-1">
                      <p class="text-sm font-medium">{{ step.title }}</p>
                      <code v-if="step.code" class="text-xs text-muted-foreground">{{ step.code }}</code>
                      <p v-else class="text-xs text-muted-foreground">{{ step.desc }}</p>
                    </div>
                  </div>
                </div>
                <div class="pt-2 border-t">
                  <p class="text-xs text-muted-foreground">
                    {{ t('homePage.quickStart.run.openAt') }}
                  </p>
                </div>
              </CardContent>
            </Card>

            <Card :class="cardInfo">
              <CardHeader>
                <CardTitle class="text-lg">{{ t('homePage.quickStart.create.title') }}</CardTitle>
                <CardDescription>{{ t('homePage.quickStart.create.subtitle') }}</CardDescription>
              </CardHeader>
              <CardContent class="space-y-4">
                <div class="space-y-3">
                  <div v-for="(step, idx) in (tm('homePage.quickStart.create.steps') as any[])" :key="idx" class="flex gap-3">
                    <span class="flex-shrink-0 w-6 h-6 rounded-full bg-primary/10 text-primary text-xs flex items-center justify-center font-medium">
                      {{ step.num }}
                    </span>
                    <div class="flex-1">
                      <p class="text-sm font-medium">{{ step.title }}</p>
                      <code class="text-xs text-muted-foreground">{{ step.code }}</code>
                    </div>
                  </div>
                </div>
                <div class="pt-2 border-t">
                  <p class="text-xs text-muted-foreground">
                    {{ t('homePage.quickStart.create.seeDetails') }}
                  </p>
                </div>
              </CardContent>
            </Card>
          </div>
        </div>
      </section>
    </ScrollReveal>

    <!-- Footer CTA -->
    <ScrollReveal :delay="500">
      <section>
        <div class="group relative overflow-hidden bg-muted/50 rounded-xl p-8 text-center transition-all duration-300 hover:bg-muted/70 hover:shadow-xl hover:shadow-primary/15">
          <div class="absolute inset-0 rounded-xl bg-gradient-to-r from-primary/0 via-primary/10 to-primary/0 opacity-0 group-hover:opacity-100 transition-opacity duration-500" />

          <div class="relative space-y-4">
            <h3 class="text-2xl font-bold">{{ t('homePage.cta.title') }}</h3>
            <div class="flex flex-col sm:flex-row gap-3 justify-center pt-2">
              <Button
                :as-child="true"
                size="lg"
                :class="btnPrimary"
              >
                <RouterLink to="/demo">
                  <span class="hidden sm:inline">{{ t('homePage.cta.tryDemos') }}: {{ t('homePage.cta.demoSubtitle') }}</span>
                  <span class="sm:hidden">{{ t('homePage.cta.tryDemos') }}</span>
                  <ArrowRight class="w-4 h-4 ml-2 transition-transform duration-300 group-hover:translate-x-1" />
                </RouterLink>
              </Button>
              <Button :as-child="true" variant="outline" size="lg" :class="btnSecondary">
                <RouterLink to="/profile">
                  <span class="hidden sm:inline">{{ t('homePage.cta.testAuth') }}: {{ t('homePage.cta.authSubtitle') }}</span>
                  <span class="sm:hidden">{{ t('homePage.cta.testAuth') }}</span>
                </RouterLink>
              </Button>
            </div>
          </div>
        </div>
      </section>
    </ScrollReveal>

    <!-- Footer Credits -->
    <footer class="text-center py-6 text-sm text-muted-foreground">
      Vue Template •
      <a
        href="https://react.antonchaynik.ru"
        target="_blank"
        rel="noopener noreferrer"
        class="text-primary hover:underline"
      >
        React version also available
      </a>
    </footer>
  </div>
</template>
