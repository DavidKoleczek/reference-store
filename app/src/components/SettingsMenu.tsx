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
import { CopyPath } from "@/components/CopyPath";
import { APP_NAME, DOCUMENTATION, VERSION } from "@/lib/brand";
import { app } from "@/lib/host";
import { appNetwork } from "@/lib/network";
import { changeSettings } from "@/lib/settings";
import { TEXT } from "@/lib/text";
import { useThemePreference } from "@/lib/theme";

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

/** What is about the app itself: its theme, how other devices open it, and its docs. */
export function SettingsMenu() {
  const theme = useThemePreference();
  const documentation = DOCUMENTATION;
  // Only on this machine, since the address carries the key, and only when the app is on the local network.
  const { lan_url: lanUrl, qr_code: code } = appNetwork();

  return (
    <Popover>
      <Tooltip content={TEXT.settings.title}>
        <PopoverTrigger
          render={<Button size="sm" icon aria-label={TEXT.settings.title} />}
        >
          <Icon name="sliders" />
        </PopoverTrigger>
      </Tooltip>
      <PopoverContent label={TEXT.settings.title} className="w-75">
        <Section label={TEXT.settings.theme}>
          <Segmented
            label={TEXT.settings.theme}
            size="sm"
            full
            value={theme}
            onChange={(theme) => changeSettings({ theme })}
            options={[
              { value: "system", label: TEXT.settings.system, icon: "monitor" },
              { value: "light", label: TEXT.settings.light, icon: "sun" },
              { value: "dark", label: TEXT.settings.dark, icon: "moon" },
            ]}
          />
        </Section>
        {lanUrl && (
          <>
            <hr className="-mx-1 my-1 border-line" />
            <Section label={TEXT.settings.localNetwork}>
              {code && (
                <img
                  src={code}
                  alt={TEXT.settings.qrCode(lanUrl)}
                  className="bg-white mx-auto mb-2 size-44 rounded-sm"
                />
              )}
              <p className="mb-2 mono-annotation break-all text-ink-muted">
                {lanUrl}
              </p>
              <CopyPath
                path={lanUrl}
                label={TEXT.settings.copyAddress}
                size="sm"
              />
            </Section>
          </>
        )}
        {documentation && (
          <>
            <hr className="-mx-1 my-1 border-line" />
            <button
              type="button"
              className={ROW}
              onClick={() => void app.openLink({ url: documentation })}
            >
              <span className="flex-1">{TEXT.settings.documentation}</span>
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
