"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";

import { updateUserRequestSchema } from "@beyond-borders/shared-types";

import { Button } from "@/components/ui/Button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/Card";
import { Field, Input } from "@/components/ui/Input";

const formSchema = updateUserRequestSchema.extend({
  home_country: z.string().length(2).or(z.literal("")).optional(),
});
type FormValues = z.infer<typeof formSchema>;

interface SettingsFormProps {
  initial: FormValues;
}

export function SettingsForm({ initial }: SettingsFormProps) {
  const [serverError, setServerError] = useState<string | null>(null);
  const [savedAt, setSavedAt] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting, isDirty },
  } = useForm<FormValues>({
    resolver: zodResolver(formSchema),
    defaultValues: initial,
  });

  async function onSubmit(values: FormValues) {
    setServerError(null);
    setSavedAt(null);
    const payload = {
      ...values,
      home_country: values.home_country ? values.home_country.toUpperCase() : undefined,
      home_currency: values.home_currency?.toUpperCase(),
      display_currency: values.display_currency?.toUpperCase(),
    };
    try {
      const res = await fetch("/api/users/me", {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      // Note: in this scaffold PATCH goes via the auth proxy path; for /users/me
      // we route through the backend directly. Keep the proxy-less path here.
      if (!res.ok) {
        const body = (await res.json().catch(() => null)) as
          | { error?: { message?: string } }
          | null;
        throw new Error(body?.error?.message ?? "Could not save your settings.");
      }
      setSavedAt(new Date().toLocaleTimeString());
    } catch (err) {
      setServerError(err instanceof Error ? err.message : "Could not save your settings.");
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Profile</CardTitle>
        <CardDescription>
          Update your display name, home country, and currencies.
        </CardDescription>
      </CardHeader>
      <CardContent>
        <form noValidate onSubmit={handleSubmit(onSubmit)} className="flex flex-col gap-4">
          <Field label="Display name" htmlFor="name" error={errors.name?.message}>
            <Input id="name" autoComplete="name" {...register("name")} />
          </Field>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
            <Field
              label="Home country"
              htmlFor="home_country"
              hint="2-letter code"
              error={errors.home_country?.message}
            >
              <Input
                id="home_country"
                maxLength={2}
                placeholder="BD"
                {...register("home_country")}
              />
            </Field>
            <Field label="Home currency" htmlFor="home_currency" error={errors.home_currency?.message}>
              <Input id="home_currency" maxLength={3} {...register("home_currency")} />
            </Field>
            <Field
              label="Display currency"
              htmlFor="display_currency"
              error={errors.display_currency?.message}
            >
              <Input id="display_currency" maxLength={3} {...register("display_currency")} />
            </Field>
          </div>
          {serverError ? (
            <p role="alert" className="text-sm text-red">
              {serverError}
            </p>
          ) : null}
          {savedAt ? (
            <p role="status" className="text-sm text-teal">
              Saved at {savedAt}.
            </p>
          ) : null}
          <Button type="submit" isLoading={isSubmitting} disabled={!isDirty && !isSubmitting}>
            Save changes
          </Button>
        </form>
      </CardContent>
    </Card>
  );
}