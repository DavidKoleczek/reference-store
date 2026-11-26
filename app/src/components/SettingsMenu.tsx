import { useState, type ReactNode } from "react";

import { Button } from "@/components/ui/button";
import { Icon } from "@/components/ui/icon";
import { Notice } from "@/components/ui/notice";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";
import { Segmented } from "@/components/ui/segmented";
import { Switch } from "@/components/ui/switch";
import { Tooltip } from "@/components/ui/tooltip";
import { CopyPath } from "@/components/CopyPath";
import { SkillDialog } from "@/components/SkillDialog";
import { ToolError, type WindowsApp } from "@/lib/api";
import { APP_NAME, DOCUMENTATION, VERSION } from "@/lib/brand";
import { app } from "@/lib/host";
import { appNetwork } from "@/lib/network";
import { changeSettings } from "@/lib/settings";
import { TEXT } from "@/lib/text";
import { useThemePreference } from "@/lib/theme";
import {
  lookForUpdate,
  refreshWindowsApp,
  setOnLocalNetwork,
  setStartAtSignIn,
  update,
  useWindowsApp,
} from "@/lib/windowsApp";

// A host that serves no version still gets the app's name there.
const VERSION_LABEL = VERSION ? `v${VERSION}` : APP_NAME;
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

/**
 * What the Windows app said it couldn't do. A call that got no answer at all isn't one of these: the server it went
 * through has ended, which is what was asked for.
 */
function refusal(cause: unknown): string | null {
  return cause instanceof ToolError ? cause.message : null;
}

/** The settings the Windows app keeps, since they are about how the server is started, and its Agent Skill. */
function ThisComputer({
  windowsApp,
  onChooseSkill,
}: {
  windowsApp: WindowsApp;
  onChooseSkill: () => void;
}) {
  const [restarting, setRestarting] = useState(false);
  const [problem, setProblem] = useState<string | null>(null);

  const changeLan = (lan: boolean) => {
    setProblem(null);
    setRestarting(true);
    setOnLocalNetwork(lan).catch((cause: unknown) => {
      const refused = refusal(cause);
      if (refused !== null) {
        setRestarting(false);
        setProblem(refused);
      }
    });
  };
  const changeStartAtSignIn = (on: boolean) => {
    setProblem(null);
    setStartAtSignIn(on).catch((cause: unknown) => setProblem(refusal(cause)));
  };

  return (
    <Section label={TEXT.settings.thisComputer}>
      <Switch
        className="flex h-7"
        checked={windowsApp.lan}
        disabled={restarting}
        title={TEXT.settings.onLocalNetworkHelp}
        onChange={changeLan}
      >
        {TEXT.settings.onLocalNetwork}
      </Switch>
      <Switch
        className="flex h-7"
        checked={windowsApp.start_at_sign_in}
        disabled={restarting}
        onChange={changeStartAtSignIn}
      >
        {TEXT.settings.startAtSignIn}
      </Switch>
      <div className="mt-1.5 flex items-center gap-2">
        <div className="min-w-0 flex-1">
          <p className="text-label">{TEXT.settings.skill}</p>
          <p className="text-caption text-ink-muted">
            {windowsApp.skill
              ? TEXT.settings.skillFor(windowsApp.skill.agents)
              : TEXT.settings.skillAbout}
          </p>
        </div>
        <Button variant="secondary" size="sm" onClick={onChooseSkill}>
          {windowsApp.skill
            ? TEXT.settings.changeSkill
            : TEXT.settings.installSkill}
        </Button>
      </div>
      {restarting && (
        <p role="status" className="mt-1 text-label text-ink-muted">
          {TEXT.settings.restarting}
        </p>
      )}
      {problem && <Notice className="mt-1.5">{problem}</Notice>}
    </Section>
  );
}

