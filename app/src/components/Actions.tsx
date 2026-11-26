import type { ReactNode } from "react";

import { Icon } from "@/components/ui/icon";
import { MenuItem, MenuSeparator } from "@/components/ui/menu";
import type { EntryFile, EntryRef, EntrySummary, Store } from "@/lib/api";
import { isImage } from "@/lib/format";
import { TEXT } from "@/lib/text";
import { copyText } from "@/lib/utils";

/** What the menus do, which the app carries out: dialogs, saving, and saying what was done. */
export type Doing = {
  /** Says something that was done, or that couldn't be. */
  say: (text: string, done?: boolean) => void;
  /** Whether this page is on the machine the stores are on, which showing in the file manager needs. */
  local: boolean;
  /** Why an entry's store can't be changed, or null when it can. */
  lockedBecause: (store: string) => string | null;
  openLink: (url: string) => void;
  reveal: (store: string, entry?: string, path?: string) => void;
  open: (entry: EntryRef) => void;
  rename: (entry: EntryRef) => void;
  move: (entry: EntryRef) => void;
  remove: (entry: EntryRef) => void;
  addFiles: (entry: EntryRef) => void;
  choosePreview: (entry: EntryRef) => void;
  clearPreview: (entry: EntryRef) => void;
  usePreview: (entry: EntryRef, file: EntryFile) => void;
  viewFile: (entry: EntryRef, file: EntryFile) => void;
  renameFile: (entry: EntryRef, file: EntryFile) => void;
  moveFile: (entry: EntryRef, file: EntryFile) => void;
  removeFile: (entry: EntryRef, file: EntryFile) => void;
  makeDefault: (store: Store) => void;
  sync: (store: Store) => void;
  removeStore: (store: Store) => void;
  arrangeStores: () => void;
};

const PLATFORM = navigator.platform;
/** The computer's file manager, by the name its own menus give it. */
const FILE_MANAGER = /win/i.test(PLATFORM)
  ? TEXT.menu.fileManager.windows
  : /mac/i.test(PLATFORM)
    ? TEXT.menu.fileManager.mac
    : TEXT.menu.fileManager.other;

/** Copies a path or a link. */
function Copy({
  text,
  link = false,
  doing,
}: {
  text: string;
  link?: boolean;
  doing: Doing;
}) {
  return (
    <MenuItem
      onClick={async () => {
        if (await copyText(text)) {
          doing.say(link ? TEXT.said.copiedLink : TEXT.said.copiedPath);
        }
      }}
    >
      <Icon name="copy" />
      {link ? TEXT.menu.copyLink : TEXT.menu.copyPath}
    </MenuItem>
  );
}

/** A menu item that changes a store's entries, off with the reason when the store can't be changed. */
function Change({
  locked,
  onClick,
  danger = false,
  children,
}: {
  locked: string | null;
  onClick: () => void;
  danger?: boolean;
  children: ReactNode;
}) {
  return (
    <MenuItem
      disabled={locked !== null}
      title={locked ?? undefined}
      onClick={onClick}
      className={danger && locked === null ? "text-danger" : undefined}
    >
      {children}
    </MenuItem>
  );
}

/** What can be done with an entry, as the items of a menu: its right click menu, and the one in its details. */
export function EntryActions({
  entry,
  folder,
  showOpen,
  doing,
}: {
  entry: EntrySummary;
  /** The entry's folder, once its files were read. */
  folder: string | null;
  /** Offers to open it, where its files don't show already. */
  showOpen: boolean;
  doing: Doing;
}) {
  const url = entry.url;
  const locked = doing.lockedBecause(entry.store);
  return (
    <>
      {showOpen && (
        <MenuItem onClick={() => doing.open(entry)}>
          <Icon name="grid" />
          {TEXT.common.open}
        </MenuItem>
      )}
      {url && (
        <MenuItem onClick={() => doing.openLink(url)}>
          <Icon name="link-out" />
          {TEXT.menu.openLink}
        </MenuItem>
      )}
      {doing.local && (
        <MenuItem onClick={() => doing.reveal(entry.store, entry.name)}>
          <Icon name="folder" />
          {TEXT.menu.showIn(FILE_MANAGER)}
        </MenuItem>
      )}
      {folder && <Copy text={folder} doing={doing} />}
      {url && <Copy text={url} link doing={doing} />}
      <MenuSeparator />
      <Change locked={locked} onClick={() => doing.rename(entry)}>
        <Icon name="rename" />
        {TEXT.common.rename}
      </Change>
      <Change locked={locked} onClick={() => doing.choosePreview(entry)}>
        <Icon name="image" />
        {TEXT.menu.setPreview}
      </Change>
      {entry.preview && (
        <Change locked={locked} onClick={() => doing.clearPreview(entry)}>
          <Icon name="close" />
          {TEXT.menu.removePreview}
        </Change>
      )}
      <Change locked={locked} onClick={() => doing.addFiles(entry)}>
        <Icon name="import" />
        {TEXT.menu.addFiles}
      </Change>
      <Change locked={locked} onClick={() => doing.move(entry)}>
        <Icon name="move" />
        {TEXT.menu.moveToStore}
      </Change>
      <MenuSeparator />
      <Change locked={locked} danger onClick={() => doing.remove(entry)}>
        <Icon name="delete" />
        {TEXT.common.delete}
      </Change>
    </>
  );
}

