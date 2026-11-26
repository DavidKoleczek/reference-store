//! Reference Store for Windows: one exe that sets the tool up, runs the app from the tray, and updates and removes it.

// Without this Windows opens a console window beside the exe.
#![windows_subsystem = "windows"]

mod cli;
mod control;
mod failure;
mod install;
mod instance;
mod package;
mod paths;
mod prerequisites;
mod run;
mod server;
mod settings;
mod setup;
mod startup;
mod tool;
mod tray;
mod update;
mod win32;

use std::env;
use std::process::ExitCode;

use cli::Command;
use failure::{Failure, OrSay, Outcome};
use install::Progress;
use package::APP_NAME;
use paths::Paths;
use setup::Purpose;

fn main() -> ExitCode {
    match run() {
        Ok(()) => ExitCode::SUCCESS,
        Err(failure) => {
            eprintln!("{failure}");
            ExitCode::FAILURE
        }
    }
}

fn run() -> Outcome<()> {
    let command = cli::parse(env::args_os().skip(1))?;
    let paths = Paths::current().or_say(|| "The folders to install to couldn't be worked out".to_owned())?;
    match command {
        Command::Open if install::is_installed(&paths) => tray::run(&paths, true).inspect_err(show),
        Command::Open => setup::run(&paths, Purpose::Install).inspect_err(show),
        Command::Background => tray::run(&paths, false).inspect_err(show),
        Command::Install(options) => install::install(&options, &paths, &mut print),
        Command::Update => setup::run(&paths, Purpose::Update).inspect_err(show),
        Command::Uninstall { quiet: true } => install::uninstall(&paths, &mut print),
        Command::Uninstall { quiet: false } => {
            let question = format!("Remove {APP_NAME} and its tool from this computer?\n\nYour stores are kept.");
            if !win32::ask(APP_NAME, &question) {
                return Ok(());
            }
            install::uninstall(&paths, &mut print).inspect_err(show)
        }
    }
}

/// Shows what went wrong to someone who started the exe with no terminal to read it in.
fn show(failure: &Failure) {
    win32::show_failure(APP_NAME, &failure.to_string());
}

/// Prints what is going on, which is seen when the exe's output goes to a file or another program.
fn print(progress: Progress) {
    match progress {
        Progress::Started(stage) => println!("{}", stage.label()),
        Progress::Note(note) => println!("{note}"),
    }
}
