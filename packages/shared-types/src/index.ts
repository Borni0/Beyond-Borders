/**
 * Shared types between the Next.js app and any future SDKs.
 * Mirrors the Pydantic schemas in services/api/app/schemas/.
 *
 * Phase 1: auth + study plan / cost / funding / readiness.
 * Later phases add scenarios, expenses, FX provider, etc.
 */
import { z } from "zod";

// ---------- Error envelope (mirrors services/api/app/schemas/common.py) ----------
export const apiErrorSchema = z.object({
  error: z.object({
    code: z.string(),
    message: z.string(),
    details: z.record(z.string(), z.string()).optional(),
  }),
});
export type ApiError = z.infer<typeof apiErrorSchema>;

// ---------- User ----------
export const userSchema = z.object({
  id: z.string().uuid(),
  email: z.string().email(),
  name: z.string(),
  home_country: z.string().length(2).nullable(),
  home_currency: z.string().length(3),
  display_currency: z.string().length(3),
  created_at: z.string(),
  updated_at: z.string(),
});
export type User = z.infer<typeof userSchema>;

// ---------- Auth requests ----------
export const registerRequestSchema = z.object({
  email: z.string().email(),
  password: z.string().min(10).max(128),
  name: z.string().min(1).max(120),
  home_country: z.string().length(2).optional(),
  home_currency: z.string().length(3).default("USD"),
  display_currency: z.string().length(3).default("USD"),
});
export type RegisterRequest = z.infer<typeof registerRequestSchema>;

export const loginRequestSchema = z.object({
  email: z.string().email(),
  password: z.string().min(1),
});
export type LoginRequest = z.infer<typeof loginRequestSchema>;

export const forgotPasswordRequestSchema = z.object({
  email: z.string().email(),
});
export type ForgotPasswordRequest = z.infer<typeof forgotPasswordRequestSchema>;

export const resetPasswordRequestSchema = z.object({
  token: z.string().min(1),
  new_password: z.string().min(10).max(128),
});
export type ResetPasswordRequest = z.infer<typeof resetPasswordRequestSchema>;

export const updateUserRequestSchema = z
  .object({
    name: z.string().min(1).max(120).optional(),
    home_country: z.string().length(2).nullable().optional(),
    home_currency: z.string().length(3).optional(),
    display_currency: z.string().length(3).optional(),
  })
  .strict();
export type UpdateUserRequest = z.infer<typeof updateUserRequestSchema>;

// ---------- Study plan ----------
export const studyPlanSchema = z.object({
  id: z.string().uuid(),
  name: z.string(),
  destination_country: z.string().length(2).nullable(),
  base_currency: z.string().length(3),
  start_date: z.string(), // ISO date (YYYY-MM-DD)
  duration_months: z.number().int().positive(),
  end_date: z.string(),
  notes: z.string().nullable(),
  // ---- Phase 1 readiness enrichment ----
  institution_name: z.string().nullable(),
  program_name: z.string().nullable(),
  city: z.string().nullable(),
  tuition_amount: z.string().nullable(), // Decimal as string
  tuition_currency: z.string().length(3).nullable(),
  home_currency: z.string().length(3).nullable(),
  created_at: z.string(),
  updated_at: z.string(),
});
export type StudyPlan = z.infer<typeof studyPlanSchema>;

export const studyPlanCreateSchema = z.object({
  name: z.string().min(1).max(120),
  destination_country: z.string().length(2).optional(),
  base_currency: z.string().length(3),
  start_date: z.string(),
  duration_months: z.number().int().positive().max(120),
  notes: z.string().max(2000).optional(),
  institution_name: z.string().max(200).optional(),
  program_name: z.string().max(200).optional(),
  city: z.string().max(120).optional(),
  tuition_amount: z.string().optional(),
  tuition_currency: z.string().length(3).optional(),
  home_currency: z.string().length(3).optional(),
});
export type StudyPlanCreate = z.infer<typeof studyPlanCreateSchema>;

