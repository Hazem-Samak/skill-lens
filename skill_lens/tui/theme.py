"""The Skill Lens brand theme and its shared, markup-free styling helpers.

Everything in this module is presentation only.  No computation, no filesystem
access and no Rich import: the TUI must never pull in a second rendering
engine, and no untrusted string may ever be parsed as markup.

The palette is one coherent set of colours.  A colour is only ever used to
carry meaning -- a healthy skill is green, a malformed one is red, the
selected row is a tint of the accent -- so the same word never appears in two
different colours.
"""

from __future__ import annotations

from textual.content import Content
from textual.theme import Theme

from skill_lens.models.enums import HeadlineState

#: The name of the one theme every Skill Lens screen renders with.
SKILL_LENS_THEME = "skill-lens"

#: The lens teal: the accent of the whole interface.
PRIMARY = "#4ec9c4"

#: The secondary blue, used for informational accents.
SECONDARY = "#7aa2f7"

#: Semantic colours: healthy, caution, broken, ambiguous.
SUCCESS = "#57ab5a"
WARNING = "#d29922"
ERROR = "#e5534b"
ACCENT = "#b083f0"

#: The canvas and the two surfaces above it.
BACKGROUND = "#0d1117"
SURFACE = "#161b23"
PANEL = "#1c2430"
BOOST = "#232d3a"

#: The main text colour.
VALUE = "#c8d3e0"

#: Labels, captions and inactive keys.  Light enough to stay readable on the
#: canvas (about 5.4:1), never used for the only copy of a fact.
MUTED = "#8b98a8"

#: Hairline separators between panes and bars.
RULE = "#31415a"

#: The surface behind a keycap.
KEYCAP = "#2b3644"

#: The text colour of a keycap.
KEY_TEXT = "#e6edf3"

#: The selected row: a dark tint of the accent, so light text stays readable
#: on it (about 8:1).  The bright accent itself would drop to about 1.3:1.
CURSOR_BACKGROUND = "#1f3b3d"
CURSOR_FOREGROUND = "#d8f3f1"

THEME = Theme(
    name=SKILL_LENS_THEME,
    primary=PRIMARY,
    secondary=SECONDARY,
    warning=WARNING,
    error=ERROR,
    success=SUCCESS,
    accent=ACCENT,
    foreground=VALUE,
    background=BACKGROUND,
    surface=SURFACE,
    panel=PANEL,
    boost=BOOST,
    dark=True,
    variables={
        "muted": MUTED,
        "rule": RULE,
        "keycap": KEYCAP,
        "value": VALUE,
        "block-cursor-background": CURSOR_BACKGROUND,
        "block-cursor-foreground": CURSOR_FOREGROUND,
        "block-cursor-text-style": "bold",
        "scrollbar": "#2b3a4a",
        "scrollbar-hover": "#3a4d61",
        "scrollbar-active": PRIMARY,
        "scrollbar-background": "#11161d",
        "scrollbar-background-hover": "#11161d",
        "scrollbar-background-active": "#11161d",
        "scrollbar-corner-color": "#11161d",
    },
)

#: The TUI's own colours for the shared resolution states.
#:
#: ``presentation.STATE_STYLE`` keeps the *meaning* of each state; this table
#: maps that meaning onto the Skill Lens palette, so the surfaces this change
#: introduced stay on one coherent set of colours.
#:
#: The candidate headings of the detail screen keep the shared style itself:
#: their styling is part of the existing contract (``tests/test_tui_why.py``
#: pins the exact style), so they deliberately do not move with the palette.
STATE_COLOUR: dict[HeadlineState, str] = {
    HeadlineState.ACTIVE: SUCCESS,
    HeadlineState.COEXISTS: SECONDARY,
    HeadlineState.SHADOWED: WARNING,
    HeadlineState.DISABLED: MUTED,
    HeadlineState.UNSEARCHED: MUTED,
    HeadlineState.INVALID: ERROR,
    HeadlineState.AMBIGUOUS: ACCENT,
}

#: The state styles, keyed by the state name the TUI prints.
_STATE_COLOUR_BY_NAME: dict[str, str] = {
    state.value: colour for state, colour in STATE_COLOUR.items()
}


def field(label: str, value: str, style: str | None = None) -> Content:
    """One ``Label: value`` line with a dim label and a bright value.

    The characters are exactly ``f"{label}: {value}"`` -- only the styling
    differs, so every assertion about the visible text still holds.
    """
    return Content.assemble(
        Content.styled(f"{label}: ", "dim"),
        Content.styled(value, style or "bold"),
    )


def _style_for_name(name: str) -> str | None:
    """The Skill Lens style for a printed state name, or None if unknown."""
    colour = _STATE_COLOUR_BY_NAME.get(name.strip())
    return f"bold {colour}" if colour else None


def state_cell(text: str) -> Content:
    """Colour each state name in a comma separated state list.

    A row can hold several states at once (active for one agent, shadowed for
    another), so each name carries its own colour instead of the whole cell
    wearing the colour of one of them.
    """
    parts: list[Content] = []
    for index, name in enumerate(text.split(", ")):
        if index:
            parts.append(Content.styled(", ", "dim"))
        style = _style_for_name(name)
        parts.append(Content.styled(name, style if style else "dim"))
    return Content.assemble(*parts)


