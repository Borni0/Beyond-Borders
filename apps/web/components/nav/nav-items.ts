/**
 * Sidebar / mobile nav destinations per spec §4.6.
 *
 * Each item points to a route inside the (dashboard) route group.
 * Stub pages render "Coming in Phase N" until the matching feature ships.
 */

import {
  LayoutDashboard,
  ClipboardCheck,
  GitCompareArrows,
  Activity,
  PiggyBank,
  CalendarClock,
  Bot,
  Receipt,
  Wallet,
  Database,
  Settings as SettingsIcon,
  type LucideIcon,
} from "lucide-react";

export interface NavItem {
  href: string;
  label: string;
  icon: LucideIcon;
  phase: 1 | 2 | 3 | 4 | 5 | 6;
}

export const NAV_ITEMS: NavItem[] = [
  { href: "/dashboard", label: "Overview", icon: LayoutDashboard, phase: 1 },
  { href: "/readiness", label: "Financial Readiness", icon: ClipboardCheck, phase: 1 },
  { href: "/living-expenses", label: "Living Expense Calculator", icon: Wallet, phase: 1 },
  { href: "/decision-studio", label: "Decision Studio", icon: GitCompareArrows, phase: 1 },
  { href: "/stress-test", label: "Stress Test", icon: Activity, phase: 1 },
  { href: "/funding-plan", label: "Funding Plan", icon: PiggyBank, phase: 1 },
  { href: "/timeline", label: "Financial Timeline", icon: CalendarClock, phase: 1 },
  { href: "/copilot", label: "Finance Copilot", icon: Bot, phase: 1 },
  { href: "/spending", label: "Spending Tracker", icon: Receipt, phase: 1 },
  { href: "/sources", label: "Sources & Assumptions", icon: Database, phase: 1 },
  { href: "/settings", label: "Settings", icon: SettingsIcon, phase: 1 },
];

export const MOBILE_NAV_ITEMS: NavItem[] = NAV_ITEMS.slice(0, 4);