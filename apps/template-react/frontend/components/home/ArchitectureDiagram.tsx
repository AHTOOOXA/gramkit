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
          name: 'template-react/',
          description: 'Next.js starter template (you are here)',
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
              description: 'Next.js application',
              icon: '✨',
              children: [
                { name: 'app/[locale]/', description: 'Next.js pages (i18n)', icon: '📂' },
                { name: 'components/', description: 'React components', icon: '📂' },
                { name: 'hooks/', description: 'Custom hooks & queries', icon: '📂' },
                { name: 'gen/', description: 'Auto-generated API client', icon: '📂' },
              ],
            },
          ],
        },
        {
          name: 'template-vue/',
          description: 'Vue starter template',
          icon: '💚',
          link: 'https://vue.antonchaynik.ru',
        },
        {
          name: 'your-new-app/',
          description: '← Clone template-react to start',
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
          name: 'frontend-react/src/',
          description: 'React shared components',
          icon: '📂',
          children: [
            { name: 'components/', description: 'Shared UI components', icon: '📂' },
            { name: 'hooks/', description: 'Shared hooks', icon: '📂' },
            { name: 'stores/', description: 'Shared Zustand stores', icon: '📂' },
          ],
        },
      ],
    },
  ],
};

function TreeRow({
  node,
  isLast = true,
  prefix = '',
  isRoot = false,
}: {
  node: TreeNode;
  isLast?: boolean;
  prefix?: string;
  isRoot?: boolean;
}) {
  const hasChildren = node.children && node.children.length > 0;
  const linePrefix = isRoot ? '' : prefix + (isLast ? '└── ' : '├── ');
  const childPrefix = isRoot ? '' : prefix + (isLast ? '    ' : '│   ');

  return (
    <>
      {/* Mobile: tree only */}
      <div className="md:hidden py-0.5">
        <span className="text-muted-foreground/60 whitespace-pre">{linePrefix}</span>
        {node.link ? (
          <a href={node.link} target="_blank" rel="noopener noreferrer" className="text-primary hover:underline">
            {node.icon} {node.name}
          </a>
        ) : (
          <>{node.icon} {node.name}</>
        )}
      </div>

      {/* Desktop: tree + inline description */}
      <div className="hidden md:flex py-0.5">
        <span className="whitespace-pre flex-shrink-0">
          <span className="text-muted-foreground/60">{linePrefix}</span>
          {node.link ? (
            <a href={node.link} target="_blank" rel="noopener noreferrer" className="text-primary hover:underline">
              {node.icon} {node.name}
            </a>
          ) : (
            <>{node.icon} {node.name}</>
          )}
        </span>
        <span className="text-muted-foreground text-xs ml-4 truncate">
          {node.description}
        </span>
      </div>

      {hasChildren &&
        node.children?.map((child, index) => (
          <TreeRow
            key={child.name}
            node={child}
            isLast={index === (node.children?.length ?? 0) - 1}
            prefix={childPrefix}
          />
        ))}
    </>
  );
}

export function ArchitectureDiagram() {
  return (
    <div className="bg-muted/50 p-3 md:p-4 rounded-lg border border-border font-mono text-xs md:text-sm overflow-x-auto">
      <TreeRow node={TREE_DATA} isRoot />
    </div>
  );
}
