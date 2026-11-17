import {
  BadgePercent,
  BarChart3,
  Bell,
  Boxes,
  History,
  LayoutDashboard,
  Radar,
  ScrollText,
  Settings,
  Star,
  Table2,
  Tags,
  type LucideIcon,
} from "lucide-react";

export interface NavItem {
  href: string;
  label: string;
  icon: LucideIcon;
  keywords?: string;
}

export const NAV_SECTIONS: { title: string; items: NavItem[] }[] = [
  {
    title: "Monitor",
    items: [
      { href: "/", label: "Overview", icon: LayoutDashboard, keywords: "dashboard home" },
      { href: "/deals", label: "All Deals", icon: Tags, keywords: "offers coinback" },
      { href: "/deals/100", label: "100%+ CoinBack", icon: BadgePercent, keywords: "hundred percent" },
      { href: "/explorer", label: "Deal Explorer", icon: Table2, keywords: "products discovery table" },
    ],
  },
  {
    title: "Intelligence",
    items: [
      { href: "/products", label: "Product Intelligence", icon: Boxes, keywords: "compare catalogue" },
      { href: "/price-history", label: "Price History", icon: History, keywords: "price drops movement" },
      { href: "/watchlist", label: "Watchlist", icon: Star, keywords: "saved" },
      { href: "/analytics", label: "Analytics", icon: BarChart3, keywords: "charts trends" },
    ],
  },
  {
    title: "Operations",
    items: [
      { href: "/notifications", label: "Notifications", icon: Bell, keywords: "telegram alerts" },
      { href: "/sources", label: "Discovery Sources", icon: Radar, keywords: "connectors providers" },
      { href: "/scanner", label: "Scanner Logs", icon: ScrollText, keywords: "scan runs" },
      { href: "/settings", label: "Settings", icon: Settings, keywords: "preferences configuration" },
    ],
  },
];

export const NAV_ITEMS = NAV_SECTIONS.flatMap((s) => s.items);

export function isActive(pathname: string, href: string) {
  if (href === "/") return pathname === "/";
  if (href === "/deals") return pathname === "/deals";
  return pathname === href || pathname.startsWith(`${href}/`);
}
