<script setup lang="ts">
import { useI18n } from 'vue-i18n'

import LoadingDemo from '@app/presentation/components/demo/LoadingDemo.vue'
import ErrorDemo from '@app/presentation/components/demo/ErrorDemo.vue'
import CacheDemo from '@app/presentation/components/demo/CacheDemo.vue'
import OptimisticDemo from '@app/presentation/components/demo/OptimisticDemo.vue'
import ThemeDemo from '@app/presentation/components/demo/ThemeDemo.vue'
import I18nDemo from '@app/presentation/components/demo/I18nDemo.vue'
import InfiniteScrollDemo from '@app/presentation/components/demo/InfiniteScrollDemo.vue'
import PrefetchDemo from '@app/presentation/components/demo/PrefetchDemo.vue'
import PollingDemo from '@app/presentation/components/demo/PollingDemo.vue'
import NetworkStatusDemo from '@app/presentation/components/demo/NetworkStatusDemo.vue'
import SuspenseDemo from '@app/presentation/components/demo/SuspenseDemo.vue'
import ParallelQueriesDemo from '@app/presentation/components/demo/ParallelQueriesDemo.vue'
import MutationComparisonDemo from '@app/presentation/components/demo/MutationComparisonDemo.vue'
import HttpStatusDemo from '@app/presentation/components/demo/HttpStatusDemo.vue'
import RetryComparisonDemo from '@app/presentation/components/demo/RetryComparisonDemo.vue'
import WebSocketDemo from '@app/presentation/components/demo/WebSocketDemo.vue'
import AiStreamingDemo from '@app/presentation/components/demo/AiStreamingDemo.vue'
import ScrollReveal from '@/components/ui/animation/ScrollReveal.vue'

const { t } = useI18n()

const animBase =
  'motion-opacity-in-[0%] motion-translate-y-in-[20px] motion-blur-in-[3px] motion-duration-[0.4s] motion-duration-[0.6s]/blur motion-ease-spring-smooth'
</script>

<template>
  <div class="py-6 space-y-4">
    <!-- Header with blur-in effect (#1, #2) -->
    <div class="text-center mb-8">
      <h1
        class="text-2xl font-bold mb-2 motion-blur-in-[6px] motion-scale-in-[0.95] motion-opacity-in-[0%] motion-duration-[0.5s] motion-duration-[0.7s]/blur motion-ease-spring-smooth"
      >
        {{ t('demo.title') }}
      </h1>
      <p
        class="text-muted-foreground motion-blur-in-[4px] motion-opacity-in-[0%] motion-duration-[0.4s] motion-delay-[0.15s] motion-ease-spring-smooth"
      >
        {{ t('demo.subtitle') }}
      </p>
    </div>

    <!-- Row 1: Loading + Error (2 cols) -->
    <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
      <div :class="[animBase, 'motion-delay-[0.1s]']">
        <LoadingDemo />
      </div>
      <div :class="[animBase, 'motion-delay-[0.15s]']">
        <ErrorDemo />
      </div>
    </div>

    <!-- Row 1.5: Error Handling Deep Dive (2 cols) -->
    <ScrollReveal :delay="0">
      <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
        <HttpStatusDemo />
        <RetryComparisonDemo />
      </div>
    </ScrollReveal>

    <!-- Row 2: Cache (full width) -->
    <ScrollReveal :delay="100">
      <CacheDemo />
    </ScrollReveal>

    <!-- Row 3: InfiniteScroll + Prefetch (2 cols) -->
    <ScrollReveal :delay="200">
      <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
        <InfiniteScrollDemo />
        <PrefetchDemo />
      </div>
    </ScrollReveal>

    <!-- Row 4: Polling + NetworkStatus (2 cols) -->
    <ScrollReveal :delay="300">
      <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
        <PollingDemo />
        <NetworkStatusDemo />
      </div>
    </ScrollReveal>

    <!-- Row 5: ParallelQueries (full width) -->
    <ScrollReveal :delay="400">
      <ParallelQueriesDemo />
    </ScrollReveal>

    <!-- Row 6: Suspense + MutationComparison (2 cols) -->
    <ScrollReveal :delay="500">
      <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
        <SuspenseDemo />
        <MutationComparisonDemo />
      </div>
    </ScrollReveal>

    <!-- Row 7: OptimisticUpdates (full width) -->
    <ScrollReveal :delay="600">
      <OptimisticDemo />
    </ScrollReveal>

    <!-- Row 8: Theme + I18n (2 cols) -->
    <ScrollReveal :delay="700">
      <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
        <ThemeDemo />
        <I18nDemo />
      </div>
    </ScrollReveal>

    <!-- Row 9: WebSocket + AI Streaming (2 cols) -->
    <ScrollReveal :delay="800">
      <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
        <WebSocketDemo />
        <AiStreamingDemo />
      </div>
    </ScrollReveal>

    <!-- CTA card with bounce entrance (#12) and hover glow (#19) -->
    <ScrollReveal :delay="900">
      <div
        class="group bg-muted/50 rounded-xl p-4 text-center transition-all duration-300 hover:bg-muted/70 hover:shadow-lg hover:shadow-primary/10"
      >
        <p class="text-sm text-muted-foreground mb-2">
          {{ t('demo.ctaText') }}
        </p>
        <router-link
          to="/profile"
          class="text-primary hover:underline font-medium inline-flex items-center gap-1"
        >
          {{ t('demo.ctaLink') }}
          <!-- CTA arrow wiggle (#6) -->
          <span
            class="inline-block transition-transform duration-200 group-hover:translate-x-1 group-hover:motion-preset-wiggle-sm"
          >
            &rarr;
          </span>
        </router-link>
      </div>
    </ScrollReveal>
  </div>
</template>
