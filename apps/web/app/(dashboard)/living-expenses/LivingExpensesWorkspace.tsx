"use client";

import * as React from "react";

import { Button } from "@/components/ui/Button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/Card";
import { Field, Input } from "@/components/ui/Input";

const CURRENCIES = ["USD", "EUR", "GBP", "AUD"];

const COUNTRY_OPTIONS = [
  "United States",
  "United Kingdom",
  "Canada",
  "Germany",
  "Australia",
  "France",
  "Spain",
  "Singapore",
  "Japan",
  "Netherlands",
];

const CITY_LOOKUP: Record<string, string[]> = {
  "United States": ["Boston", "New York", "Chicago", "Seattle"],
  "United Kingdom": ["London", "Manchester", "Edinburgh"],
  Canada: ["Toronto", "Vancouver", "Montreal"],
  Germany: ["Berlin", "Munich", "Frankfurt"],
  Australia: ["Sydney", "Melbourne", "Brisbane"],
  France: ["Paris", "Lyon", "Bordeaux"],
  Spain: ["Madrid", "Barcelona", "Valencia"],
  Singapore: ["Singapore"],
  Japan: ["Tokyo", "Osaka", "Kyoto"],
  Netherlands: ["Amsterdam", "Rotterdam", "Utrecht"],
};

const INSTITUTION_LOOKUP: Record<string, string[]> = {
  Boston: ["Boston University", "Northeastern University", "MIT"],
  "New York": ["Columbia University", "NYU", "Fordham University"],
  Chicago: ["University of Chicago", "DePaul University", "Northwestern"],
  Seattle: ["University of Washington", "Seattle University", "Bellevue College"],
  London: ["University College London", "King's College London", "Imperial College London"],
  Manchester: ["University of Manchester", "Manchester Metropolitan University"],
  Edinburgh: ["University of Edinburgh", "Heriot-Watt University"],
  Toronto: ["University of Toronto", "Toronto Metropolitan University"],
  Vancouver: ["University of British Columbia", "Simon Fraser University"],
  Montreal: ["McGill University", "Université de Montréal"],
  Berlin: ["Humboldt University of Berlin", "Freie Universität Berlin"],
  Munich: ["LMU Munich", "Technical University of Munich"],
  Frankfurt: ["Goethe University Frankfurt", "Frankfurt School of Finance"],
  Sydney: ["UNSW Sydney", "University of Sydney", "Macquarie University"],
  Melbourne: ["University of Melbourne", "Monash University"],
  Brisbane: ["University of Queensland", "Griffith University"],
  Paris: ["Sciences Po", "Sorbonne University", "ESSEC Business School"],
  Lyon: ["Université Lumière Lyon 2", "INSA Lyon"],
  Bordeaux: ["University of Bordeaux", "Bordeaux Montaigne University"],
  Madrid: ["Universidad Complutense de Madrid", "IE University"],
  Barcelona: ["Universitat de Barcelona", "ESADE Business School"],
  Valencia: ["University of Valencia", "Universitat Politècnica de València"],
  Singapore: ["NUS", "NTU", "SMU"],
  Tokyo: ["University of Tokyo", "Waseda University"],
  Osaka: ["Osaka University", "Kansai University"],
  Kyoto: ["Kyoto University", "Doshisha University"],
  Amsterdam: ["University of Amsterdam", "Vrije Universiteit Amsterdam"],
  Rotterdam: ["Erasmus University Rotterdam"],
  Utrecht: ["Utrecht University"],
};

const CITY_COST_MULTIPLIERS: Record<string, Record<string, number>> = {
  "United States": { Boston: 1.08, "New York": 1.22, Chicago: 1.12, Seattle: 1.17 },
  "United Kingdom": { London: 1.19, Manchester: 1.1, Edinburgh: 1.13 },
  Canada: { Toronto: 1.09, Vancouver: 1.11, Montreal: 1.05 },
  Germany: { Berlin: 1.06, Munich: 1.12, Frankfurt: 1.09 },
  Australia: { Sydney: 1.18, Melbourne: 1.14, Brisbane: 1.08 },
  France: { Paris: 1.13, Lyon: 1.07, Bordeaux: 1.05 },
  Spain: { Madrid: 1.08, Barcelona: 1.12, Valencia: 1.04 },
  Singapore: { Singapore: 1.24 },
  Japan: { Tokyo: 1.26, Osaka: 1.13, Kyoto: 1.1 },
  Netherlands: { Amsterdam: 1.16, Rotterdam: 1.08, Utrecht: 1.07 },
};

