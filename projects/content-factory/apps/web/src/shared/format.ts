export function formatDateTime(value: string | null | undefined): string {
  if (!value) {
    return "Not scheduled";
  }

  return new Intl.DateTimeFormat("en", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

export function formatStatus(value: string): string {
  return value.replaceAll("_", " ");
}

export function formatChannel(value: string): string {
  return value.replaceAll("_", " ");
}