/** This version, with the newer one the Windows app has found, or a look for one. */
function Update({ windowsApp }: { windowsApp: WindowsApp }) {
  const [checking, setChecking] = useState(false);
  const [looked, setLooked] = useState(false);
  const [problem, setProblem] = useState<string | null>(null);

  const check = () => {
    setProblem(null);
    setChecking(true);
    lookForUpdate()
      .then(() => setLooked(true))
      .catch((cause: unknown) => setProblem(refusal(cause)))
      .finally(() => setChecking(false));
  };
  const install = () => {
    setProblem(null);
    update().catch((cause: unknown) => setProblem(refusal(cause)));
  };

  const version = windowsApp.update;
  return (
    <div className="px-2 pb-2">
      <div className="flex h-6 items-center gap-2">
        <p className="flex-1 mono-annotation text-ink-muted">{VERSION_LABEL}</p>
        {version === null && (
          <Button
            variant="secondary"
            size="sm"
            disabled={checking}
            onClick={check}
          >
            {checking ? TEXT.settings.checking : TEXT.settings.checkForUpdates}
          </Button>
        )}
      </div>
      {version === null ? (
        looked &&
        !checking && (
          <p
            role="status"
            className="mt-1 text-right text-label text-ink-muted"
          >
            {TEXT.settings.newest}
          </p>
        )
      ) : windowsApp.updating ? (
        <p role="status" className="flex h-6 items-center text-label">
          {TEXT.settings.updating(version)}
        </p>
      ) : (
        <div className="mt-1 flex items-center gap-2">
          <p className="flex-1 text-label">
            {TEXT.settings.updateAvailable(version)}
          </p>
          <Button variant="primary" size="sm" onClick={install}>
            {TEXT.settings.update}
          </Button>
        </div>
      )}
      {problem && <Notice className="mt-1.5">{problem}</Notice>}
    </div>
  );
}

/** What is about the app itself: its theme, how other devices open it, its docs, and its version. */
export function SettingsMenu() {
  const theme = useThemePreference();
  const documentation = DOCUMENTATION;
  // Only on this machine, since the address carries the key, and only when the app is on the local network.
  const { lan_url: lanUrl, qr_code: code } = appNetwork();
  // Only when the Windows app is what runs the server.
  const windowsApp = useWindowsApp();
  const newer = windowsApp?.update ?? null;
  const title =
    newer === null ? TEXT.settings.title : TEXT.settings.titleWithUpdate(newer);
  const [open, setOpen] = useState(false);
  // Outside the menu, which closes as the dialog opens.
  const [choosingSkill, setChoosingSkill] = useState(false);

  return (
    <>
      <Popover
        open={open}
        onOpenChange={(opening) => {
          setOpen(opening);
          // It changes from its own menu too.
          if (opening && windowsApp) {
            void refreshWindowsApp();
          }
        }}
      >
        <Tooltip content={title}>
          <PopoverTrigger
            render={
              <Button size="sm" icon aria-label={title} className="relative" />
            }
          >
            <Icon name="sliders" />
            {newer !== null && (
              <span className="absolute top-0 right-0 size-1.5 rounded-full bg-accent" />
            )}
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
                {
                  value: "system",
                  label: TEXT.settings.system,
                  icon: "monitor",
                },
                { value: "light", label: TEXT.settings.light, icon: "sun" },
                { value: "dark", label: TEXT.settings.dark, icon: "moon" },
              ]}
            />
          </Section>
          {windowsApp && (
            <>
              <hr className="-mx-1 my-1 border-line" />
              <ThisComputer
                windowsApp={windowsApp}
                onChooseSkill={() => {
                  setOpen(false);
                  setChoosingSkill(true);
                }}
              />
            </>
          )}
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
          {windowsApp ? (
            <Update windowsApp={windowsApp} />
          ) : (
            <p className="flex h-6 items-center px-2 mono-annotation text-ink-muted">
              {VERSION_LABEL}
            </p>
          )}
        </PopoverContent>
      </Popover>
      {choosingSkill && windowsApp && (
        <SkillDialog
          installed={windowsApp.skill !== null}
          installedMode={windowsApp.skill?.mode ?? "symlink"}
          onClose={() => setChoosingSkill(false)}
        />
      )}
    </>
  );
}