export const studyPlanUpdateSchema = z
  .object({
    name: z.string().min(1).max(120).optional(),
    destination_country: z.string().length(2).nullable().optional(),
    base_currency: z.string().length(3).optional(),
    start_date: z.string().optional(),
    duration_months: z.number().int().positive().max(120).optional(),
    notes: z.string().max(2000).nullable().optional(),
    institution_name: z.string().max(200).nullable().optional(),
    program_name: z.string().max(200).nullable().optional(),
    city: z.string().max(120).nullable().optional(),
    tuition_amount: z.string().nullable().optional(),
    tuition_currency: z.string().length(3).nullable().optional(),
    home_currency: z.string().length(3).nullable().optional(),
  })
  .strict();
export type StudyPlanUpdate = z.infer<typeof studyPlanUpdateSchema>;

// ---------- Cost item ----------
export const costCategoryEnum = z.enum([
  "tuition",
  "accommodation",
  "food",
  "transport",
  "utilities",
  "insurance",
  "travel",
  "visa",
  "deposits",
  "study_materials",
  "personal",
  "miscellaneous",
]);
export type CostCategory = z.infer<typeof costCategoryEnum>;

export const frequencyEnum = z.enum([
  "one_time",
  "monthly",
  "quarterly",
  "semester",
  "annual",
]);
export type Frequency = z.infer<typeof frequencyEnum>;

export const costItemSchema = z.object({
  id: z.string().uuid(),
  plan_id: z.string().uuid(),
  category: costCategoryEnum,
  description: z.string(),
  amount: z.string(), // Decimal as string
  currency: z.string().length(3),
  frequency: frequencyEnum,
  start_date: z.string().nullable(),
  end_date: z.string().nullable(),
  is_one_time: z.boolean(),
  is_refundable: z.boolean(),
  due_before_departure: z.boolean(),
  source_id: z.string().uuid().nullable(),
  created_at: z.string(),
  updated_at: z.string(),
});
export type CostItem = z.infer<typeof costItemSchema>;

export const costItemCreateSchema = z.object({
  category: costCategoryEnum,
  description: z.string().max(500).default(""),
  amount: z.string(),
  currency: z.string().length(3),
  frequency: frequencyEnum,
  start_date: z.string().nullable().optional(),
  end_date: z.string().nullable().optional(),
  is_one_time: z.boolean().default(false),
  is_refundable: z.boolean().default(false),
  due_before_departure: z.boolean().default(false),
  source_id: z.string().uuid().nullable().optional(),
});
export type CostItemCreate = z.infer<typeof costItemCreateSchema>;

export const costItemUpdateSchema = z
  .object({
    category: costCategoryEnum.optional(),
    description: z.string().max(500).optional(),
    amount: z.string().optional(),
    currency: z.string().length(3).optional(),
    frequency: frequencyEnum.optional(),
    start_date: z.string().nullable().optional(),
    end_date: z.string().nullable().optional(),
    is_one_time: z.boolean().optional(),
    is_refundable: z.boolean().optional(),
    due_before_departure: z.boolean().optional(),
    source_id: z.string().uuid().nullable().optional(),
  })
  .strict();
export type CostItemUpdate = z.infer<typeof costItemUpdateSchema>;

// ---------- Funding source ----------
export const fundingTypeEnum = z.enum([
  "savings",
  "family",
  "scholarship",
  "loan",
  "income",
  "other",
]);
export type FundingType = z.infer<typeof fundingTypeEnum>;

export const fundingStatusEnum = z.enum([
  "confirmed",
  "conditional",
  "expected",
  "unavailable",
]);
export type FundingStatus = z.infer<typeof fundingStatusEnum>;

export const fundingSourceSchema = z.object({
  id: z.string().uuid(),
  plan_id: z.string().uuid(),
  name: z.string(),
  funding_type: fundingTypeEnum,
  amount: z.string(),
  currency: z.string().length(3),
  status: fundingStatusEnum,
  expected_date: z.string().nullable(),
  notes: z.string().nullable(),
  created_at: z.string(),
  updated_at: z.string(),
});
export type FundingSource = z.infer<typeof fundingSourceSchema>;

export const fundingSourceCreateSchema = z.object({
  name: z.string().min(1).max(120),
  funding_type: fundingTypeEnum,
  amount: z.string(),
  currency: z.string().length(3),
  status: fundingStatusEnum,
  expected_date: z.string().nullable().optional(),
  notes: z.string().max(2000).nullable().optional(),
});
export type FundingSourceCreate = z.infer<typeof fundingSourceCreateSchema>;

