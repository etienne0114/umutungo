import type { ReactNode, SVGProps } from "react";

type IconName =
  | "overview"
  | "assets"
  | "maintenance"
  | "recommendations"
  | "search"
  | "plus"
  | "arrow"
  | "chevron"
  | "close"
  | "calendar"
  | "clock"
  | "activity"
  | "menu"
  | "refresh"
  | "check"
  | "warning"
  | "users";

const paths: Record<IconName, ReactNode> = {
  overview: (
    <>
      <rect x="3" y="3" width="8" height="8" rx="1.4" />
      <rect x="13" y="3" width="8" height="5" rx="1.4" />
      <rect x="13" y="10" width="8" height="11" rx="1.4" />
      <rect x="3" y="13" width="8" height="8" rx="1.4" />
    </>
  ),
  assets: (
    <>
      <path d="M3 11h18l-2-5H5l-2 5Z" />
      <path d="M5 11v7h14v-7M8 18v2m8-2v2M7 14h3m4 0h3" />
    </>
  ),
  maintenance: (
    <>
      <path d="M14.5 6.5a4 4 0 0 0-5-5l2.2 2.2-3 3-2.2-2.2a4 4 0 0 0 5 5L19 17a2.1 2.1 0 0 1-3 3l-5.5-7.5" />
      <path d="m4 20 5-5" />
    </>
  ),
  recommendations: (
    <>
      <path d="m12 3 2.4 5 5.6.8-4 3.9.9 5.6-4.9-2.6-5 2.6 1-5.6-4.1-3.9 5.6-.8L12 3Z" />
    </>
  ),
  search: (
    <>
      <circle cx="10.8" cy="10.8" r="6.8" />
      <path d="m16 16 4.5 4.5" />
    </>
  ),
  plus: <path d="M12 5v14M5 12h14" />,
  arrow: <path d="M5 12h14m-6-6 6 6-6 6" />,
  chevron: <path d="m9 18 6-6-6-6" />,
  close: <path d="m6 6 12 12M18 6 6 18" />,
  calendar: (
    <>
      <rect x="3" y="5" width="18" height="16" rx="2" />
      <path d="M16 3v4M8 3v4M3 10h18" />
    </>
  ),
  clock: (
    <>
      <circle cx="12" cy="12" r="9" />
      <path d="M12 7v5l3.5 2" />
    </>
  ),
  activity: (
    <>
      <path d="M3 12h4l3-8 4 16 3-8h4" />
    </>
  ),
  menu: <path d="M4 6h16M4 12h16M4 18h16" />,
  refresh: (
    <>
      <path d="M20 7v5h-5M4 17v-5h5" />
      <path d="M5.5 9A7 7 0 0 1 18 6l2 6M4 12l2 6a7 7 0 0 0 12.5-3" />
    </>
  ),
  check: <path d="m5 12 4 4L19 6" />,
  warning: (
    <>
      <path d="m12 3 10 18H2L12 3Z" />
      <path d="M12 9v4m0 4h.01" />
    </>
  ),
  users: (
    <>
      <path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2" />
      <circle cx="9" cy="7" r="4" />
      <path d="M22 21v-2a4 4 0 0 0-3-3.87M16 3.13a4 4 0 0 1 0 7.75" />
    </>
  ),
};

export function Icon({
  name,
  ...props
}: SVGProps<SVGSVGElement> & { name: IconName }) {
  return (
    <svg
      aria-hidden="true"
      fill="none"
      stroke="currentColor"
      strokeLinecap="round"
      strokeLinejoin="round"
      strokeWidth="1.7"
      viewBox="0 0 24 24"
      {...props}
    >
      {paths[name]}
    </svg>
  );
}

export type { IconName };
