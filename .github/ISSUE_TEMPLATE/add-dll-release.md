---
name: Add DLL Release to Registry
about: Register a native DLL plugin release in the registry
title: "[DLL RELEASE] PLUGIN_NAME Version PLUGIN_VERSION"
labels: ''
assignees: ''

---

- Publish a GitHub release with a semantic version tag, such as `v1.0.0`.
- Commit `plugin.json` at the repository root before tagging the release. Use the [plugin.json schema](https://github.com/Chiv2-Community/zero-infra-mod-registry/blob/v1/schemas/plugin.schema.json) for its structure and dependencies.
- If you forget to create or update it for a particular release, upload the corrected file to that release's assets. The file in the release assets takes precedence over the file in the repo.
- Attach your `.dll` file.

Replace `PLUGIN_NAME` in the title and `USERNAME/PLUGIN_REPO_NAME` below. Replace `PLUGIN_VERSION` in the title and JSON with the exact release tag. Leave `action` unchanged.

```json
{
  "action": "add-dll-release",
  "repo_url": "https://github.com/USERNAME/PLUGIN_REPO_NAME",
  "release_tag": "PLUGIN_VERSION"
}
```

The registry creates a pull request for approval by a registry admin. Every DLL version requires approval, including updates. Your DLL release is added and this issue closes when that pull request is merged.

DLLs run native code. Registry approval and hash checks do not make them safe.

If the request fails, fix the reported error and reply "retry".
