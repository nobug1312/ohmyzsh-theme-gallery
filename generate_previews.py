#!/usr/bin/env python3
"""Generate static previews from the bundled Oh My Zsh themes."""

from __future__ import annotations

import html
import json
import os
import pty
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parent
OH_MY_ZSH = ROOT / "vendor" / "ohmyzsh"
THEMES_DIR = OH_MY_ZSH / "themes"
OUTPUT = ROOT / "themes.json"
SGR = re.compile(r"\x1b\[([0-9;]*)m")
OTHER_ESCAPE = re.compile(r"\x1b(?:\[[0-?]*[ -/]*[@-~]|\][^\x07]*(?:\x07|\x1b\\))")


def xterm_color(index: int) -> str:
    if index < 16:
        basic = [
            "#000000", "#800000", "#008000", "#808000",
            "#000080", "#800080", "#008080", "#c0c0c0",
            "#808080", "#ff0000", "#00ff00", "#ffff00",
            "#0000ff", "#ff00ff", "#00ffff", "#ffffff",
        ]
        return basic[max(0, min(index, 15))]
    if index < 232:
        value = index - 16
        levels = [0, 95, 135, 175, 215, 255]
        red, green, blue = value // 36, value // 6 % 6, value % 6
        return f"#{levels[red]:02x}{levels[green]:02x}{levels[blue]:02x}"
    gray = 8 + (index - 232) * 10
    return f"#{gray:02x}{gray:02x}{gray:02x}"


def ansi_to_html(text: str) -> str:
    colors = [
        "#000000", "#cd0000", "#00cd00", "#cdcd00",
        "#0000ee", "#cd00cd", "#00cdcd", "#e5e5e5",
        "#7f7f7f", "#ff0000", "#00ff00", "#ffff00",
        "#5c5cff", "#ff00ff", "#00ffff", "#ffffff",
    ]
    state: dict[str, str] = {}
    output: list[str] = []
    position = 0
    span_open = False

    def open_span() -> str:
        declarations = ";".join(f"{key}:{value}" for key, value in state.items())
        return f'<span style="{declarations}">' if declarations else ""

    for match in SGR.finditer(text):
        output.append(html.escape(text[position:match.start()]))
        if span_open:
            output.append("</span>")
        codes = [int(code or "0") for code in match.group(1).split(";")]
        index = 0
        while index < len(codes):
            code = codes[index]
            if code == 0:
                state.clear()
            elif code == 1:
                state["font-weight"] = "700"
            elif code == 2:
                state["opacity"] = "0.7"
            elif code == 3:
                state["font-style"] = "italic"
            elif code == 4:
                state["text-decoration"] = "underline"
            elif code == 22:
                state.pop("font-weight", None)
                state.pop("opacity", None)
            elif code == 23:
                state.pop("font-style", None)
            elif code == 24:
                state.pop("text-decoration", None)
            elif 30 <= code <= 37 or 90 <= code <= 97:
                state["color"] = colors[code - 30 if code < 90 else code - 90 + 8]
            elif code == 39:
                state.pop("color", None)
            elif 40 <= code <= 47 or 100 <= code <= 107:
                state["background-color"] = colors[code - 40 if code < 100 else code - 100 + 8]
            elif code == 49:
                state.pop("background-color", None)
            elif code in (38, 48) and index + 1 < len(codes):
                property_name = "color" if code == 38 else "background-color"
                if codes[index + 1] == 5 and index + 2 < len(codes):
                    state[property_name] = xterm_color(codes[index + 2])
                    index += 2
                elif codes[index + 1] == 2 and index + 4 < len(codes):
                    red, green, blue = codes[index + 2:index + 5]
                    state[property_name] = f"rgb({red},{green},{blue})"
                    index += 4
            index += 1
        if state:
            output.append(open_span())
            span_open = True
        else:
            span_open = False
        position = match.end()

    output.append(html.escape(SGR.sub("", text[position:])))
    if span_open:
        output.append("</span>")
    rendered = "".join(output)
    rendered = OTHER_ESCAPE.sub("", rendered)
    return "".join(char for char in rendered if char in "\n\t" or ord(char) >= 32)