export const fundingSourceUpdateSchema = z
  .object({
    name: z.string().min(1).max(120).optional(),
    funding_type: fundingTypeEnum.optional(),
    amount: z.string().optional(),
    currency: z.string().length(3).optional(),
    status: fundingStatusEnum.optional(),
    expected_date: z.string().nullable().optional(),
    notes: z.string().max(2000).nullable().optional(),
  })
  .strict();
export type FundingSourceUpdate = z.infer<typeof fundingSourceUpdateSchema>;

// ---------- Data source registry ----------
export const dataSourceSchema = z.object({
  id: z.string().uuid(),
  label: z.string(),
  url: z.string().nullable(),
  notes: z.string().nullable(),
  created_at: z.string(),
  updated_at: z.string(),
});
export type DataSource = z.infer<typeof dataSourceSchema>;

export const dataSourceCreateSchema = z.object({
  label: z.string().min(1).max(120),
  url: z.string().max(2000).nullable().optional(),
  notes: z.string().max(2000).nullable().optional(),
});
export type DataSourceCreate = z.infer<typeof dataSourceCreateSchema>;

export const dataSourceUpdateSchema = z
  .object({
    label: z.string().min(1).max(120).optional(),
    url: z.string().max(2000).nullable().optional(),
    notes: z.string().max(2000).nullable().optional(),
  })
  .strict();
export type DataSourceUpdate = z.infer<typeof dataSourceUpdateSchema>;

// ---------- Exchange rate ----------
export const rateTypeEnum = z.enum([
  "reference",
  "provider_quote",
  "user_entered",
]);
export type RateType = z.infer<typeof rateTypeEnum>;

export const exchangeRateSchema = z.object({
  id: z.string().uuid(),
  base_currency: z.string().length(3),
  quote_currency: z.string().length(3),
  rate: z.string(),
  rate_type: rateTypeEnum,
  observed_at: z.string(),
  created_at: z.string(),
  updated_at: z.string(),
});
export type ExchangeRate = z.infer<typeof exchangeRateSchema>;

export const exchangeRateUpsertSchema = z.object({
  base_currency: z.string().length(3),
  quote_currency: z.string().length(3),
  rate: z.string(),
  rate_type: rateTypeEnum.default("user_entered"),
  observed_at: z.string(),
});
export type ExchangeRateUpsert = z.infer<typeof exchangeRateUpsertSchema>;

// ---------- Readiness result ----------
export const yearCostSchema = z.object({
  year_index: z.number().int().positive(),
  recurring_total: z.string(),
  one_time_total: z.string(),
  total: z.string(),
});
export type YearCost = z.infer<typeof yearCostSchema>;

export const costBreakdownSchema = z.object({
  base_currency: z.string().length(3),
  per_year: z.array(yearCostSchema),
  first_year_cost: z.string(),
  total_projected_cost: z.string(),
  refundable_deposits: z.string(),
  per_category: z.record(z.string(), z.string()),
});
export type CostBreakdown = z.infer<typeof costBreakdownSchema>;

export const fundingBreakdownSchema = z.object({
  base_currency: z.string().length(3),
  confirmed_total: z.string(),
  conditional_total: z.string(),
  expected_total: z.string(),
  unavailable_total: z.string(),
  eligible_confirmed: z.string(),
  eligible_with_conditional: z.string(),
  available_before_departure: z.string(),
});
export type FundingBreakdown = z.infer<typeof fundingBreakdownSchema>;

export const readinessStatusCodeEnum = z.enum([
  "funding_gap_identified",
  "upfront_cash_gap",
  "conditional_funding",
  "scenario_sensitive",
  "no_modeled_shortfall",
  "needs_more_information",
]);
export type ReadinessStatusCode = z.infer<typeof readinessStatusCodeEnum>;

export const readinessResultSchema = z.object({
  plan_id: z.string().uuid(),
  base_currency: z.string().length(3),
  breakdown: costBreakdownSchema,
  funding: fundingBreakdownSchema,
  funding_gap: z.string(),
  funding_surplus: z.string(),
  upfront_cash_requirement: z.string(),
  upfront_cash_gap: z.string(),
  upfront_cash_window_days: z.number().int().positive(),
  statuses: z.array(readinessStatusCodeEnum),
  missing_inputs: z.array(z.string()),
  notes: z.array(z.string()),
  // ---- Phase 1 readiness enrichment ----
  first_year_funding_gap: z.string(),
  coverage_pct: z.string().nullable(), // null when there is no cost to compare against
  potential_gap_after_expected: z.string(),
});
export type ReadinessResult = z.infer<typeof readinessResultSchema>;

