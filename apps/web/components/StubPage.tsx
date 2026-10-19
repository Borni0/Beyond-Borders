import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/Card";

interface StubPageProps {
  title: string;
  description: string;
  phase: 2 | 3 | 4 | 5 | 6;
}

export function StubPage({ title, description, phase }: StubPageProps) {
  return (
    <div className="flex flex-col gap-8">
      <header className="flex flex-col gap-1">
        <h1 className="text-3xl font-semibold text-midnight">{title}</h1>
        <p className="text-sm text-slate">{description}</p>
      </header>
      <Card>
        <CardHeader>
          <CardTitle>Coming in Phase {phase}</CardTitle>
          <CardDescription>
            The navigation, design tokens, and data shapes for this page are
            already in place. The feature itself ships in a later phase per the
            spec roadmap (§16).
          </CardDescription>
        </CardHeader>
        <CardContent>
          <p className="text-xs text-slate">
            Until then, the overview and settings pages are fully functional.
          </p>
        </CardContent>
      </Card>
    </div>
  );
}