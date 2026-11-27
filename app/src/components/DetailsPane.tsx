import { useState, type KeyboardEvent, type ReactNode } from "react";
import { Group as PanelGroup, Panel } from "react-resizable-panels";

import { EntryActions, type Doing } from "@/components/Actions";
import { CopyPath, PathLine } from "@/components/CopyPath";
import { Preview } from "@/components/Preview";
import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/empty-state";
import { Input, Textarea } from "@/components/ui/field";
import { Icon } from "@/components/ui/icon";
import { Markdown } from "@/components/ui/markdown";
import { Menu, MenuContent, MenuTrigger } from "@/components/ui/menu";
import { Rating } from "@/components/ui/rating";
import { ResizeHandle } from "@/components/ui/resizable";
import { TagsEditor } from "@/components/TagsEditor";
import { Tooltip } from "@/components/ui/tooltip";
import type {
  Entry,
  EntryChange,
  EntryFile,
  EntrySummary,
  FileChange,
} from "@/lib/api";
import {
  clipped,
  dimensions,
  fileName,
  formatDay,
  formatSize,
  formatTime,
  fromLocalTime,
  localTimeOf,
  plural,
  shownName,
} from "@/lib/format";
import { TEXT } from "@/lib/text";
import { cn } from "@/lib/utils";

// How much of the pane the preview takes at first, and the least each part keeps, in pixels.
const PREVIEW = {
  stacked: "44%",
  stackedMin: 96,
  beside: "62%",
  besideMin: 200,
};
// The most of a link the details show, in characters.
const LINK_LENGTH = 80;
const FIELDS = { stackedMin: 140, besideMin: 240 };

function Field({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div>
      <h3 className="mb-1 text-label text-ink-muted">{label}</h3>
      {children}
    </div>
  );
}

/**
 * Text that reads as text until it is clicked, then is a field. What is typed is saved once the field is left, or
 * with Enter on a single line and Ctrl+Enter on several. Escape puts it back.
 */
function EditableText({
  label,
  value,
  placeholder,
  multiline = true,
  markdown = false,
  locked,
  onChange,
}: {
  label: string;
  value: string;
  placeholder: string;
  multiline?: boolean;
  /** It reads as rendered Markdown, with a button to edit it, since a button can't hold its links. */
  markdown?: boolean;
  /** Why it can't be changed, or null when it can. */
  locked: string | null;
  onChange: (value: string) => void;
}) {
  const [draft, setDraft] = useState<string | null>(null);
  if (draft === null && markdown && value) {
    return (
      <div
        onClick={(event) => {
          // A link or a button in it does its own thing, and text selected in it is there to be copied.
          const inside =
            event.target instanceof Element &&
            event.target.closest("a, button") !== null;
          if (
            locked === null &&
            !inside &&
            !window.getSelection()?.toString()
          ) {
            setDraft(value);
          }
        }}
        className={cn(
          "group/text relative -mx-1.5 rounded-sm px-1.5 py-0.5",
          locked === null && "cursor-text hover:bg-hover",
        )}
      >
        <Markdown breaks>{value}</Markdown>
        {locked === null && (
          <Button
            size="sm"
            icon
            aria-label={TEXT.details.edit(label)}
            title={TEXT.details.edit(label)}
            onClick={() => setDraft(value)}
            className="absolute top-0 right-0 bg-panel opacity-0 group-hover/text:opacity-100 focus-visible:opacity-100"
          >
            <Icon name="rename" />
          </Button>
        )}
      </div>
    );
  }
  if (draft === null) {
    return (
      <button
        type="button"
        aria-label={TEXT.details.edit(label)}
        disabled={locked !== null}
        title={locked ?? undefined}
        onClick={() => setDraft(value)}
        className={cn(
          "-mx-1.5 block w-[calc(100%+12px)] rounded-sm px-1.5 py-0.5 text-left wrap-break-word whitespace-pre-wrap outline-none focus-visible:focus-ring enabled:cursor-text enabled:hover:bg-hover",
          !value && "text-ink-muted",
        )}
      >
        {value || (locked === null ? placeholder : TEXT.common.none)}
      </button>
    );
  }
  const save = () => {
    if (draft.trim() !== value) {
      onChange(draft.trim());
    }
    setDraft(null);
  };
  const keys = (event: KeyboardEvent<HTMLElement>) => {
    if (event.key === "Escape") {
      event.stopPropagation();
      setDraft(null);
    } else if (
      event.key === "Enter" &&
      (!multiline || event.ctrlKey || event.metaKey)
    ) {
      event.preventDefault();
      save();
    }
  };
  return multiline ? (
    <Textarea
      autoFocus
      aria-label={label}
      value={draft}
      placeholder={placeholder}
      onChange={(event) => setDraft(event.target.value)}
      onBlur={save}
      onKeyDown={keys}
      className="field-sizing-content max-h-80 resize-none"
    />
  ) : (
    <Input
      autoFocus
      aria-label={label}
      value={draft}
      placeholder={placeholder}
      onChange={(event) => setDraft(event.target.value)}
      onBlur={save}
      onKeyDown={keys}
    />
  );
}

