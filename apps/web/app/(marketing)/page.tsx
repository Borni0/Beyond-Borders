import Link from "next/link";

import { Button } from "@/components/ui/Button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/Card";

const FEATURES = [
  {
    title: "Financial Readiness Calculator",
    body: "Estimate total study cost, available funding, and your upfront cash gap before you commit.",
  },
  {
    title: "Living Expense Calculator",
    body: "Estimate the recurring cost of living in your target city and build a realistic monthly baseline.",
  },
  {
    title: "Financial Weather",
    body: "Stress-test adverse changes to exchange rates, rent, scholarships, and family support.",
  },
  {
    title: "Decision Studio",
    body: "Compare up to three study-abroad plans side by side with consistent assumptions.",
  },
  {
    title: "Financial Timeline",
    body: "Schedule application fees, deposits, insurance, rent, and tuition in one chronological view.",
  },
  {
    title: "Finance Copilot",
    body: "Ask plain-language questions about your saved plan. Answers cite the underlying numbers.",
  },
  {
    title: "Sources & Assumptions",
    body: "Every important input is labelled: verified source, planning estimate, or your own value.",
  },
];

export default function HomePage() {
  return (
    <main className="mx-auto max-w-6xl px-6 py-16">
      <header className="flex flex-col gap-8">
        <nav className="flex items-center justify-between">
          <Link href="/" className="flex items-center gap-2 text-lg font-semibold">
            <span aria-hidden="true" className="inline-block h-6 w-6 rounded-md bg-teal" />
            Beyond Borders
          </Link>
          <div className="flex items-center gap-3">
            <Link href="/sign-in">
              <Button variant="ghost">Sign in</Button>
            </Link>
            <Link href="/sign-up">
              <Button>Get started</Button>
            </Link>
          </div>
        </nav>

        <section className="flex flex-col items-start gap-6 py-12">
          <p className="rounded-full bg-mint px-3 py-1 text-xs font-medium uppercase tracking-wide text-teal-dark">
            For international students
          </p>
          <h1 className="max-w-3xl text-4xl font-semibold leading-tight text-midnight sm:text-5xl">
            Your global education journey starts with financial clarity.
          </h1>
          <p className="max-w-2xl text-base text-slate">
            Beyond Borders helps you understand whether studying abroad is
            financially feasible, prepare for uncertainty, and manage your
            money once you arrive — without making promises it can't keep.
          </p>
          <div className="flex flex-col gap-3 sm:flex-row">
            <Link href="/sign-up">
              <Button size="lg">Check My Financial Readiness</Button>
            </Link>
            <Link href="/sign-in">
              <Button size="lg" variant="secondary">
                I already have an account
              </Button>
            </Link>
          </div>
        </section>
      </header>

      <section aria-labelledby="how-it-works" className="mt-16 flex flex-col gap-6">
        <h2 id="how-it-works" className="text-2xl font-semibold text-midnight">
          How it works
        </h2>
        <ol className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {[
            "Enter your study plan",
            "Add costs and funding",
            "See your funding gap",
            "Stress-test and compare",
          ].map((step, idx) => (
            <li key={step}>
              <Card>
                <CardHeader>
                  <p className="text-xs font-medium uppercase text-teal">Step {idx + 1}</p>
                  <CardTitle>{step}</CardTitle>
                </CardHeader>
              </Card>
            </li>
          ))}
        </ol>
      </section>

      <section aria-labelledby="features" className="mt-16 flex flex-col gap-6">
        <h2 id="features" className="text-2xl font-semibold text-midnight">
          What's included
        </h2>
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {FEATURES.map((f) => (
            <Card key={f.title}>
              <CardHeader>
                <CardTitle>{f.title}</CardTitle>
                <CardDescription>{f.body}</CardDescription>
              </CardHeader>
              <CardContent>
                <p className="text-xs text-slate">Available now in this build.</p>
              </CardContent>
            </Card>
          ))}
        </div>
      </section>

      <footer className="mt-24 border-t border-border pt-8 text-xs text-slate">
        <p>
          Beyond Borders is a financial planning tool, not a bank. All figures
          are estimates based on the inputs you provide.
        </p>
      </footer>
    </main>
  );
}