//! Installing the app and the tool for the current user, and removing them.

use std::os::windows::process::CommandExt;
use std::path::{self, Path, PathBuf};
use std::process::{Command, Stdio};
use std::time::{Duration, Instant};
use std::{env, fs, io, thread};

use windows::Win32::Foundation::ERROR_FILE_NOT_FOUND;
use windows::Win32::System::Threading::CREATE_NO_WINDOW;
use windows_registry::CURRENT_USER;

use crate::failure::{Failure, OrSay, Outcome};
use crate::package::{APP_NAME, PUBLISHER, REPOSITORY, VERSION};
use crate::paths::Paths;
use crate::settings::Settings;
use crate::{instance, prerequisites, startup, tool, win32};

const VERSION_VALUE: &str = "DisplayVersion";
// An app that has only just quit can hold its exe a moment longer.
const COPY_PATIENCE: Duration = Duration::from_secs(5);
const COPY_CHECK: Duration = Duration::from_millis(100);

/// What the person installing chose.
#[derive(Debug, Default, PartialEq)]
pub struct Options {
    /// The folder for a first store, used only when the tool has no store yet.
    pub store: Option<PathBuf>,
    /// Whether devices on the local network can open the app.
    pub lan: bool,
    pub shortcuts: Shortcuts,
    pub start_at_sign_in: bool,
}

/// Which shortcuts to the app there are to be.
#[derive(Debug, Default, PartialEq)]
pub struct Shortcuts {
    pub desktop: bool,
    pub start_menu: bool,
}

/// What is on the machine before anything is installed.
pub struct Existing {
    /// The version of the app that is installed, if one is.
    pub version: Option<String>,
    pub has_stores: bool,
    /// The choices that would leave an installed app as it is, or the ones to start from when there is none.
    pub options: Options,
}

#[derive(Clone, Copy)]
pub enum Stage {
    InstallGit,
    InstallUv,
    InstallTool,
    AddStore,
    UseStore,
    InstallApp,
    RemoveTool,
    RemoveApp,
}

pub enum Progress {
    Started(Stage),
    /// Something that didn't go as asked and didn't stop the rest.
    Note(String),
}

impl Stage {
    pub fn label(self) -> &'static str {
        match self {
            Self::InstallGit => "Installing Git",
            Self::InstallUv => "Installing uv",
            Self::InstallTool => "Installing the tool",
            Self::AddStore => "Adding the store",
            Self::UseStore => "Making the store the default",
            Self::InstallApp => "Installing the app and tray icon",
            Self::RemoveTool => "Removing the tool",
            Self::RemoveApp => "Removing the app from Windows",
        }
    }
}

impl Existing {
    /// Looks at what is installed, which takes a moment when the tool is there to be asked about its stores.
    pub fn find(paths: &Paths) -> Self {
        let version = CURRENT_USER.open(paths.uninstall_key()).and_then(|key| key.get_string(VERSION_VALUE)).ok();
        let has_stores = tool::remembers_stores(paths);
        let installed = version.is_some();
        let options = Options {
            store: (!has_stores).then(|| paths.documents.join(APP_NAME)),
            // Kept from an app that was removed, since uninstalling leaves what the app remembers.
            lan: Settings::read(paths).lan,
            shortcuts: Shortcuts {
                desktop: !installed || shortcut(&paths.desktop).is_file(),
                start_menu: !installed || shortcut(&paths.start_menu).is_file(),
            },
            start_at_sign_in: startup::is_on(paths),
        };
        Self { version, has_stores, options }
    }

    /// Returns the choices that install over the app and leave it as it was set up, which is how it is updated.
    pub fn kept(self) -> Outcome<Options> {
        if self.version.is_none() {
            return Err(Failure::new(format!(
                "{APP_NAME} isn't installed, so there is nothing to update. Open this exe by itself to set it up."
            )));
        }
        Ok(Options { store: None, ..self.options })
    }
}

