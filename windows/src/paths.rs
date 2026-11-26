//! Where things are on this machine. With `REFERENCE_STORE_SANDBOX` naming a folder, all of it is in that folder, so
//! the exe can be tried without touching what is really installed.

use std::path::{self, PathBuf};
use std::{env, io};

use windows::Win32::UI::Shell::{
    FOLDERID_Desktop, FOLDERID_Documents, FOLDERID_LocalAppData, FOLDERID_Profile, FOLDERID_Programs,
    FOLDERID_RoamingAppData, FOLDERID_UserProgramFiles,
};

use crate::package::APP_NAME;
use crate::win32;

pub const SANDBOX_VARIABLE: &str = "REFERENCE_STORE_SANDBOX";
const EXE_NAME: &str = "ReferenceStore.exe";
// Where Windows keeps what is about the current user's apps, under that user's part of the registry.
const WINDOWS_REGISTRY: &str = r"Software\Microsoft\Windows\CurrentVersion";
// A key Windows reads nothing from, so a sandbox adds no app to its list.
const SANDBOX_REGISTRY: &str = r"Software\ReferenceStoreSandbox";
const UNINSTALL_KEY: &str = r"Uninstall\ReferenceStore";
const RUN_KEY: &str = "Run";
const STARTUP_APPROVED_KEY: &str = r"Explorer\StartupApproved\Run";
// The tool's own names for its folder, and for the variable that moves it.
const HOME_FOLDER: &str = "reference-store";
const HOME_VARIABLE: &str = "REFERENCE_STORE_HOME";
const INSTANCE: &str = "ReferenceStore";
const SANDBOX_INSTANCE: &str = "ReferenceStoreSandbox";
// Where uv's installer puts it, under the user's own folder.
const UV_BIN: &str = r".local\bin";

#[derive(Clone)]
pub struct Paths {
    /// The folder the exe is installed in.
    pub install: PathBuf,
    /// The folder for what the exe keeps for itself and can make again.
    pub local: PathBuf,
    /// The folder the tool keeps its configuration in, and the app its own beside it.
    pub home: PathBuf,
    /// The folder of the Start menu's shortcuts.
    pub start_menu: PathBuf,
    pub desktop: PathBuf,
    /// The folder a first store is suggested in.
    pub documents: PathBuf,
    /// The folder Astral's installer puts uv in, where it is looked for when `PATH` doesn't have it yet.
    pub uv_bin: PathBuf,
    registry: &'static str,
    sandbox: Option<PathBuf>,
}

/// The folders Windows knows, which a real install is spread over.
struct KnownFolders {
    programs: PathBuf,
    local_app_data: PathBuf,
    roaming_app_data: PathBuf,
    /// The tool's folder, when `REFERENCE_STORE_HOME` has moved it.
    home: Option<PathBuf>,
    start_menu: PathBuf,
    desktop: PathBuf,
    documents: PathBuf,
    profile: PathBuf,
}

impl Paths {
    /// Returns where things are, in the sandbox when there is one.
    pub fn current() -> io::Result<Self> {
        match env::var_os(SANDBOX_VARIABLE).filter(|folder| !folder.is_empty()) {
            // Named from wherever the exe was started, and what is installed is started from elsewhere.
            Some(folder) => Ok(Self::sandboxed(path::absolute(folder)?)),
            None => Ok(Self::real(KnownFolders {
                programs: win32::known_folder(&FOLDERID_UserProgramFiles)?,
                local_app_data: win32::known_folder(&FOLDERID_LocalAppData)?,
                roaming_app_data: win32::known_folder(&FOLDERID_RoamingAppData)?,
                home: env::var_os(HOME_VARIABLE).filter(|folder| !folder.is_empty()).map(path::absolute).transpose()?,
                start_menu: win32::known_folder(&FOLDERID_Programs)?,
                desktop: win32::known_folder(&FOLDERID_Desktop)?,
                documents: win32::known_folder(&FOLDERID_Documents)?,
                profile: win32::known_folder(&FOLDERID_Profile)?,
            })),
        }
    }

    fn real(folders: KnownFolders) -> Self {
        Self {
            install: folders.programs.join(APP_NAME),
            local: folders.local_app_data.join(APP_NAME),
            home: folders.home.unwrap_or_else(|| folders.roaming_app_data.join(HOME_FOLDER)),
            start_menu: folders.start_menu,
            desktop: folders.desktop,
            documents: folders.documents,
            uv_bin: folders.profile.join(UV_BIN),
            registry: WINDOWS_REGISTRY,
            sandbox: None,
        }
    }

    fn sandboxed(sandbox: PathBuf) -> Self {
        Self {
            install: sandbox.join("install"),
            local: sandbox.join("local"),
            home: sandbox.join("home"),
            start_menu: sandbox.join("start-menu"),
            desktop: sandbox.join("desktop"),
            documents: sandbox.join("documents"),
            uv_bin: sandbox.join("uv"),
            registry: SANDBOX_REGISTRY,
            sandbox: Some(sandbox),
        }
    }

    pub fn is_sandbox(&self) -> bool {
        self.sandbox.is_some()
    }

