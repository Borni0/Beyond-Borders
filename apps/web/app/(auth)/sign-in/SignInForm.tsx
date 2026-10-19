"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useRouter, useSearchParams } from "next/navigation";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";

import { Button } from "@/components/ui/Button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/Card";
import { Field, Input } from "@/components/ui/Input";

const formSchema = z.object({
  email: z.string().email("Enter a valid email."),
  password: z.string().min(1, "Password is required."),
});
type FormValues = z.infer<typeof formSchema>;

export function SignInForm() {
  const router = useRouter();
  const params = useSearchParams();
  const nextPath = params.get("next") ?? "/dashboard";
  const [serverError, setServerError] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<FormValues>({
    resolver: zodResolver(formSchema),
    defaultValues: { email: "", password: "" },
  });

  async function onSubmit(values: FormValues) {
    setServerError(null);
    try {
      const res = await fetch("/api/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(values),
      });
      if (!res.ok) {
        const body = (await res.json().catch(() => null)) as
          | { error?: { message?: string } }
          | null;
        throw new Error(body?.error?.message ?? "Sign-in failed.");
      }
      router.replace(nextPath);
      router.refresh();
    } catch (err) {
      setServerError(err instanceof Error ? err.message : "Sign-in failed.");
    }
  }

  return (
    <Card className="w-full max-w-md">
      <CardHeader>
        <CardTitle>Welcome back</CardTitle>
        <CardDescription>Sign in to your Beyond Borders account.</CardDescription>
      </CardHeader>
      <CardContent>
        <form noValidate onSubmit={handleSubmit(onSubmit)} className="flex flex-col gap-4">
          <Field label="Email" htmlFor="email" required error={errors.email?.message}>
            <Input
              id="email"
              type="email"
              autoComplete="email"
              invalid={Boolean(errors.email)}
              {...register("email")}
            />
          </Field>
          <Field label="Password" htmlFor="password" required error={errors.password?.message}>
            <Input
              id="password"
              type="password"
              autoComplete="current-password"
              invalid={Boolean(errors.password)}
              {...register("password")}
            />
          </Field>
          {serverError ? (
            <p role="alert" className="text-sm text-red">
              {serverError}
            </p>
          ) : null}
          <Button type="submit" isLoading={isSubmitting}>
            Sign in
          </Button>
          <div className="flex flex-col gap-1 text-sm text-slate">
            <a className="hover:underline" href="/forgot-password">
              Forgot your password?
            </a>
            <a className="hover:underline" href="/sign-up">
              Create an account
            </a>
          </div>
        </form>
      </CardContent>
    </Card>
  );
}