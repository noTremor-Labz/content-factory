export const cockpitRoutes = [
  { id: "overview", label: "Overview" },
  { id: "brands-assets", label: "Brands & Assets" },
  { id: "avatars", label: "Avatars" },
  { id: "content", label: "Content" },
  { id: "review", label: "Review" },
  { id: "audit", label: "Audit" },
] as const;

export type CockpitRouteId = (typeof cockpitRoutes)[number]["id"];

const cockpitRouteIds = new Set<CockpitRouteId>(cockpitRoutes.map((route) => route.id));

export function normalizeCockpitRoute(value: string | null | undefined): CockpitRouteId {
  if (value && cockpitRouteIds.has(value as CockpitRouteId)) {
    return value as CockpitRouteId;
  }

  return "overview";
}

export function toCockpitHash(route: CockpitRouteId): string {
  return `#${route}`;
}
