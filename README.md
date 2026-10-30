# ViX Client 1.4.1

Accessible Windows client with a native catalogue, global search and native playback controls. The main window contains only Catalogue and Player. Its required web engine stays hidden, except when the user explicitly opens the necessary Mi cuenta workflow.

## Fixes in 1.4.1

Season and episode-group changes show the first new episodes without waiting for ViX's persistent load-more spinner. The client checks more frequently only while a selection is pending. Rapid choices compare episode rows at the actual site click, and returning to the original season supersedes the earlier request. Initial Vecinos checks went from about 15.6 seconds to 0.25 seconds; network and site response times still vary.

## Updates in 1.4.0

Startup checks are enabled by default, with a Yes/No prompt before any download. Turn them off in Options, or check manually through Help. Downloads are signed with Ed25519, verified by size and SHA-256, and installed in place with settings/session preservation and failed-start rollback. Source checkouts do not install binaries. Existing users need one manual installation of 1.4.0 to get the updater.

Updates come from stable GitHub Releases, not ordinary source pushes. See [RELEASING.md](RELEASING.md) for the one-command local build/sign/publish procedure. The private signing key stays on the publisher's computer and must be backed up separately.

## New in 1.3.0

En vivo now has a native channel guide with channel numbers, current and next programmes, local times, categories and favorites. Filter loaded channels by number, name or programme. F4 opens the available schedule; Ctrl+1 through Ctrl+7 reads columns. The live integration check loaded 80 channels in this session; availability depends on ViX and region.

Browsing does not start playback automatically. The live player displays delay from the broadcast and offers Ir al directo when seeking is available. Refreshing during playback preserves the stream. The F6 return bridge is reinstalled after navigation.

## Fixes in 1.2.2

Seasons and episode groups now have separate native selectors. Their options are discovered automatically and remain available after selection. Changing seasons waits for the corresponding episodes, replaces the old list and clears the old local filter. Rapid requests accept only the latest choice. Failed requests recover after an error/timeout instead of leaving updates stuck.

Episode descriptions now include the available episode number, synopsis and duration from their cards. Collections open as collections instead of entering an empty player. Favorites stop background catalogue loading and disable irrelevant season controls. Returning from account management reconnects the catalogue engine. Background catalogue loading no longer overwrites the player title, and secondary-frame failures are not reported as catalogue connection errors.

Updates import data from the latest older neighbouring version, rather than a fixed old version. Close the previous version first; active profiles are not copied.

## Use

Open a series and choose Temporada. Use Grupo de episodios only when ViX divides the list into ranges. Actualizar temporadas y grupos retries discovery if necessary. Ctrl+M continues loading episodes. Ctrl+F searches all ViX results; the separate local filter only filters loaded rows.

F6 returns to the catalogue and preserves selection; F8 opens the native player. Native controls handle pause/resume, stop, position, volume/mute, and exposed audio/subtitle tracks. Account/profile status is persistent, accessible and silent; F9 consults it on request. Homepage groups remain separate, with explanations and a Secciones column. Gentle interface sounds have independent volume/preview/off controls in Options.

The engine is still required internally for catalogue rendering, authentication and playback/DRM. Availability and subscriptions are controlled by ViX. The app does not guarantee an exhaustive catalogue index. Unsupported tracks remain disabled.

## Run and validate

Python 3.13 plus requirements.txt: `python main.py`.
Build: `python setup_cx.py build`; output: `build/VixClient-1.4.1/VixClient.exe`. Keep the whole output folder. Microsoft Edge WebView2 Runtime is required.

Tests: `python -m pytest`. Public live-season checks: `python tools/check_season_navigation.py` (La Rosa de Guadalupe, Mujeres Asesinas, Vecinos and Mi Corazón Es Tuyo episode ranges). A specific search result can be checked with `python tools/check_season_navigation.py search:Vecinos`. Playback/return check: `python tools/check_native_updates.py`. Startup: `python main.py --comprobar-arranque`; a live search check is available through --comprobar-webview with isolated APP_DATA_DIR.

App settings/favorites are in data/config, the embedded session in data/sessions, sound cache in data/cache and logs in data/logs. Do not distribute personal data. Session encryption can depend on the Windows user/computer. Signed-in profile detection, Premium playback and a real NVDA/JAWS/Narrator walkthrough remain manual checks.
