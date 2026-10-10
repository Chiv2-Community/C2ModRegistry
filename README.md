# C2ModRegistry
A registry for available chivalry 2 mods.  People who create mods can register them here, so that they show up in the mod browser.

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

**Using an Issue:**
   - Create an issue in this repository using the "Add Package to Registry" template.
   - Fill out the mod name and repository URL. The issue body must include the following JSON:
     ```json
     {
       "action": "add-package",
       "repo_url": "https://github.com/Username/Mod-Name"
     }
     ```
   - The registry processes the mod's releases and creates a pull request for approval.

**Using a Pull Request:**

**2. Fork the ModRegistry Repository:**
   - Visit the ModRegistry repository and create a fork.

**3. Register your Organization or Username:**
   - In the `registry` directory, add or update a `.txt` file named after your organization or username, such as `Username.txt`.
   - Add your mod's GitHub repository URL on its own line, such as `https://github.com/Username/Mod-Name`.

**4. Commit and Update:**
   - Save your changes locally and then push them to your forked ModRegistry repository.

**5. Requesting Inclusion:**
   - From your fork, submit a pull request to merge with the main ModRegistry repository.
   - Inform the review team of your mod inclusion request.

**6. Approval:**
   - Once approved, your mod's data will be integrated and updated in the main registry.

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
