Drop custom themes here.

A theme is either:
  - a folder with a theme.css inside (plus optional theme.json), or
  - a single .css file (e.g. MyTheme.css).

theme.json (optional) can set:
  { "name": "My Cool Theme", "base": "cyber_radial" }

"base" is which built-in theme yours starts from and overrides:
dawning_horizon, night_horizon, or cyber_radial.
Your CSS is layered on top of the base, so you only need to write
the rules you want to change. Target the body class
  body.layout-user-<your-theme-slug>
for rules that should only apply to your theme.
