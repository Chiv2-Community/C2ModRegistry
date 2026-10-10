---
name: Add Release to Registry
about: Automatically add a release for a registered mod
title: "[RELEASE] MOD_NAME Version MOD_VERSION"
labels: 'mod-release'
assignees: ''

---

Hello, I have created a new mod release for "MOD_NAME" with version "MOD_VERSION"

**1. Pre-Release Checklist:**
   - Ensure your mod is registered in the mod list. If it is not, create an issue using the "Add Package to Registry" template instead. That request processes your mod's releases and creates a pull request for approval.
   - Commit `mod.json` at the root of your mod repository before creating the release tag.
   - Create a GitHub release with a semantic version tag, such as `v1.1.0`.
   - Attach a single `.pak` file to the release. The registry scans it to generate the asset manifest and file hash.

**2. Update Request:**
   - Replace `MOD_NAME` and `MOD_VERSION` in the title and description with your mod name and exact release tag.
   - Replace `USERNAME/MOD_REPO_NAME` below with your GitHub organization or username and repository name.
   - Replace `MOD_VERSION` below with the exact release tag, such as `v1.1.0`. Leave `action` unchanged.

```json
{
  "action": "add-package-release",
  "repo_url": "https://github.com/USERNAME/MOD_REPO_NAME",
  "release_tag": "MOD_VERSION"
}
```

   - The registry processes the release and updates the package database. A successful request closes this issue automatically.

**3. Troubleshooting:**
   - If the request fails, check the error posted on this issue. After correcting the problem, reply "retry".
