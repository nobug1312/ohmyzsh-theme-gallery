import json
import re
import unittest

from generate_previews import ROOT, THEMES_DIR, ansi_to_html, extract


class PreviewTests(unittest.TestCase):
    def test_ansi_colours_are_balanced_and_reset(self):
        self.assertEqual(
            ansi_to_html("\x1b[31mred\x1b[0m<&"),
            '<span style="color:#cd0000">red</span>&lt;&amp;',
        )

    def test_extended_colours_and_terminal_controls(self):
        self.assertEqual(
            ansi_to_html("\x1b]0;title\x07\x1b[38;5;196mred\x1b[48;2;1;2;3m!"),
            '<span style="color:#ff0000">red</span>'
            '<span style="color:#ff0000;background-color:rgb(1,2,3)">!</span>',
        )

    def test_missing_marker_is_not_silently_accepted(self):
        with self.assertRaises(ValueError):
            extract("__START__broken", "__START__", "__END__")

    def test_bundled_theme_coverage_and_git_branch(self):
        themes = json.loads((ROOT / "themes.json").read_text())
        self.assertEqual({theme["name"] for theme in themes}, {path.stem for path in THEMES_DIR.glob("*.zsh-theme")})
        for theme in themes:
            for preview in theme["previews"].values():
                self.assertTrue(re.sub(r"<[^>]*>", "", preview["prompt"]).strip(), theme["name"])
                self.assertEqual(preview["prompt"].count("<span "), preview["prompt"].count("</span>"))
        robbyrussell = next(theme for theme in themes if theme["name"] == "robbyrussell")
        self.assertIn("main", robbyrussell["previews"]["git"]["prompt"])
        self.assertNotIn("main", robbyrussell["previews"]["home"]["prompt"])


if __name__ == "__main__":
    unittest.main()