// ---------- Phase 2: payment events + savings goals + funding-plan ----------

// Payment categories mirror the cost-item vocabulary.
export const paymentCategoryEnum = costCategoryEnum;
export type PaymentCategory = CostCategory;

// Stored statuses. `overdue` is derived, not stored, and is included in
// the public display-status enum returned by the API.
export const paymentStatusEnum = z.enum([
  "planned",
  "scheduled",
  "paid",
  "cancelled",
]);
export type PaymentStatus = z.infer<typeof paymentStatusEnum>;

export const paymentStatusDisplayEnum = z.enum([
  "planned",
  "scheduled",
  "paid",
  "overdue",
  "cancelled",
]);
export type PaymentStatusDisplay = z.infer<typeof paymentStatusDisplayEnum>;

export const recurrenceFrequencyEnum = z.enum([
  "monthly",
  "quarterly",
  "semester",
  "annual",
]);
export type RecurrenceFrequency = z.infer<typeof recurrenceFrequencyEnum>;

export const paymentEventSchema = z.object({
  id: z.string().uuid(),
  user_id: z.string().uuid(),
  plan_id: z.string().uuid().nullable(),
  title: z.string(),
  category: paymentCategoryEnum,
  amount: z.string(),
  currency: z.string().length(3),
  due_date: z.string(),
  display_status: paymentStatusDisplayEnum,
  notes: z.string().nullable(),
  is_recurring: z.boolean(),
  recurrence_frequency: recurrenceFrequencyEnum.nullable(),
  recurrence_end_date: z.string().nullable(),
  created_at: z.string(),
  updated_at: z.string(),
});
export type PaymentEvent = z.infer<typeof paymentEventSchema>;

export const paymentEventCreateSchema = z.object({
  title: z.string().min(1).max(200),
  category: paymentCategoryEnum,
  amount: z.string(),
  currency: z.string().length(3),
  due_date: z.string(),
  status: paymentStatusEnum.default("planned"),
  notes: z.string().max(2000).nullable().optional(),
  is_recurring: z.boolean().default(false),
  recurrence_frequency: recurrenceFrequencyEnum.nullable().optional(),
  recurrence_end_date: z.string().nullable().optional(),
  plan_id: z.string().uuid().nullable().optional(),
});
export type PaymentEventCreate = z.infer<typeof paymentEventCreateSchema>;

export const paymentEventUpdateSchema = z
  .object({
    title: z.string().min(1).max(200).optional(),
    category: paymentCategoryEnum.optional(),
    amount: z.string().optional(),
    currency: z.string().length(3).optional(),
    due_date: z.string().optional(),
    status: paymentStatusEnum.optional(),
    notes: z.string().max(2000).nullable().optional(),
    is_recurring: z.boolean().optional(),
    recurrence_frequency: recurrenceFrequencyEnum.nullable().optional(),
    recurrence_end_date: z.string().nullable().optional(),
    plan_id: z.string().uuid().nullable().optional(),
  })
  .strict();
export type PaymentEventUpdate = z.infer<typeof paymentEventUpdateSchema>;

export const savingsGoalSchema = z.object({
  id: z.string().uuid(),
  user_id: z.string().uuid(),
  plan_id: z.string().uuid().nullable(),
  name: z.string(),
  target_amount: z.string(),
  current_amount: z.string(),
  currency: z.string().length(3),
  target_date: z.string(),
  notes: z.string().nullable(),
  created_at: z.string(),
  updated_at: z.string(),
});
export type SavingsGoal = z.infer<typeof savingsGoalSchema>;

export const savingsGoalCreateSchema = z.object({
  name: z.string().min(1).max(120),
  target_amount: z.string(),
  current_amount: z.string().default("0"),
  currency: z.string().length(3),
  target_date: z.string(),
  notes: z.string().max(2000).nullable().optional(),
  plan_id: z.string().uuid().nullable().optional(),
});
export type SavingsGoalCreate = z.infer<typeof savingsGoalCreateSchema>;

