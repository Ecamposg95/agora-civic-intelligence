import type { Paginated } from "./auth";

export interface Organization {
  id: string;
  name: string;
  slug: string;
  is_active: boolean;
}

export type OrganizationsResponse = Paginated<Organization>;
