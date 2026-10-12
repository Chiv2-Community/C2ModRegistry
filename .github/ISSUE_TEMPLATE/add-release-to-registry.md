---
name: Add Release to Registry
about: Automatically add a release for a registered mod
title: "[RELEASE] MOD_NAME Version MOD_VERSION"
labels: 'mod-release'
assignees: ''

---

If your mod is not registered, use the "Add Package to Registry" template instead.

- Commit `mod.json` at the repository root before tagging the release.
- Use `mod_dependencies` for pak mods and `plugin_dependencies` for DLL plugins. Both use `repo_url` and `version`. Existing `dependencies` fields are read as `mod_dependencies`.
- Publish a GitHub release with a semantic version tag, such as `v1.1.0`.
- Attach exactly one `.pak` file.

Replace `MOD_NAME` in the title and `USERNAME/MOD_REPO_NAME` below. Replace `MOD_VERSION` in the title and JSON with the exact release tag. Leave `action` unchanged.

```json
{
  "action": "add-package-release",
  "repo_url": "https://github.com/USERNAME/MOD_REPO_NAME",
  "release_tag": "MOD_VERSION"
}
```

If the request fails, fix the reported error and reply "retry".
