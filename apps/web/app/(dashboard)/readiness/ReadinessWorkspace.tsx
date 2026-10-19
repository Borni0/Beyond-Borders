"use client";

/**
 * Financial Readiness workspace.
 *
 * The user picks (or creates) a plan, then edits:
 *   - plan basics (name, currency, dates)
 *   - costs (one-time, recurring, refundable deposits)
 *   - funding sources (savings, scholarships, etc.)
 *   - FX rates for any non-base currency used
 * And sees a live readiness panel that re-derives on every change.
 *
 * To keep this self-contained, the workspace runs as one big client
 * component and refetches readiness whenever any of the four lists
 * changes. Server-side data fetching happens in the parent server
 * component (`page.tsx`) and is hydrated as the initial state.
 */

import * as React from "react";
import { Plus, Trash2, AlertCircle } from "lucide-react";

import { Button } from "@/components/ui/Button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/Card";
import { Field, Input } from "@/components/ui/Input";
import { ReadinessPanel } from "@/components/readiness/ReadinessPanel";
import {
  costsApi,
  fundingApi,
  fxApi,
  readinessApi,
  studyPlansApi,
} from "@/lib/readiness-api";
import { formatDate, formatMoney, toDateInputValue } from "@/lib/format";
import { ApiClientError } from "@/lib/client-api";

import type {
  CostItem,
  CostItemCreate,
  CostCategory,
  ExchangeRate,
  Frequency,
  FundingSource,
  FundingSourceCreate,
  FundingStatus,
  FundingType,
  RateType,
  ReadinessResult,
  StudyPlan,
  StudyPlanCreate,
} from "@beyond-borders/shared-types";

interface Props {
  initialPlans: StudyPlan[];
  initialPlanId: string | null;
}

const CATEGORIES: CostCategory[] = [
  "tuition", "accommodation", "food", "transport", "utilities",
  "insurance", "travel", "visa", "deposits", "study_materials",
  "personal", "miscellaneous",
];
const FREQUENCIES: Frequency[] = [
  "one_time", "monthly", "quarterly", "semester", "annual",
];
const FUNDING_TYPES: FundingType[] = [
  "savings", "family", "scholarship", "loan", "income", "other",
];
const FUNDING_STATUSES: FundingStatus[] = [
  "confirmed", "conditional", "expected", "unavailable",
];
const RATE_TYPES: RateType[] = ["reference", "provider_quote", "user_entered"];

const DESTINATION_COUNTRIES = Array.from(
  new Map(
    [
      { value: "US", label: "United States" },
      { value: "CA", label: "Canada" },
      { value: "GB", label: "United Kingdom" },
      { value: "IE", label: "Ireland" },
      { value: "AU", label: "Australia" },
      { value: "NZ", label: "New Zealand" },
      { value: "DE", label: "Germany" },
      { value: "FR", label: "France" },
      { value: "ES", label: "Spain" },
      { value: "IT", label: "Italy" },
      { value: "NL", label: "Netherlands" },
      { value: "BE", label: "Belgium" },
      { value: "AT", label: "Austria" },
      { value: "CH", label: "Switzerland" },
      { value: "SE", label: "Sweden" },
      { value: "NO", label: "Norway" },
      { value: "DK", label: "Denmark" },
      { value: "FI", label: "Finland" },
      { value: "PT", label: "Portugal" },
      { value: "GR", label: "Greece" },
      { value: "PL", label: "Poland" },
      { value: "CZ", label: "Czech Republic" },
      { value: "HU", label: "Hungary" },
      { value: "RO", label: "Romania" },
      { value: "BG", label: "Bulgaria" },
      { value: "TR", label: "Turkey" },
      { value: "AE", label: "United Arab Emirates" },
      { value: "SA", label: "Saudi Arabia" },
      { value: "QA", label: "Qatar" },
      { value: "KW", label: "Kuwait" },
      { value: "OM", label: "Oman" },
      { value: "BH", label: "Bahrain" },
      { value: "JP", label: "Japan" },
      { value: "KR", label: "South Korea" },
      { value: "CN", label: "China" },
      { value: "SG", label: "Singapore" },
      { value: "MY", label: "Malaysia" },
      { value: "TH", label: "Thailand" },
      { value: "VN", label: "Vietnam" },
      { value: "ID", label: "Indonesia" },
      { value: "PH", label: "Philippines" },
      { value: "IN", label: "India" },
      { value: "PK", label: "Pakistan" },
      { value: "BD", label: "Bangladesh" },
      { value: "LK", label: "Sri Lanka" },
      { value: "NP", label: "Nepal" },
      { value: "ZA", label: "South Africa" },
      { value: "EG", label: "Egypt" },
      { value: "MA", label: "Morocco" },
      { value: "DZ", label: "Algeria" },
      { value: "TN", label: "Tunisia" },
      { value: "NG", label: "Nigeria" },
      { value: "GH", label: "Ghana" },
      { value: "KE", label: "Kenya" },
      { value: "MU", label: "Mauritius" },
      { value: "AR", label: "Argentina" },
      { value: "BR", label: "Brazil" },
      { value: "CL", label: "Chile" },
      { value: "CO", label: "Colombia" },
      { value: "PE", label: "Peru" },
      { value: "MX", label: "Mexico" },
      { value: "UY", label: "Uruguay" },
      { value: "EC", label: "Ecuador" },
      { value: "CR", label: "Costa Rica" },
      { value: "PA", label: "Panama" },
      { value: "GT", label: "Guatemala" },
      { value: "DO", label: "Dominican Republic" },
      { value: "PR", label: "Puerto Rico" },
      { value: "RU", label: "Russia" },
      { value: "UA", label: "Ukraine" },
      { value: "BY", label: "Belarus" },
      { value: "LT", label: "Lithuania" },
      { value: "LV", label: "Latvia" },
      { value: "EE", label: "Estonia" },
      { value: "IS", label: "Iceland" },
      { value: "RS", label: "Serbia" },
      { value: "HR", label: "Croatia" },
      { value: "SI", label: "Slovenia" },
      { value: "SK", label: "Slovakia" },
      { value: "LU", label: "Luxembourg" },
      { value: "MT", label: "Malta" },
      { value: "CY", label: "Cyprus" },
      { value: "AL", label: "Albania" },
      { value: "MK", label: "North Macedonia" },
      { value: "ME", label: "Montenegro" },
      { value: "AM", label: "Armenia" },
      { value: "GE", label: "Georgia" },
      { value: "AZ", label: "Azerbaijan" },
      { value: "KZ", label: "Kazakhstan" },
      { value: "UZ", label: "Uzbekistan" },
      { value: "MN", label: "Mongolia" },
      { value: "IL", label: "Israel" },
      { value: "IR", label: "Iran" },
      { value: "IQ", label: "Iraq" },
      { value: "JO", label: "Jordan" },
      { value: "LB", label: "Lebanon" },
      { value: "SY", label: "Syria" },
      { value: "YE", label: "Yemen" },
      { value: "TZ", label: "Tanzania" },
      { value: "UG", label: "Uganda" },
      { value: "RW", label: "Rwanda" },
    ].map((country) => [country.value, country] as const),
  ).values(),
);

