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

    Export-MeridianFilterPresets $exportDir
}

# Also snapshot the user's saved filter presets, with membership resolved
# by Playnite itself. Meridian's "Playnite filter sections" toggle turns
# each of these into its own section, so the filter logic (genres, sources,
# install state, whatever the preset says) never has to be reimplemented
# on the Python side — Playnite evaluates it here and Meridian just reads
# name + matching game ids.
#
# GetFilteredGames(FilterPresetSettings) is the SDK call for this. Older
# builds may lack it; when that happens we fall back to matching the most
# common preset fields ourselves (name search, installed state, sources,
# genres) so presets aren't left empty. If a preset uses filter fields the
# fallback doesn't understand, it's still exported by name (possibly with
# fewer/zero games) rather than crashing the export.
function Export-MeridianFilterPresets {
    param($exportDir)

    $presetPath = Join-Path $exportDir "playnite_filter_presets.json"
    $presetsOut = @()

    try {
        $allGames = @($PlayniteApi.Database.Games)
        foreach ($preset in $PlayniteApi.Database.FilterPresets) {
            $gameIds = @()
            $settings = $preset.Settings
            $resolved = $false

            # Primary: let Playnite evaluate the preset.
            try {
                $matched = $PlayniteApi.Database.GetFilteredGames($settings)
                if ($null -ne $matched) {
                    foreach ($g in $matched) { $gameIds += $g.Id.ToString() }
                    $resolved = $true
                }
            } catch { }

            # Fallback: evaluate the common filter fields ourselves.
            if (-not $resolved -and $null -ne $settings) {
                foreach ($g in $allGames) {
                    if (Test-MeridianGameMatchesPreset $g $settings) {
                        $gameIds += $g.Id.ToString()
                    }
                }
            }

            $presetsOut += [PSCustomObject]@{
                Id      = $preset.Id.ToString()
                Name    = $preset.Name
                GameIds = $gameIds
            }
        }
    } catch {
        $PlayniteApi.Dialogs.ShowErrorMessage("Meridian: filter preset export failed: $($_.Exception.Message)", "Meridian Exporter")
    }

    # ConvertTo-Json turns a single-element array into a bare object;
    # Meridian's reader handles both shapes, so no wrapping gymnastics here.
    # Force an array wrapper so an empty result still writes "[]".
    ,$presetsOut | ConvertTo-Json -Depth 4 | Out-File -LiteralPath $presetPath -Encoding utf8
}

# Best-effort local evaluation of a FilterPresetSettings against one game,
# covering the fields people most commonly build presets from. Anything not
# handled here is simply ignored (treated as "no constraint").
function Test-MeridianGameMatchesPreset {
    param($game, $settings)

    try {
        # free-text name search
        if ($settings.Name -and $settings.Name.Trim().Length -gt 0) {
            if (-not $game.Name -or ($game.Name.ToLower().IndexOf($settings.Name.ToLower()) -lt 0)) {
                return $false
            }
        }
        # installed / uninstalled toggles
        if ($settings.IsInstalled -eq $true -and -not $game.IsInstalled) { return $false }
        if ($settings.IsUnInstalled -eq $true -and $game.IsInstalled) { return $false }
        if ($settings.Hidden -ne $true -and $game.Hidden) { return $false }
        if ($settings.Favorite -eq $true -and -not $game.Favorite) { return $false }

        # id-list filters: Source / Genre / Platform / Category. Each
        # FilterItemProperties exposes .Ids; a game matches if it carries at
        # least one of the requested ids.
        if (-not (Test-MeridianIdFilter $settings.Source  $game.SourceId))       { return $false }
        if (-not (Test-MeridianIdFilter $settings.Genre   $game.GenreIds))       { return $false }
        if (-not (Test-MeridianIdFilter $settings.Platform $game.PlatformIds))   { return $false }
        if (-not (Test-MeridianIdFilter $settings.Category $game.CategoryIds))   { return $false }
        return $true
    } catch {
        return $false
    }
}

function Test-MeridianIdFilter {
    param($filterItem, $gameIds)
    # No constraint set -> always passes.
    if ($null -eq $filterItem -or $null -eq $filterItem.Ids -or $filterItem.Ids.Count -eq 0) {
        return $true
    }
    if ($null -eq $gameIds) { return $false }
    # normalize a single-id (Guid) to a list
    $ids = @()
    if ($gameIds -is [System.Collections.IEnumerable] -and -not ($gameIds -is [string])) {
        $ids = @($gameIds)
    } else {
        $ids = @($gameIds)
    }
    foreach ($want in $filterItem.Ids) {
        foreach ($have in $ids) {
            if ($have -and $want -and ($have.ToString() -eq $want.ToString())) { return $true }
        }
    }
    return $false
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
    $presetCount = 0
    try { $presetCount = @($PlayniteApi.Database.FilterPresets).Count } catch { }
    $PlayniteApi.Dialogs.ShowMessage("Meridian library export updated. Filter presets exported: $presetCount")
}

function GetMainMenuItems {
    param($getMainMenuItemsArgs)
    $menuItem = New-Object Playnite.SDK.Plugins.ScriptMainMenuItem
    $menuItem.Description = "Export library for Meridian"
    $menuItem.FunctionName = "ExportMeridianLibraryNow"
    $menuItem.MenuSection = "@"
    return $menuItem
}

