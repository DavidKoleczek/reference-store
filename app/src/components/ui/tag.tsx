import { Icon } from "@/components/ui/icon";
import { pastelOf } from "@/lib/format";
import { TEXT } from "@/lib/text";
import { cn } from "@/lib/utils";

/** The square of a tag's own pastel, which stands beside its name wherever the tag shows. */
export function TagSwatch({
  tag,
  className,
}: {
  tag: string;
  className?: string;
}) {
  return (
    <span
      aria-hidden
      className={cn(
        "size-2.5 shrink-0 rounded-[2px] border border-ink/15",
        pastelOf(tag),
        className,
      )}
    />
  );
}

/** A tag on an entry or a file. Clicking it narrows the view to it, and its cross takes it off. */
export function Tag({
  tag,
  active = false,
  onClick,
  onRemove,
}: {
  tag: string;
  /** It is one of the filters now. */
  active?: boolean;
  /** Told whether Ctrl or Shift was held, which adds it to the tags shown rather than showing it alone. */
  onClick?: (several: boolean) => void;
  onRemove?: () => void;
}) {
  return (
    <span
      className={cn(
        "inline-flex h-5 max-w-full min-w-0 items-center rounded-sm border text-caption",
        active ? "border-accent-ink bg-accent-soft" : "border-line bg-panel",
      )}
    >
      <button
        type="button"
        disabled={!onClick}
        onClick={(event) =>
          onClick?.(event.ctrlKey || event.metaKey || event.shiftKey)
        }
        title={onClick ? TEXT.tags.showOnly(tag) : undefined}
        className={cn(
          "flex h-full min-w-0 cursor-default items-center gap-1.5 rounded-sm pl-1.5 outline-none focus-visible:focus-ring",
          onRemove ? "pr-0.5" : "pr-1.5",
          onClick && "hover:text-accent-ink",
        )}
      >
        <TagSwatch tag={tag} />
        <span className="truncate">{tag}</span>
      </button>
      {onRemove && (
        <button
          type="button"
          aria-label={TEXT.tags.remove(tag)}
          onClick={onRemove}
          className="grid h-full w-4.5 shrink-0 cursor-default place-items-center rounded-sm text-ink-muted outline-none hover:text-ink focus-visible:focus-ring"
        >
          <Icon name="close" className="size-2.5" />
        </button>
      )}
    </span>
  );
}
