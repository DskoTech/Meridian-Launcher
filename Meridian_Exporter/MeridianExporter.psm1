# Meridian Library Exporter
#
# A Playnite PowerShell script extension. Its only job: write out a JSON
# snapshot of your Playnite library (title, source store, install state,
# cover art path, and the resolved Play action) to a fixed location
# Meridian's Python backend reads directly. No auth, no API calls, no
# reverse-engineered store protocols — Playnite already solved that
# problem for Steam/GOG/Epic/Amazon; this just hands Meridian what
# Playnite already knows.
#
# Including the resolved Play action (via Playnite's own documented
# ExpandGameVariables API) is what lets Meridian launch an installed game
# directly — subprocess for a File-type action, or handing off to the
# resolved URL for a URL-type action (which, for library-imported games,
# is often itself something like steam://rungameid/X or
# com.epicgames.launcher://... that Playnite already resolved for us) —
# without needing Playnite itself running at all. Only Emulator-type
# actions fall back to asking Playnite to handle the launch, since
# resolving an emulator profile correctly needs more of Playnite's own
# logic than is worth reimplementing here.
#
# Source-name detection is defensive on purpose: Playnite's Game.Source
# property has changed shape across versions (sometimes a direct object
# with .Name, sometimes only a SourceId needing a lookup in
# Database.Sources). If games show up under "Unknown" in Meridian instead
# of grouped correctly, open Main Menu -> Extensions -> Interactive SDK
# PowerShell in Playnite and run:
#   $PlayniteApi.Database.Games[0] | Format-List *
# to see the real shape on your installed version, then adjust
# Get-MeridianSourceName below to match.

function Get-MeridianSourceName {
    param($game)

    try {
        if ($game.Source -and $game.Source.Name) {
            return $game.Source.Name
        }
    } catch { }

    try {
        if ($game.SourceId -and $PlayniteApi.Database.Sources) {
            $src = $PlayniteApi.Database.Sources[$game.SourceId]
            if ($src -and $src.Name) {
                return $src.Name
            }
        }
    } catch { }

    return "Unknown"
}

function Get-MeridianPlayAction {
    param($game)

    $result = [PSCustomObject]@{
        Type       = $null
        Path       = $null
        Arguments  = $null
        WorkingDir = $null
    }

    try {
        $playAction = $game.GameActions | Where-Object { $_.IsPlayAction } | Select-Object -First 1
        if (-not $playAction) { return $result }

        $expanded = $PlayniteApi.ExpandGameVariables($game, $playAction)
        $result.Type = $expanded.Type.ToString()
        $result.Path = $expanded.Path
        $result.Arguments = $expanded.Arguments
        $result.WorkingDir = $expanded.WorkingDir
    } catch { }

    return $result
}

function Export-MeridianLibrary {
    $exportDir = Join-Path $env:APPDATA "Meridian"
    if (-not (Test-Path -LiteralPath $exportDir)) {
        New-Item -ItemType Directory -Path $exportDir -Force | Out-Null
    }
    $exportPath = Join-Path $exportDir "playnite_library.json"

    $exported = @()
    foreach ($game in $PlayniteApi.Database.Games) {
        $coverPath = $null
        if ($game.CoverImage) {
            try {
                $coverPath = $PlayniteApi.Database.GetFullFilePath($game.CoverImage)
            } catch { }
        }

        $playAction = Get-MeridianPlayAction $game

        $exported += [PSCustomObject]@{
            Id                = $game.Id.ToString()
            Name              = $game.Name
            Source            = Get-MeridianSourceName $game
            IsInstalled       = [bool]$game.IsInstalled
            InstallDirectory  = $game.InstallDirectory
            CoverImagePath    = $coverPath
            Playtime          = $game.Playtime
            PlayActionType    = $playAction.Type
            PlayActionPath    = $playAction.Path
            PlayActionArgs    = $playAction.Arguments
            PlayActionWorkDir = $playAction.WorkingDir
        }
    }

    $exported | ConvertTo-Json -Depth 4 | Out-File -LiteralPath $exportPath -Encoding utf8
}

# Runs automatically on every Playnite startup and after every library sync
# (manual or automatic), so Meridian's data stays reasonably fresh without
# you doing anything. Install-state changes specifically may lag until the
# next library update runs though — use the manual menu item below (or
# just wait for the next auto-sync) if you need it fresher than that.
function OnApplicationStarted {
    Export-MeridianLibrary
}

function OnLibraryUpdated {
    Export-MeridianLibrary
}

# Manual "Export library for Meridian" entry under Playnite's Extensions
# menu, for an on-demand refresh — this signature matches Playnite's own
# documented ScriptMainMenuItem example exactly.
function ExportMeridianLibraryNow {
    param($scriptMainMenuItemActionArgs)
    Export-MeridianLibrary
    $PlayniteApi.Dialogs.ShowMessage("Meridian library export updated.")
}

function GetMainMenuItems {
    param($getMainMenuItemsArgs)
    $menuItem = New-Object Playnite.SDK.Plugins.ScriptMainMenuItem
    $menuItem.Description = "Export library for Meridian"
    $menuItem.FunctionName = "ExportMeridianLibraryNow"
    $menuItem.MenuSection = "@"
    return $menuItem
}