const CITY_OPTIONS = Array.from(new Set([
  "Berlin",
  "London",
  "Manchester",
  "Birmingham",
  "Leeds",
  "Glasgow",
  "Edinburgh",
  "Paris",
  "Lyon",
  "Marseille",
  "Amsterdam",
  "Rotterdam",
  "Brussels",
  "Copenhagen",
  "Stockholm",
  "Oslo",
  "Helsinki",
  "Vienna",
  "Zurich",
  "Geneva",
  "Basel",
  "Munich",
  "Hamburg",
  "Frankfurt",
  "Dublin",
  "Barcelona",
  "Madrid",
  "Valencia",
  "Lisbon",
  "Porto",
  "Rome",
  "Milan",
  "Naples",
  "Athens",
  "Prague",
  "Warsaw",
  "Budapest",
  "Bucharest",
  "Istanbul",
  "Toronto",
  "Montreal",
  "Vancouver",
  "Calgary",
  "Ottawa",
  "Halifax",
  "New York",
  "Boston",
  "Chicago",
  "Los Angeles",
  "San Francisco",
  "Seattle",
  "Austin",
  "Miami",
  "Houston",
  "Dallas",
  "Atlanta",
  "Philadelphia",
  "Sydney",
  "Melbourne",
  "Brisbane",
  "Perth",
  "Adelaide",
  "Auckland",
  "Singapore",
  "Kuala Lumpur",
  "Bangkok",
  "Tokyo",
  "Kyoto",
  "Osaka",
  "Seoul",
  "Busan",
  "Shanghai",
  "Beijing",
  "Hong Kong",
  "Dubai",
  "Abu Dhabi",
  "Doha",
  "Riyadh",
  "Jeddah",
  "Johannesburg",
  "Cape Town",
  "Nairobi",
  "Lagos",
  "Cairo",
  "Casablanca",
  "São Paulo",
  "Rio de Janeiro",
  "Buenos Aires",
  "Santiago",
  "Mexico City",
  "Bogotá",
  "Lima",
  "Delhi",
  "Mumbai",
  "Bengaluru",
  "Hyderabad",
  "Chennai",
  "Kolkata",
  "Dhaka",
  "Hanoi",
  "Ho Chi Minh City",
]));

