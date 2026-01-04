interface DemoSectionProps {
  icon: string;
  title: string;
  children: React.ReactNode;
}

export function DemoSection({ icon, title, children }: DemoSectionProps) {
  return (
    // Card hover lift with enhanced depth and subtle gradient
    // h-full + flex ensures equal height cards in grid layouts
    // group enables child animations on card hover
    <section className="group h-full flex flex-col bg-card rounded-xl border p-4 transition-all duration-300 ease-out hover:shadow-2xl hover:shadow-primary/10 hover:-translate-y-1.5 hover:scale-[1.01] hover:border-primary/30 hover:bg-gradient-to-br hover:from-card hover:to-primary/[0.02] motion-reduce:transition-none motion-reduce:hover:transform-none">
      <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
        {/* Floating icon - speeds up and scales on card hover */}
        <span className="inline-block motion-preset-oscillate-sm motion-duration-[3s] motion-loop-infinite transition-transform duration-200 group-hover:scale-110 group-hover:motion-duration-[1.5s]">
          {icon}
        </span>
        <span>{title}</span>
      </h2>
      <div className="flex-1">{children}</div>
    </section>
  );
}
