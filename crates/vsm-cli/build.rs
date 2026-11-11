//! Embeds the source commit so the binary can report its provenance.
use std::process::Command;

fn main() {
    let commit = Command::new("git")
        .args(["rev-parse", "--short=7", "HEAD"])
        .output()
        .ok()
        .filter(|o| o.status.success())
        .and_then(|o| String::from_utf8(o.stdout).ok())
        .map(|s| s.trim().to_string())
        .filter(|s| !s.is_empty())
        .unwrap_or_else(|| "unknown".into());
    let dirty = Command::new("git")
        .args(["status", "--porcelain", "--untracked-files=no"])
        .output()
        .ok()
        .is_some_and(|o| o.status.success() && !o.stdout.is_empty());
    let commit = if dirty && commit != "unknown" {
        format!("{commit}-dirty")
    } else {
        commit
    };
    println!("cargo:rustc-env=VSM_GIT_COMMIT={commit}");
    // Rebuild when HEAD or the index moves. Ask git for the paths: in a worktree `.git` is a file.
    for name in ["HEAD", "index"] {
        if let Some(path) = Command::new("git")
            .args(["rev-parse", "--path-format=absolute", "--git-path", name])
            .output()
            .ok()
            .filter(|o| o.status.success())
            .and_then(|o| String::from_utf8(o.stdout).ok())
        {
            println!("cargo:rerun-if-changed={}", path.trim());
        }
    }
    println!("cargo:rerun-if-changed=build.rs");
}
