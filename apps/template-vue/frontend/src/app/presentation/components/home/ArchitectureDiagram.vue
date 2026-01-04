<script setup lang="ts">
import { computed } from 'vue';

interface TreeNode {
  name: string;
  description: string;
  children?: TreeNode[];
  icon?: string;
  link?: string;
}

const TREE_DATA: TreeNode = {
  name: '.',
  description: 'Monorepo root',
  icon: '📦',
  children: [
    {
      name: 'apps/',
      description: 'Application packages',
      icon: '📁',
      children: [
        {
          name: 'template/',
          description: 'Vue starter template (you are here)',
          icon: '📂',
          children: [
            {
              name: 'backend/',
              description: 'FastAPI application',
              icon: '⚙️',
              children: [
                { name: 'migrations/', description: 'Alembic migrations', icon: '📂' },
                {
                  name: 'src/app/',
                  description: 'Application code',
                  icon: '📂',
                  children: [
                    { name: 'schemas/', description: 'Pydantic schemas', icon: '📂' },
                    { name: 'services/', description: 'Business logic', icon: '📂' },
                    { name: 'webhook/', description: 'FastAPI routers & deps', icon: '📂' },
                    { name: 'worker/', description: 'Background jobs', icon: '📂' },
                  ],
                },
              ],
            },
            {
              name: 'frontend/',
              description: 'Vue application',
              icon: '✨',
              children: [
                { name: 'src/app/', description: 'App code (composables, store)', icon: '📂' },
                { name: 'src/components/', description: 'Vue components', icon: '📂' },
                { name: 'src/gen/', description: 'Auto-generated API client', icon: '📂' },
              ],
            },
          ],
        },
        {
          name: 'template-react/',
          description: 'React/Next.js starter template',
          icon: '💙',
          link: 'https://react.antonchaynik.ru',
        },
        {
          name: 'your-new-app/',
          description: '← Clone template to start',
          icon: '🚀',
        },
      ],
    },
    {
      name: 'core/',
      description: 'Shared packages',
      icon: '🔧',
      children: [
        {
          name: 'backend/src/core/',
          description: 'Python shared code',
          icon: '📂',
          children: [
            { name: 'auth/', description: 'Auth service & JWT', icon: '📂' },
            { name: 'models/', description: 'SQLAlchemy base models', icon: '📂' },
            { name: 'repos/', description: 'Repository pattern base', icon: '📂' },
            { name: 'services/', description: 'Base services', icon: '📂' },
            { name: 'telegram/', description: 'Telegram integration', icon: '📂' },
          ],
        },
        {
          name: 'frontend-vue/src/',
          description: 'Vue shared components',
          icon: '📂',
          children: [
            { name: 'components/', description: 'Shared UI components', icon: '📂' },
            { name: 'composables/', description: 'Shared composables', icon: '📂' },
          ],
        },
      ],
    },
  ],
};

const renderTree = (node: TreeNode, isLast = true, prefix = '', isRoot = false): string[] => {
  const lines: string[] = [];
  const hasChildren = node.children && node.children.length > 0;
  const linePrefix = isRoot ? '' : prefix + (isLast ? '└── ' : '├── ');
  const childPrefix = isRoot ? '' : prefix + (isLast ? '    ' : '│   ');

  // Create the line for this node
  const line = {
    prefix: linePrefix,
    icon: node.icon || '',
    name: node.name,
    description: node.description,
    link: node.link,
  };

  lines.push(JSON.stringify(line));

  // Recursively render children
  if (hasChildren && node.children) {
    node.children.forEach((child, index) => {
      const isLastChild = index === node.children!.length - 1;
      lines.push(...renderTree(child, isLastChild, childPrefix, false));
    });
  }

  return lines;
};

const treeLines = computed(() => {
  return renderTree(TREE_DATA, true, '', true).map(line => JSON.parse(line));
});
</script>

<template>
  <div class="bg-muted/50 p-3 md:p-4 rounded-lg border border-border font-mono text-xs md:text-sm overflow-x-auto">
    <div v-for="(line, index) in treeLines" :key="index">
      <!-- Mobile: tree only -->
      <div class="md:hidden py-0.5">
        <span class="text-muted-foreground/60 whitespace-pre">{{ line.prefix }}</span>
        <a v-if="line.link" :href="line.link" target="_blank" rel="noopener noreferrer" class="text-primary hover:underline">
          {{ line.icon }} {{ line.name }}
        </a>
        <template v-else>{{ line.icon }} {{ line.name }}</template>
      </div>

      <!-- Desktop: tree + inline description -->
      <div class="hidden md:flex py-0.5">
        <span class="whitespace-pre flex-shrink-0">
          <span class="text-muted-foreground/60">{{ line.prefix }}</span>
          <a v-if="line.link" :href="line.link" target="_blank" rel="noopener noreferrer" class="text-primary hover:underline">
            {{ line.icon }} {{ line.name }}
          </a>
          <template v-else>{{ line.icon }} {{ line.name }}</template>
        </span>
        <span class="text-muted-foreground text-xs ml-4 truncate">
          {{ line.description }}
        </span>
      </div>
    </div>
  </div>
</template>
