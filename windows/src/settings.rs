//! What the app remembers between runs, in `desktop.json` beside the tool's own configuration.

use std::fs;
use std::path::PathBuf;

use serde_json::{Value, json};

use crate::failure::{OrSay, Outcome};
use crate::paths::Paths;

const FILE: &str = "desktop.json";
/// The port the app asks for, so its address is the same on every machine until something else holds the port.
const FIRST_PORT: u16 = 8790;

#[derive(Clone, Copy, Debug, PartialEq)]
pub struct Settings {
    /// Whether devices on the local network can open the app.
    pub lan: bool,
    /// The port the app was last served on, which it asks for again so its address stays the same.
    pub port: u16,
}

impl Default for Settings {
    fn default() -> Self {
        Self { lan: false, port: FIRST_PORT }
    }
}

impl Settings {
    /// Returns what was remembered. Whatever is missing or can't be read is as it is at first.
    pub fn read(paths: &Paths) -> Self {
        fs::read_to_string(file(paths)).map_or_else(|_| Self::default(), |text| Self::from_json(&text))
    }

    pub fn write(self, paths: &Paths) -> Outcome<()> {
        let file = file(paths);
        let failed = || format!("{} couldn't be written", file.display());
        fs::create_dir_all(&paths.home).or_say(failed)?;
        fs::write(&file, self.to_json()).or_say(failed)
    }

    fn from_json(text: &str) -> Self {
        let read: Value = serde_json::from_str(text).unwrap_or_default();
        let first = Self::default();
        Self {
            lan: read["lan"].as_bool().unwrap_or(first.lan),
            port: read["port"]
                .as_u64()
                .and_then(|port| u16::try_from(port).ok())
                .filter(|port| *port != 0)
                .unwrap_or(first.port),
        }
    }

    fn to_json(self) -> String {
        format!("{:#}\n", json!({ "lan": self.lan, "port": self.port }))
    }
}

fn file(paths: &Paths) -> PathBuf {
    paths.home.join(FILE)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn what_is_written_is_read_back() {
        let settings = Settings { lan: true, port: 51234 };
        assert_eq!(Settings::from_json(&settings.to_json()), settings);
    }

    #[test]
    fn what_cant_be_read_is_as_it_is_at_first() {
        let first = Settings { lan: false, port: 8790 };
        for text in ["", "not json", "[]", r#"{"lan": "yes", "port": 0}"#, r#"{"port": 70000}"#] {
            assert_eq!(Settings::from_json(text), first, "{text}");
        }
        assert_eq!(Settings::from_json(r#"{"lan": true}"#), Settings { lan: true, port: 8790 });
    }
}
