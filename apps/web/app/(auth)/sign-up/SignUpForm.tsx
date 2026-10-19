"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";

import { Button } from "@/components/ui/Button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/Card";
import { Field, Input } from "@/components/ui/Input";

const formSchema = z.object({
  name: z.string().min(1, "Name is required.").max(120),
  email: z.string().email("Enter a valid email."),
  password: z
    .string()
    .min(10, "Password must be at least 10 characters.")
    .max(128, "Password is too long."),
  home_country: z
    .string()
    .length(2, "Use a 2-letter country code (e.g. BD, DE, US).")
    .optional()
    .or(z.literal("")),
  home_currency: z.string().length(3, "Use a 3-letter currency code (e.g. USD)."),
  display_currency: z.string().length(3, "Use a 3-letter currency code (e.g. USD)."),
});
type FormValues = z.infer<typeof formSchema>;

export function SignUpForm() {
  const router = useRouter();
  const [serverError, setServerError] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<FormValues>({
    resolver: zodResolver(formSchema),
    defaultValues: {
      name: "",
      email: "",
      password: "",
      home_country: "",
      home_currency: "USD",
      display_currency: "USD",
    },
  });

  async function onSubmit(values: FormValues) {
    setServerError(null);
    const payload = {
      ...values,
      home_country: values.home_country ? values.home_country.toUpperCase() : undefined,
      home_currency: values.home_currency.toUpperCase(),
      display_currency: values.display_currency.toUpperCase(),
    };
    try {
      const res = await fetch("/api/auth/register", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      if (!res.ok) {
        const body = (await res.json().catch(() => null)) as
          | { error?: { message?: string } }
          | null;
        throw new Error(body?.error?.message ?? "Could not create account.");
      }
      router.replace("/dashboard");
      router.refresh();
    } catch (err) {
      setServerError(err instanceof Error ? err.message : "Could not create account.");
    }
  }

  return (
    <Card className="w-full max-w-lg">
      <CardHeader>
        <CardTitle>Create your account</CardTitle>
        <CardDescription>
          Set up the basics. You can update your home country, currencies, and
          study plan later.
        </CardDescription>
      </CardHeader>
      <CardContent>
        <form noValidate onSubmit={handleSubmit(onSubmit)} className="flex flex-col gap-4">
          <Field label="Full name" htmlFor="name" required error={errors.name?.message}>
            <Input
              id="name"
              autoComplete="name"
              invalid={Boolean(errors.name)}
              {...register("name")}
            />
          </Field>
          <Field label="Email" htmlFor="email" required error={errors.email?.message}>
            <Input
              id="email"
              type="email"
              autoComplete="email"
              invalid={Boolean(errors.email)}
              {...register("email")}
            />
          </Field>
          <Field
            label="Password"
            htmlFor="password"
            required
            hint="At least 10 characters."
            error={errors.password?.message}
          >
            <Input
              id="password"
              type="password"
              autoComplete="new-password"
              invalid={Boolean(errors.password)}
              {...register("password")}
            />
          </Field>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
            <Field
              label="Home country"
              htmlFor="home_country"
              hint="2-letter code (optional)"
              error={errors.home_country?.message}
            >
              <Input
                id="home_country"
                placeholder="BD"
                maxLength={2}
                invalid={Boolean(errors.home_country)}
                {...register("home_country")}
              />
            </Field>
            <Field
              label="Home currency"
              htmlFor="home_currency"
              required
              error={errors.home_currency?.message}
            >
              <Input
                id="home_currency"
                maxLength={3}
                invalid={Boolean(errors.home_currency)}
                {...register("home_currency")}
              />
            </Field>
            <Field
              label="Display currency"
              htmlFor="display_currency"
              required
              error={errors.display_currency?.message}
            >
              <Input
                id="display_currency"
                maxLength={3}
                invalid={Boolean(errors.display_currency)}
                {...register("display_currency")}
              />
            </Field>
          </div>
          {serverError ? (
            <p role="alert" className="text-sm text-red">
              {serverError}
            </p>
          ) : null}
          <Button type="submit" isLoading={isSubmitting}>
            Create account
          </Button>
          <p className="text-sm text-slate">
            Already have an account?{" "}
            <a className="text-teal hover:underline" href="/sign-in">
              Sign in
            </a>
          </p>
        </form>
      </CardContent>
    </Card>
  );
}