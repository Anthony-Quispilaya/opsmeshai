export type NavItem = {
  href: string;
  label: string;
  description: string;
};

export const primaryNav: NavItem[] = [
  {
    href: "/dashboard",
    label: "Dashboard",
    description: "Your agent and iMessage status",
  },
  {
    href: "/settings",
    label: "Settings",
    description: "Phone number and account",
  },
];
