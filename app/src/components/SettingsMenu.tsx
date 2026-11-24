import type { ReactNode } from "react";

import { Button } from "@/components/ui/button";
import { Icon } from "@/components/ui/icon";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";
import { Segmented } from "@/components/ui/segmented";
import { Tooltip } from "@/components/ui/tooltip";
import { APP_NAME, DOCUMENTATION, VERSION } from "@/lib/brand";
import { app } from "@/lib/host";
import { setThemePreference, useThemePreference } from "@/lib/theme";

const ROW =
  "flex h-7 w-full cursor-default items-center gap-2 rounded-sm px-2 text-left whitespace-nowrap hover:bg-hover";

function Section({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className="px-2 pt-2 pb-2.5">
      <p className="mb-1.5 text-label text-ink-muted">{label}</p>
      {children}
    </div>
  );
}

/** What is about the app itself: its theme and its docs. */
export function SettingsMenu() {
  const theme = useThemePreference();
  const documentation = DOCUMENTATION;

  return (
    <Popover>
      <Tooltip content="Settings">
        <PopoverTrigger
          render={<Button size="sm" icon aria-label="Settings" />}
        >
          <Icon name="sliders" />
        </PopoverTrigger>
      </Tooltip>
      <PopoverContent label="Settings" className="w-75">
        <Section label="Theme">
          <Segmented
            label="Theme"
            size="sm"
            full
            value={theme}
            onChange={setThemePreference}
            options={[
              { value: "system", label: "System", icon: "monitor" },
              { value: "light", label: "Light", icon: "sun" },
              { value: "dark", label: "Dark", icon: "moon" },
            ]}
          />
        </Section>
        {documentation && (
          <>
            <hr className="-mx-1 my-1 border-line" />
            <button
              type="button"
              className={ROW}
              onClick={() => void app.openLink({ url: documentation })}
            >
              <span className="flex-1">Documentation</span>
              <Icon name="link-out" className="text-ink-muted" />
            </button>
          </>
        )}
        <hr className="-mx-1 my-1 border-line" />
        <p className="flex h-6 items-center px-2 mono-annotation text-ink-muted">
          {APP_NAME}
          {VERSION && ` ${VERSION}`}
        </p>
      </PopoverContent>
    </Popover>
  );
}
