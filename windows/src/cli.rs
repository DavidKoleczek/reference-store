//! What the exe was started to do, from its arguments.

use std::ffi::OsString;
use std::path::PathBuf;

use crate::failure::{Failure, Outcome};
use crate::install::Options;
use crate::startup::BACKGROUND;
use crate::update::UPDATE;

const USAGE: &str = "\
ReferenceStoreSetup.exe
    Open setup. Once installed, the exe opens the app in the browser instead, and stays by the clock.
ReferenceStoreSetup.exe --background
    Run the app without opening the browser, as Windows does at sign-in.
ReferenceStoreSetup.exe --install [--store <folder>] [--local-network] [--desktop-shortcut] [--start-menu-shortcut]
        [--start-at-sign-in]
    Install without asking anything, with git and uv when they are missing. The folder becomes the first store, when
    there is none, and the default when it is a store already. The Agent Skill is updated where it is installed.
ReferenceStoreSetup.exe --update
    Install this exe over the installed app as that one was set up, and start the app again. The app does this with
    a newer exe it has downloaded.
ReferenceStoreSetup.exe --uninstall [--quiet]
    Remove the app and the tool, and keep the stores. Asks first, unless --quiet.";

#[derive(Debug, PartialEq)]
pub enum Command {
    /// Opened with nothing said, as a shortcut or a download is: the app when the exe is the installed one, and
    /// setup otherwise.
    Open,
    Background,
    Install(Options),
    Update,
    Uninstall {
        quiet: bool,
    },
}

/// Reads the arguments after the exe's own name.
pub fn parse(arguments: impl IntoIterator<Item = OsString>) -> Outcome<Command> {
    let mut alone = Vec::new();
    let mut install = false;
    let mut uninstall = false;
    let mut quiet = false;
    let mut chosen = false;
    let mut options = Options::default();
    let mut arguments = arguments.into_iter();
    while let Some(argument) = arguments.next() {
        match argument.to_str() {
            Some(BACKGROUND) => alone.push(Command::Background),
            Some(UPDATE) => alone.push(Command::Update),
            Some("--install") => install = true,
            Some("--uninstall") => uninstall = true,
            Some("--quiet") => quiet = true,
            Some("--local-network") => (chosen, options.lan) = (true, true),
            Some("--desktop-shortcut") => (chosen, options.shortcuts.desktop) = (true, true),
            Some("--start-menu-shortcut") => (chosen, options.shortcuts.start_menu) = (true, true),
            Some("--start-at-sign-in") => (chosen, options.start_at_sign_in) = (true, true),
            Some("--store") => {
                let folder = arguments.next().ok_or_else(|| wrong("--store needs a folder."))?;
                (chosen, options.store) = (true, Some(PathBuf::from(folder)));
            }
            _ => return Err(wrong(&format!("{} isn't an argument of this exe.", argument.display()))),
        }
    }
    match (install, uninstall) {
        _ if alone.len() > 1 || (!alone.is_empty() && (install || uninstall || quiet || chosen)) => {
            Err(wrong("--background and --update each go alone."))
        }
        (true, true) => Err(wrong("--install and --uninstall can't go together.")),
        (true, false) if quiet => Err(wrong("--quiet goes with --uninstall. --install never asks anything.")),
        (true, false) => Ok(Command::Install(options)),
        (false, _) if chosen => Err(wrong("What to install goes with --install.")),
        (false, true) => Ok(Command::Uninstall { quiet }),
        (false, false) if quiet => Err(wrong("--quiet goes with --uninstall.")),
        (false, false) => Ok(alone.pop().unwrap_or(Command::Open)),
    }
}

fn wrong(problem: &str) -> Failure {
    Failure::new(format!("{problem}\n\n{USAGE}"))
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::install::Shortcuts;

    fn parsed(arguments: &[&str]) -> Outcome<Command> {
        parse(arguments.iter().map(OsString::from))
    }

    #[test]
    fn no_arguments_open_it() {
        assert_eq!(parsed(&[]).unwrap(), Command::Open);
    }

    #[test]
    fn background_is_what_windows_starts_it_with() {
        assert_eq!(parsed(&["--background"]).unwrap(), Command::Background);
    }

    #[test]
    fn update_is_what_the_app_starts_a_newer_exe_with() {
        assert_eq!(parsed(&["--update"]).unwrap(), Command::Update);
    }

    #[test]
    fn install_takes_what_setup_would_ask() {
        const STORE: &str = "D:/references";
        let arguments = ["--install", "--store", STORE, "--local-network", "--desktop-shortcut", "--start-at-sign-in"];
        let command = parsed(&arguments).unwrap();
        let options = Options {
            store: Some(PathBuf::from(STORE)),
            lan: true,
            shortcuts: Shortcuts { desktop: true, start_menu: false },
            start_at_sign_in: true,
            ..Options::default()
        };
        assert_eq!(command, Command::Install(options));
        assert_eq!(parsed(&["--install"]).unwrap(), Command::Install(Options::default()));
    }

    #[test]
    fn uninstall_asks_unless_quiet() {
        assert_eq!(parsed(&["--uninstall"]).unwrap(), Command::Uninstall { quiet: false });
        assert_eq!(parsed(&["--uninstall", "--quiet"]).unwrap(), Command::Uninstall { quiet: true });
    }

    #[test]
    fn arguments_that_dont_go_together_are_refused_with_the_usage() {
        for arguments in [
            &["--install", "--uninstall"][..],
            &["--install", "--quiet"],
            &["--uninstall", "--desktop-shortcut"],
            &["--store", r"D:\references"],
            &["--install", "--store"],
            &["--quiet"],
            &["--background", "--install"],
            &["--background", "--quiet"],
            &["--background", "--update"],
            &["--update", "--background"],
            &["--update", "--update"],
            &["--update", "--store", "D:/references"],
            &["--unknown"],
        ] {
            let failure = parsed(arguments).unwrap_err().to_string();
            assert!(failure.contains("--install [--store <folder>]"), "{arguments:?}: {failure}");
        }
    }
}
