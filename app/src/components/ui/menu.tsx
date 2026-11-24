import { ContextMenu as ContextMenuPrimitive } from "@base-ui/react/context-menu";
import { Menu as MenuPrimitive } from "@base-ui/react/menu";
import type { ComponentProps, ReactNode } from "react";

import { Icon } from "@/components/ui/icon";
import { GROUP_LABEL, ITEM, POPUP, SEPARATOR } from "@/components/ui/popup";
import { cn } from "@/lib/utils";

export const Menu = MenuPrimitive.Root;
export const MenuTrigger = MenuPrimitive.Trigger;
export const MenuGroup = MenuPrimitive.Group;

/** A menu opened by a right click, or a long press, on its trigger; it takes the same items as `Menu`. */
export const ContextMenu = ContextMenuPrimitive.Root;
export const ContextMenuTrigger = ContextMenuPrimitive.Trigger;

/** The open context menu, at the pointer. */
export function ContextMenuContent({
  className,
  children,
}: {
  className?: string;
  children: ReactNode;
}) {
  return (
    <ContextMenuPrimitive.Portal>
      <ContextMenuPrimitive.Positioner
        collisionPadding={8}
        className="z-50 outline-none"
      >
        <ContextMenuPrimitive.Popup
          className={cn(POPUP, "min-w-44", className)}
        >
          {children}
        </ContextMenuPrimitive.Popup>
      </ContextMenuPrimitive.Positioner>
    </ContextMenuPrimitive.Portal>
  );
}

/** The open menu, placed against its trigger. */
export function MenuContent({
  side = "bottom",
  align = "start",
  className,
  children,
}: {
  side?: "top" | "bottom" | "left" | "right";
  align?: "start" | "center" | "end";
  className?: string;
  children: ReactNode;
}) {
  return (
    <MenuPrimitive.Portal>
      <MenuPrimitive.Positioner
        side={side}
        align={align}
        sideOffset={4}
        collisionPadding={8}
        className="z-50 outline-none"
      >
        <MenuPrimitive.Popup className={cn(POPUP, "min-w-44", className)}>
          {children}
        </MenuPrimitive.Popup>
      </MenuPrimitive.Positioner>
    </MenuPrimitive.Portal>
  );
}

export function MenuItem({
  className,
  ...props
}: ComponentProps<typeof MenuPrimitive.Item>) {
  return <MenuPrimitive.Item className={cn(ITEM, className)} {...props} />;
}

export function MenuSeparator() {
  return <MenuPrimitive.Separator className={SEPARATOR} />;
}

export function MenuGroupLabel({
  className,
  ...props
}: ComponentProps<typeof MenuPrimitive.GroupLabel>) {
  return (
    <MenuPrimitive.GroupLabel
      className={cn(GROUP_LABEL, className)}
      {...props}
    />
  );
}

export const MenuRadioGroup = MenuPrimitive.RadioGroup;

/** One choice of several in a menu, with a check on the one picked. */
export function MenuRadioItem({
  className,
  children,
  ...props
}: ComponentProps<typeof MenuPrimitive.RadioItem>) {
  return (
    <MenuPrimitive.RadioItem className={cn(ITEM, className)} {...props}>
      <span className="flex-1">{children as ReactNode}</span>
      <MenuPrimitive.RadioItemIndicator className="text-accent-ink">
        <Icon name="check" />
      </MenuPrimitive.RadioItemIndicator>
    </MenuPrimitive.RadioItem>
  );
}
