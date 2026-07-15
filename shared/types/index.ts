export type TenantStatus = "trial" | "active" | "suspended";

export interface Tenant {
  id: string;
  name: string;
  subdomain: string;
  custom_domain: string | null;
  status: TenantStatus;
  created_at: string;
}