export const savingsGoalUpdateSchema = z
  .object({
    name: z.string().min(1).max(120).optional(),
    target_amount: z.string().optional(),
    current_amount: z.string().optional(),
    currency: z.string().length(3).optional(),
    target_date: z.string().optional(),
    notes: z.string().max(2000).nullable().optional(),
    plan_id: z.string().uuid().nullable().optional(),
  })
  .strict();
export type SavingsGoalUpdate = z.infer<typeof savingsGoalUpdateSchema>;

// The funding-plan summary, returned by
// `GET /api/v1/plans/{id}/funding-plan/summary`. The bucket shape is
// intentionally permissive — backend may add fields over time.
export const fundingBucketSchema = z.object({
  currency: z.string().length(3),
  total: z.string(),
  confirmed: z.string(),
  conditional: z.string(),
  expected: z.string(),
  unavailable: z.string(),
});
export type FundingBucket = z.infer<typeof fundingBucketSchema>;

export const savingsBucketSchema = z.object({
  currency: z.string().length(3),
  target_total: z.string(),
  current_total: z.string(),
});
export type SavingsBucket = z.infer<typeof savingsBucketSchema>;

export const fundingPlanSummarySchema = z.object({
  plan_id: z.string().uuid(),
  base_currency: z.string().length(3),
  buckets: z.array(fundingBucketSchema),
  savings_buckets: z.array(savingsBucketSchema),
  upcoming_payments: z.string(),
  overdue_payments: z.string(),
  upcoming_payments_count: z.number().int().nonnegative(),
  overdue_payments_count: z.number().int().nonnegative(),
  payments_by_currency: z.record(z.string(), z.string()),
  notes: z.array(z.string()),
});
export type FundingPlanSummary = z.infer<typeof fundingPlanSummarySchema>;

// Timeline entry — projected recurrences included.
export const timelineEntrySchema = z.object({
  event_id: z.string().uuid(),
  title: z.string(),
  category: paymentCategoryEnum,
  amount: z.string(),
  currency: z.string().length(3),
  due_date: z.string(),
  display_status: paymentStatusDisplayEnum,
  plan_id: z.string().uuid().nullable(),
  is_recurring: z.boolean(),
});
export type TimelineEntry = z.infer<typeof timelineEntrySchema>;

export const fundingPlanTimelineSchema = z.object({
  plan_id: z.string().uuid(),
  entries: z.array(timelineEntrySchema),
});
export type FundingPlanTimeline = z.infer<typeof fundingPlanTimelineSchema>;

export const convertRequestSchema = z.object({
  from_amount: z.string(),
  from_currency: z.string().length(3),
  to_currency: z.string().length(3),
  fee_pct: z.string().nullable().optional(),
});
export type ConvertRequest = z.infer<typeof convertRequestSchema>;

export const convertResponseSchema = z.object({
  from_currency: z.string().length(3),
  to_currency: z.string().length(3),
  from_amount: z.string(),
  converted_amount: z.string(),
  fee_pct: z.string(),
  fee_amount: z.string(),
  total_cost: z.string(),
  rate_used: z.string(),
  rate_type: z.string(),
});
export type ConvertResponse = z.infer<typeof convertResponseSchema>;

// ---------- Decision Studio (Phase 3) ----------------------------------------

export const scenarioAdjustmentTypeEnum = z.enum([
  "rent_increase_pct",
  "tuition_increase_pct",
  "scholarship_reduction_pct",
  "family_support_delay_days",
  "fx_shift_pct",
  "deposit_change",
  "custom_note",
]);
export type ScenarioAdjustmentType = z.infer<typeof scenarioAdjustmentTypeEnum>;

export const scenarioAdjustmentSchema = z.object({
  type: scenarioAdjustmentTypeEnum,
  value: z.string().max(40).nullable().optional(),
  note: z.string().max(500).nullable().optional(),
});
export type ScenarioAdjustment = z.infer<typeof scenarioAdjustmentSchema>;

export const scenarioSpecSchema = z.object({
  plan_id: z.string().min(1).max(64),
  name: z.string().min(1).max(80).default("baseline"),
  adjustments: z.array(scenarioAdjustmentSchema).default([]),
  note: z.string().max(500).nullable().optional(),
});
export type ScenarioSpec = z.infer<typeof scenarioSpecSchema>;

