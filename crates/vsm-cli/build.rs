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
    // HEAD is usually symbolic, so also watch the branch ref it points at (a commit moves only that).
    let branch_ref = Command::new("git")
        .args(["symbolic-ref", "-q", "HEAD"])
        .output()
        .ok()
        .filter(|o| o.status.success())
        .and_then(|o| String::from_utf8(o.stdout).ok())
        .map(|s| s.trim().to_string());
    let mut names = vec![
        "HEAD".to_string(),
        "index".to_string(),
        "packed-refs".to_string(),
    ];
    names.extend(branch_ref);
    for name in &names {
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
