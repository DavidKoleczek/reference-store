//! The tool itself, which uv installs from the wheel the exe carries.

use std::fs;
use std::path::{Path, PathBuf};

use serde_json::Value;

use crate::failure::{Failure, OrSay, Outcome};
use crate::package::{CONSTRAINTS, PYTHON_VERSION, VERSION, WHEEL, WHEEL_NAME};
use crate::paths::Paths;
use crate::{prerequisites, run};

const TOOL: &str = "reference-store";
const FIRST_STORE: &str = "main";
const CONFIGURATION: &str = "config.json";
const PROJECT_PRIORITY: i32 = 0;

/// Returns uv, which installs the tool and knows where it is.
pub fn find_uv(paths: &Paths) -> Outcome<PathBuf> {
    prerequisites::find_uv(paths)
        .ok_or_else(|| Failure::new("uv isn't installed, and the tool runs on it. Setup installs it again."))
}

/// Installs this exe's version of the tool in place of any other, and returns its program.
pub fn install(uv: &Path, paths: &Paths) -> Outcome<PathBuf> {
    // uv takes a wheel and its pins as files. It looks for the wheel there again on `uv tool upgrade`, which fails
    // without it, so the wheel stays, and the one of the version before goes.
    let package = paths.local.join("package");
    let wheel = package.join(WHEEL_NAME);
    let constraints = package.join("constraints.txt");
    let _ = fs::remove_dir_all(&package);
    fs::create_dir_all(&package).or_say(|| format!("{} couldn't be made", package.display()))?;
    fs::write(&wheel, WHEEL).or_say(|| format!("{} couldn't be written", wheel.display()))?;
    fs::write(&constraints, CONSTRAINTS).or_say(|| format!("{} couldn't be written", constraints.display()))?;
    run::output(
        run::hidden(uv, paths)
            .args(["tool", "install", "--force", "--python", PYTHON_VERSION])
            .arg(&wheel)
            .arg("--constraints")
            .arg(&constraints),
    )?;

    let tool = program(uv, paths)?;
    let version = run::output(run::hidden(&tool, paths).arg("--version"))?;
    if version.trim() != format!("{TOOL} {VERSION}") {
        return Err(Failure::new(format!(
            "{} says it is `{}`, not version {VERSION}, after it was installed.",
            tool.display(),
            version.trim()
        )));
    }
    Ok(tool)
}

/// Returns the tool's program, which is where uv keeps the programs of the tools it has installed.
pub fn program(uv: &Path, paths: &Paths) -> Outcome<PathBuf> {
    let folder = run::output(run::hidden(uv, paths).args(["tool", "dir", "--bin"]))?;
    let tool = Path::new(folder.trim()).join(format!("{TOOL}.exe"));
    if !tool.is_file() {
        return Err(Failure::new(format!(
            "The tool isn't installed: {} isn't there. Setup installs it again.",
            tool.display()
        )));
    }
    Ok(tool)
}

/// Puts the folder of uv's tools on the user's `PATH`, so a terminal and an agent find the tool.
pub fn put_on_path(uv: &Path, paths: &Paths) -> Outcome<()> {
    run::output(run::hidden(uv, paths).args(["tool", "update-shell"])).map(drop)
}

pub fn uninstall(uv: &Path, paths: &Paths) -> Outcome<()> {
    run::output(run::hidden(uv, paths).args(["tool", "uninstall", TOOL])).map(drop)
}

/// A store the tool has registered.
pub struct Store {
    pub name: String,
    pub path: PathBuf,
    pub default: bool,
}

/// Returns whether the tool has stores registered. Its own file says so, which uninstalling leaves, so stores are
/// known of before the tool is there to ask.
pub fn remembers_stores(paths: &Paths) -> bool {
    fs::read_to_string(paths.home.join(CONFIGURATION)).is_ok_and(|configuration| has_stores(&configuration))
}

fn has_stores(configuration: &str) -> bool {
    serde_json::from_str::<Value>(configuration)
        .is_ok_and(|configuration| configuration["stores"].as_array().is_some_and(|stores| !stores.is_empty()))
}

/// Returns the stores the tool has registered.
pub fn stores(tool: &Path, paths: &Paths) -> Outcome<Vec<Store>> {
    let listed = run::output(run::hidden(tool, paths).args(["list-stores", "--json"]))?;
    registered(&listed).ok_or_else(|| Failure::new(format!("The tool's list of stores couldn't be read: {listed}")))
}

fn registered(listed: &str) -> Option<Vec<Store>> {
    let stores: Vec<Value> = serde_json::from_str(listed).ok()?;
    stores
        .iter()
        // A project's own store is listed from inside the project, and is not one the tool has registered.
        .filter(|store| store["priority_order"] != PROJECT_PRIORITY)
        .map(|store| {
            Some(Store {
                name: store["name"].as_str()?.to_owned(),
                path: PathBuf::from(store["path"].as_str()?),
                default: store["default"].as_bool()?,
            })
        })
        .collect()
}

/// Registers a folder as the default store. One that holds a store already is connected as it is.
pub fn add_first_store(tool: &Path, folder: &Path, paths: &Paths) -> Outcome<()> {
    run::output(run::hidden(tool, paths).args(["add-store", FIRST_STORE]).arg(folder).arg("--default")).map(drop)
}

pub fn set_default_store(tool: &Path, name: &str, paths: &Paths) -> Outcome<()> {
    run::output(run::hidden(tool, paths).args(["set-default-store", name])).map(drop)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn stores_are_known_of_from_the_tools_own_file() {
        assert!(has_stores(r#"{"default_store": "main", "stores": [{"name": "main", "location": "D:/references"}]}"#));
        assert!(!has_stores(r#"{"stores": []}"#));
        assert!(!has_stores(r#"{"sites": {}}"#));
        assert!(!has_stores("not JSON"));
    }

    #[test]
    fn a_projects_own_store_is_not_a_registered_one() {
        let listed = r#"[
            {"name": "game-1", "path": "C:\\Projects\\game-1\\.reference-store", "default": false, "priority_order": 0},
            {"name": "main", "path": "D:\\references", "default": true, "priority_order": 1}
        ]"#;
        let stores = registered(listed).unwrap();
        assert_eq!(stores.len(), 1);
        assert_eq!(stores[0].name, "main");
        assert_eq!(stores[0].path, Path::new(r"D:\references"));
        assert!(stores[0].default);
    }

    #[test]
    fn a_list_that_is_not_one_of_stores_is_not_read() {
        assert!(registered("[{}]").is_none());
        assert!(registered("{}").is_none());
    }
}