/// Installs what is missing of git and uv, then the tool and the app, in place of any version already there.
///
/// Windows is told of the app last, so an install that fails on the way leaves nothing listed.
pub fn install(options: &Options, paths: &Paths, report: &mut dyn FnMut(Progress)) -> Outcome<()> {
    // A running app holds the tool's files and the exe, which are both about to be replaced.
    instance::quit_running(paths)?;
    if prerequisites::find_git().is_none() {
        report(Progress::Started(Stage::InstallGit));
        if let Err(failure) = prerequisites::install_git(paths) {
            report(Progress::Note(format!("Git wasn't installed. Only stores on GitHub need it. {failure}")));
        }
    }
    let uv = if let Some(uv) = prerequisites::find_uv(paths) {
        uv
    } else {
        report(Progress::Started(Stage::InstallUv));
        prerequisites::install_uv(paths)?
    };

    report(Progress::Started(Stage::InstallTool));
    let program = tool::install(&uv, paths)?;
    // A sandbox's tools are not for the rest of the machine to find.
    if !paths.is_sandbox()
        && let Err(failure) = tool::put_on_path(&uv, paths)
    {
        report(Progress::Note(format!("The tool works, but may not be found from a terminal. {failure}")));
    }

    if let Some(folder) = &options.store {
        let folder = path::absolute(folder).or_say(|| format!("{} isn't a folder's path", folder.display()))?;
        let stores = tool::stores(&program, paths)?;
        if let Some(store) = stores.iter().find(|store| is_same_place(&store.path, &folder)) {
            report(Progress::Started(Stage::UseStore));
            if !store.default {
                tool::set_default_store(&program, &store.name, paths)?;
            }
        } else {
            report(Progress::Started(Stage::AddStore));
            if stores.is_empty() {
                tool::add_first_store(&program, &folder, paths)?;
            } else {
                report(Progress::Note(format!("The tool has stores already, so {} wasn't added.", folder.display())));
            }
        }
    }

    report(Progress::Started(Stage::InstallApp));
    let exe = paths.exe();
    copy_exe(&exe)?;
    for (wanted, folder) in
        [(options.shortcuts.desktop, &paths.desktop), (options.shortcuts.start_menu, &paths.start_menu)]
    {
        let shortcut = shortcut(folder);
        if wanted {
            // Windows has both folders already. A sandbox's are made here.
            fs::create_dir_all(folder).or_say(|| format!("{} couldn't be made", folder.display()))?;
            win32::create_shortcut(&shortcut, &exe, APP_NAME)
                .or_say(|| format!("The shortcut {} couldn't be made", shortcut.display()))?;
        } else {
            remove_file(&shortcut)?;
        }
    }
    Settings { lan: options.lan, ..Settings::read(paths) }.write(paths)?;
    startup::set(paths, options.start_at_sign_in)?;
    register(paths, &exe)
}

/// Removes the tool and the app. The stores and what the tool keeps about them are left alone.
pub fn uninstall(paths: &Paths, report: &mut dyn FnMut(Progress)) -> Outcome<()> {
    instance::quit_running(paths)?;
    report(Progress::Started(Stage::RemoveTool));
    if let Err(failure) = tool::find_uv(paths).and_then(|uv| tool::uninstall(&uv, paths)) {
        report(Progress::Note(format!("The tool wasn't removed. {failure}")));
    }

    report(Progress::Started(Stage::RemoveApp));
    for folder in [&paths.desktop, &paths.start_menu] {
        remove_file(&shortcut(folder))?;
    }
    startup::set(paths, false)?;
    for key in [Some(paths.uninstall_key()), paths.sandbox_registry().map(str::to_owned)].into_iter().flatten() {
        if let Err(error) = CURRENT_USER.remove_tree(&key)
            && error.code() != ERROR_FILE_NOT_FOUND.to_hresult()
        {
            return Err(error).or_say(|| format!("The registry key {key} couldn't be removed"));
        }
    }
    match fs::remove_dir_all(&paths.local) {
        Err(error) if error.kind() != io::ErrorKind::NotFound => {
            return Err(error).or_say(|| format!("{} couldn't be removed", paths.local.display()));
        }
        _ => {}
    }
    remove_exe(paths)
}

/// Returns whether the exe that is running is the installed one, which is the app, and not a download of it.
pub fn is_installed(paths: &Paths) -> bool {
    env::current_exe().is_ok_and(|running| is_same_place(&running, &paths.exe()))
}

