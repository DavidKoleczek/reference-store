/** What went wrong, for the person. */
export function describe(cause: unknown): string {
  return cause instanceof Error ? cause.message : String(cause);
}
