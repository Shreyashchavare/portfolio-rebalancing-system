import type { ComponentType } from 'react';

export interface NavItem {
  name: string;
  href: string;
  icon: ComponentType<{ className?: string }>;
  badge?: string;
  exact?: boolean;
}

export interface BreadcrumbItem {
  label: string;
  href?: string;
}
