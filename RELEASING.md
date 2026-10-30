# Publishing updates

Users update from signed assets in GitHub Releases. Ordinary source pushes do not offer unfinished code as an update. The updater checks at startup by default, asks Yes/No before downloading, and also supports a manual Help menu check.

## Signing key

The private Ed25519 key is local at `tools/claves/firma_ed25519.key`. Git ignores this folder and all `.key`/`.pem` files. It is never uploaded, included in a build, or stored in GitHub Actions. Back it up outside this computer. Losing it prevents existing clients from trusting future releases.

The public key is embedded in `app/services/actualizador.py`. For rotation, first publish a version signed with the old key that embeds both public keys, then switch signers. Do not regenerate or overwrite the original key for routine releases.

## Publish a version

1. Increase `APP_VERSION`, the matching `pyproject.toml` version and the output folder in `setup_cx.py`.
2. Add an entry for that version to `data/docs/novedades.md`; update the manual and keyboard guide for visible changes.
3. Commit and push `main`.
4. Run `python tools/publicar_version.py --publicar`. It runs tests, builds into a new folder, rejects personal data/keys, creates the ZIP, signs `version.json`, creates a draft GitHub Release, uploads both assets, and publishes it only after both uploads succeed. It uses Git Credential Manager or `GH_TOKEN` for GitHub access; it never uploads the signing key.
5. Check the published assets and test an upgrade in a separate portable installation, preserving sample settings and sessions. Verify pause, cancellation and a failed-start rollback before distributing major changes.

The command refuses to delete an existing build. If a clean build already exists and has been verified, use `--solo-paquete --publicar`. `--solo-paquete` alone creates local signed assets in `dist/<version>`. If an upload fails, the draft remains unpublished; inspect/remove that draft before retrying the same tag.

The update feed is `https://github.com/AnimalMetal/vix-windows-client/releases/latest/download/version.json`. Its signed ZIP URL points to a specific version tag so a later publication cannot swap the download mid-update. Publish stable, increasing version numbers. Never overwrite an already published version; publish a greater version with the fix.

## Installation safety

The Windows helper waits for the old process to exit normally. It backs up the program before replacement and skips user data. Only declared resources such as docs and sounds are refreshed. The new app must confirm its version after the main window/event loop starts; missing confirmation restores the old program. Source checkouts can check availability but cannot install binary updates.

Old builds without the updater need one manual installation of version 1.4.0 or newer. Keep the entire portable folder together, not just the executable.
