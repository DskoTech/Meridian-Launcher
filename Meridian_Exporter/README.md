# Meridian Library Exporter (Playnite extension)

A small PowerShell script extension for Playnite. It doesn't change
anything about how Playnite works — it just writes a JSON snapshot of
your library to `%AppData%\Meridian\playnite_library.json` whenever
Playnite starts or finishes a library sync, so Meridian's Python backend
can read it directly instead of trying to talk to Steam/GOG/Epic/Amazon
itself.

As of this version it also exports each game's resolved **Play action**
(via Playnite's own `ExpandGameVariables` API) — the real executable path
or launch URL Playnite would use to start the game. That's what lets
Meridian launch an already-installed game directly, without needing
Playnite running at all in the common case.

## Installing

1. Copy the whole `MeridianExporter` folder into:
   `%AppData%\Playnite\Extensions\`
   (so you end up with `...\Extensions\MeridianExporter\extension.yaml`)
2. Restart Playnite, or use **Tools > Reload Scripts** if it's already running.
3. Trigger a library sync (Playnite does this automatically on startup) —
   or just use the manual option below.

## Manual export

Open the Extensions menu in Playnite and choose **Export library for
Meridian** any time you want an on-demand refresh, rather than waiting
for the next automatic sync.

## If games show up under the wrong section in Meridian

Playnite's internal `Source` field has changed shape across versions, and
this script's detection is defensive but not guaranteed to match every
version. If everything lands under "Other" instead of Steam/GOG/Epic/
Amazon, open **Main Menu > Extensions > Interactive SDK PowerShell** in
Playnite and run:

```powershell
$PlayniteApi.Database.Games[0] | Format-List *
```

That'll show you the real property shape on your installed version —
adjust the `Get-MeridianSourceName` function in `MeridianExporter.psm1`
to match what you see, then reload scripts.

## If launching an installed game still opens Playnite's window

That means the Play action didn't resolve to something Meridian could run
directly (File or URL type) — likely an Emulator-type action, or one that
failed to expand. Meridian falls back to asking Playnite to handle it in
that case, same as before this version. Nothing broken, just a case this
version doesn't shortcut.

## Note on PowerShell script extensions generally

Playnite's own docs mention PowerShell script support is being removed in
their next major release (v11) in favor of compiled .NET plugins. This
extension will need porting to C# if/when that happens — not something to
worry about for the current stable line, just flagging it so it's not a
surprise later.