def styled_line(text: str) -> Content:
    """Style one ``Label: value`` line: dim label, bright value.

    The characters never change.  A line without a label separator is dim, and
    the two labels that carry meaning -- a note and the report headline -- get
    the colour their meaning deserves.
    """
    label, separator, value = text.partition(": ")
    if not separator:
        return Content.styled(text, "dim")
    stripped = label.strip()
    if stripped == "Note":
        return Content.assemble(
            Content.styled(f"{label}: ", "yellow"),
            Content.styled(value, "italic"),
        )
    if stripped == "Report-wide headline":
        style = _style_for_name(value)
        return Content.assemble(
            Content.styled(f"{label}: ", "dim"),
            Content.styled(value, style if style else "bold"),
        )
    return Content.assemble(
        Content.styled(f"{label}: ", "dim"),
        Content.styled(value, "bold"),
    )


def fact_block(text: str) -> Content:
    """Style a block of plain ``Label: value`` lines.

    Every character of the original text survives, including blank lines, so
    a report that is read as plain text still reads the same.
    """
    parts: list[Content | str] = []
    for index, line in enumerate(text.split("\n")):
        if index:
            parts.append("\n")
        parts.append(styled_line(line))
    return Content.assemble(*parts)


def help_block(text: str) -> Content:
    """Style the Help body: section headings in the accent, keys in bright text.

    The characters never change; only the styling does.
    """
    parts: list[Content | str] = []
    for index, line in enumerate(text.split("\n")):
        if index:
            parts.append("\n")
        if _is_section_heading(line):
            parts.append(Content.styled(line, f"bold {PRIMARY}"))
            continue
        keys, separator, action = line.partition(" — ")
        if separator and line[:1].isspace():
            parts.append(
                Content.assemble(
                    Content.styled(keys, "bold"),
                    Content.styled(" — ", "dim"),
                    Content.styled(action, ""),
                )
            )
            continue
        parts.append(Content.styled(line, ""))
    return Content.assemble(*parts)


def keycap(key: str, label: str) -> Content:
    """One hint in the key bar: the key on a chip, the action dim."""
    return Content.assemble(
        Content.styled(f" {key} ", f"bold {KEY_TEXT} on {KEYCAP}"),
        Content.styled(f" {label}", "dim"),
    )


def _is_section_heading(line: str) -> bool:
    """True for a Help section heading: an upper-case line with no indent."""
    if not line or line[:1].isspace():
        return False
    letters = [character for character in line if character.isalpha()]
    return bool(letters) and all(character.isupper() for character in letters)


#: The chrome every screen shares: bars, tables, inputs, tabs and scrollbars.
APP_CSS = """
Screen {
    background: $background;
    color: $foreground;
    scrollbar-size-vertical: 1;
    scrollbar-size-horizontal: 1;
}

/* -- top bar ---------------------------------------------------------- */
Header {
    background: $surface;
    color: $muted;
    text-style: bold;
}
HeaderIcon {
    display: none;
}
HeaderTitle {
    color: $foreground;
    content-align: left middle;
    padding: 0 2;
}

/* -- bottom key bar ---------------------------------------------------- */
Footer {
    background: $surface;
    color: $muted;
}
FooterKey > .footer-key--key {
    background: $keycap;
    color: $foreground;
    text-style: bold;
}
FooterKey > .footer-key--description {
    color: $muted;
}

/* -- tables ------------------------------------------------------------ */
DataTable {
    background: $background;
    color: $foreground;
    padding: 0 1;
}
DataTable > .datatable--header {
    background: $panel;
    color: $muted;
    text-style: bold;
}
DataTable > .datatable--even-row {
    background: $surface 40%;
}
DataTable > .datatable--hover {
    background: $panel 60%;
}
DataTable > .datatable--cursor {
    background: $block-cursor-background;
    color: $block-cursor-foreground;
    text-style: bold;
}

/* -- text fields ------------------------------------------------------- */
Input {
    background: $background;
    border: none;
    border-bottom: solid $rule;
    color: $foreground;
    height: 2;
    padding: 0 1;
    width: 1fr;
}
Input:focus {
    background: $background;
    border-bottom: solid $primary;
}
Input > .input--placeholder {
    color: $muted;
}

/* -- tabs (the agent strip) -------------------------------------------- */
Button {
    background: transparent;
    border: none;
    color: $muted;
    min-width: 0;
    padding: 0 1;
    margin: 0 1 0 0;
}
Button:hover {
    background: $boost;
    color: $foreground;
}
Button.active {
    background: $primary 25%;
    color: $primary;
    text-style: bold;
}

/* -- action buttons ------------------------------------------------------ */
#compare-submit, #help-close {
    background: $primary;
    color: $background;
    text-style: bold;
}
#compare-submit:hover, #help-close:hover {
    background: $primary;
    color: $background;
    text-style: bold;
}
"""


__all__ = [
    "ACCENT",
    "APP_CSS",
    "BACKGROUND",
    "BOOST",
    "ERROR",
    "KEYCAP",
    "KEY_TEXT",
    "MUTED",
    "PANEL",
    "PRIMARY",
    "RULE",
    "SECONDARY",
    "SKILL_LENS_THEME",
    "STATE_COLOUR",
    "SUCCESS",
    "SURFACE",
    "THEME",
    "VALUE",
    "WARNING",
    "fact_block",
    "field",
    "help_block",
    "keycap",
    "state_cell",
    "styled_line",
]