    /// Returns the installed exe.
    pub fn exe(&self) -> PathBuf {
        self.install.join(EXE_NAME)
    }

    /// Returns the registry key, under the current user's, that lists the app among the installed ones.
    pub fn uninstall_key(&self) -> String {
        format!(r"{}\{UNINSTALL_KEY}", self.registry)
    }

    /// Returns the registry key whose values are what Windows starts when the user signs in.
    pub fn run_key(&self) -> String {
        format!(r"{}\{RUN_KEY}", self.registry)
    }

    /// Returns the registry key where Windows notes the startup apps the user has turned off.
    pub fn startup_approved_key(&self) -> String {
        format!(r"{}\{STARTUP_APPROVED_KEY}", self.registry)
    }

    /// Returns the name the running app goes by on this machine, which a sandbox's doesn't share.
    pub fn instance(&self) -> &'static str {
        if self.is_sandbox() { SANDBOX_INSTANCE } else { INSTANCE }
    }

    /// Returns the registry key a sandbox made, which is all its own, and None outside one.
    pub fn sandbox_registry(&self) -> Option<&'static str> {
        self.sandbox.as_ref().map(|_| self.registry)
    }

    /// Returns the variables that keep the tool and uv inside the sandbox, and none outside one.
    pub fn environment(&self) -> Vec<(&'static str, PathBuf)> {
        self.sandbox.as_ref().map_or_else(Vec::new, |sandbox| {
            vec![
                (HOME_VARIABLE, self.home.clone()),
                ("UV_TOOL_DIR", sandbox.join("uv-tools")),
                ("UV_TOOL_BIN_DIR", sandbox.join("uv-bin")),
            ]
        })
    }
}

#[cfg(test)]
mod tests {
    use std::path::Path;

    use super::*;

    fn real(home: Option<&str>) -> Paths {
        Paths::real(KnownFolders {
            programs: PathBuf::from(r"C:\Users\me\AppData\Local\Programs"),
            local_app_data: PathBuf::from(r"C:\Users\me\AppData\Local"),
            roaming_app_data: PathBuf::from(r"C:\Users\me\AppData\Roaming"),
            home: home.map(PathBuf::from),
            start_menu: PathBuf::from(r"C:\Users\me\AppData\Roaming\Microsoft\Windows\Start Menu\Programs"),
            desktop: PathBuf::from(r"C:\Users\me\OneDrive\Desktop"),
            documents: PathBuf::from("C:/Users/me/OneDrive/Documents"),
            profile: PathBuf::from("C:/Users/me"),
        })
    }

    #[test]
    fn installs_among_the_users_programs() {
        let paths = real(None);
        assert_eq!(paths.exe(), Path::new(r"C:\Users\me\AppData\Local\Programs\Reference Store\ReferenceStore.exe"));
        assert_eq!(paths.local, Path::new(r"C:\Users\me\AppData\Local\Reference Store"));
        assert_eq!(paths.home, Path::new(r"C:\Users\me\AppData\Roaming\reference-store"));
        assert_eq!(paths.desktop, Path::new(r"C:\Users\me\OneDrive\Desktop"));
        assert_eq!(paths.uv_bin, Path::new(r"C:\Users\me\.local\bin"));
        assert_eq!(paths.uninstall_key(), r"Software\Microsoft\Windows\CurrentVersion\Uninstall\ReferenceStore");
        assert_eq!(paths.run_key(), r"Software\Microsoft\Windows\CurrentVersion\Run");
        let approved = r"Software\Microsoft\Windows\CurrentVersion\Explorer\StartupApproved\Run";
        assert_eq!(paths.startup_approved_key(), approved);
        assert!(!paths.is_sandbox());
        assert_eq!(paths.environment(), Vec::new());
        assert_eq!(paths.sandbox_registry(), None);
    }

    #[test]
    fn the_tools_folder_is_where_the_tool_has_it() {
        assert_eq!(real(Some(r"D:\references\home")).home, Path::new(r"D:\references\home"));
    }

    #[test]
    fn a_sandbox_holds_everything() {
        let sandbox = Path::new(r"D:\try");
        let paths = Paths::sandboxed(sandbox.to_owned());
        let folders = [&paths.install, &paths.local, &paths.home, &paths.start_menu, &paths.desktop, &paths.documents];
        for folder in folders.into_iter().chain([&paths.uv_bin]) {
            assert!(folder.starts_with(sandbox));
        }
        for (_, folder) in paths.environment() {
            assert!(folder.starts_with(sandbox));
        }
        assert!(paths.is_sandbox());
    }

    #[test]
    fn a_sandbox_keeps_out_of_the_keys_windows_reads() {
        let paths = Paths::sandboxed(PathBuf::from(r"D:\try"));
        assert_eq!(paths.uninstall_key(), r"Software\ReferenceStoreSandbox\Uninstall\ReferenceStore");
        assert_eq!(paths.run_key(), r"Software\ReferenceStoreSandbox\Run");
        assert_ne!(paths.instance(), real(None).instance());
        assert_eq!(paths.sandbox_registry(), Some(r"Software\ReferenceStoreSandbox"));
    }
}
