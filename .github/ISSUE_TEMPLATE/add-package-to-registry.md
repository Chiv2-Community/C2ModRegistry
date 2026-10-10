---
name: Add Package to Registry
about: Register a new mod package in the registry
title: "[NEW MOD] MOD_NAME"
labels: 'new-mod'
assignees: ''

---

- Commit `mod.json` at the repository root before tagging the release.
- Publish a GitHub release with a semantic version tag, such as `v1.0.0`.
- Attach exactly one `.pak` file.

Replace `MOD_NAME` in the title and `USERNAME/MOD_REPO_NAME` below. Leave `action` unchanged.

```json
{
  "action": "add-package",
  "repo_url": "https://github.com/USERNAME/MOD_REPO_NAME"
}
```

If the request fails, fix the reported error and reply "retry".
