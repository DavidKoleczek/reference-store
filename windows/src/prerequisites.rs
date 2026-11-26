//! What the tool needs that setup installs when it is missing: uv, which installs and runs the tool, and git, which
//! only stores on GitHub are fetched with.

use std::env;
use std::path::{Path, PathBuf};

use crate::failure::{Failure, Outcome};
use crate::paths::Paths;
use crate::run;

// Astral's own installer, which is what its documentation has people run.
const INSTALL_UV: &str = "irm https://astral.sh/uv/install.ps1 | iex";
// Has that installer put uv in a folder it is told, and leave `PATH` and the rest of the machine alone.
const UV_UNMANAGED_INSTALL: &str = "UV_UNMANAGED_INSTALL";
const GIT_PACKAGE: &str = "Git.Git";
// Where Git for Windows installs itself, under the folder of the machine's programs.
const GIT_PROGRAM: &str = r"Git\cmd\git.exe";
// The Git for Windows installer, fetched and run, for a machine with no winget.
const INSTALL_GIT: &str = include_str!("install-git.ps1");

/// Returns uv, from `PATH` or from where its installer puts it, which a `PATH` read before it ran doesn't have.
pub fn find_uv(paths: &Paths) -> Option<PathBuf> {
    run::find("uv").or_else(|| Some(paths.uv_bin.join("uv.exe")).filter(|uv| uv.is_file()))
}

/// Installs uv for the current user and returns it.
pub fn install_uv(paths: &Paths) -> Outcome<PathBuf> {
    let mut install = powershell(INSTALL_UV, paths)?;
    if paths.is_sandbox() {
        install.env(UV_UNMANAGED_INSTALL, &paths.uv_bin);
    }
    run::output(&mut install)?;
    find_uv(paths).ok_or_else(|| {
        Failure::new(format!("uv was installed, but it isn't in {}. Open setup again.", paths.uv_bin.display()))
    })
}

pub fn find_git() -> Option<PathBuf> {
    let installed = || Some(PathBuf::from(env::var_os("ProgramFiles")?).join(GIT_PROGRAM)).filter(|git| git.is_file());
    run::find("git").or_else(installed)
}

/// Installs Git for Windows, which is for the whole machine, so Windows may ask to allow it.
pub fn install_git(paths: &Paths) -> Outcome<()> {
    if paths.is_sandbox() {
        return Err(Failure::new("A sandbox doesn't install it, since it would be for the whole machine."));
    }
    let mut install = match run::find("winget") {
        Some(winget) => {
            let mut install = run::hidden(&winget, paths);
            install.args(["install", "--id", GIT_PACKAGE, "--exact", "--source", "winget", "--silent"]).args([
                "--accept-package-agreements",
                "--accept-source-agreements",
                "--disable-interactivity",
            ]);
            install
        }
        None => powershell(INSTALL_GIT, paths)?,
    };
    run::output(&mut install)?;
    find_git().map(drop).ok_or_else(|| Failure::new("Git's installer ran, but git isn't where it installs itself."))
}

fn powershell(script: &str, paths: &Paths) -> Outcome<std::process::Command> {
    let powershell = run::find("powershell").ok_or_else(|| Failure::new("PowerShell wasn't found on PATH."))?;
    let mut command = run::hidden(Path::new(&powershell), paths);
    command.args(["-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-Command", script]);
    // Started from a newer PowerShell, this one is handed that one's modules and can't load its own.
    command.env_remove("PSModulePath");
    Ok(command)
}
