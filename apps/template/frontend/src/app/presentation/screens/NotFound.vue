<script setup lang="ts">
import { RouterLink } from 'vue-router';
import { Button } from '@/components/ui/button';
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
</script>

<template>
  <div class="flex min-h-screen items-center justify-center p-4">
    <Card class="w-full max-w-md">
      <CardHeader class="text-center">
        <CardTitle class="text-4xl">404</CardTitle>
        <CardDescription>Page not found</CardDescription>
      </CardHeader>
      <CardContent class="text-center">
        <p class="text-muted-foreground mb-4 text-sm">
          The page you're looking for doesn't exist.
        </p>
        <Button as-child>
          <RouterLink to="/">Go Home</RouterLink>
        </Button>
      </CardContent>
    </Card>
  </div>
</template>
