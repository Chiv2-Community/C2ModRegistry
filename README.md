# C2ModRegistry
A registry for available chivalry 2 mods.  People who create mods can register them here, so that they show up in the mod browser.

### Registering your mod

### Creating a Release:

**1. Setting up your `mod.json` file:**
   - Every mod requires a `mod.json` file, which should be located at the root of your mod repository.
   - Your `mod.json` must match the format described by the [mod.json schema](https://github.com/Chiv2-Community/zero-infra-mod-registry/blob/prepare-v1/schemas/mod.schema.json). A schema lists the allowed fields, which are required, and what values they accept.
   - To check your file, open the [online JSON Schema validator](https://json-schema.hyperjump.io/). Copy the linked schema's contents into **Schema** and your `mod.json` contents into **Instance**. Fix any reported errors before publishing.
   - Commit `mod.json` before creating the release tag. If you forget to create or update it for a particular release, upload the corrected file to that release's assets.


**2. Creating a Repository Release:**
   - Head over to your mod repository's main page.
   - Find and click on "Create a new release", typically on the right-hand side.
   - Assign a name and a unique semantic version tag, such as `v1.0.0`, to your release.
   - Attach a single `.pak` file which contains your mod release.
   - You do not need to submit a separate manifest.

---

### Adding a Release to the Mod List:

**1. Pre-Release Checklist:** 
   - Ensure you've completed the "Creating a Release" steps.

**2. Requesting Inclusion:**
   - Create an issue in this repository using the "Add Release to Registry" template for both your mod's first release and later versions.
   - Fill out the mod name, repository URL and exact release tag. The issue body must include the following JSON:
     ```json
     {
       "action": "add-package-release",
       "repo_url": "https://github.com/Username/Mod-Name",
       "release_tag": "v1.0.0"
     }
     ```
   - The registry processes only the requested release and creates a pull request for approval. Submit a separate request for each version.

**3. Approval:**
   - Every release requires approval, including updates. Your release is added to the mod list and the issue closes when its pull request is merged.

**4. Troubleshooting:**
   - If the request fails, check the error posted on the issue. After correcting the problem, reply "retry".

---

### Registering a DLL Plugin:

Most mods use `.pak` files and should follow the steps above. This section is for advanced users publishing native DLL plugins. DLLs run native code; approval and hash checks do not make them safe. Only enable plugins from publishers you trust.

**1. Creating a Release:**
   - Create a GitHub release with a semantic version tag, such as `v1.0.0`. Prereleases such as `v1.0.0-RC2` are supported.
   - Your `plugin.json` must match the format described by the [plugin.json schema](https://github.com/Chiv2-Community/zero-infra-mod-registry/blob/prepare-v1/schemas/plugin.schema.json). A schema lists the allowed fields, which are required, and what values they accept.
   - To check your file, open the [online JSON Schema validator](https://json-schema.hyperjump.io/). Copy the linked schema's contents into **Schema** and your `plugin.json` contents into **Instance**. Fix any reported errors before publishing.
   - Place `plugin.json` at the repository root before tagging the release. If you forget to create or update it for a particular release, upload the corrected file to that release's assets.
   - Attach your `.dll` file.

**2. Requesting Inclusion:**
   - Create an issue using the "Add DLL Release to Registry" template:
     ```json
     {
       "action": "add-dll-release",
       "repo_url": "https://github.com/Username/Plugin-Name",
       "release_tag": "v1.0.0"
     }
     ```
   - The registry downloads and verifies the DLL, then opens a pull request for approval. Every version requires approval, including updates.
   - To update a published DLL, create a new version rather than replacing an existing release's DLL.

**3. Troubleshooting:**
   - If the release has multiple DLLs, the bot will ask you to add `"dll_file": "Plugin-Name.dll"` to the issue JSON. Use the exact, case-sensitive asset filename, then reply "retry".
   - For other failures, check the error posted on the issue. After correcting the problem, reply "retry".
