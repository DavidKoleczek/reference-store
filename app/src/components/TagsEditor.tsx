import { useState } from "react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/field";
import { Icon } from "@/components/ui/icon";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";
import { ITEM } from "@/components/ui/popup";
import { Tag, TagSwatch } from "@/components/ui/tag";
import { hasTag, tagKey } from "@/lib/filters";
import { formatCount } from "@/lib/format";
import { TEXT } from "@/lib/text";
import { cn } from "@/lib/utils";

/** The tags on one thing: each can be made a filter or taken off, and more can be added from those in use. */
export function TagsEditor({
  tags,
  known,
  active,
  locked,
  onFilter,
  onAdd,
  onRemove,
}: {
  tags: string[];
  /** The tags in use with how many have each, to pick from before making up a new one. */
  known: { tag: string; count: number }[];
  /** The tags that are filters now. */
  active: string[];
  locked: string | null;
  /** Makes a tag a filter; left out where the tags aren't filters, such as in the Add dialog. */
  onFilter?: (tag: string, several: boolean) => void;
  onAdd: (tag: string) => void;
  onRemove: (tag: string) => void;
}) {
  const [open, setOpen] = useState(false);
  const [typed, setTyped] = useState("");
  const wanted = typed.trim();
  const offered = known.filter(
    ({ tag }) => !hasTag(tags, tag) && tagKey(tag).includes(tagKey(wanted)),
  );
  const add = (tag: string) => {
    if (tag && !hasTag(tags, tag)) {
      onAdd(tag);
    }
    setTyped("");
    setOpen(false);
  };
  return (
    <div className="flex flex-wrap items-center gap-1.5">
      {tags.map((tag) => (
        <Tag
          key={tag}
          tag={tag}
          active={hasTag(active, tag)}
          onClick={onFilter && ((several) => onFilter(tag, several))}
          onRemove={locked === null ? () => onRemove(tag) : undefined}
        />
      ))}
      {locked === null && (
        <Popover open={open} onOpenChange={setOpen}>
          <PopoverTrigger
            render={<Button size="sm" className="-ml-0.5 h-5 text-ink-muted" />}
          >
            <Icon name="add" className="size-3" />
            {TEXT.tags.add}
          </PopoverTrigger>
          <PopoverContent
            label={TEXT.tags.addTitle}
            align="start"
            className="w-56"
          >
            <Input
              autoFocus
              value={typed}
              placeholder={TEXT.tags.placeholder}
              aria-label={TEXT.tags.placeholder}
              onChange={(event) => setTyped(event.target.value)}
              onKeyDown={(event) => {
                if (event.key === "Enter" && wanted) {
                  // A tag in use is taken as it is written there, since tags that differ only by case are the same.
                  const same = known.find(
                    ({ tag }) => tagKey(tag) === tagKey(wanted),
                  );
                  add(same ? same.tag : wanted);
                }
              }}
            />
            <div className="mt-1 max-h-56 overflow-y-auto">
              {offered.map(({ tag, count }) => (
                <button
                  key={tag}
                  type="button"
                  onClick={() => add(tag)}
                  className={cn(ITEM, "w-full text-left hover:bg-hover")}
                >
                  <TagSwatch tag={tag} />
                  <span className="min-w-0 flex-1 truncate">{tag}</span>
                  <span className="mono-annotation text-ink-muted">
                    {formatCount(count)}
                  </span>
                </button>
              ))}
              {offered.length === 0 && (
                <p className="px-2 py-1 text-ink-muted">
                  {wanted ? TEXT.tags.enterToAdd : TEXT.tags.noMore}
                </p>
              )}
            </div>
          </PopoverContent>
        </Popover>
      )}
      {locked !== null && tags.length === 0 && (
        <span className="text-ink-muted">{TEXT.common.none}</span>
      )}
    </div>
  );
}