fn shortcut(folder: &Path) -> PathBuf {
    folder.join(format!("{APP_NAME}.lnk"))
}

fn copy_exe(installed: &Path) -> Outcome<()> {
    let running = env::current_exe().or_say(|| "This exe's own path couldn't be read".to_owned())?;
    if is_same_place(&running, installed) {
        return Ok(());
    }
    if let Some(folder) = installed.parent() {
        fs::create_dir_all(folder).or_say(|| format!("{} couldn't be made", folder.display()))?;
    }
    let started = Instant::now();
    while let Err(error) = fs::copy(&running, installed) {
        if started.elapsed() > COPY_PATIENCE {
            return Err(error).or_say(|| format!("The exe couldn't be copied to {}", installed.display()));
        }
        thread::sleep(COPY_CHECK);
    }
    Ok(())
}

fn is_same_place(one: &Path, other: &Path) -> bool {
    match (fs::canonicalize(one), fs::canonicalize(other)) {
        (Ok(one), Ok(other)) => one == other,
        _ => false,
    }
}

fn remove_file(file: &Path) -> Outcome<()> {
    match fs::remove_file(file) {
        Err(error) if error.kind() != io::ErrorKind::NotFound => {
            Err(error).or_say(|| format!("{} couldn't be removed", file.display()))
        }
        _ => Ok(()),
    }
}

/// Lists the app among the installed ones, with what Windows shows about it and how to remove it.
fn register(paths: &Paths, exe: &Path) -> Outcome<()> {
    let path = paths.uninstall_key();
    let failed = || format!("The registry key {path} couldn't be written");
    let key = CURRENT_USER.create(&path).or_say(failed)?;
    let uninstall = format!("\"{}\" --uninstall", exe.display());
    let size_kb = fs::metadata(exe).map_or(0, |exe| exe.len() / 1024);
    for (name, value) in [
        ("DisplayName", APP_NAME),
        (VERSION_VALUE, VERSION),
        ("Publisher", PUBLISHER),
        ("URLInfoAbout", REPOSITORY),
        ("DisplayIcon", &exe.display().to_string()),
        ("InstallLocation", &paths.install.display().to_string()),
        ("UninstallString", &uninstall),
        ("QuietUninstallString", &format!("{uninstall} --quiet")),
    ] {
        key.set_string(name, value).or_say(failed)?;
    }
    for (name, value) in [
        ("EstimatedSize", u32::try_from(size_kb).unwrap_or(u32::MAX)),
        // There is nothing to modify or repair, so Windows offers only Uninstall.
        ("NoModify", 1),
        ("NoRepair", 1),
    ] {
        key.set_u32(name, value).or_say(failed)?;
    }
    Ok(())
}

/// Removes the installed exe and its folder, when nothing else is in it.
fn remove_exe(paths: &Paths) -> Outcome<()> {
    let exe = paths.exe();
    let running = env::current_exe().or_say(|| "This exe's own path couldn't be read".to_owned())?;
    if !is_same_place(&running, &exe) {
        remove_file(&exe)?;
        // Fails when something else is in the folder, which is then left.
        let _ = fs::remove_dir(&paths.install);
        return Ok(());
    }
    // Windows won't delete an exe that is running, so a command prompt does it once this one has ended, trying for
    // twenty seconds. `rmdir` without `/s` only removes an empty folder.
    let script = format!(
        "/d /s /c \"(for /l %i in (1,1,20) do if exist \"{exe}\" (del /f /q \"{exe}\" & ping -n 2 127.0.0.1 >nul)) & \
         rmdir \"{folder}\"\"",
        exe = exe.display(),
        folder = paths.install.display()
    );
    Command::new(env::var_os("ComSpec").unwrap_or_else(|| "cmd.exe".into()))
        .raw_arg(script)
        // Not the folder being removed, which a running program would hold in place.
        .current_dir(env::temp_dir())
        // Nothing of this exe's is left open in it, so whatever waits on this exe isn't kept waiting.
        .stdin(Stdio::null())
        .stdout(Stdio::null())
        .stderr(Stdio::null())
        .creation_flags(CREATE_NO_WINDOW.0)
        .spawn()
        .or_say(|| format!("{} couldn't be removed", exe.display()))?;
    Ok(())
}
