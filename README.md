# C2ModRegistry
A registry for available chivalry 2 mods.  People who create mods can register them here, so that they show up in the mod browser.

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

---

### Registering a DLL Plugin:

Most mods use `.pak` files and should follow the steps above. This section is for advanced users publishing native DLL plugins. DLLs run native code; approval and hash checks do not make them safe. Only enable plugins from publishers you trust.

**1. Creating a Release:**
   - Create a GitHub release with a semantic version tag, such as `v1.0.0`. Prereleases such as `v1.0.0-RC2` are supported.
   - Attach your `.dll` file. DLL plugins do not need a `mod.json` or a pak asset manifest.

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
   - Approved entries go in `dll_db/index.json`, separate from pak mods, with their download URL, SHA-256, size, and version. Published versions cannot be replaced; create a new version instead.

**3. Troubleshooting:**
   - If the release has multiple DLLs, the bot will ask you to add `"dll_file": "Plugin-Name.dll"` to the issue JSON. Use the exact, case-sensitive asset filename, then reply "retry".
   - For other failures, check the error posted on the issue. After correcting the problem, reply "retry".
   - DLL download verification is required in issue processing and PR checks. Failed issue validation blocks commits and PR creation.
