---
description: Switch to main and delete previous branch
---

Switch back to main branch and delete the branch you were on, discarding all commits and changes. Also closes any upstream pull requests for the deleted branch.

Steps:
1. Check current branch with `git branch --show-current`
2. If already on main/master, inform user no reset needed
3. If on feature branch:
   - Show commits to be lost: `git log main..HEAD --oneline`
   - Store the branch name
   - Use GitHub MCP to find and close any PRs for this branch: `mcp__github__list_pull_requests` (filter by head branch), then `mcp__github__update_pull_request` to close them
   - Switch to main: `git checkout main`
   - Delete the feature branch: `git branch -D <branch-name>`
   - Clean up working directory: `git reset --hard HEAD` to discard all tracked file changes
   - Remove untracked files: `git clean -fd` to remove untracked files and directories
   - Show result: `git status` and `git branch`

WARNING: Permanently deletes the feature branch, all its commits/changes, and closes upstream PRs. Also discards ALL working directory changes and removes untracked files.
