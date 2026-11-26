import { useState, type ReactNode } from "react";

import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogFooter } from "@/components/ui/dialog";
import { Input, Label } from "@/components/ui/field";
import { Icon } from "@/components/ui/icon";
import { Notice } from "@/components/ui/notice";
import { Select } from "@/components/ui/select";
import { Switch } from "@/components/ui/switch";
import type { Store } from "@/lib/api";
import { describe } from "@/lib/errors";
import { TEXT } from "@/lib/text";
import { cn } from "@/lib/utils";

/**
 * A dialog that does one thing when its button is pressed, and stays open with the library's message when that
 * fails, so the person can fix what they typed.
 */
function ActionDialog({
  title,
  action,
  danger = false,
  ready = true,
  onAct,
  onClose,
  className,
  children,
}: {
  title: string;
  action: string;
  danger?: boolean;
  ready?: boolean;
  onAct: () => Promise<void>;
  onClose: () => void;
  className?: string;
  children: ReactNode;
}) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const act = () => {
    if (!ready || busy) {
      return;
    }
    setBusy(true);
    setError(null);
    onAct().then(onClose, (cause: unknown) => {
      setBusy(false);
      setError(describe(cause));
    });
  };
  return (
    <Dialog open onOpenChange={(open) => !open && onClose()}>
      <DialogContent title={title} className={cn("sm:max-w-110", className)}>
        <form
          onSubmit={(event) => {
            event.preventDefault();
            act();
          }}
          className="flex flex-col gap-4 overflow-y-auto px-5 py-4"
        >
          {children}
          {error && <Notice>{error}</Notice>}
          {/* Lets Enter in a field submit, since the dialog's buttons are in its footer. */}
          <button type="submit" hidden />
        </form>
        <DialogFooter>
          <span className="flex-1" />
          <Button onClick={onClose}>{TEXT.common.cancel}</Button>
          <Button
            variant={danger ? "danger" : "primary"}
            disabled={!ready || busy}
            onClick={act}
          >
            {action}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

/** Asks for a name or a path, starting from the one there is. */
export function TextDialog({
  title,
  label,
  initial,
  hint,
  action,
  onSubmit,
  onClose,
}: {
  title: string;
  label: string;
  initial: string;
  hint?: string;
  action: string;
  onSubmit: (value: string) => Promise<void>;
  onClose: () => void;
}) {
  const [value, setValue] = useState(initial);
  const wanted = value.trim();
  return (
    <ActionDialog
      title={title}
      action={action}
      ready={wanted !== "" && wanted !== initial}
      onAct={() => onSubmit(wanted)}
      onClose={onClose}
    >
      <div>
        <Label htmlFor="text-dialog">{label}</Label>
        <Input
          id="text-dialog"
          autoFocus
          value={value}
          onChange={(event) => setValue(event.target.value)}
          onFocus={(event) => {
            // The name without its extension is picked, as a file manager does when renaming.
            const dot = event.target.value.lastIndexOf(".");
            const slash = event.target.value.lastIndexOf("/");
            event.target.setSelectionRange(
              slash + 1,
              dot > slash + 1 ? dot : event.target.value.length,
            );
          }}
        />
        {hint && <p className="mt-1.5 text-caption text-ink-muted">{hint}</p>}
      </div>
    </ActionDialog>
  );
}

/** Asks before something that can't be undone. */
export function ConfirmDialog({
  title,
  action,
  onConfirm,
  onClose,
  children,
}: {
  title: string;
  action: string;
  onConfirm: () => Promise<void>;
  onClose: () => void;
  children: ReactNode;
}) {
  return (
    <ActionDialog
      title={title}
      action={action}
      danger
      onAct={onConfirm}
      onClose={onClose}
    >
      <div className="flex flex-col gap-2">{children}</div>
    </ActionDialog>
  );
}

function storeItems(stores: Store[], without: string | null) {
  return stores.map((store) => ({
    value: store.name,
    label: store.name,
    disabled:
      store.name === without
        ? TEXT.stores.isThisOne
        : !store.available
          ? TEXT.stores.unreachable
          : store.read_only
            ? TEXT.stores.isReadOnly
            : undefined,
  }));
}

/** Asks which store to move an entry to. */
export function MoveDialog({
  name,
  from,
  stores,
  onSubmit,
  onClose,
}: {
  name: string;
  from: string;
  stores: Store[];
  onSubmit: (store: string) => Promise<void>;
  onClose: () => void;
}) {
  const items = storeItems(stores, from);
  const [store, setStore] = useState(
    items.find((item) => !item.disabled)?.value ?? from,
  );
  return (
    <ActionDialog
      title={TEXT.dialogs.move.title(name)}
      action={TEXT.common.move}
      ready={store !== from}
      onAct={() => onSubmit(store)}
      onClose={onClose}
    >
      <div>
        <Label>{TEXT.dialogs.move.toStore}</Label>
        <Select
          label={TEXT.fields.store.label}
          value={store}
          onChange={setStore}
          items={items}
        />
        <p className="mt-1.5 text-caption text-ink-muted">
          {TEXT.dialogs.move.help}
        </p>
      </div>
    </ActionDialog>
  );
}

/** Asks which entry to move a file to, by its name. */
export function MoveFileDialog({
  file,
  store,
  stores,
  onSubmit,
  onClose,
}: {
  file: string;
  store: string;
  stores: Store[];
  onSubmit: (entry: string, store: string) => Promise<void>;
  onClose: () => void;
}) {
  const [entry, setEntry] = useState("");
  const [to, setTo] = useState(store);
  return (
    <ActionDialog
      title={TEXT.dialogs.move.title(file)}
      action={TEXT.common.move}
      ready={entry.trim() !== ""}
      onAct={() => onSubmit(entry.trim(), to)}
      onClose={onClose}
    >
      <div>
        <Label htmlFor="move-entry">{TEXT.dialogs.moveFile.toEntry}</Label>
        <Input
          id="move-entry"
          autoFocus
          value={entry}
          placeholder={TEXT.dialogs.moveFile.entryPlaceholder}
          onChange={(event) => setEntry(event.target.value)}
        />
      </div>
      <div>
        <Label>{TEXT.dialogs.moveFile.inStore}</Label>
        <Select
          label={TEXT.fields.store.label}
          value={to}
          onChange={setTo}
          items={storeItems(stores, null)}
        />
        <p className="mt-1.5 text-caption text-ink-muted">
          {TEXT.dialogs.moveFile.help}
        </p>
      </div>
    </ActionDialog>
  );
}

/** Adds a store by a folder on this machine or a repository on GitHub. */
export function AddStoreDialog({
  onSubmit,
  onClose,
}: {
  onSubmit: (name: string, location: string, push: boolean) => Promise<void>;
  onClose: () => void;
}) {
  const [name, setName] = useState("");
  const [location, setLocation] = useState("");
  const [push, setPush] = useState(false);
  const github = /^https?:\/\/(www\.)?github\.com\//i.test(location.trim());
  return (
    <ActionDialog
      title={TEXT.common.addStore}
      action={TEXT.common.add}
      ready={name.trim() !== "" && location.trim() !== ""}
      onAct={() => onSubmit(name.trim(), location.trim(), push)}
      onClose={onClose}
    >
      <div>
        <Label htmlFor="store-location">{TEXT.dialogs.addStore.location}</Label>
        <Input
          id="store-location"
          autoFocus
          value={location}
          placeholder={TEXT.dialogs.addStore.locationPlaceholder}
          onChange={(event) => setLocation(event.target.value)}
        />
        <p className="mt-1.5 text-caption text-ink-muted">
          {TEXT.dialogs.addStore.locationHelp}
        </p>
      </div>
      <div>
        <Label htmlFor="store-name">{TEXT.fields.name.label}</Label>
        <Input
          id="store-name"
          value={name}
          placeholder={TEXT.dialogs.addStore.namePlaceholder}
          onChange={(event) => setName(event.target.value)}
        />
      </div>
      <Switch checked={push} onChange={setPush}>
        {github
          ? TEXT.dialogs.addStore.pushGithub
          : TEXT.dialogs.addStore.pushClone}
      </Switch>
    </ActionDialog>
  );
}

/** The stores in their order, which is the order an entry's name is looked for in, with a way to move each. */
export function StoreOrderDialog({
  stores,
  onMove,
  onAdd,
  onClose,
}: {
  stores: Store[];
  onMove: (store: string, place: number) => Promise<void>;
  /** Left out where stores can't be added, such as from another device. */
  onAdd?: () => void;
  onClose: () => void;
}) {
  const [error, setError] = useState<string | null>(null);
  const ordered = stores.filter((store) => store.priority_order > 0);
  const move = (store: string, place: number) => {
    setError(null);
    onMove(store, place).catch((cause: unknown) => setError(describe(cause)));
  };
  return (
    <Dialog open onOpenChange={(open) => !open && onClose()}>
      <DialogContent title={TEXT.filters.stores} className="sm:max-w-110">
        <div className="flex flex-col gap-3 overflow-y-auto px-5 py-4">
          <p className="text-ink-muted">{TEXT.dialogs.stores.help}</p>
          <ol className="flex flex-col">
            {ordered.map((store, index) => (
              <li
                key={store.name}
                className="flex h-8 items-center gap-2 border-b border-line"
              >
                <span className="w-5 mono-annotation text-ink-muted">
                  {store.priority_order}
                </span>
                <span className="min-w-0 flex-1 truncate">{store.name}</span>
                {store.default && (
                  <span className="mono-annotation text-ink-muted">
                    {TEXT.stores.default}
                  </span>
                )}
                <Button
                  size="sm"
                  icon
                  aria-label={TEXT.dialogs.stores.up(store.name)}
                  disabled={index === 0}
                  onClick={() => move(store.name, store.priority_order - 1)}
                >
                  <Icon name="chevron" className="rotate-180" />
                </Button>
                <Button
                  size="sm"
                  icon
                  aria-label={TEXT.dialogs.stores.down(store.name)}
                  disabled={index === ordered.length - 1}
                  onClick={() => move(store.name, store.priority_order + 1)}
                >
                  <Icon name="chevron" />
                </Button>
              </li>
            ))}
          </ol>
          {error && <Notice>{error}</Notice>}
        </div>
        <DialogFooter>
          {onAdd && (
            <Button variant="secondary" onClick={onAdd}>
              <Icon name="add" />
              {TEXT.common.addStore}
            </Button>
          )}
          <span className="flex-1" />
          <Button onClick={onClose}>{TEXT.common.done}</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