/**
 * A time that reads as text until it is clicked, then is a date and time field. It is saved once the field is left
 * or with Enter, and emptying it clears it. Escape, or a time left half typed, puts it back.
 */
function EditableTime({
  label,
  value,
  placeholder,
  locked,
  onChange,
}: {
  label: string;
  /** A time in ISO 8601, or null for none. */
  value: string | null;
  placeholder: string;
  /** Why it can't be changed, or null when it can. */
  locked: string | null;
  onChange: (value: string | null) => void;
}) {
  const [draft, setDraft] = useState<string | null>(null);
  const local = value === null ? "" : localTimeOf(value);
  if (draft === null) {
    return (
      <button
        type="button"
        aria-label={TEXT.details.edit(label)}
        disabled={locked !== null}
        title={locked ?? undefined}
        onClick={() => setDraft(local)}
        className={cn(
          "-mx-1.5 block w-[calc(100%+12px)] rounded-sm px-1.5 py-0.5 text-left outline-none focus-visible:focus-ring enabled:cursor-text enabled:hover:bg-hover",
          value === null && "text-ink-muted",
        )}
      >
        {value !== null
          ? formatTime(value)
          : locked === null
            ? placeholder
            : TEXT.common.none}
      </button>
    );
  }
  const save = (field: HTMLInputElement) => {
    if (!field.validity.badInput && draft !== local) {
      onChange(draft ? fromLocalTime(draft) : null);
    }
    setDraft(null);
  };
  return (
    <Input
      type="datetime-local"
      autoFocus
      aria-label={label}
      value={draft}
      onChange={(event) => setDraft(event.target.value)}
      onBlur={(event) => save(event.currentTarget)}
      onKeyDown={(event) => {
        if (event.key === "Escape") {
          event.stopPropagation();
          setDraft(null);
        } else if (event.key === "Enter") {
          event.preventDefault();
          save(event.currentTarget);
        }
      }}
    />
  );
}

