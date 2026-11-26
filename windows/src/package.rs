//! What the exe carries, put there by the build.

pub const APP_NAME: &str = env!("APP_NAME");
/// The tool's version, which is the exe's too.
pub const VERSION: &str = env!("APP_VERSION");
pub const PUBLISHER: &str = env!("CARGO_PKG_AUTHORS");
pub const REPOSITORY: &str = env!("APP_REPOSITORY");
pub const WHEEL_NAME: &str = env!("WHEEL_NAME");
pub const WHEEL: &[u8] = include_bytes!(env!("WHEEL_PATH"));
/// The versions of the tool's dependencies it was tested with, as a requirements file.
pub const CONSTRAINTS: &str = include_str!(env!("CONSTRAINTS_PATH"));
/// The Python the tool was tested on.
pub const PYTHON_VERSION: &str = env!("PYTHON_VERSION");
/// The tool's Agent Skill, which tells an agent how to use it.
pub const SKILL: &str = include_str!(env!("SKILL_PATH"));

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn the_wheel_is_this_version_of_the_tool() {
        assert_eq!(WHEEL_NAME, format!("reference_store-{VERSION}-py3-none-any.whl"));
        // A wheel is a zip file, which starts with these bytes.
        assert!(WHEEL.starts_with(b"PK\x03\x04"));
    }

    #[test]
    fn the_dependencies_are_pinned_and_the_tool_is_not_among_them() {
        assert!(CONSTRAINTS.lines().any(|line| line.starts_with("fastapi==")));
        assert!(CONSTRAINTS.lines().all(|line| line.contains("==")));
        assert!(!CONSTRAINTS.contains("reference-store"));
    }

    #[test]
    fn the_skill_is_all_of_its_folder() {
        assert!(SKILL.starts_with("---") && SKILL.contains("name: reference-store"));
        let folder = std::path::Path::new(env!("SKILL_PATH")).parent().unwrap();
        // The exe carries the one file, so another beside it would be left out of what is installed.
        assert_eq!(std::fs::read_dir(folder).unwrap().count(), 1);
    }

    #[test]
    fn the_repository_and_python_are_known() {
        assert!(REPOSITORY.starts_with("https://github.com/"));
        assert!(PYTHON_VERSION.starts_with("3."));
    }
}
