# C2ModRegistry
A registry for available chivalry 2 mods.  People who create mods can register them here, so that they show up in the mod browser.

---

### Registering your mod

**1. Fork the Mod Registry:**
- Start by forking the mod registry. This creates a personal copy of the mod registry on your GitHub account.

**2. Adding Your Mod(s) To the Registry files**
- Navigate to the `registry` folder on your fork.
- Create a new file named `$UserOrg.txt`. 
  - If your repo is `https://github.com/Jeoffrey/GoodForNothing`, the file should be named `Jeoffrey.txt`
- For each mod that you want listed, put the mod repo url as a line within the file.
  - Following the example above, Your file should look like this:
    ```
    # registry/Jeoffrey.txt
    https://github.com/Jeoffrey/GoodForNothing 
    ```
  - Check the [registry dir](./registry/) for more examples.

**3. Submitting Your Changes:**
- Now that you've updated your copy of the registry, you need to get those changes merged in to the main registry
- Create a PR here: https://github.com/Chiv2-Community/C2ModRegistry/pulls
- Set `Chiv2-Community/main` as the base branch, and your branch containing changes as the compare branch.
- Include some description of your mod in the PR

**4. Awaiting Approval:**
- Members of the Chiv2-Community will review your PR.
- If everything looks good, they will approve it.

---

### How it works

**1. Merging the Pull Request:**
- Once approved, the PR is merged into the `main` branch of the mod registry.

**2. Triggering the GitHub Action:**
- The merge into the `main` branch automatically triggers a GitHub action.

**3. Merging Changes:**
- This GitHub action will merge the changes from the `main` branch into the `db` branch.

**4. Scanning the Registry Folder:**
- The action will then scan the `registry` folder to identify all the files present.

**5. Reading the Registry Files:**
- Each file in the registry is read by the action.
- Every line in these files represents a separate mod repository.

**6. Processing New Repositories:**
- For each new mod repository identified:
  - **Initialization:** The action will pull all releases that contain a `pak` file.
  - **Updating the Package List:** The mod is added to the list in `package_db/mod_list_index.txt`.
  - **Storing Mod Metadata:** Metadata for the mod (including release metadata) is saved in a JSON file located at `package_db/packages/$org/$repo.json`.