function EntryDetails({
  entry,
  full,
  open,
  known,
  activeTags,
  onFilterTag,
  onChange,
  doing,
}: {
  entry: EntrySummary;
  /** The entry with its files, once they are read. */
  full: Entry | null;
  open: boolean;
  known: { tag: string; count: number }[];
  activeTags: string[];
  onFilterTag: (tag: string, several: boolean) => void;
  onChange: (change: EntryChange) => void;
  doing: Doing;
}) {
  const locked = doing.lockedBecause(entry.store);
  const url = entry.url;
  return (
    <>
      <div className="flex items-start gap-2">
        <div className="min-w-0 flex-1">
          <h3 className="text-title wrap-break-word">{shownName(entry)}</h3>
          {entry.title !== null && (
            <p className="mono-value wrap-break-word text-ink-muted">
              {entry.name}
            </p>
          )}
          <p className="mt-0.5 flex flex-wrap gap-x-3 mono-annotation text-ink-muted">
            <span>{entry.store}</span>
            {entry.file_count > 0 && (
              <>
                <span>{plural(entry.file_count, "file")}</span>
                <span>{formatSize(entry.size)}</span>
              </>
            )}
          </p>
        </div>
        <Menu>
          <MenuTrigger render={<Button icon aria-label={TEXT.details.more} />}>
            <Icon name="more" />
          </MenuTrigger>
          <MenuContent align="end">
            <EntryActions
              entry={entry}
              folder={full?.folder ?? null}
              showOpen={!open}
              doing={doing}
            />
          </MenuContent>
        </Menu>
      </div>
      {url && (
        // The link itself, not just its site, cut off past a length that still tells one page from another.
        <a
          href={url}
          title={url}
          onClick={(event) => {
            event.preventDefault();
            doing.openLink(url);
          }}
          className="flex min-w-0 items-center gap-1.5 rounded-sm text-accent-ink outline-none focus-visible:focus-ring"
        >
          <Icon name="link-out" className="shrink-0" />
          <span className="truncate underline underline-offset-2">
            {clipped(url, LINK_LENGTH)}
          </span>
        </a>
      )}
      {!open && entry.file_count > 0 && (
        <div>
          <Button variant="secondary" onClick={() => doing.open(entry)}>
            <Icon name="grid" />
            {TEXT.details.showFiles}
          </Button>
        </div>
      )}
      {locked && (
        <p className="flex items-start gap-1.5 text-ink-muted">
          <Icon name="warning" className="mt-0.5 shrink-0" />
          {locked}
        </p>
      )}
      <Field label={TEXT.fields.rating.label}>
        {locked === null ? (
          <Rating
            value={entry.rating}
            onChange={(rating) => onChange({ rating })}
            className="-ml-1"
          />
        ) : entry.rating === null ? (
          <span className="text-ink-muted">{TEXT.common.none}</span>
        ) : (
          <Rating value={entry.rating} />
        )}
      </Field>
      <Field label={TEXT.fields.title.label}>
        <EditableText
          label={TEXT.fields.title.label}
          value={entry.title ?? ""}
          placeholder={TEXT.fields.title.help}
          multiline={false}
          locked={locked}
          onChange={(title) => onChange({ title: title || null })}
        />
      </Field>
      <Field label={TEXT.fields.description.label}>
        <EditableText
          label={TEXT.fields.description.label}
          value={entry.description}
          placeholder={TEXT.fields.description.help}
          locked={locked}
          onChange={(description) => onChange({ description })}
        />
      </Field>
      <Field label={TEXT.fields.link.label}>
        <EditableText
          label={TEXT.fields.link.label}
          value={entry.url ?? ""}
          placeholder={TEXT.fields.link.placeholder}
          multiline={false}
          locked={locked}
          onChange={(link) => onChange({ url: link || null })}
        />
      </Field>
      <Field label={TEXT.fields.published.label}>
        <EditableTime
          label={TEXT.fields.published.label}
          value={entry.source_published_at}
          placeholder={TEXT.fields.published.help}
          locked={locked}
          onChange={(published) => onChange({ source_published_at: published })}
        />
      </Field>
      <Field label={TEXT.fields.tags.label}>
        <TagsEditor
          tags={entry.tags}
          known={known}
          active={activeTags}
          locked={locked}
          onFilter={onFilterTag}
          onAdd={(tag) => onChange({ add_tags: [tag] })}
          onRemove={(tag) => onChange({ remove_tags: [tag] })}
        />
      </Field>
      <Field label={TEXT.fields.notes.label}>
        <EditableText
          label={TEXT.fields.notes.label}
          value={entry.notes}
          placeholder={TEXT.fields.notes.help}
          markdown
          locked={locked}
          onChange={(notes) => onChange({ notes })}
        />
      </Field>
      {full && (
        <Field label={TEXT.fields.folder.label}>
          <PathLine path={full.folder} />
          <div className="mt-1.5">
            <CopyPath path={full.folder} />
          </div>
        </Field>
      )}
      <p className="flex flex-wrap gap-x-3 mono-annotation text-ink-muted">
        <span>{TEXT.details.created(formatDay(entry.created))}</span>
        <span>{TEXT.details.updated(formatDay(entry.updated))}</span>
      </p>
    </>
  );
}

function FileDetails({
  entry,
  file,
  size,
  known,
  activeTags,
  onFilterTag,
  onChange,
  doing,
}: {
  entry: EntrySummary;
  file: EntryFile;
  size: [number, number] | null;
  known: { tag: string; count: number }[];
  activeTags: string[];
  onFilterTag: (tag: string, several: boolean) => void;
  onChange: (change: FileChange) => void;
  doing: Doing;
}) {
  const locked = doing.lockedBecause(entry.store);
  return (
    <>
      <div>
        <h3 className="text-title wrap-break-word">{fileName(file)}</h3>
        <p className="mt-0.5 flex flex-wrap gap-x-3 mono-annotation text-ink-muted">
          {size && <span>{dimensions(size)}</span>}
          <span>{formatSize(file.size)}</span>
        </p>
        <p className="mt-1 text-ink-muted">
          {TEXT.details.inEntry}{" "}
          <button
            type="button"
            onClick={() => doing.open(entry)}
            className="cursor-default rounded-sm text-accent-ink underline underline-offset-2 outline-none focus-visible:focus-ring"
          >
            {shownName(entry)}
          </button>
        </p>
      </div>
      <div>
        <CopyPath path={file.full_path} />
      </div>
      <Field label={TEXT.fields.description.label}>
        <EditableText
          label={TEXT.fields.description.label}
          value={file.description}
          placeholder={TEXT.fields.description.fileHelp}
          locked={locked}
          onChange={(description) => onChange({ description })}
        />
      </Field>
      <Field label={TEXT.fields.tags.label}>
        <TagsEditor
          tags={file.tags}
          known={known}
          active={activeTags}
          locked={locked}
          onFilter={onFilterTag}
          onAdd={(tag) => onChange({ add_tags: [tag] })}
          onRemove={(tag) => onChange({ remove_tags: [tag] })}
        />
      </Field>
      <Field label={TEXT.fields.notes.label}>
        <EditableText
          label={TEXT.fields.notes.label}
          value={file.notes}
          placeholder={TEXT.fields.notes.help}
          markdown
          locked={locked}
          onChange={(notes) => onChange({ notes })}
        />
      </Field>
      <Field label={TEXT.fields.path.label}>
        <PathLine path={file.full_path} />
      </Field>
    </>
  );
}

