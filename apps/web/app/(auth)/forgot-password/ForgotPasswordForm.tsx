"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";

import { Button } from "@/components/ui/Button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/Card";
import { Field, Input } from "@/components/ui/Input";

const formSchema = z.object({
  email: z.string().email("Enter a valid email."),
});
type FormValues = z.infer<typeof formSchema>;

export function ForgotPasswordForm() {
  const [submitted, setSubmitted] = useState(false);

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<FormValues>({
    resolver: zodResolver(formSchema),
    defaultValues: { email: "" },
  });

  async function onSubmit(values: FormValues) {
    await fetch("/api/auth/forgot-password", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(values),
    });
    // Always show success to avoid email enumeration.
    setSubmitted(true);
  }

  return (
    <Card className="w-full max-w-md">
      <CardHeader>
        <CardTitle>Reset your password</CardTitle>
        <CardDescription>
          Enter the email associated with your account. If it exists, we'll
          send instructions for resetting your password.
        </CardDescription>
      </CardHeader>
      <CardContent>
        {submitted ? (
          <p className="text-sm text-slate" role="status">
            If an account exists for that email, a reset link is on its way.
            You can close this page.
          </p>
        ) : (
          <form
            noValidate
            onSubmit={handleSubmit(onSubmit)}
            className="flex flex-col gap-4"
          >
            <Field label="Email" htmlFor="email" required error={errors.email?.message}>
              <Input
                id="email"
                type="email"
                autoComplete="email"
                invalid={Boolean(errors.email)}
                {...register("email")}
              />
            </Field>
            <Button type="submit" isLoading={isSubmitting}>
              Send reset instructions
            </Button>
            <a className="text-sm text-teal hover:underline" href="/sign-in">
              Back to sign in
            </a>
          </form>
        )}
      </CardContent>
    </Card>
  );
}