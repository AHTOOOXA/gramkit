'use client';

import type { ReactNode } from 'react';
import { useTranslations } from 'next-intl';

import { Link } from '@/i18n/navigation';
import { useAuth, useScrollReveal } from '@/hooks';
import { cn } from '@/lib/utils';
import {
  LoadingDemo,
  ErrorDemo,
  CacheDemo,
  OptimisticDemo,
  ThemeDemo,
  I18nDemo,
  InfiniteScrollDemo,
  PrefetchDemo,
  PollingDemo,
  NetworkStatusDemo,
  SuspenseDemo,
  ParallelQueriesDemo,
  MutationComparisonDemo,
  HttpStatusDemo,
  RetryComparisonDemo,
  WebSocketDemo,
  AiStreamingDemo,
} from '@/components/demo';

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

export default function DemoPage() {
  const t = useTranslations('demo');
  const { isAuthenticated } = useAuth();

  return (
    <div className="py-6 space-y-4">
      {/* Header - Hero moment with dramatic emphasis */}
      <div className="text-center mb-6">
        <h1 className="text-2xl font-bold mb-2 motion-blur-in-[10px] motion-scale-in-[0.95] motion-opacity-in-[0%] motion-duration-[0.7s] motion-duration-[1s]/blur motion-ease-spring-smooth">
          {t('title')}
        </h1>
        <p className="text-muted-foreground motion-blur-in-[5px] motion-opacity-in-[0%] motion-translate-y-in-[10px] motion-duration-[0.5s] motion-delay-[0.25s] motion-ease-spring-smooth">
          {t('subtitle')}
        </p>
      </div>

      {/* Row 1: Basic Query Patterns - 2 columns */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="motion-opacity-in-[0%] motion-translate-y-in-[30px] motion-blur-in-[4px] motion-duration-[0.5s] motion-delay-[0.35s] motion-ease-spring-smooth">
          <LoadingDemo />
        </div>
        <div className="motion-opacity-in-[0%] motion-translate-y-in-[30px] motion-blur-in-[4px] motion-duration-[0.5s] motion-delay-[0.45s] motion-ease-spring-smooth">
          <ErrorDemo />
        </div>
      </div>

      {/* Row 1.5: Error Handling Deep Dive - 2 columns */}
      <ScrollReveal delay={0}>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <HttpStatusDemo />
          <RetryComparisonDemo />
        </div>
      </ScrollReveal>

      {/* Row 2: Cache - full width (scale animation) */}
      <ScrollReveal delay={100}>
        <CacheDemo />
      </ScrollReveal>

      {/* Row 3: Data Loading Patterns - 2 columns */}
      <ScrollReveal delay={200}>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <InfiniteScrollDemo />
          <PrefetchDemo />
        </div>
      </ScrollReveal>

      {/* Row 4: Live Data - 2x2 grid */}
      <ScrollReveal delay={300}>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <PollingDemo />
          <WebSocketDemo />
          <AiStreamingDemo />
          <NetworkStatusDemo />
        </div>
      </ScrollReveal>

      {/* Row 5: Parallel Queries - full width */}
      <ScrollReveal delay={400}>
        <ParallelQueriesDemo />
      </ScrollReveal>

      {/* Row 6: Advanced Patterns - 2 columns */}
      <ScrollReveal delay={500}>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <SuspenseDemo />
          <MutationComparisonDemo />
        </div>
      </ScrollReveal>

      {/* Row 7: Optimistic Updates - full width */}
      <ScrollReveal delay={600}>
        <OptimisticDemo />
      </ScrollReveal>

      {/* Row 8: App Features - 2 columns */}
      <ScrollReveal delay={700}>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <ThemeDemo />
          <I18nDemo />
        </div>
      </ScrollReveal>

      {/* CTA - Final flourish with glow effect */}
      <ScrollReveal delay={800}>
        <div className="group relative overflow-hidden bg-muted/50 rounded-xl p-4 text-center transition-all duration-300 hover:bg-muted/70 hover:shadow-xl hover:shadow-primary/15">
          {/* Animated border glow on hover */}
          <div className="absolute inset-0 rounded-xl bg-gradient-to-r from-primary/0 via-primary/10 to-primary/0 opacity-0 group-hover:opacity-100 transition-opacity duration-500" />

          <p className="relative text-sm text-muted-foreground mb-2">
            {isAuthenticated ? 'Want to manage your account?' : 'Ready to try the auth system?'}
          </p>
          <Link
            href={isAuthenticated ? '/profile' : '/login'}
            className="relative text-primary hover:underline font-medium inline-flex items-center gap-1"
          >
            {isAuthenticated ? 'Manage your profile' : 'Create your account'}{' '}
            <span className="inline-block transition-transform duration-300 group-hover:translate-x-2">
              &rarr;
            </span>
          </Link>
        </div>
      </ScrollReveal>
    </div>
  );
}