const INSTITUTION_OPTIONS = Array.from(new Set([
  "University of Oxford",
  "University of Cambridge",
  "Imperial College London",
  "London School of Economics and Political Science",
  "University College London",
  "University of Toronto",
  "University of British Columbia",
  "McGill University",
  "University of Melbourne",
  "University of Sydney",
  "Australian National University",
  "University of Queensland",
  "Monash University",
  "University of Auckland",
  "Technische Universität Berlin",
  "Ludwig Maximilian University of Munich",
  "University of Hamburg",
  "University of Heidelberg",
  "Sorbonne University",
  "École Polytechnique",
  "University of Amsterdam",
  "Delft University of Technology",
  "ETH Zurich",
  "University of Zurich",
  "University of Copenhagen",
  "KTH Royal Institute of Technology",
  "University of Edinburgh",
  "University of Dublin",
  "University of Barcelona",
  "University of Madrid",
  "University of Milan",
  "University of Lisbon",
  "University of Vienna",
  "RWTH Aachen University",
  "Technical University of Munich",
  "TU Delft",
  "McMaster University",
  "University of Alberta",
  "Harvard University",
  "Massachusetts Institute of Technology",
  "Stanford University",
  "University of California, Berkeley",
  "New York University",
  "Columbia University",
  "University of Michigan",
  "University of Pennsylvania",
  "University of Chicago",
  "Nanyang Technological University",
  "National University of Singapore",
  "University of Tokyo",
  "Kyoto University",
  "Seoul National University",
  "KAIST",
  "University of Hong Kong",
  "Chinese University of Hong Kong",
  "University of Dubai",
  "American University in Dubai",
  "University of Cape Town",
  "University of Johannesburg",
  "University of Nairobi",
  "University of São Paulo",
  "University of Buenos Aires",
  "University of Mexico",
  "University of Pretoria",
  "University of the Witwatersrand",
  "University of Warwick",
  "University of Manchester",
  "King's College London",
  "University of Glasgow",
  "University of Birmingham",
  "University of Nottingham",
  "University of Leeds",
  "University of Exeter",
  "University of Southampton",
  "Erasmus University Rotterdam",
  "Leiden University",
  "Maastricht University",
  "University of Groningen",
  "University of Utrecht",
  "Bocconi University",
  "Politecnico di Milano",
  "University of Bologna",
  "University of Valencia",
  "University of Pisa",
  "University of Munich",
  "Freie Universität Berlin",
  "University of Potsdam",
  "Aarhus University",
  "Technical University of Denmark",
  "University of Oslo",
  "Norwegian University of Science and Technology",
  "University of Helsinki",
  "Aalto University",
]));

export function resolveDatalistValue(
  value: string,
  options: Array<{ value: string; label: string }>,
): string {
  const input = value.trim();
  if (!input) return "";

  const match = options.find(
    (option) =>
      option.value.toLowerCase() === input.toLowerCase() ||
      option.label.toLowerCase() === input.toLowerCase(),
  );

  return match ? match.value : input;
}

