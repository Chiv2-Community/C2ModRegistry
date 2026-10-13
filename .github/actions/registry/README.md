# Registry integration

Builds `zero-infra-mod-registry` directly from the immutable `REVISION` pinned in
`action.yml`. No source patches are maintained or applied here. Registry logic,
including DLL support and the index/error-handling fixes, lives upstream.

DLL support extends the upstream CLI, `FilesystemPackageRegistry`, and GitHub
retriever, not a separate script. `add-dll-release REPO_URL TAG`
writes per-plugin files under `dll_db/packages`, listed in `dll_db/plugin_list_index.txt`; `validate` checks both databases and
`validate --verify-dll-downloads` checks downloaded bytes. The composite action
exposes that option as `verify_dll_downloads: 'true'` (the default). DLL issue
processing explicitly requires download verification before committing registry
changes or opening a PR; issue payloads cannot disable it.

For releases with multiple DLL assets, set `dll_file: 'Plugin.dll'` to select an
exact, case-sensitive filename. The action passes it as `--dll-file`; omission
requires exactly one DLL asset. Issue requests use the same `dll_file` field.
Only the selected DLL is registered, with no fallback on missing matches.

Release metadata follows the upstream [mod.json](https://github.com/Chiv2-Community/zero-infra-mod-registry/blob/prepare-v1/schemas/mod.schema.json) and [plugin.json](https://github.com/Chiv2-Community/zero-infra-mod-registry/blob/prepare-v1/schemas/plugin.schema.json) schemas. Release uploads take precedence over repository-root files at the release tag. Plugin records include release notes and publication dates; they do not contain pak manifests.

Merge upstream changes before submitting the C2ModRegistry PR, then update the
pin to the published upstream commit as needed.
