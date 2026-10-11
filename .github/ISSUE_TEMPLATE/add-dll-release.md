---
name: Add DLL Release to Registry
about: Request review of a native plugin release (separate from pak mods)
title: 'Add DLL release: '
---

The release must have a semantic version tag.
Native code is not sandboxed; each version requires approval in a pull request.

```json
{
  "action": "add-dll-release",
  "repo_url": "https://github.com/Organization/PluginName",
  "release_tag": "v1.0.0"
}
```
