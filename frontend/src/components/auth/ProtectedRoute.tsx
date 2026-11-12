import type { ReactNode } from 'react';
import { useAuth } from '@/hooks/useAuth';
import type { ReviewerRole, BusinessPersona } from '@/types/auth';
import { UnauthorizedPage } from '@/features/common/UnauthorizedPage';

interface ProtectedRouteProps {
  children: ReactNode;
  allowedRoles?: ReviewerRole[];
  allowedPersonas?: BusinessPersona[];
}

export function ProtectedRoute({
  children,
  allowedRoles,
  allowedPersonas,
}: ProtectedRouteProps) {
  const { reviewer, persona } = useAuth();
  const role = reviewer?.role;

  // Check role requirement
  if (allowedRoles && allowedRoles.length > 0) {
    if (!role || !allowedRoles.includes(role)) {
      return (
        <UnauthorizedPage
          requiredRole={allowedRoles.join(', ')}
          requiredPersona={allowedPersonas?.join(', ')}
        />
      );
    }
  }

  // Check persona requirement
  if (allowedPersonas && allowedPersonas.length > 0) {
    if (!allowedPersonas.includes(persona)) {
      return (
        <UnauthorizedPage
          requiredRole={allowedRoles?.join(', ')}
          requiredPersona={allowedPersonas.join(', ')}
        />
      );
    }
  }

  return <>{children}</>;
}