export const compareRequestSchema = z.object({
  study_plan_ids: z.array(z.string()).min(2).max(3),
  scenarios: z.array(scenarioSpecSchema).optional(),
  upfront_window_days: z.number().int().min(1).max(365).default(30),
});
export type CompareRequest = z.infer<typeof compareRequestSchema>;

export const comparisonPlanSchema = z.object({
  id: z.string(),
  name: z.string(),
  destination_country: z.string().nullable().optional(),
  institution_name: z.string().nullable().optional(),
  program_name: z.string().nullable().optional(),
  city: z.string().nullable().optional(),
  base_currency: z.string(),
  start_date: z.string(),
  duration_months: z.number().int(),
  end_date: z.string(),
  scenario_name: z.string(),
  data_completeness: z.enum(["complete", "partial", "missing"]),
  missing_inputs: z.array(z.string()),
});
export type ComparisonPlan = z.infer<typeof comparisonPlanSchema>;

export const comparisonCostMetricsSchema = z.object({
  base_currency: z.string(),
  total_projected_cost: z.string(),
  first_year_cost: z.string(),
  refundable_deposits: z.string(),
  per_category: z.record(z.string(), z.string()),
  per_year: z.array(z.record(z.string(), z.unknown())),
  cost_for_displayed_period: z.string(),
  displayed_period_months: z.number().int(),
});
export type ComparisonCostMetrics = z.infer<typeof comparisonCostMetricsSchema>;

export const comparisonFundingMetricsSchema = z.object({
  base_currency: z.string(),
  confirmed_total: z.string(),
  conditional_total: z.string(),
  expected_total: z.string(),
  unavailable_total: z.string(),
  eligible_confirmed: z.string(),
  eligible_with_conditional: z.string(),
  funding_gap: z.string(),
  funding_surplus: z.string(),
  available_before_departure: z.string(),
});
export type ComparisonFundingMetrics = z.infer<typeof comparisonFundingMetricsSchema>;

export const comparisonUpfrontMetricsSchema = z.object({
  base_currency: z.string(),
  upfront_window_days: z.number().int(),
  upfront_cash_requirement: z.string(),
  upfront_cash_gap: z.string(),
});
export type ComparisonUpfrontMetrics = z.infer<typeof comparisonUpfrontMetricsSchema>;

export const comparisonPaymentRowSchema = z.object({
  id: z.string(),
  title: z.string(),
  category: z.string(),
  amount: z.string(),
  currency: z.string(),
  due_date: z.string().nullable().optional(),
  display_status: z.string(),
});
export type ComparisonPaymentRow = z.infer<typeof comparisonPaymentRowSchema>;

export const deadlinePlanRankingSchema = z.object({
  plan_id: z.string(),
  rank: z.number().int(),
  score: z.number().int(),
  status: z.enum(["no_shortfall", "shortfall", "no_payment_data"]),
  earliest_shortfall_date: z.string().nullable().optional(),
  shortfall_amount: z.string().nullable().optional(),
  funded_by_deadline: z.string().nullable().optional(),
  required_by_deadline: z.string().nullable().optional(),
  rationale: z.string(),
});
export type DeadlinePlanRanking = z.infer<typeof deadlinePlanRankingSchema>;

export const comparisonRowSchema = z.object({
  plan: comparisonPlanSchema,
  cost: comparisonCostMetricsSchema,
  funding: comparisonFundingMetricsSchema,
  upfront: comparisonUpfrontMetricsSchema,
  earliest_payment: comparisonPaymentRowSchema.nullable(),
  payments: z.array(comparisonPaymentRowSchema),
  deadline_status: z.enum(["no_shortfall", "shortfall", "no_payment_data"]).nullable().optional(),
  earliest_shortfall_date: z.string().nullable().optional(),
  shortfall_amount: z.string().nullable().optional(),
  deadline_rationale: z.string().nullable().optional(),
});
export type ComparisonRow = z.infer<typeof comparisonRowSchema>;

export const comparisonWarningCodeEnum = z.enum([
  "missing_costs",
  "missing_funding",
  "missing_fx",
  "different_currencies",
  "different_durations",
  "incomplete_data",
  "no_known_payments",
]);
export type ComparisonWarningCode = z.infer<typeof comparisonWarningCodeEnum>;