const INSTITUTION_COST_MULTIPLIERS: Record<string, number> = {
  "Boston University": 1.02,
  "Northeastern University": 1.04,
  MIT: 1.06,
  "Columbia University": 1.09,
  NYU: 1.11,
  "Fordham University": 1.04,
  "University of Chicago": 1.06,
  "DePaul University": 1.02,
  Northwestern: 1.07,
  "University of Washington": 1.06,
  "Seattle University": 1.03,
  "Bellevue College": 1.01,
  "University College London": 1.1,
  "King's College London": 1.08,
  "Imperial College London": 1.13,
  "University of Manchester": 1.07,
  "Manchester Metropolitan University": 1.03,
  "University of Edinburgh": 1.09,
  "Heriot-Watt University": 1.05,
  "University of Toronto": 1.08,
  "Toronto Metropolitan University": 1.04,
  "University of British Columbia": 1.09,
  "Simon Fraser University": 1.05,
  "McGill University": 1.12,
  "Université de Montréal": 1.08,
  "Humboldt University of Berlin": 1.06,
  "Freie Universität Berlin": 1.05,
  "LMU Munich": 1.08,
  "Technical University of Munich": 1.09,
  "Goethe University Frankfurt": 1.05,
  "Frankfurt School of Finance": 1.07,
  "UNSW Sydney": 1.1,
  "University of Sydney": 1.09,
  "Macquarie University": 1.05,
  "University of Melbourne": 1.08,
  "Monash University": 1.09,
  "University of Queensland": 1.06,
  "Griffith University": 1.04,
  "Sciences Po": 1.08,
  "Sorbonne University": 1.1,
  "ESSEC Business School": 1.07,
  "Université Lumière Lyon 2": 1.04,
  "INSA Lyon": 1.06,
  "University of Bordeaux": 1.05,
  "Bordeaux Montaigne University": 1.04,
  "Universidad Complutense de Madrid": 1.06,
  "IE University": 1.08,
  "Universitat de Barcelona": 1.05,
  "ESADE Business School": 1.07,
  "University of Valencia": 1.04,
  "Universitat Politècnica de València": 1.05,
  NUS: 1.14,
  NTU: 1.13,
  SMU: 1.1,
  "University of Tokyo": 1.12,
  "Waseda University": 1.1,
  "Osaka University": 1.08,
  "Kansai University": 1.06,
  "Kyoto University": 1.09,
  "Doshisha University": 1.05,
  "University of Amsterdam": 1.1,
  "Vrije Universiteit Amsterdam": 1.08,
  "Erasmus University Rotterdam": 1.06,
  "Utrecht University": 1.08,
};

const DEFAULT_VALUES = {
  rent: "900",
  groceries: "450",
  transport: "140",
  utilities: "110",
  insurance: "80",
  personal: "180",
};

type FieldKey = keyof typeof DEFAULT_VALUES;

const INPUTS: Array<{ key: FieldKey; label: string; hint: string }> = [
  { key: "rent", label: "Monthly rent", hint: "Accommodation, utilities, or shared housing" },
  { key: "groceries", label: "Food & groceries", hint: "Groceries, lunch, and everyday basics" },
  { key: "transport", label: "Transport", hint: "Public transport, fuel, and travel passes" },
  { key: "utilities", label: "Utilities & internet", hint: "Electricity, water, mobile, and Wi‑Fi" },
  { key: "insurance", label: "Insurance & healthcare", hint: "Health cover, travel insurance, and essentials" },
  { key: "personal", label: "Personal & misc", hint: "Leisure, clothing, and other household spend" },
];

function formatMoney(value: number, currency: string) {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency,
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(value);
}

function uniqueItems(items: string[]) {
  return Array.from(new Set(items.filter(Boolean)));
}

