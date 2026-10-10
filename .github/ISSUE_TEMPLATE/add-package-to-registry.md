---
name: Add Package to Registry
about: Register a new mod package in the registry
title: "[NEW MOD] MOD_NAME"
labels: 'new-mod'
assignees: ''

---

Hello, I would like to register a new mod called "MOD_NAME" in the registry.

**1. Pre-Release Checklist:**
   - Commit `mod.json` at the root of your mod repository before creating the release tag.
   - Create a GitHub release with a semantic version tag, such as `v1.0.0`.
   - Attach a single `.pak` file to the release. The registry scans it to generate the asset manifest and file hash.

**2. Requesting Inclusion:**
   - Replace `MOD_NAME` in the title and description with your mod name.
   - Replace `USERNAME/MOD_REPO_NAME` below with your GitHub organization or username and repository name. Leave `action` unchanged.

```json
{
  "action": "add-package",
  "repo_url": "https://github.com/USERNAME/MOD_REPO_NAME"
}
```

**3. Approval:**
   - The registry processes your mod's releases and creates a pull request for approval. You do not need to open a pull request yourself.
   - This issue closes when the pull request is merged.

**4. Troubleshooting:**
   - If the request fails, check the error posted on this issue. After correcting the problem, reply "retry".
