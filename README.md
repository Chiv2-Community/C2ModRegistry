# C2ModRegistry
A registry for available chivalry 2 mods.  People who create mods can register them here, so that they show up in the mod browser.

### DLL registry

DLL plugins are separate from pak mods: `dll_db/index.json` is their index and
contains one entry per organization/name/version, with an HTTPS download source,
SHA-256 hash and byte size. Versions are immutable; submit a new version rather
than replacing a published binary. The launcher only loads explicitly enabled
DLL releases whose bytes match this metadata. UnchainedPlugin is enabled by default.

To register a DLL, use the **Add DLL Release to Registry** issue template:

```json
{
  "action": "add-dll-release",
  "repo_url": "https://github.com/MyOrg/MyPlugin",
  "release_tag": "v1.0.0"
}
```

The existing registry tool's `add-dll-release` command downloads the release's
selected DLL asset to calculate its hash and size. Organization and name come from
the GitHub repository. The issue workflow opens a pull request for approval for
every DLL version (including updates). The existing `validate` command validates
DLL metadata too; `validate --verify-dll-downloads` also checks the binaries.
The registry action enables download verification by default. Both PR CI and DLL
issue processing explicitly require it; failed issue validation blocks commits
and PR creation, and cannot be disabled through the issue JSON.
DLLs do not enter `package_db`, the mod index, or the Unreal asset scanner.

Semantic-version prereleases such as `v1.0.0-RC2` can be registered with the same
command and review process. To test a release without writing its metadata, run
the pinned registry tool with the global dry-run option:

```sh
zero-infra-mod-registry --dry-run add-dll-release https://github.com/Chiv2-Community/UnchainedPlugin v1.0.0-RC2
```

Dry runs still fetch the release and download its DLL to calculate and validate
integrity metadata, but leave the DLL index unchanged. Releases containing
multiple DLL assets (for example, normal and debug builds) require an explicit
`dll_file` in the issue JSON, or `--dll-file UnchainedPlugin.dll` on the CLI.
The initial issue template omits this optional field. If automatic registration
fails because multiple DLLs are present, a follow-up issue comment explains how
to add the filename and reply `retry`; no PR is created until registration succeeds.
The filename must match exactly (case-sensitive); missing or non-DLL assets are
rejected, with no fallback. Without a filename, exactly one DLL asset is required.
Each plugin/version still has one immutable registry entry. Tags must be valid semantic versions;
historical tags such as `v0.0.1dev` are not accepted.
Registry approval and hash checks establish provenance and integrity, not a
sandbox or a guarantee that native code is safe. Only enable publishers you trust.

---

### Registering your mod

### Creating a Release:

**1. Setting up your `mod.json` file:**
   - Every mod requires a `mod.json` file, which should be located at the root of your mod repository.
   - Here's a generic structure for the `mod.json`:
     ```json
     {
       "name": "[Mod-Name]",
       "description": "[Short-Description]",
       "authors": [ "[Author-Name]" ],
       "dependencies": [
         {
           "repo_url": "[Dependency-Repo-URL]",
           "version": "[Version-Number]"
         }
       ]
     }
     ```
   - Replace placeholders like `[Dependency-Repo-URL]`, `[Mod-Name]`, etc., with your actual data.
   - Dependency URLs must point to the mod's GitHub repository. Use a version such as `1.0.0` or a version range such as `>=1.0.0`. If your mod has no dependencies, use `"dependencies": []`.
   - You can also include `"icon_url": "[Icon-URL]"` and `"image_urls": [ "[Image-URL]" ]`. These fields are optional.
   - Commit `mod.json` before creating the release tag. The registry reads it from that tag.


**2. Creating a Repository Release:**
   - Head over to your mod repository's main page.
   - Find and click on "Create a new release", typically on the right-hand side.
   - Assign a name and a unique semantic version tag, such as `v1.0.0`, to your release.
   - Attach a single `.pak` file which contains your mod release.
   - When the package or release is added to the registry, it downloads the `.pak` file and runs `UnchainedScanner` to generate the asset manifest and file hash. You do not need to submit a separate manifest.

---

### Adding Your Mod to the Mod List:

**1. Pre-Release Checklist:** 
   - Ensure you've completed the "Creating a Release" steps.

**2. Requesting Inclusion:**
   - Create an issue in this repository using the "Add Package to Registry" template.
   - Fill out the mod name and repository URL. The issue body must include the following JSON:
     ```json
     {
       "action": "add-package",
       "repo_url": "https://github.com/Username/Mod-Name"
     }
     ```
   - The registry processes the mod's releases and creates a pull request for approval.

**3. Approval:**
   - Once approved, your mod's data will be integrated and updated in the main registry.

**4. Troubleshooting:**
   - If the request fails, check the error posted on the issue. After correcting the problem, reply "retry".

---

### Adding a New Release to the Mod List:

**1. Release Creation:** 
   - Ensure you have a fresh release following the earlier guidelines.

**2. Update Request on ModRegistry:**
   - Navigate to the main ModRegistry repository and create an issue using the "Add Release to Registry" template.
   - Use the following generic JSON structure in the issue:
     ```json
     {
       "action": "add-package-release",
       "repo_url": "[Your-Repo-URL]",
       "release_tag": "[Version-Tag]"
     }
     ```
     Replace placeholders with your mod details. Use the exact release tag, such as `v1.1.0`.
   - The registry processes the release and updates the package database. A successful request closes the issue automatically.

**3. Troubleshooting:**
   - If the request fails, check the error posted on the issue. After correcting the problem, reply "retry".
   - For any challenges or queries, consult with a community member. They'll likely be able to guide or assist you.
