//! `vsm`: the Voting System Metrics (VSM) pipeline command.

use serde::Serialize;
use std::process::ExitCode;

/// Runtime identity: release version, deployment environment and source commit, kept separate.
#[derive(Debug, Serialize, PartialEq, Eq)]
struct VersionInfo {
    version: &'static str,
    environment: String,
    commit: &'static str,
}

fn version_info(env: Option<String>) -> VersionInfo {
    VersionInfo {
        version: env!("CARGO_PKG_VERSION"),
        environment: env
            .filter(|e| !e.trim().is_empty())
            .unwrap_or_else(|| "unknown".into()),
        commit: env!("VSM_GIT_COMMIT"),
    }
}

const USAGE: &str = "usage: vsm <command>\n\ncommands:\n  version    print version, environment and commit as JSON\n\noptions:\n  -V, --version    same as `vsm version`\n  -h, --help       show this help";

fn main() -> ExitCode {
    let args: Vec<String> = std::env::args().skip(1).collect();
    match args.first().map(String::as_str) {
        Some("version" | "-V" | "--version") => {
            let info = version_info(std::env::var("VSM_ENV").ok());
            println!("{}", serde_json::to_string(&info).expect("serialisable"));
            ExitCode::SUCCESS
        }
        Some("-h" | "--help") | None => {
            println!("{USAGE}");
            ExitCode::SUCCESS
        }
        Some(other) => {
            eprintln!("vsm: unknown command `{other}`\n\n{USAGE}");
            ExitCode::from(2)
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn environment_defaults_to_unknown() {
        assert_eq!(version_info(None).environment, "unknown");
        assert_eq!(version_info(Some("  ".into())).environment, "unknown");
        assert_eq!(version_info(Some("dev".into())).environment, "dev");
    }

    #[test]
    fn version_matches_manifest() {
        assert_eq!(version_info(None).version, env!("CARGO_PKG_VERSION"));
    }
}
