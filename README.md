# Oh My Zsh Theme Viewer

A lightweight, offline viewer for 143 bundled [Oh My Zsh](https://ohmyz.sh/) themes. Compare home and Git previews, search themes, save favourites, and copy theme settings. Built with vanilla HTML, CSS and JavaScript, with an Arch-inspired interface and bundled JetBrains Mono Nerd Font.

## Run

From the project directory:

```sh
python3 -m http.server 8765 --bind 127.0.0.1
```

Open **http://localhost:8765**. Viewing requires no Zsh or Oh My Zsh installation.

## Regenerate previews

Requires Python 3.9+, Zsh and Git on Linux or macOS:

```sh
python3 generate_previews.py
```

Previews are generated from `vendor/ohmyzsh/themes/` using a temporary home directory and a modified Git repository. Your shell configuration is never changed. Colours and optional plugin output may differ from your terminal; `random` shows a sampled theme.

## Attribution

Oh My Zsh themes and runtime: [MIT licence](vendor/ohmyzsh/LICENSE.txt), snapshot [`2100c630`](https://github.com/ohmyzsh/ohmyzsh/tree/2100c630ba4bd67bb48802c3e7da893a4fdaa1a0). JetBrains Mono Nerd Font: [SIL Open Font Licence](fonts/OFL.txt).