export const comparisonWarningSchema = z.object({
  code: comparisonWarningCodeEnum,
  message: z.string(),
  plan_ids: z.array(z.string()),
});
export type ComparisonWarning = z.infer<typeof comparisonWarningSchema>;

export const compareResultSchema = z.object({
  comparison_id: z.string().nullable(),
  plans: z.array(comparisonRowSchema),
  warnings: z.array(comparisonWarningSchema),
  generated_at: z.string(),
  calculation_version: z.string(),
  recommended_plan_id: z.string().nullable().optional(),
  winner: z.string().nullable().optional(),
  deadline_rankings: z.array(deadlinePlanRankingSchema).default([]),
  deadline_analysis: z.array(deadlinePlanRankingSchema).default([]),
  ranked_plans: z.array(comparisonRowSchema).default([]),
});
export type CompareResult = z.infer<typeof compareResultSchema>;

export const savedComparisonCreateSchema = z.object({
  name: z.string().min(1).max(120),
  study_plan_ids: z.array(z.string()).min(2).max(3),
  scenarios: z.array(scenarioSpecSchema).optional(),
});
export type SavedComparisonCreate = z.infer<typeof savedComparisonCreateSchema>;

export const savedComparisonUpdateSchema = z.object({
  name: z.string().min(1).max(120).optional(),
  study_plan_ids: z.array(z.string()).min(2).max(3).optional(),
  scenarios: z.array(scenarioSpecSchema).optional(),
});
export type SavedComparisonUpdate = z.infer<typeof savedComparisonUpdateSchema>;

export const savedComparisonPublicSchema = z.object({
  id: z.string(),
  user_id: z.string(),
  name: z.string(),
  study_plan_ids: z.array(z.string()),
  scenarios: z.array(scenarioSpecSchema).nullable(),
  calculation_version: z.string(),
  created_at: z.string(),
  updated_at: z.string(),
});
export type SavedComparisonPublic = z.infer<typeof savedComparisonPublicSchema>;

export const savedComparisonDetailSchema = z.object({
  comparison: savedComparisonPublicSchema,
  result: compareResultSchema,
});
export type SavedComparisonDetail = z.infer<typeof savedComparisonDetailSchema>;

// ---------- Stress Test (Phase 3 — Financial Weather) ----------------------

export const stressScenarioKeyEnum = z.enum([
  "rent_shock",
  "scholarship_cut",
  "tuition_shock",
  "living_expense_shock",
  "fx_shock",
  "family_delay",
  "custom",
]);
export type StressScenarioKey = z.infer<typeof stressScenarioKeyEnum>;

export const stressPresetSchema = z.object({
  label: z.string(),
  description: z.string(),
  default_adjustment: scenarioAdjustmentSchema,
});
export type StressPreset = z.infer<typeof stressPresetSchema>;

export const stressScenarioSchema = z.object({
  id: z.string().uuid(),
  user_id: z.string().uuid(),
  plan_id: z.string().uuid().nullable(),
  name: z.string(),
  scenario_key: stressScenarioKeyEnum,
  adjustments: z.array(scenarioAdjustmentSchema),
  notes: z.string().nullable(),
  created_at: z.string(),
  updated_at: z.string(),
});
export type StressScenario = z.infer<typeof stressScenarioSchema>;

export const stressScenarioCreateSchema = z.object({
  name: z.string().min(1).max(120),
  scenario_key: stressScenarioKeyEnum,
  adjustments: z.array(scenarioAdjustmentSchema).default([]),
  plan_id: z.string().uuid().nullable().optional(),
  notes: z.string().max(2000).nullable().optional(),
});
export type StressScenarioCreate = z.infer<typeof stressScenarioCreateSchema>;

export const stressScenarioUpdateSchema = z
  .object({
    name: z.string().min(1).max(120).optional(),
    scenario_key: stressScenarioKeyEnum.optional(),
    adjustments: z.array(scenarioAdjustmentSchema).optional(),
    plan_id: z.string().uuid().nullable().optional(),
    notes: z.string().max(2000).nullable().optional(),
  })
  .strict();
export type StressScenarioUpdate = z.infer<typeof stressScenarioUpdateSchema>;

