---
description: Create a new demo branch with auto-incrementing number
---

Create a new git branch named "demo-branch" (or "demo-branch-2", "demo-branch-3", etc. if it already exists).

Steps:
1. Check if "demo-branch" exists: `git branch --list demo-branch`
2. If it exists, check "demo-branch-2", "demo-branch-3", etc. until you find an available name
3. Create and checkout the new branch: `git checkout -b <branch-name>`
4. Confirm the branch was created and show current status
