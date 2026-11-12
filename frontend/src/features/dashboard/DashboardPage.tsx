import { useAuth } from '@/hooks/useAuth';
import { CustomerWorkspace } from '@/features/customer/CustomerWorkspace';
import { AnalystWorkspace } from '@/features/analyst/AnalystWorkspace';
import { ComplianceWorkspace } from '@/features/compliance/ComplianceWorkspace';
import { AdminWorkspace } from '@/features/admin/AdminWorkspace';

export function DashboardPage() {
  const { persona } = useAuth();

  switch (persona) {
    case 'CUSTOMER':
      return <CustomerWorkspace />;
    case 'ANALYST':
      return <AnalystWorkspace />;
    case 'COMPLIANCE':
      return <ComplianceWorkspace />;
    case 'ADMIN':
      return <AdminWorkspace />;
    default:
      return <CustomerWorkspace />;
  }
}