function DatalistField({
  label,
  htmlFor,
  value,
  onChange,
  options,
  placeholder,
}: {
  label: string;
  htmlFor: string;
  value: string;
  onChange: (value: string) => void;
  options: Array<{ value: string; label: string }>;
  placeholder: string;
}) {
  const datalistId = React.useId();

  return (
    <Field label={label} htmlFor={htmlFor}>
      <Input
        id={htmlFor}
        list={datalistId}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
      />
      <datalist id={datalistId}>
        {options.map((option) => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </datalist>
    </Field>
  );
}

export function ReadinessWorkspace({ initialPlans, initialPlanId }: Props) {
  const [plans, setPlans] = React.useState<StudyPlan[]>(initialPlans);
  const [activePlanId, setActivePlanId] = React.useState<string | null>(
    initialPlanId,
  );
  const [costs, setCosts] = React.useState<CostItem[]>([]);
  const [funding, setFunding] = React.useState<FundingSource[]>([]);
  const [rates, setRates] = React.useState<ExchangeRate[]>([]);
  const [readiness, setReadiness] = React.useState<ReadinessResult | null>(null);
  const [error, setError] = React.useState<string | null>(null);
  const [busy, setBusy] = React.useState(false);

  const activePlan = plans.find((p) => p.id === activePlanId) ?? null;

  // Reload everything that depends on the active plan.
  const refreshAll = React.useCallback(
    async (planId: string) => {
      setError(null);
      try {
        const [c, f, r, rd] = await Promise.all([
          costsApi.list(planId),
          fundingApi.list(planId),
          fxApi.list(),
          readinessApi.get(planId),
        ]);
        setCosts(c);
        setFunding(f);
        setRates(r);
        setReadiness(rd);
      } catch (err) {
        setError(errorMessage(err, "Could not load plan data."));
      }
    },
    [],
  );

  React.useEffect(() => {
    if (activePlanId) {
      void refreshAll(activePlanId);
    } else {
      setCosts([]);
      setFunding([]);
      setReadiness(null);
    }
  }, [activePlanId, refreshAll]);

  // ---- Plan CRUD ----
  const createPlan = async (input: StudyPlanCreate) => {
    setError(null);
    setBusy(true);
    try {
      const plan = await studyPlansApi.create(input);
      setPlans((prev) => [plan, ...prev]);
      setActivePlanId(plan.id);
    } catch (err) {
      setError(errorMessage(err, "Could not create plan."));
    } finally {
      setBusy(false);
    }
  };

  const updateActivePlan = async (patch: Partial<StudyPlan>) => {
    if (!activePlan) return;
    setError(null);
    setBusy(true);
    try {
      const updated = await studyPlansApi.update(activePlan.id, patch);
      setPlans((prev) => prev.map((p) => (p.id === updated.id ? updated : p)));
    } catch (err) {
      setError(errorMessage(err, "Could not save plan."));
    } finally {
      setBusy(false);
    }
  };

  // ---- Cost CRUD ----
  const addCost = async (input: CostItemCreate) => {
    if (!activePlan) return;
    setError(null);
    setBusy(true);
    try {
      const created = await costsApi.create(activePlan.id, input);
      setCosts((prev) => [...prev, created]);
      await refreshReadiness();
    } catch (err) {
      setError(errorMessage(err, "Could not add cost."));
    } finally {
      setBusy(false);
    }
  };

  const removeCost = async (id: string) => {
    if (!activePlan) return;
    setError(null);
    setBusy(true);
    try {
      await costsApi.remove(activePlan.id, id);
      setCosts((prev) => prev.filter((c) => c.id !== id));
      await refreshReadiness();
    } catch (err) {
      setError(errorMessage(err, "Could not remove cost."));
    } finally {
      setBusy(false);
    }
  };

  // ---- Funding CRUD ----
  const addFunding = async (input: FundingSourceCreate) => {
    if (!activePlan) return;
    setError(null);
    setBusy(true);
    try {
      const created = await fundingApi.create(activePlan.id, input);
      setFunding((prev) => [...prev, created]);
      await refreshReadiness();
    } catch (err) {
      setError(errorMessage(err, "Could not add funding source."));
    } finally {
      setBusy(false);
    }
  };

  const removeFunding = async (id: string) => {
    if (!activePlan) return;
    setError(null);
    setBusy(true);
    try {
      await fundingApi.remove(activePlan.id, id);
      setFunding((prev) => prev.filter((f) => f.id !== id));
      await refreshReadiness();
    } catch (err) {
      setError(errorMessage(err, "Could not remove funding source."));
    } finally {
      setBusy(false);
    }
  };

  // ---- FX CRUD ----
  const upsertRate = async (
    base: string,
    quote: string,
    rate: string,
  ) => {
    setError(null);
    setBusy(true);
    try {
      const updated = await fxApi.upsert({
        base_currency: base.toUpperCase(),
        quote_currency: quote.toUpperCase(),
        rate,
        rate_type: "user_entered",
        observed_at: new Date().toISOString().slice(0, 10),
      });
      setRates((prev) => {
        const filtered = prev.filter(
          (r) => !(r.base_currency === updated.base_currency &&
                   r.quote_currency === updated.quote_currency),
        );
        return [...filtered, updated];
      });
      if (activePlanId) await refreshReadiness();
    } catch (err) {
      setError(errorMessage(err, "Could not save FX rate."));
    } finally {
      setBusy(false);
    }
  };

  const refreshReadiness = async () => {
    if (!activePlanId) return;
    try {
      const rd = await readinessApi.get(activePlanId);
      setReadiness(rd);
    } catch (err) {
      setError(errorMessage(err, "Could not refresh readiness."));
    }
  };

  return (
    <div className="flex flex-col gap-6">
      {error ? (
        <div
          role="alert"
          className="flex items-start gap-2 rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700"
        >
          <AlertCircle className="mt-0.5 h-4 w-4 flex-shrink-0" />
          <span>{error}</span>
        </div>
      ) : null}

      <PlanPicker
        plans={plans}
        activePlanId={activePlanId}
        onSelect={setActivePlanId}
        onCreate={createPlan}
        busy={busy}
      />

      {activePlan ? (
        <>
          <PlanEditor plan={activePlan} onSave={updateActivePlan} busy={busy} />
          <div className="grid gap-6 lg:grid-cols-2">
            <CostsEditor
              costs={costs}
              baseCurrency={activePlan.base_currency}
              onAdd={addCost}
              onRemove={removeCost}
              busy={busy}
            />
            <FundingEditor
              funding={funding}
              baseCurrency={activePlan.base_currency}
              onAdd={addFunding}
              onRemove={removeFunding}
              busy={busy}
            />
          </div>
          <FxEditor rates={rates} onUpsert={upsertRate} busy={busy} />
        </>
      ) : null}

      {readiness ? <ReadinessPanel result={readiness} /> : null}
    </div>
  );
}

function errorMessage(err: unknown, fallback: string): string {
  if (err instanceof ApiClientError) return err.message ?? fallback;
  if (err instanceof Error) return err.message;
  return fallback;
}

// ---------- Sub-components ----------

function PlanPicker({
  plans,
  activePlanId,
  onSelect,
  onCreate,
  busy,
}: {
  plans: StudyPlan[];
  activePlanId: string | null;
  onSelect: (id: string) => void;
  onCreate: (input: StudyPlanCreate) => Promise<void>;
  busy: boolean;
}) {
  const [showNew, setShowNew] = React.useState(false);
  return (
    <Card>
      <CardHeader>
        <div className="flex flex-wrap items-center justify-between gap-2">
          <CardTitle>Plans</CardTitle>
          <Button size="sm" onClick={() => setShowNew((v) => !v)}>
            <Plus className="h-4 w-4" /> New plan
          </Button>
        </div>
      </CardHeader>
      <CardContent>
        {plans.length === 0 && !showNew ? (
          <p className="text-sm text-slate">No plans yet — create one to get started.</p>
        ) : (
          <ul className="flex flex-wrap gap-2">
            {plans.map((p) => (
              <li key={p.id}>
                <button
                  type="button"
                  onClick={() => onSelect(p.id)}
                  className={
                    "rounded-lg border px-3 py-1.5 text-sm transition-colors " +
                    (p.id === activePlanId
                      ? "border-teal bg-mint/40 text-midnight"
                      : "border-border bg-white text-slate hover:bg-ivory")
                  }
                >
                  {p.name}
                  <span className="ml-1 text-xs text-slate">({p.base_currency})</span>
                </button>
              </li>
            ))}
          </ul>
        )}
        {showNew ? (
          <NewPlanForm
            onCancel={() => setShowNew(false)}
            onSubmit={async (input) => {
              await onCreate(input);
              setShowNew(false);
            }}
            busy={busy}
          />
        ) : null}
      </CardContent>
    </Card>
  );
}

function NewPlanForm({
  onCancel,
  onSubmit,
  busy,
}: {
  onCancel: () => void;
  onSubmit: (input: StudyPlanCreate) => Promise<void>;
  busy: boolean;
}) {
  const [name, setName] = React.useState("My study plan");
  const [baseCurrency, setBaseCurrency] = React.useState("USD");
  const [homeCurrency, setHomeCurrency] = React.useState("USD");
  const [destinationCountry, setDestinationCountry] = React.useState("");
  const [institutionName, setInstitutionName] = React.useState("");
  const [programName, setProgramName] = React.useState("");
  const [city, setCity] = React.useState("");
  const [tuitionAmount, setTuitionAmount] = React.useState("");
  const [tuitionCurrency, setTuitionCurrency] = React.useState("");
  const [startDate, setStartDate] = React.useState(
    new Date().toISOString().slice(0, 10),
  );
  const [durationMonths, setDurationMonths] = React.useState(24);

  return (
    <form
      className="mt-4 grid gap-3 sm:grid-cols-4"
      onSubmit={async (e) => {
        e.preventDefault();
        const trimmed = (s: string) => s.trim();
        const normalizedCountry = resolveDatalistValue(
          destinationCountry,
          DESTINATION_COUNTRIES,
        );
        await onSubmit({
          name: trimmed(name),
          base_currency: baseCurrency.toUpperCase(),
          home_currency: homeCurrency.toUpperCase(),
          destination_country: normalizedCountry ? normalizedCountry.toUpperCase() : undefined,
          institution_name: institutionName || undefined,
          program_name: programName || undefined,
          city: city || undefined,
          tuition_amount: tuitionAmount || undefined,
          tuition_currency: tuitionCurrency
            ? tuitionCurrency.toUpperCase()
            : undefined,
          start_date: startDate,
          duration_months: durationMonths,
        });
      }}
    >
      <Field label="Name" htmlFor="np-name" required>
        <Input id="np-name" value={name} onChange={(e) => setName(e.target.value)} />
      </Field>
      <Field label="Base currency" htmlFor="np-ccy" required>
        <Input
          id="np-ccy"
          maxLength={3}
          value={baseCurrency}
          onChange={(e) => setBaseCurrency(e.target.value.toUpperCase())}
        />
      </Field>
      <Field label="Home currency" htmlFor="np-home-ccy" required>
        <Input
          id="np-home-ccy"
          maxLength={3}
          value={homeCurrency}
          onChange={(e) => setHomeCurrency(e.target.value.toUpperCase())}
        />
      </Field>
      <Field label="Start date" htmlFor="np-start" required>
        <Input
          id="np-start"
          type="date"
          value={startDate}
          onChange={(e) => setStartDate(e.target.value)}
        />
      </Field>
      <Field label="Duration (months)" htmlFor="np-dur" required>
        <Input
          id="np-dur"
          type="number"
          min={1}
          max={120}
          value={durationMonths}
          onChange={(e) => setDurationMonths(Number(e.target.value))}
        />
      </Field>
      <DatalistField
        label="Destination country"
        htmlFor="np-ctry"
        value={destinationCountry}
        onChange={(value) => setDestinationCountry(value)}
        options={DESTINATION_COUNTRIES}
        placeholder="Select or type country"
      />
      <DatalistField
        label="City"
        htmlFor="np-city"
        value={city}
        onChange={setCity}
        options={CITY_OPTIONS.map((option) => ({ value: option, label: option }))}
        placeholder="Select or type city"
      />
      <DatalistField
        label="Institution"
        htmlFor="np-inst"
        value={institutionName}
        onChange={setInstitutionName}
        options={INSTITUTION_OPTIONS.map((option) => ({ value: option, label: option }))}
        placeholder="Select or type institution"
      />
      <Field label="Program" htmlFor="np-prog">
        <Input
          id="np-prog"
          value={programName}
          onChange={(e) => setProgramName(e.target.value)}
          placeholder="e.g. MSc Computer Science"
        />
      </Field>
      <Field label="Tuition amount" htmlFor="np-tu-amt">
        <Input
          id="np-tu-amt"
          inputMode="decimal"
          value={tuitionAmount}
          onChange={(e) => setTuitionAmount(e.target.value)}
          placeholder="optional, e.g. 15000"
        />
      </Field>
      <Field label="Tuition currency" htmlFor="np-tu-ccy">
        <Input
          id="np-tu-ccy"
          maxLength={3}
          value={tuitionCurrency}
          onChange={(e) => setTuitionCurrency(e.target.value.toUpperCase())}
          placeholder="e.g. EUR"
        />
      </Field>
      <div className="col-span-full flex justify-end gap-2">
        <Button type="button" variant="secondary" onClick={onCancel}>
          Cancel
        </Button>
        <Button type="submit" isLoading={busy}>
          Create plan
        </Button>
      </div>
    </form>
  );
}

function PlanEditor({
  plan,
  onSave,
  busy,
}: {
  plan: StudyPlan;
  onSave: (patch: Partial<StudyPlan>) => Promise<void>;
  busy: boolean;
}) {
  // Local controlled state, hydrated from `plan` whenever it changes.
  const [name, setName] = React.useState(plan.name);
  const [destinationCountry, setDestinationCountry] = React.useState(
    plan.destination_country ?? "",
  );
  const [city, setCity] = React.useState(plan.city ?? "");
  const [institutionName, setInstitutionName] = React.useState(
    plan.institution_name ?? "",
  );
  const [programName, setProgramName] = React.useState(
    plan.program_name ?? "",
  );
  const [tuitionAmount, setTuitionAmount] = React.useState(
    plan.tuition_amount ?? "",
  );
  const [tuitionCurrency, setTuitionCurrency] = React.useState(
    plan.tuition_currency ?? "",
  );
  const [homeCurrency, setHomeCurrency] = React.useState(
    plan.home_currency ?? "",
  );

  React.useEffect(() => {
    setName(plan.name);
    setDestinationCountry(plan.destination_country ?? "");
    setCity(plan.city ?? "");
    setInstitutionName(plan.institution_name ?? "");
    setProgramName(plan.program_name ?? "");
    setTuitionAmount(plan.tuition_amount ?? "");
    setTuitionCurrency(plan.tuition_currency ?? "");
    setHomeCurrency(plan.home_currency ?? "");
  }, [plan]);

  return (
    <Card>
      <CardHeader>
        <CardTitle>{plan.name}</CardTitle>
        <p className="text-sm text-slate">
          {plan.base_currency} · {formatDate(plan.start_date)} → {formatDate(plan.end_date)} ({plan.duration_months} months)
        </p>
      </CardHeader>
      <CardContent>
        <form
          className="grid gap-3 sm:grid-cols-4"
          onSubmit={async (e) => {
            e.preventDefault();
            const norm = (s: string) => s.trim();
            const upper = (s: string) => norm(s).toUpperCase();
            const normalizedCountry = resolveDatalistValue(
              destinationCountry,
              DESTINATION_COUNTRIES,
            );
            await onSave({
              name: norm(name),
              destination_country: normalizedCountry
                ? upper(normalizedCountry)
                : null,
              city: norm(city) || null,
              institution_name: norm(institutionName) || null,
              program_name: norm(programName) || null,
              tuition_amount: tuitionAmount || null,
              tuition_currency: tuitionCurrency
                ? upper(tuitionCurrency)
                : null,
              home_currency: homeCurrency ? upper(homeCurrency) : null,
            });
          }}
        >
          <Field label="Plan name" htmlFor="pe-name" required>
            <Input
              id="pe-name"
              value={name}
              onChange={(e) => setName(e.target.value)}
            />
          </Field>
          <DatalistField
            label="Destination country"
            htmlFor="pe-ctry"
            value={destinationCountry}
            onChange={(value) => setDestinationCountry(value)}
            options={DESTINATION_COUNTRIES}
            placeholder="Select or type country"
          />
          <DatalistField
            label="City"
            htmlFor="pe-city"
            value={city}
            onChange={setCity}
            options={CITY_OPTIONS.map((option) => ({ value: option, label: option }))}
            placeholder="Select or type city"
          />
          <DatalistField
            label="Institution"
            htmlFor="pe-inst"
            value={institutionName}
            onChange={setInstitutionName}
            options={INSTITUTION_OPTIONS.map((option) => ({ value: option, label: option }))}
            placeholder="Select or type institution"
          />
          <Field label="Program" htmlFor="pe-prog">
            <Input
              id="pe-prog"
              value={programName}
              onChange={(e) => setProgramName(e.target.value)}
              placeholder="e.g. MSc Computer Science"
            />
          </Field>
          <Field label="Home currency" htmlFor="pe-home-ccy">
            <Input
              id="pe-home-ccy"
              maxLength={3}
              value={homeCurrency}
              onChange={(e) =>
                setHomeCurrency(e.target.value.toUpperCase())
              }
              placeholder="e.g. BDT"
            />
          </Field>
          <Field label="Tuition amount" htmlFor="pe-tu-amt">
            <Input
              id="pe-tu-amt"
              inputMode="decimal"
              value={tuitionAmount}
              onChange={(e) => setTuitionAmount(e.target.value)}
              placeholder="optional"
            />
          </Field>
          <Field label="Tuition currency" htmlFor="pe-tu-ccy">
            <Input
              id="pe-tu-ccy"
              maxLength={3}
              value={tuitionCurrency}
              onChange={(e) =>
                setTuitionCurrency(e.target.value.toUpperCase())
              }
              placeholder="e.g. EUR"
            />
          </Field>
          <div className="col-span-full flex justify-end">
            <Button type="submit" size="sm" isLoading={busy}>
              Save
            </Button>
          </div>
        </form>
      </CardContent>
    </Card>
  );
}

function CostsEditor({
  costs,
  baseCurrency,
  onAdd,
  onRemove,
  busy,
}: {
  costs: CostItem[];
  baseCurrency: string;
  onAdd: (input: CostItemCreate) => Promise<void>;
  onRemove: (id: string) => Promise<void>;
  busy: boolean;
}) {
  const [category, setCategory] = React.useState<CostCategory>("tuition");
  const [description, setDescription] = React.useState("");
  const [amount, setAmount] = React.useState("");
  const [currency, setCurrency] = React.useState(baseCurrency);
  const [frequency, setFrequency] = React.useState<Frequency>("monthly");
  const [startDate, setStartDate] = React.useState("");
  const [isRefundable, setIsRefundable] = React.useState(false);
  const [dueBeforeDeparture, setDueBeforeDeparture] = React.useState(false);

  React.useEffect(() => setCurrency(baseCurrency), [baseCurrency]);

  return (
    <Card>
      <CardHeader>
        <CardTitle>Costs</CardTitle>
        <p className="text-sm text-slate">
          Recurring and one-time costs in their own currency; the readiness engine
          converts to the plan's base currency.
        </p>
      </CardHeader>
      <CardContent>
        {costs.length === 0 ? (
          <p className="text-sm text-slate">No costs yet.</p>
        ) : (
          <ul className="mb-4 flex flex-col gap-2">
            {costs.map((c) => (
              <li
                key={c.id}
                className="flex items-center justify-between rounded border border-border/60 px-3 py-2 text-sm"
              >
                <div>
                  <span className="font-medium text-midnight">
                    {c.description || c.category}
                  </span>
                  <span className="ml-2 text-slate">
                    {formatMoney(c.amount, c.currency)} · {c.frequency}
                    {c.is_refundable ? " · refundable" : ""}
                  </span>
                </div>
                <button
                  type="button"
                  onClick={() => onRemove(c.id)}
                  className="text-slate hover:text-red"
                  aria-label={`Remove ${c.description || c.category}`}
                >
                  <Trash2 className="h-4 w-4" />
                </button>
              </li>
            ))}
          </ul>
        )}
        <form
          className="grid gap-3 sm:grid-cols-6"
          onSubmit={async (e) => {
            e.preventDefault();
            await onAdd({
              category,
              description,
              amount,
              currency: currency.toUpperCase(),
              frequency,
              start_date: startDate || null,
              is_one_time: frequency === "one_time",
              is_refundable: isRefundable,
              due_before_departure: dueBeforeDeparture,
            });
            setDescription("");
            setAmount("");
            setStartDate("");
            setDueBeforeDeparture(false);
          }}
        >
          <Field label="Category" htmlFor="co-cat">
            <select
              id="co-cat"
              className="h-10 w-full rounded-lg border border-border bg-white px-2 text-sm"
              value={category}
              onChange={(e) => setCategory(e.target.value as CostCategory)}
            >
              {CATEGORIES.map((c) => (
                <option key={c} value={c}>
                  {c}
                </option>
              ))}
            </select>
          </Field>
          <Field label="Description" htmlFor="co-desc">
            <Input
              id="co-desc"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="e.g. Monthly rent"
            />
          </Field>
          <Field label="Amount" htmlFor="co-amt" required>
            <Input
              id="co-amt"
              inputMode="decimal"
              value={amount}
              onChange={(e) => setAmount(e.target.value)}
              placeholder="0.00"
            />
          </Field>
          <Field label="Currency" htmlFor="co-ccy" required>
            <Input
              id="co-ccy"
              maxLength={3}
              value={currency}
              onChange={(e) => setCurrency(e.target.value.toUpperCase())}
            />
          </Field>
          <Field label="Frequency" htmlFor="co-freq">
            <select
              id="co-freq"
              className="h-10 w-full rounded-lg border border-border bg-white px-2 text-sm"
              value={frequency}
              onChange={(e) => setFrequency(e.target.value as Frequency)}
            >
              {FREQUENCIES.map((f) => (
                <option key={f} value={f}>
                  {f}
                </option>
              ))}
            </select>
          </Field>
          <Field label="Start date" htmlFor="co-start">
            <Input
              id="co-start"
              type="date"
              value={startDate}
              onChange={(e) => setStartDate(e.target.value)}
            />
          </Field>
          <label className="col-span-full flex items-center gap-2 text-sm text-slate">
            <input
              type="checkbox"
              checked={isRefundable}
              onChange={(e) => setIsRefundable(e.target.checked)}
            />
            Refundable deposit (tracked separately, not in projected cost)
          </label>
          <label className="col-span-full flex items-center gap-2 text-sm text-slate">
            <input
              type="checkbox"
              checked={dueBeforeDeparture}
              onChange={(e) => setDueBeforeDeparture(e.target.checked)}
            />
            Due before departure (counted in the upfront-cash window even
            without a start date)
          </label>
          <div className="col-span-full flex justify-end">
            <Button type="submit" size="sm" isLoading={busy}>
              <Plus className="h-4 w-4" /> Add cost
            </Button>
          </div>
        </form>
      </CardContent>
    </Card>
  );
}

function FundingEditor({
  funding,
  baseCurrency,
  onAdd,
  onRemove,
  busy,
}: {
  funding: FundingSource[];
  baseCurrency: string;
  onAdd: (input: FundingSourceCreate) => Promise<void>;
  onRemove: (id: string) => Promise<void>;
  busy: boolean;
}) {
  const [name, setName] = React.useState("Family savings");
  const [type, setType] = React.useState<FundingType>("savings");
  const [amount, setAmount] = React.useState("");
  const [currency, setCurrency] = React.useState(baseCurrency);
  const [status, setStatus] = React.useState<FundingStatus>("confirmed");
  const [expectedDate, setExpectedDate] = React.useState("");

  React.useEffect(() => setCurrency(baseCurrency), [baseCurrency]);

  return (
    <Card>
      <CardHeader>
        <CardTitle>Funding</CardTitle>
        <p className="text-sm text-slate">
          Only confirmed sources count against the funding gap. Conditional
          and expected sources reduce the gap only when they land.
        </p>
      </CardHeader>
      <CardContent>
        {funding.length === 0 ? (
          <p className="text-sm text-slate">No funding sources yet.</p>
        ) : (
          <ul className="mb-4 flex flex-col gap-2">
            {funding.map((s) => (
              <li
                key={s.id}
                className="flex items-center justify-between rounded border border-border/60 px-3 py-2 text-sm"
              >
                <div>
                  <span className="font-medium text-midnight">{s.name}</span>
                  <span className="ml-2 text-slate">
                    {formatMoney(s.amount, s.currency)} · {s.status}
                  </span>
                </div>
                <button
                  type="button"
                  onClick={() => onRemove(s.id)}
                  className="text-slate hover:text-red"
                  aria-label={`Remove ${s.name}`}
                >
                  <Trash2 className="h-4 w-4" />
                </button>
              </li>
            ))}
          </ul>
        )}
        <form
          className="grid gap-3 sm:grid-cols-6"
          onSubmit={async (e) => {
            e.preventDefault();
            await onAdd({
              name,
              funding_type: type,
              amount,
              currency: currency.toUpperCase(),
              status,
              expected_date: expectedDate || null,
            });
            setAmount("");
            setExpectedDate("");
          }}
        >
          <Field label="Name" htmlFor="fn-name" required>
            <Input id="fn-name" value={name} onChange={(e) => setName(e.target.value)} />
          </Field>
          <Field label="Type" htmlFor="fn-type">
            <select
              id="fn-type"
              className="h-10 w-full rounded-lg border border-border bg-white px-2 text-sm"
              value={type}
              onChange={(e) => setType(e.target.value as FundingType)}
            >
              {FUNDING_TYPES.map((t) => (
                <option key={t} value={t}>
                  {t}
                </option>
              ))}
            </select>
          </Field>
          <Field label="Amount" htmlFor="fn-amt" required>
            <Input
              id="fn-amt"
              inputMode="decimal"
              value={amount}
              onChange={(e) => setAmount(e.target.value)}
              placeholder="0.00"
            />
          </Field>
          <Field label="Currency" htmlFor="fn-ccy" required>
            <Input
              id="fn-ccy"
              maxLength={3}
              value={currency}
              onChange={(e) => setCurrency(e.target.value.toUpperCase())}
            />
          </Field>
          <Field label="Status" htmlFor="fn-status">
            <select
              id="fn-status"
              className="h-10 w-full rounded-lg border border-border bg-white px-2 text-sm"
              value={status}
              onChange={(e) => setStatus(e.target.value as FundingStatus)}
            >
              {FUNDING_STATUSES.map((s) => (
                <option key={s} value={s}>
                  {s}
                </option>
              ))}
            </select>
          </Field>
          <Field label="Expected date" htmlFor="fn-date">
            <Input
              id="fn-date"
              type="date"
              value={expectedDate}
              onChange={(e) => setExpectedDate(e.target.value)}
            />
          </Field>
          <div className="col-span-full flex justify-end">
            <Button type="submit" size="sm" isLoading={busy}>
              <Plus className="h-4 w-4" /> Add funding
            </Button>
          </div>
        </form>
      </CardContent>
    </Card>
  );
}

function FxEditor({
  rates,
  onUpsert,
  busy,
}: {
  rates: ExchangeRate[];
  onUpsert: (base: string, quote: string, rate: string) => Promise<void>;
  busy: boolean;
}) {
  const [base, setBase] = React.useState("EUR");
  const [quote, setQuote] = React.useState("USD");
  const [rate, setRate] = React.useState("");

  return (
    <Card>
      <CardHeader>
        <CardTitle>Exchange rates</CardTitle>
        <p className="text-sm text-slate">
          Enter a rate whenever a cost or funding source uses a different
          currency than the plan's base.
        </p>
      </CardHeader>
      <CardContent>
        {rates.length > 0 ? (
          <ul className="mb-4 grid gap-2 sm:grid-cols-2">
            {rates.map((r) => (
              <li
                key={r.id}
                className="flex items-center justify-between rounded border border-border/60 px-3 py-2 text-sm tabular-nums"
              >
                <span className="text-slate">
                  1 {r.base_currency} ={" "}
                  <span className="font-medium text-midnight">{r.rate}</span>{" "}
                  {r.quote_currency}
                </span>
                <span className="text-xs text-slate">{r.rate_type}</span>
              </li>
            ))}
          </ul>
        ) : null}
        <form
          className="grid gap-3 sm:grid-cols-4"
          onSubmit={async (e) => {
            e.preventDefault();
            await onUpsert(base, quote, rate);
            setRate("");
          }}
        >
          <Field label="Base" htmlFor="fx-base" required>
            <Input
              id="fx-base"
              maxLength={3}
              value={base}
              onChange={(e) => setBase(e.target.value.toUpperCase())}
            />
          </Field>
          <Field label="Quote" htmlFor="fx-quote" required>
            <Input
              id="fx-quote"
              maxLength={3}
              value={quote}
              onChange={(e) => setQuote(e.target.value.toUpperCase())}
            />
          </Field>
          <Field label="Rate" htmlFor="fx-rate" required>
            <Input
              id="fx-rate"
              inputMode="decimal"
              value={rate}
              onChange={(e) => setRate(e.target.value)}
              placeholder="e.g. 0.9"
            />
          </Field>
          <div className="flex items-end justify-end">
            <Button type="submit" size="sm" isLoading={busy}>
              Save rate
            </Button>
          </div>
        </form>
      </CardContent>
    </Card>
  );
}

// Suppress unused import warning for the RateType array — we reference
// RATE_TYPES in the schema list but TypeScript can't see that.
void RATE_TYPES;
void toDateInputValue;
