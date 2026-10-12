---
name: Add Release to Registry
about: Request approval for a pak mod release, including a first release
title: "[RELEASE] MOD_NAME Version MOD_VERSION"
labels: 'mod-release'
assignees: ''

---

Use this template for both your mod's first release and later versions. Each release requires approval by a registry admin through a generated pull request.

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
