import type { ReactNode } from "react";

import { EntryCover } from "@/components/Grids";
import { Button } from "@/components/ui/button";
import { CropMarks } from "@/components/ui/empty-state";
import { Icon } from "@/components/ui/icon";
import { Tag } from "@/components/ui/tag";
import type { Entry } from "@/lib/api";
import { fileTagsOf } from "@/lib/arrange";
import { hasTag, pickTag } from "@/lib/filters";
import { shownName, siteOf } from "@/lib/format";
import { TEXT } from "@/lib/text";

/** An entry that is a link and holds no files: its preview at a size worth looking at, and the way to the link. */
function LinkPage({
  entry,
  onOpenLink,
}: {
  entry: Entry;
  onOpenLink: (url: string) => void;
}) {
  const url = entry.url;
  return (
    <div className="mx-auto flex w-full max-w-2xl flex-col gap-4 py-2">
      {entry.preview && (
        <div className="relative p-3">
          <CropMarks />
          <div className="aspect-video w-full overflow-hidden rounded-sm border border-line bg-field">
            <EntryCover entry={entry} size="large" className="object-contain" />
          </div>
        </div>
      )}
      <div className="flex flex-col gap-2 px-3">
        <h3 className="text-title">{shownName(entry)}</h3>
        {entry.description && (
          <p className="text-ink-muted">{entry.description}</p>
        )}
        {url && (
          <div>
            <Button variant="secondary" onClick={() => onOpenLink(url)}>
              <Icon name="link-out" />
              {TEXT.common.openSite(siteOf(url))}
            </Button>
          </div>
        )}
        {!url && <p className="text-ink-muted">{TEXT.entry.noFilesYet}</p>}
      </div>
    </div>
  );
}

/**
 * One entry open in the middle. Over its files, which are `children`, are the tags its files have, to narrow them by.
 * An entry with no files shows what it links to.
 */
export function EntryPage({
  entry,
  shown,
  fileTags,
  onFileTags,
  onShowAll,
  onOpenLink,
  children,
}: {
  entry: Entry;
  /** How many of its files pass the file tags and the search. */
  shown: number;
  fileTags: string[];
  onFileTags: (tags: string[]) => void;
  onShowAll: () => void;
  onOpenLink: (url: string) => void;
  children: ReactNode;
}) {
  if (entry.files.length === 0) {
    return (
      <div className="p-3">
        <LinkPage entry={entry} onOpenLink={onOpenLink} />
      </div>
    );
  }
  const tags = fileTagsOf(entry);
  const partial = shown < entry.files.length;
  return (
    <>
      {(tags.length > 0 || partial) && (
        <div className="flex flex-wrap items-center gap-1.5 px-3 pt-3 pb-1">
          {tags.map(({ tag }) => (
            <Tag
              key={tag}
              tag={tag}
              active={hasTag(fileTags, tag)}
              onClick={(several) => onFileTags(pickTag(fileTags, tag, several))}
            />
          ))}
          {partial && (
            <>
              <span className="ml-1.5 mono-annotation text-ink-muted">
                {TEXT.count.filesOf(shown, entry.files.length)}
              </span>
              <Button size="sm" onClick={onShowAll}>
                {TEXT.entry.showAll}
              </Button>
            </>
          )}
        </div>
      )}
      {children}
    </>
  );
}
