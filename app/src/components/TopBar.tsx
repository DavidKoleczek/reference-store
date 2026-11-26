import type { RefObject } from "react";

import { SettingsMenu } from "@/components/SettingsMenu";
import { Button } from "@/components/ui/button";
import { Icon } from "@/components/ui/icon";
import { Kbd } from "@/components/ui/kbd";
import { Tooltip } from "@/components/ui/tooltip";
import { Wordmark } from "@/components/Wordmark";
import { TEXT } from "@/lib/text";

export type Pane = "filters" | "details";

const PANE_LABELS: Record<Pane, string> = {
  filters: TEXT.panes.filters,
  details: TEXT.panes.details,
};

function Divider() {
  return <span aria-hidden className="mx-1 h-5 w-px shrink-0 bg-line" />;
}

function PaneToggle({
  pane,
  open,
  onToggle,
}: {
  pane: Pane;
  open: boolean;
  onToggle: (pane: Pane) => void;
}) {
  const label = PANE_LABELS[pane];
  return (
    <Tooltip content={label} keys={pane === "filters" ? "[" : "]"}>
      <Button
        size="sm"
        icon
        aria-label={label}
        aria-pressed={open}
        onClick={() => onToggle(pane)}
      >
        <Icon name={pane === "filters" ? "sidebar-left" : "sidebar-right"} />
      </Button>
    </Tooltip>
  );
}

/** The bar along the top: the brand, the search over every store, and the app's controls. */
export function TopBar({
  query,
  onQuery,
  placeholder,
  search,
  panes,
  onTogglePane,
  onAdd,
  onRefresh,
}: {
  query: string;
  onQuery: (query: string) => void;
  placeholder: string;
  search: RefObject<HTMLInputElement | null>;
  panes: Record<Pane, boolean>;
  onTogglePane: (pane: Pane) => void;
  onAdd: () => void;
  /** Reads the stores again, for what agents changed. */
  onRefresh: () => void;
}) {
  return (
    <header className="flex h-11 shrink-0 items-center gap-2 border-b border-line bg-panel pr-2 pl-3">
      <h1 className="flex shrink-0 items-center">
        <Wordmark />
      </h1>
      <Divider />
      <label className="flex h-7 w-full max-w-105 min-w-0 items-center gap-2 rounded-sm border border-line-control bg-field pr-1.5 pl-2 transition-[background-color,border-color] focus-within:border-ink focus-within:bg-panel">
        <Icon name="search" className="text-ink-muted" />
        <input
          ref={search}
          value={query}
          onChange={(event) => onQuery(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === "Escape") {
              onQuery("");
              event.currentTarget.blur();
            }
          }}
          placeholder={placeholder}
          aria-label={TEXT.common.search}
          className="min-w-0 flex-1 bg-transparent outline-none placeholder:text-ink-muted"
        />
        {query ? (
          <Button
            size="sm"
            icon
            aria-label={TEXT.topBar.clearSearch}
            onClick={() => onQuery("")}
            className="-mr-1"
          >
            <Icon name="close" />
          </Button>
        ) : (
          <Kbd>/</Kbd>
        )}
      </label>
      <span className="flex-1" />
      <Tooltip content={TEXT.topBar.refresh}>
        <Button
          size="sm"
          icon
          aria-label={TEXT.topBar.refresh}
          onClick={onRefresh}
        >
          <Icon name="loop" />
        </Button>
      </Tooltip>
      <Tooltip content={TEXT.common.addReference} keys="N">
        <Button variant="secondary" size="sm" onClick={onAdd}>
          <Icon name="add" />
          {TEXT.common.add}
        </Button>
      </Tooltip>
      <Divider />
      <PaneToggle pane="filters" open={panes.filters} onToggle={onTogglePane} />
      <PaneToggle pane="details" open={panes.details} onToggle={onTogglePane} />
      <SettingsMenu />
    </header>
  );
}
