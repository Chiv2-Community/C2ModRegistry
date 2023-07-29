# C2ModRegistry
A registry for available chivalry 2 mods.  People who create mods can register them here, so that they show up in the mod browser.

## Instructions
* Fork this repo
* Create a new file in the `registry` dir and name it `MyOrg.txt`
* Add 1 line to the file per repo that hosts mods
* Add a mod manifest to your repo root, and keep it up to date as you create releases
* Create releases through github releases, and attach your mod assets as Mod.zip

TODO: Improve these instructions

## Example

```
# registry/Chiv2-Community.txt
https://github.com/Chiv2-Community/C2ServerPlugin
https://github.com/Chiv2-Community/C2BrowserPlugin
https://github.com/Chiv2-Community/C2AssetLoaderPlugin
```

Follow those repo links to see what a mod manifest may look like