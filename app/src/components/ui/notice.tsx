import type { ReactNode } from "react";

import { Button } from "@/components/ui/button";
import { Icon, type IconName } from "@/components/ui/icon";
import { cn } from "@/lib/utils";

/**
 * What happened, then what to do. Danger for failures; neutral for an ending that is not one, like a stopped run.
 */
export function Notice({
  title,
  children,
  tone = "danger",
  icon,
  onDismiss,
  className,
}: {
  title?: ReactNode;
  children?: ReactNode;
  tone?: "danger" | "neutral";
  icon?: IconName;
  /** Puts a button on it that takes it away, for one that reports something over and done with. */
  onDismiss?: () => void;
  className?: string;
}) {
  return (
    <div
      role={tone === "danger" ? "alert" : undefined}
      className={cn(
        "flex min-w-0 gap-2 rounded-md px-2.5 py-2 text-body",
        tone === "danger" ? "bg-danger-soft" : "border border-line bg-field",
        className,
      )}
    >
      <Icon
        name={icon ?? (tone === "danger" ? "warning" : "stop")}
        className={cn(
          "mt-0.5",
          tone === "danger" ? "text-danger" : "text-ink-muted",
        )}
      />
      <div className="min-w-0 flex-1 wrap-break-word">
        {title && (
          <b
            className={cn(
              "font-medium",
              tone === "danger" ? "text-danger" : "text-ink",
            )}
          >
            {title}
          </b>
        )}
        {title && children ? " " : null}
        {children}
      </div>
      {onDismiss && (
        <Button
          size="sm"
          icon
          aria-label="Dismiss"
          onClick={onDismiss}
          className="-my-0.5 -mr-1"
        >
          <Icon name="close" />
        </Button>
      )}
    </div>
  );
}
