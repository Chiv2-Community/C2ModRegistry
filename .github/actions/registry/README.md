# Registry integration

Builds `zero-infra-mod-registry` directly from the immutable `REVISION` pinned in
`action.yml`. No source patches are maintained or applied here. Registry logic,
including DLL support and the index/error-handling fixes, lives upstream.

DLL support extends the upstream CLI, `FilesystemPackageRegistry`, and GitHub
retriever, not a separate script. `add-dll-release REPO_URL TAG`
writes the separate `dll_db/index.json`; `validate` checks its schema and
`validate --verify-dll-downloads` checks downloaded bytes. The composite action
exposes that option as `verify_dll_downloads: 'true'`.

For releases with multiple DLL assets, set `dll_file: 'Plugin.dll'` to select an
exact, case-sensitive filename. The action passes it as `--dll-file`; omission
requires exactly one DLL asset. Issue requests use the same `dll_file` field.
Only the selected DLL is registered, with no fallback on missing matches.

Run the deterministic Docker/CLI regression suite with:

```sh
python3 -m unittest discover -s tests -v
```

Before an upstream dependency is published, you can test a local source checkout
at the exact pinned commit with `REGISTRY_TEST_SOURCE=/path/to/checkout` set for
that command. The production workflow still fetches upstream; it does not use
local source overrides. Merge the upstream changes before submitting the
C2ModRegistry PR, then update the pin to the published upstream commit as needed.