export function LivingExpensesWorkspace() {
  const [currency, setCurrency] = React.useState("USD");
  const [values, setValues] = React.useState(DEFAULT_VALUES);
  const [submitted, setSubmitted] = React.useState(false);
  const [selectedCountry, setSelectedCountry] = React.useState("United States");
  const [selectedCity, setSelectedCity] = React.useState("Boston");
  const [selectedInstitution, setSelectedInstitution] = React.useState("Boston University");
  const [customCountryInput, setCustomCountryInput] = React.useState("");
  const [customCityInput, setCustomCityInput] = React.useState("");
  const [customInstitutionInput, setCustomInstitutionInput] = React.useState("");
  const [customCountries, setCustomCountries] = React.useState<string[]>([]);
  const [customCitiesByCountry, setCustomCitiesByCountry] = React.useState<Record<string, string[]>>({});
  const [customInstitutionsByCity, setCustomInstitutionsByCity] = React.useState<Record<string, string[]>>({});
  const [comparisonApplied, setComparisonApplied] = React.useState(false);

  const monthlyTotal = React.useMemo(() => {
    return INPUTS.reduce((sum, item) => {
      const numericValue = Number(values[item.key] ?? "0");
      return sum + (Number.isFinite(numericValue) ? numericValue : 0);
    }, 0);
  }, [values]);

  const annualTotal = monthlyTotal * 12;
  const emergencyReserve = monthlyTotal * 0.15;

  const countryOptions = React.useMemo(
    () => uniqueItems([...COUNTRY_OPTIONS, ...customCountries]),
    [customCountries],
  );

  const cityOptions = React.useMemo(() => {
    const baseCities = CITY_LOOKUP[selectedCountry] ?? [];
    const customCities = customCitiesByCountry[selectedCountry] ?? [];
    return uniqueItems([...baseCities, ...customCities]);
  }, [customCitiesByCountry, selectedCountry]);

  const institutionOptions = React.useMemo(() => {
    const baseInstitutions = INSTITUTION_LOOKUP[selectedCity] ?? [];
    const customInstitutions = customInstitutionsByCity[selectedCity] ?? [];
    return uniqueItems([...baseInstitutions, ...customInstitutions]);
  }, [customInstitutionsByCity, selectedCity]);

  React.useEffect(() => {
    const fallbackCity = cityOptions[0] ?? "";
    if (!cityOptions.includes(selectedCity) && fallbackCity) {
      setSelectedCity(fallbackCity);
    }
  }, [cityOptions, selectedCity]);

  React.useEffect(() => {
    const fallbackInstitution = institutionOptions[0] ?? "";
    if (!institutionOptions.includes(selectedInstitution) && fallbackInstitution) {
      setSelectedInstitution(fallbackInstitution);
    }
  }, [institutionOptions, selectedInstitution]);

  const destinationMultiplier = React.useMemo(() => {
    const countryMultiplier = CITY_COST_MULTIPLIERS[selectedCountry]?.[selectedCity] ?? 1;
    const institutionMultiplier = INSTITUTION_COST_MULTIPLIERS[selectedInstitution] ?? 1;
    return countryMultiplier * institutionMultiplier;
  }, [selectedCity, selectedCountry, selectedInstitution]);

  const destinationMonthlyTotal = monthlyTotal * destinationMultiplier;
  const destinationAnnualTotal = destinationMonthlyTotal * 12;
  const destinationDelta = destinationMonthlyTotal - monthlyTotal;

  const onNumberChange = (key: FieldKey, raw: string) => {
    setValues((current) => ({
      ...current,
      [key]: raw,
    }));
  };

  const handleAddCustomCountry = () => {
    const trimmed = customCountryInput.trim();
    if (!trimmed) return;

    const nextValue = trimmed
      .split(" ")
      .filter(Boolean)
      .map((word) => word.charAt(0).toUpperCase() + word.slice(1).toLowerCase())
      .join(" ");

    if (!countryOptions.includes(nextValue)) {
      setCustomCountries((current) => [...current, nextValue]);
      setSelectedCountry(nextValue);
      setSelectedCity("");
      setSelectedInstitution("");
    }
    setCustomCountryInput("");
  };

  const handleAddCustomCity = () => {
    const trimmed = customCityInput.trim();
    if (!trimmed || !selectedCountry) return;

    const nextValue = trimmed.charAt(0).toUpperCase() + trimmed.slice(1);

    setCustomCitiesByCountry((current) => ({
      ...current,
      [selectedCountry]: uniqueItems([...(current[selectedCountry] ?? []), nextValue]),
    }));
    setSelectedCity(nextValue);
    setSelectedInstitution("");
    setCustomCityInput("");
  };

  const handleAddCustomInstitution = () => {
    const trimmed = customInstitutionInput.trim();
    if (!trimmed || !selectedCity) return;

    const nextValue = trimmed;

    setCustomInstitutionsByCity((current) => ({
      ...current,
      [selectedCity]: uniqueItems([...(current[selectedCity] ?? []), nextValue]),
    }));
    setSelectedInstitution(nextValue);
    setCustomInstitutionInput("");
  };

  return (
    <div className="flex flex-col gap-6">
      <header className="flex flex-col gap-2">
        <p className="text-sm font-medium uppercase tracking-wide text-teal">Cost planning</p>
        <h1 className="text-3xl font-semibold text-midnight">Living Expense Calculator</h1>
        <p className="max-w-2xl text-sm text-slate">
          Model the monthly cost of living in your destination city and see your yearly baseline before applying for funding or stress testing a plan.
        </p>
      </header>

      <div className="grid gap-6 xl:grid-cols-[1.5fr_0.9fr]">
        <Card>
          <CardHeader>
            <CardTitle>Monthly essentials</CardTitle>
            <CardDescription>Enter your expected recurring costs.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-5">
            <div className="grid gap-4 sm:grid-cols-2">
              {INPUTS.map((item) => (
                <Field key={item.key} label={item.label} htmlFor={item.key} hint={item.hint}>
                  <Input
                    id={item.key}
                    type="number"
                    inputMode="decimal"
                    min="0"
                    step="0.01"
                    value={values[item.key]}
                    onChange={(event) => onNumberChange(item.key, event.target.value)}
                    placeholder="0.00"
                  />
                </Field>
              ))}
            </div>

            <div className="flex flex-col gap-2 rounded-xl border border-border bg-ivory p-4 sm:flex-row sm:items-center sm:justify-between">
              <div>
                <p className="text-sm font-medium text-midnight">Display currency</p>
                <p className="text-xs text-slate">Use the same range as your study plan.</p>
              </div>
              <select
                aria-label="Currency"
                value={currency}
                onChange={(event) => setCurrency(event.target.value)}
                className="h-10 rounded-lg border border-border bg-white px-3 text-sm text-midnight focus-visible:border-teal"
              >
                {CURRENCIES.map((item) => (
                  <option key={item} value={item}>
                    {item}
                  </option>
                ))}
              </select>
            </div>

            <div className="rounded-xl border border-border bg-ivory p-4">
              <div className="mb-3 flex items-center justify-between gap-2">
                <div>
                  <p className="text-sm font-medium text-midnight">Destination comparison</p>
                  <p className="text-xs text-slate">Choose a destination profile and compare the estimate.</p>
                </div>
              </div>

              <div className="grid gap-3 md:grid-cols-3">
                <Field label="Destination country" htmlFor="destination-country">
                  <select
                    id="destination-country"
                    value={selectedCountry}
                    onChange={(event) => {
                      setSelectedCountry(event.target.value);
                      setSelectedCity("");
                      setSelectedInstitution("");
                    }}
                    className="h-10 rounded-lg border border-border bg-white px-3 text-sm text-midnight focus-visible:border-teal"
                  >
                    {countryOptions.map((item) => (
                      <option key={item} value={item}>
                        {item}
                      </option>
                    ))}
                  </select>
                </Field>

                <Field label="City" htmlFor="destination-city">
                  <select
                    id="destination-city"
                    value={selectedCity}
                    onChange={(event) => {
                      setSelectedCity(event.target.value);
                      setSelectedInstitution("");
                    }}
                    className="h-10 rounded-lg border border-border bg-white px-3 text-sm text-midnight focus-visible:border-teal"
                  >
                    {cityOptions.map((item) => (
                      <option key={item} value={item}>
                        {item}
                      </option>
                    ))}
                  </select>
                </Field>

                <Field label="Institution" htmlFor="destination-institution">
                  <select
                    id="destination-institution"
                    value={selectedInstitution}
                    onChange={(event) => setSelectedInstitution(event.target.value)}
                    className="h-10 rounded-lg border border-border bg-white px-3 text-sm text-midnight focus-visible:border-teal"
                  >
                    {institutionOptions.map((item) => (
                      <option key={item} value={item}>
                        {item}
                      </option>
                    ))}
                  </select>
                </Field>
              </div>

              <div className="mt-3 grid gap-3 md:grid-cols-3">
                <Field label="Add country" htmlFor="custom-country">
                  <div className="flex gap-2">
                    <Input
                      id="custom-country"
                      value={customCountryInput}
                      onChange={(event) => setCustomCountryInput(event.target.value)}
                      placeholder="Add country"
                    />
                    <Button type="button" variant="secondary" onClick={handleAddCustomCountry}>
                      Add
                    </Button>
                  </div>
                </Field>

                <div className="flex flex-col gap-1.5">
                  <div className="flex gap-2">
                    <Input
                      id="custom-city"
                      value={customCityInput}
                      onChange={(event) => setCustomCityInput(event.target.value)}
                      placeholder="Add city"
                    />
                    <Button type="button" variant="secondary" onClick={handleAddCustomCity}>
                      Add
                    </Button>
                  </div>
                </div>

                <div className="flex flex-col gap-1.5">
                  <div className="flex gap-2">
                    <Input
                      id="custom-institution"
                      value={customInstitutionInput}
                      onChange={(event) => setCustomInstitutionInput(event.target.value)}
                      placeholder="Add institution"
                    />
                    <Button type="button" variant="secondary" onClick={handleAddCustomInstitution}>
                      Add
                    </Button>
                  </div>
                </div>
              </div>
            </div>

            <div className="flex flex-col gap-3 sm:flex-row">
              <Button
                type="button"
                onClick={() => {
                  setSubmitted(true);
                  setComparisonApplied(false);
                }}
              >
                Calculate my monthly cost
              </Button>
              <Button
                type="button"
                variant="secondary"
                onClick={() => {
                  setSubmitted(true);
                  setComparisonApplied(true);
                }}
              >
                Compare destination cost
              </Button>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Estimate</CardTitle>
            <CardDescription>Based on your monthly assumptions.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {submitted ? (
              <>
                <div className="rounded-xl border border-border bg-white p-4">
                  <p className="text-xs uppercase tracking-wide text-slate">Monthly living estimate</p>
                  <p className="mt-2 text-3xl font-semibold text-midnight tabular-nums">
                    {formatMoney(monthlyTotal, currency)}
                  </p>
                </div>

                <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-1">
                  <div className="rounded-xl border border-border bg-white p-3">
                    <p className="text-xs uppercase tracking-wide text-slate">Annual estimate</p>
                    <p className="mt-2 text-xl font-semibold text-midnight tabular-nums">
                      {formatMoney(annualTotal, currency)}
                    </p>
                  </div>
                  <div className="rounded-xl border border-border bg-white p-3">
                    <p className="text-xs uppercase tracking-wide text-slate">Emergency reserve</p>
                    <p className="mt-2 text-xl font-semibold text-midnight tabular-nums">
                      {formatMoney(emergencyReserve, currency)}
                    </p>
                  </div>
                </div>
              </>
            ) : (
              <p className="text-sm text-slate">
                Enter your monthly costs and click calculate to see the estimated total.
              </p>
            )}

            {comparisonApplied && (
              <div className="rounded-xl border border-border bg-ivory/60 p-4">
                <div className="mb-3 flex items-center justify-between gap-3">
                  <div>
                    <p className="text-[11px] font-semibold uppercase tracking-wide text-slate">Monthly comparison</p>
                    <p className="mt-1 text-sm font-medium text-midnight">
                      {selectedCountry} • {selectedCity} • {selectedInstitution}
                    </p>
                  </div>
                  <span
                    className={`rounded-full border px-2 py-1 text-[10px] font-medium uppercase tracking-wide ${
                      destinationDelta >= 0
                        ? "border-red/30 bg-red/10 text-red"
                        : "border-teal/30 bg-teal/10 text-teal-dark"
                    }`}
                  >
                    {destinationDelta >= 0 ? "Higher cost" : "Lower cost"}
                  </span>
                </div>

                <div className="flex flex-col gap-2 text-xs">
                  <div className="flex items-center justify-between gap-3 rounded-lg border border-border bg-white px-3 py-2">
                    <span className="text-slate">Baseline monthly</span>
                    <span className="tabular-nums font-medium text-midnight">{formatMoney(monthlyTotal, currency)}</span>
                  </div>
                  <div className="flex items-center justify-between gap-3 rounded-lg border border-border bg-white px-3 py-2">
                    <span className="text-slate">Selected destination</span>
                    <span className="tabular-nums font-medium text-midnight">{formatMoney(destinationMonthlyTotal, currency)}</span>
                  </div>
                  <div className="flex items-center justify-between gap-3 rounded-lg border border-border bg-white px-3 py-2">
                    <span className="text-slate">Monthly delta</span>
                    <span className={`tabular-nums font-medium ${destinationDelta >= 0 ? "text-red" : "text-teal-dark"}`}>
                      {formatMoney(destinationDelta, currency)}
                    </span>
                  </div>
                  <div className="flex items-center justify-between gap-3 rounded-lg border border-border bg-white px-3 py-2">
                    <span className="text-slate">Annual equivalent</span>
                    <span className="tabular-nums font-medium text-midnight">{formatMoney(destinationAnnualTotal, currency)}</span>
                  </div>
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