PROMPT_SCRIPT = r"""
ZSH="$OH_MY_ZSH"
ZSH_THEME="$THEME"
ZSH_CACHE_DIR="$CACHE"
ZSH_CUSTOM="$HOME/.oh-my-zsh-custom"
ZSH_COMPDUMP="$CACHE/.zcompdump"
zstyle ':omz:update' mode disabled
zstyle ':omz:alpha:lib:git' async-prompt false
plugins=()
if [[ "$THEME" == "emotty" ]]; then
  plugins=(emoji emotty)
fi
source "$ZSH/oh-my-zsh.sh" || exit 2
run_prompt_hooks() {
  local hook
  if (( $+functions[precmd] )); then
    precmd
  fi
  for hook in $precmd_functions; do
    "$hook"
  done
}
cd "$HOME" || exit 3
run_prompt_hooks
print -r -n -- "__HOME_PROMPT__"
print -P -n -- "$PROMPT"
print -r -n -- "__HOME_RPROMPT__"
print -P -n -- "$RPROMPT"
cd "$HOME/Projects/demo" || exit 4
run_prompt_hooks
print -r -n -- "__GIT_PROMPT__"
print -P -n -- "$PROMPT"
print -r -n -- "__GIT_RPROMPT__"
print -P -n -- "$RPROMPT"
print -r -n -- "__END__"
"""


def extract(output: str, start: str, end: str) -> str:
    section = output.partition(start)[2]
    if not section or end not in section:
        raise ValueError(f"Missing preview marker: {start} or {end}")
    return ansi_to_html(section.partition(end)[0])


def render_theme(theme: str, home: Path, environment: dict[str, str]) -> dict:
    # TTY-aware themes such as emotty require a real terminal on stdin.
    master, slave = pty.openpty()
    try:
        result = subprocess.run(
            ["zsh", "-f", "-c", PROMPT_SCRIPT],
            stdin=slave,
            cwd=home,
            env=environment | {"THEME": theme},
            capture_output=True,
            text=True,
            timeout=10,
            check=True,
        )
    finally:
        os.close(slave)
        os.close(master)
    output = result.stdout
    previews = {}
    for mode, next_marker in (("home", "__GIT_PROMPT__"), ("git", "__END__")):
        prefix = mode.upper()
        prompt = extract(output, f"__{prefix}_PROMPT__", f"__{prefix}_RPROMPT__")
        if not re.sub(r"<[^>]*>", "", prompt).strip():
            raise ValueError(f"{mode} preview is empty")
        previews[mode] = {
            "prompt": prompt,
            "right": extract(output, f"__{prefix}_RPROMPT__", next_marker),
        }
    return {"name": theme, "previews": previews}


def main() -> None:
    if not THEMES_DIR.is_dir():
        raise SystemExit(f"Bundled themes directory not found: {THEMES_DIR}")
    for command in ("zsh", "git"):
        if not shutil.which(command):
            raise SystemExit(f"Required command not found: {command}")

    with tempfile.TemporaryDirectory(prefix="omz-gallery-") as temporary:
        root = Path(temporary)
        home = root / "home"
        repo = home / "Projects" / "demo"
        repo.mkdir(parents=True)
        (repo / "README.md").write_text("Theme preview fixture\n", encoding="utf-8")
        subprocess.run(["git", "init", "-q", "-b", "main", str(repo)], check=True)
        subprocess.run(["git", "-C", str(repo), "config", "user.name", "Theme Preview"], check=True)
        subprocess.run(["git", "-C", str(repo), "config", "user.email", "preview@example.invalid"], check=True)
        subprocess.run(["git", "-C", str(repo), "add", "README.md"], check=True)
        subprocess.run(["git", "-C", str(repo), "commit", "-q", "-m", "preview fixture"], check=True)
        (repo / "README.md").write_text("Theme preview fixture (modified)\n", encoding="utf-8")
        cache = root / "cache"
        cache.mkdir()

        environment = {
            "PATH": os.environ.get("PATH", os.defpath),
            "HOME": str(home),
            "OH_MY_ZSH": str(OH_MY_ZSH),
            "CACHE": str(cache),
            "TERM": "xterm-256color",
            "LANG": "C.UTF-8",
            "COLUMNS": "100",
            "LINES": "30",
            "USER": "preview",
            "USERNAME": "preview",
            "HOST": "arch",
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_CONFIG_GLOBAL": os.devnull,
        }
        themes = []
        failures = []
        for theme_file in sorted(THEMES_DIR.glob("*.zsh-theme"), key=lambda path: path.stem.casefold()):
            theme = theme_file.stem
            try:
                themes.append(render_theme(theme, home, environment))
            except (subprocess.SubprocessError, OSError, ValueError) as error:
                failures.append(theme)
                detail = getattr(error, "stderr", None) or str(error)
                print(f"error: {theme}: {detail.strip()}", file=sys.stderr)

    if failures:
        raise SystemExit(f"Failed to render {len(failures)} themes; existing previews preserved.")
    OUTPUT.write_text(json.dumps(themes, ensure_ascii=False), encoding="utf-8")
    print(f"Wrote {len(themes)} theme previews to {OUTPUT}")


if __name__ == "__main__":
    main()
