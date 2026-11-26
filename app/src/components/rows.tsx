import type { WindowRow } from "@/components/Windowed";
import { Icon } from "@/components/ui/icon";
import { TEXT } from "@/lib/text";

const LOADER_HEIGHT = 44;

/** The row at the end of a list that is still being read, which reads the next page once it is near the screen. */
export function loaderRow(
  key: string,
  loading: boolean,
  error: string | null,
  onNear: () => void,
  onRetry: () => void,
): WindowRow {
  return {
    key: `loader:${key}`,
    height: LOADER_HEIGHT,
    onNear,
    render: () => (
      <div className="flex h-full items-center gap-2 px-3 mono-annotation text-ink-muted">
        {error ? (
          <>
            <Icon name="warning" className="text-danger" />
            <span className="truncate">{error}</span>
            <button
              type="button"
              onClick={onRetry}
              className="shrink-0 cursor-default rounded-sm text-accent-ink underline underline-offset-2 outline-none focus-visible:focus-ring"
            >
              {TEXT.common.tryAgain}
            </button>
          </>
        ) : (
          loading && TEXT.common.loadingMore
        )}
      </div>
    ),
  };
}
