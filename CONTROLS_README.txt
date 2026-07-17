================================================================================
 MERIDIAN SUITE - CONTROLS README
 Full controller + keyboard reference for every program in the suite
================================================================================

Every app is designed gamepad-first (Xbox-style layout, via GameInput with
XInput fallback), with keyboard and mouse always available as a backup.

Button names below use the Xbox convention:
  A / B / X / Y        face buttons
  LB / RB              left / right shoulder (bumper) buttons
  LT / RT              left / right triggers
  L3 / R3              clicking the left / right analog stick in
  Start / Select       the small menu buttons (Select is also called Back/View)

--------------------------------------------------------------------------------
 1. MERIDIAN LAUNCHER
--------------------------------------------------------------------------------
Controller:
  A ..................... Confirm / select the highlighted item
  B ..................... Back / close overlays
  D-pad or Left stick ... Navigate: up/down through lists, left/right across
                          sections and panels
  Y (tap) ............... Jump to the subfolder / filter side panel
  Start (over a photo) .. Edit / Set as Background popup (Photos section)
  X (tap) ............... Jump to / away from the open-programs bar (a
                          controller taskbar replacement, in every theme). On the bar: navigate
                          along it, A refocuses the highlighted program,
                          B returns to the sections bar. Blocked entirely
                          while Explorer/Browser/a webapp plugin is loaded.
  X (hold 3 seconds) .... Close the highlighted task on the open-programs
                          bar (asks for confirmation unless the "Close
                          tasks without prompt" setting is on)
  LB .................... Previous music track
  RB .................... Next music track
  LB + RB (together) .... Play a random track
  Start + Select ........ Bring Meridian Launcher to the foreground
  L3 + R3 (together) .... Quit the app instantly

Kiosk mode exits (work any time, using the physical buttons regardless of
remapping):
  Y held 45 seconds ..... Disable kiosk mode
  D-pad code ............ Up, Up, Down, Down, Left, Right, Left, Right, B, A

Keyboard:
  Enter ................. Confirm
  Space ................. Back
  Arrow keys ............ Navigate
  \ (backslash) ......... Jump to the subfolder / filter side panel
  ContextMenu key ....... Same as Start on a controller (Edit / Set as
                          Background popup over a photo)
  Shift ................. Jump to / away from the open-programs bar
  Delete ................ Close the highlighted task on the open-programs bar
  Kiosk code ............ Up, Up, Down, Down, Left, Right, Left, Right, B, A
                          (arrow keys plus the literal B and A keys)

Sections (Settings toggles, off by default unless noted):
  Desktop .............. On by default. Shows what's on your actual
                          Windows Desktop, folders included now - clicking
                          a folder routes to Explorer (if on) or standalone
                          Meridian Explorer / Windows Explorer (if off).
  Explorer ............. Right after Desktop. Boxes Meridian FileBrowse
                          into the section instead of a fixed list.
  Browser .............. Right after Explorer. Boxes Meridian NetBrowse,
                          pinned to whatever URL was internally launched.
  Chat ................. Telegram / Discord / Messenger / Snapchat /
                          Phone Link show up here as "webapp" plugins (or
                          as their own sections instead - see
                          CUSTOMIZATION.md for the "option" vs "webapp"
                          plugin type).
  Plugins .............. Settings > Plugins lists everything auto-scanned
                          from the Plugins/ folder, with a toggle per
                          plugin and a Rescan button. See CUSTOMIZATION.md.

Controller input backend (Settings > Controls): a cycle button steps
through XInput (default) / GameInput / DirectInput / SDL3 / Auto. XInput
is the default because it's the plain, stable, fully-public API and
correctly reports every button/trigger/stick.

Remapping: confirm / back / up / down / left / right are remappable in
controller_controls.json and keyboard_controls.json in the app data folder
(%LOCALAPPDATA%\Meridian Launcher\). Combos always use the physical buttons
listed above.

--------------------------------------------------------------------------------
 2. MERIDIAN GAME LIBRARY
--------------------------------------------------------------------------------
Controller:
  A ..................... Confirm / launch the selected game
  B ..................... Back / close menus and overlays
  D-pad or Left stick ... Navigate: up/down through the games list or gallery,
                          left/right across sections
  Y (tap) ............... Jump to the "Show" filter side panel
                          (All Games / Installed / Not Installed)
  Start ................. Open the Start menu (see below)
  Start + Select ........ Bring Meridian Game Library to the foreground
  L3 + R3 (together) .... Quit the app instantly

Start menu (Start button, or Tab on keyboard):
  When the selection is a game in a games list/gallery:
    Hide "<game>" ....... Hide the title from every game section (asks for
                          confirmation first; only shown while the game is
                          not already hidden)
    Unhide "<game>" ..... Bring a hidden title back (only shown when the
                          selected game is hidden - i.e. while hidden games
                          are being displayed)
    Rename "<game>" ..... Give the title a custom display name (display-only;
                          Playnite's own data is never touched; save an empty
                          name to restore the original)
  Always available:
    Unhide hidden games . Show all hidden titles, dimmed and badged "hidden"
    Hide hidden games ... (replaces the option above only while hidden games
                          are being shown) hide them again
    Close program ....... Quit Meridian Game Library

  Inside the Start menu: up/down to move, A to select, B or Start to close.

Keyboard:
  Enter ................. Confirm
  Space ................. Back
  Arrow keys ............ Navigate
  \ (backslash) ......... Jump to the "Show" filter side panel
  Tab ................... Open / close the Start menu
  Escape ................ Quit the app

Remapping: same as Meridian Launcher - controller_controls.json and
keyboard_controls.json in the app data folder.

--------------------------------------------------------------------------------
 3. CYBERDECKBROWSER
--------------------------------------------------------------------------------
Controller:
  Left stick ............ Move the cursor
  LT / RT (hold) ........ Cursor speed boost while held (multiplier is the
                          "Trigger Boost" value in Settings)
  L3 (click stick) ...... Reset page zoom
  Right stick up/down ... Scroll the page
  Right stick l/r ....... Zoom out / in
  A ..................... Left click; also selects virtual-keyboard keys and
                          menu items when one of those has focus
  B ..................... Right click (context menu); closes popups and the
                          virtual keyboard when one is open
  D-pad ................. Navigate the virtual keyboard / popup menus when
                          open; otherwise up/down scroll the page and
                          left/right send arrow-key presses to it
  LB .................... Previous browser tab
  RB .................... Next browser tab
  Y ..................... Browser menu (History, Downloads, Bookmarks,
                          Translate, Settings, Find In Page)
  X ..................... Tools menu
  Start ................. Open the search window
  Select ................ Launch the Windows on-screen keyboard (osk.bat)

The built-in virtual keyboard appears automatically whenever a text field
gains focus; D-pad moves across the keys, A types, B dismisses.

Keyboard & mouse: a full physical keyboard and mouse work normally at all
times - the controller layer never blocks them.

--------------------------------------------------------------------------------
 4. ONSCREENMENU
--------------------------------------------------------------------------------
Controller:
  Y ..................... Toggle the Shortcuts menu
  X ..................... Toggle the Key Combos menu
  Select ................ Open the Recent Apps switcher
  Start ................. Launch the Windows on-screen keyboard (osk.bat)
  Start + Select ........ Hibernate / resume the overlay
  D-pad ................. Navigate whichever menu is open
  A ..................... Select the highlighted menu entry
  B ..................... Close the open menu

Keyboard:
  Ctrl+H ................ Hibernate / resume the overlay

--------------------------------------------------------------------------------
 5. MERIDIAN EXPLORER
--------------------------------------------------------------------------------
Controller:
  A ..................... Open / enter the selected file or folder (in
                          multi-select mode: toggle the current item)
  B ..................... Go up a folder (in multi-select mode: exit
                          multi-select; in popups: cancel)
  D-pad or Left stick ... Up/down moves within the pane; left/right switches
                          between the two panes
  LT .................... Fast scroll up
  RT .................... Fast scroll down
  LB .................... Switch to the left pane
  RB .................... Switch to the right pane
  Y ..................... Options menu for the selected item (Open, Edit,
                          Copy, Cut, Paste, Rename, Change File Extension,
                          Move 2 Other Side, Copy 2 Other Side, Delete)
  Select (hold) ......... Enter multi-select mode
  R3 (click stick) ...... "Select all" prompt
  Start ................. Open the options popup (same as Y) - "Exit
                          Program" is a selectable item inside it, not an
                          instant action on Start anymore

  In popups/menus: D-pad or stick up/down to move, A to confirm, B to cancel.
  Delete and select-all prompts: A = yes, B = no.

Keyboard:
  Arrow up/down ......... Move within the pane
  Arrow left/right, Tab . Switch panes
  Enter ................. Open / confirm (in prompts: yes; Y also = yes)
  Escape ................ Close menu / cancel (at top level: quit - keyboard
                          Escape still quits directly; only the controller's
                          Start button was changed to open the menu instead)
  Backspace ............. Go up a folder / cancel prompts (N also = no)
  Page Up / Page Down ... Fast scroll
  M ..................... Options menu
  S ..................... Multi-select mode
  R ..................... Rename
  Mouse ................. Left click select/open, right click back/cancel

Meridian Explorer options menu (Y) now also offers:
  View...   Text / List / Icon / Gallery view modes, plus a day/night
            theme (System follows Windows' own light/dark setting).
  Sort...   Sort by Name / Size / Type / Date, Ascending or Descending.
  Search    Type a name fragment; jumps to the first match in the pane.
  Select All  Selects everything in the pane (B then selects none).
  Undo Move / Redo Move  Reverses or re-applies the last move operation.
  Properties  Windows-like info for the highlighted item.
  Set as Background  (images only) Stretch or Center; sets the Meridian
            Launcher background.
  Switch Pane Modes  Cycles Dual-pane -> Single-pane -> Quick Access
            (a Windows-style shortcut rail plus a wide main pane).

In Icon/Gallery view, left/right moves within a grid row and only switches
pane at the row edge; up/down steps a whole row.

Built-in Text Editor / Hex Editor (from the Y options menu: Edit / Hex
Edit). The screen splits into two dedicated boxes: the document on top
(scrolls internally, never covered) and a prominent virtual keyboard
below with a wide VOICE INPUT button on its bottom row:
  D-pad / Left stick .... Move the virtual-keyboard cursor
  A ..................... Press the highlighted key
  B ..................... Backspace (text) / Delete byte (hex)
  Y ..................... Shift (text editor, one-shot)
  LB / RB ............... Move the document cursor left / right
  LT / RT ............... Move the document cursor up / down
  Start ................. Save
  Select ................ Voice input (triggers Windows voice typing, Win+H)
  Physical keyboard ..... Types directly; arrows move, Ctrl+S saves,
                          Esc exits (twice to discard unsaved changes)

--------------------------------------------------------------------------------
 6. MERIDIAN FILEBROWSE
--------------------------------------------------------------------------------
A separate-source-files fork of Meridian Explorer, boxed into Meridian
Launcher's Explorer section (never full-screen - sized/positioned to that
section's list-frame box). Same controls as Meridian Explorer above, with
one difference: since it's always launched boxed by Meridian Launcher,
"Start" opening the options popup and "Exit Program" inside that popup are
the ONLY way it closes - closing it hands focus and controls back to
Meridian Launcher automatically (watched for on Meridian Launcher's side,
not something you need to do anything extra for).

"Make Meridian FileBrowse the default shell browser" (a Settings > Macros
option, once its shell-handler trampoline is built) routes Windows folder
opens through Meridian Launcher's Explorer section instead of Windows
Explorer or standalone Meridian Explorer.

--------------------------------------------------------------------------------
 7. MERIDIAN NETBROWSE
--------------------------------------------------------------------------------
A separate-source-files fork of CyberDeckBrowser, boxed into Meridian
Launcher's Browser section (and into Chat-section webapp plugins like
Telegram/Discord/Messenger/Snapchat/Phone Link) - never full-screen. Same
controller/keyboard/mouse layout as CyberDeckBrowser above (virtual mouse
via the left stick, A/B click, D-pad for the on-screen keyboard and
popups), with these differences from the standalone browser:
  - No first-boot cyberpunk-effects prompt, and no cyberpunk aesthetic
    options in Settings (HUD/CRT/scanlines/glitch) - always off.
  - The Y (Browser) and X (Tools) menus are stripped down to a single
    "Exit Program" entry - New Tab and the URL/search entry point have
    been removed entirely, and there's nothing else in either menu to
    navigate to since a boxed instance is meant to stay on the one site/
    section it was loaded for.
  - Exit Program (either menu, or the [x] button in the corner) closes it
    the same way as Meridian FileBrowse above: Meridian Launcher notices
    and restores its own controls/focus automatically.

"Make Meridian NetBrowse the default system web browser" (a Settings >
Macros option, once its shell-handler trampoline is built) routes links
through Meridian Launcher's Browser section instead of CyberDeckBrowser or
the system default browser.

================================================================================
 Vibecoded by Samuel "Zenith" Schimmel (Madisico) 2026
 This is open source software.
 Donations Appreciated, but Money Not Required.
================================================================================
