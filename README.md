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
       "mod_type": "[Type]",
       "authors": [ "[Author-Name]" ],
       "dependencies": [
         {
           "repo_url": "[Dependency-Repo-URL]",
           "version": "[Version-Number]"
         }
       ],
       "tags": [ "[Tag]" ]
     }
     ```
   - Replace placeholders like `[Your-Repo-URL]`, `[Mod-Name]`, etc., with your actual data.
   - The mod_type can have the following values: "shared", "client", or "server".
   - The available tags for your mod are: "Weapon","Map","Assets","Framework","Mod","Gamemode","Misc","Explicit". These tags help categorize and easily identify the purpose and nature of your mod.


**2. Creating a Repository Release:**
   - Head over to your mod repository's main page.
   - Find and click on "Create a new release", typically on the right-hand side.
   - Assign a name and a unique tag to your release.
   - Attach the a single `.pak` file which contains your mod release.

---

### Adding Your Mod to the Mod List:

**1. Pre-Release Checklist:** 
   - Ensure you've completed the "Creating a Release" steps.

**2. Fork the ModRegistry Repository:**
   - Visit the ModRegistry repository and create a fork.

**3. Register your Organization or Username:**
   - In the `registry` directory, add or update a file named after your organization or username.

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
   - Navigate to the main ModRegistry repository and initiate a new issue.
   - Use the following generic JSON structure in the issue:
     ```json
     {
       "repo_url": "[Your-Repo-URL]",
       "release_tag": "[Version-Tag]"
     }
     ```
     Replace placeholders with your mod details.

**3. Troubleshooting:**
   - For any challenges or queries, consult with a community member. They'll likely be able to guide or assist you.