/** What is known about the entry or the file picked, where it is changed and saved, and its path to hand on. */
export function DetailsPane({
  entry,
  full,
  file,
  size,
  open,
  beside,
  onBeside,
  tags,
  fileTags,
  activeTags,
  activeFileTags,
  onFilterTag,
  onFilterFileTag,
  onEntry,
  onFile,
  onView,
  doing,
}: {
  entry: EntrySummary | null;
  full: Entry | null;
  /** The file picked in `entry`, if one is. */
  file: EntryFile | null;
  size: [number, number] | null;
  /** `entry` is the one open in the middle. */
  open: boolean;
  /** The preview is beside the details rather than above them. */
  beside: boolean;
  onBeside: () => void;
  tags: { tag: string; count: number }[];
  fileTags: { tag: string; count: number }[];
  activeTags: string[];
  activeFileTags: string[];
  onFilterTag: (tag: string, several: boolean) => void;
  onFilterFileTag: (tag: string, several: boolean) => void;
  onEntry: (change: EntryChange) => void;
  onFile: (change: FileChange) => void;
  onView: () => void;
  doing: Doing;
}) {
  return (
    <aside className="flex h-full min-w-0 flex-col bg-panel">
      <header className="flex h-10 shrink-0 items-center border-b border-line pr-2 pl-3">
        <h2 className="flex-1 truncate text-label">{TEXT.panes.details}</h2>
        <Tooltip
          content={
            beside ? TEXT.details.previewAbove : TEXT.details.previewBeside
          }
        >
          <Button
            size="sm"
            icon
            aria-label={TEXT.details.previewBeside}
            aria-pressed={beside}
            onClick={onBeside}
          >
            <Icon name="compare" />
          </Button>
        </Tooltip>
      </header>
      {entry === null ? (
        <div className="p-3">
          <EmptyState
            tile={<Icon name="select" size={24} />}
            tileClassName="bg-pastel-butter"
            title={TEXT.details.pick}
            className="bg-panel"
          />
        </div>
      ) : (
        <PanelGroup
          // Keyed so each way of laying the two out starts from its own sizes.
          key={beside ? "beside" : "stacked"}
          orientation={beside ? "horizontal" : "vertical"}
          className="min-h-0 flex-1"
        >
          <Panel
            id="preview"
            minSize={beside ? PREVIEW.besideMin : PREVIEW.stackedMin}
            defaultSize={beside ? PREVIEW.beside : PREVIEW.stacked}
            className="min-h-0 min-w-0"
          >
            <Preview entry={entry} file={file} size={size} onView={onView} />
          </Panel>
          <ResizeHandle label={TEXT.panes.resizePreview} stacked={!beside} />
          <Panel
            id="fields"
            minSize={beside ? FIELDS.besideMin : FIELDS.stackedMin}
            className="min-h-0 min-w-0"
          >
            <div
              // Keyed so a draft being typed does not carry over to the next thing picked.
              key={`${entry.store}/${entry.name}/${file?.path ?? ""}`}
              className="flex h-full flex-col gap-4 overflow-y-auto p-3"
            >
              {file ? (
                <FileDetails
                  entry={entry}
                  file={file}
                  size={size}
                  known={fileTags}
                  activeTags={activeFileTags}
                  onFilterTag={onFilterFileTag}
                  onChange={onFile}
                  doing={doing}
                />
              ) : (
                <EntryDetails
                  entry={entry}
                  full={full}
                  open={open}
                  known={tags}
                  activeTags={activeTags}
                  onFilterTag={onFilterTag}
                  onChange={onEntry}
                  doing={doing}
                />
              )}
            </div>
          </Panel>
        </PanelGroup>
      )}
    </aside>
  );
}