const stressDeltaSchema = z.object({
  baseline: z.string(),
  scenario: z.string(),
  delta: z.string(),
});
export type StressDelta = z.infer<typeof stressDeltaSchema>;

export const stressRunRequestSchema = z.object({
  plan_id: z.string().min(1).max(64),
  scenario_id: z.string().min(1).max(64).optional(),
  adjustments: z.array(scenarioAdjustmentSchema).optional(),
  scenario_name: z.string().min(1).max(80).default("baseline"),
  upfront_window_days: z.number().int().min(1).max(365).default(30),
});
export type StressRunRequest = z.infer<typeof stressRunRequestSchema>;

export const stressRunResultSchema = z.object({
  plan_id: z.string(),
  base_currency: z.string(),
  scenario_id: z.string().nullable(),
  scenario_name: z.string(),
  upfront_window_days: z.number().int(),
  funding_gap: stressDeltaSchema,
  funding_surplus: stressDeltaSchema,
  upfront_cash_requirement: stressDeltaSchema,
  upfront_cash_gap: stressDeltaSchema,
  first_year_cost: stressDeltaSchema,
  total_projected_cost: stressDeltaSchema,
  eligible_confirmed: stressDeltaSchema,
  eligible_with_conditional: stressDeltaSchema,
  available_before_departure: stressDeltaSchema,
  notes: z.array(z.string()),
  warnings: z.array(z.string()),
  statuses_baseline: z.array(z.string()),
  statuses_scenario: z.array(z.string()),
  generated_at: z.string(),
  calculation_version: z.string(),
});
export type StressRunResult = z.infer<typeof stressRunResultSchema>;

// ---------- Expenses (Phase 4 — Spending Tracker) -------------------------

export const expenseSchema = z.object({
  id: z.string().uuid(),
  user_id: z.string().uuid(),
  category: z.string(),
  description: z.string(),
  amount: z.string(),
  currency: z.string().length(3),
  spent_on: z.string(),
  plan_id: z.string().uuid().nullable(),
  payment_method: z.string().nullable(),
  notes: z.string().nullable(),
  created_at: z.string(),
  updated_at: z.string(),
});
export type Expense = z.infer<typeof expenseSchema>;

export const expenseCreateSchema = z.object({
  category: z.string().min(1).max(32),
  description: z.string().max(500).default(""),
  amount: z.string(),
  currency: z.string().length(3),
  spent_on: z.string(),
  plan_id: z.string().uuid().nullable().optional(),
  payment_method: z.string().max(64).nullable().optional(),
  notes: z.string().max(2000).nullable().optional(),
});
export type ExpenseCreate = z.infer<typeof expenseCreateSchema>;

export const expenseUpdateSchema = z
  .object({
    category: z.string().min(1).max(32).optional(),
    description: z.string().max(500).optional(),
    amount: z.string().optional(),
    currency: z.string().length(3).optional(),
    spent_on: z.string().optional(),
    plan_id: z.string().uuid().nullable().optional(),
    payment_method: z.string().max(64).nullable().optional(),
    notes: z.string().max(2000).nullable().optional(),
  })
  .strict();
export type ExpenseUpdate = z.infer<typeof expenseUpdateSchema>;

export const expenseImportResultSchema = z.object({
  created: z.number().int().nonnegative(),
  skipped: z.number().int().nonnegative(),
  errors: z.array(z.string()),
});
export type ExpenseImportResult = z.infer<typeof expenseImportResultSchema>;

export const categoryTotalSchema = z.object({
  category: z.string(),
  total: z.string(),
  currency: z.string(),
  count: z.number().int(),
});
export type CategoryTotal = z.infer<typeof categoryTotalSchema>;

export const monthlyBucketSchema = z.object({
  month: z.string(),
  total: z.string(),
  currency: z.string(),
  count: z.number().int(),
  by_category: z.array(categoryTotalSchema),
});
export type MonthlyBucket = z.infer<typeof monthlyBucketSchema>;

export const expenseSummarySchema = z.object({
  base_currency: z.string(),
  total: z.string(),
  count: z.number().int(),
  months: z.array(monthlyBucketSchema),
  by_category: z.array(categoryTotalSchema),
});
export type ExpenseSummary = z.infer<typeof expenseSummarySchema>;