/** What can be done with a file of an entry, as the items of a menu. */
export function FileActions({
  entry,
  file,
  showOpenEntry,
  doing,
}: {
  entry: EntryRef;
  file: EntryFile;
  /** Offers to open the entry it is in, where that isn't open already. */
  showOpenEntry: boolean;
  doing: Doing;
}) {
  const locked = doing.lockedBecause(entry.store);
  return (
    <>
      <MenuItem onClick={() => doing.viewFile(entry, file)}>
        <Icon name="expand" />
        {TEXT.menu.view}
      </MenuItem>
      {showOpenEntry && (
        <MenuItem onClick={() => doing.open(entry)}>
          <Icon name="grid" />
          {TEXT.menu.openEntry}
        </MenuItem>
      )}
      {doing.local && (
        <MenuItem
          onClick={() => doing.reveal(entry.store, entry.name, file.path)}
        >
          <Icon name="folder" />
          {TEXT.menu.showIn(FILE_MANAGER)}
        </MenuItem>
      )}
      <Copy text={file.full_path} doing={doing} />
      <MenuSeparator />
      <Change locked={locked} onClick={() => doing.renameFile(entry, file)}>
        <Icon name="rename" />
        {TEXT.common.rename}
      </Change>
      {isImage(file) && (
        <Change locked={locked} onClick={() => doing.usePreview(entry, file)}>
          <Icon name="image" />
          {TEXT.menu.usePreview}
        </Change>
      )}
      <Change locked={locked} onClick={() => doing.moveFile(entry, file)}>
        <Icon name="move" />
        {TEXT.menu.moveToEntry}
      </Change>
      <MenuSeparator />
      <Change
        locked={locked}
        danger
        onClick={() => doing.removeFile(entry, file)}
      >
        <Icon name="delete" />
        {TEXT.common.delete}
      </Change>
    </>
  );
}

/** What can be done with a store, as the items of a menu. */
export function StoreActions({ store, doing }: { store: Store; doing: Doing }) {
  return (
    <>
      {doing.local && (
        <MenuItem onClick={() => doing.reveal(store.name)}>
          <Icon name="folder" />
          {TEXT.menu.showIn(FILE_MANAGER)}
        </MenuItem>
      )}
      <Copy text={store.path} doing={doing} />
      {store.kind === "github" && (
        <Copy text={store.location} link doing={doing} />
      )}
      <MenuSeparator />
      {store.kind === "github" && (
        <MenuItem onClick={() => doing.sync(store)}>
          <Icon name="loop" />
          {TEXT.menu.sync}
        </MenuItem>
      )}
      <MenuItem
        disabled={store.default || store.priority_order === 0}
        title={
          store.priority_order === 0 ? TEXT.menu.projectIsDefault : undefined
        }
        onClick={() => doing.makeDefault(store)}
      >
        <Icon name="check" />
        {TEXT.menu.makeDefault}
      </MenuItem>
      <MenuItem
        disabled={store.priority_order === 0}
        onClick={doing.arrangeStores}
      >
        <Icon name="list" />
        {TEXT.menu.changeOrder}
      </MenuItem>
      {doing.local && (
        <MenuItem
          disabled={store.priority_order === 0}
          title={
            store.priority_order === 0
              ? TEXT.menu.projectNotRegistered
              : undefined
          }
          onClick={() => doing.removeStore(store)}
        >
          <Icon name="close" />
          {TEXT.menu.removeStore}
        </MenuItem>
      )}
    </>
  );
}
