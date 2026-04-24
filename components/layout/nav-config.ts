export type NavItem = {
  href: string;
  label: string;
  description: string;
};

export const primaryNav: NavItem[] = [
  {
    href: "/",
    label: "Home",
    description: "Your agent and iMessage status",
  },
  {
    href: "/settings",
    label: "Settings",
    description: "Phone number and account",
  },
];
