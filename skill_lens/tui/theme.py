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

from textual.app import ComposeResult
from textual.binding import Binding
from textual.content import Content
from textual.theme import Theme
from textual.widgets import Footer, Static

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


#: A blank cell that is not whitespace.
#:
#: It gives the gap between a key and its action without giving the line
#: wrapper a place to break, so a narrow terminal wraps between hints and
#: never splits one in two.  It is the Unicode braille blank, which terminal
#: fonts draw as an empty cell.
_BLANK = "\u2800"


def keycap(key: str, label: str) -> Content:
    """One hint in the key bar: the key on a chip, the action dim.

    The action is joined to its chip with a blank cell, so the pair can never
    be split across two lines.
    """
    return Content.assemble(
        Content.styled(f"{_BLANK}{key}{_BLANK}", f"bold {KEY_TEXT} on {KEYCAP}"),
        Content.styled(f"{label} ", "dim"),
    )


def key_group(*hints: tuple[str, str]) -> Content:
    """One group of hints in the key bar, e.g. the keys that navigate.

    The hints of a group sit close together; the groups themselves are
    separated by a rule, so the bar reads as a map instead of a run-on list.
    """
    return Content.assemble(*[keycap(key, label) for key, label in hints])


def key_bar(*groups: tuple[tuple[str, str], ...]) -> Content:
    """The whole key bar: groups of hints, separated by a dim rule."""
    parts: list[Content | str] = []
    for index, group in enumerate(groups):
        if index:
            # The rule is joined to the group behind it, so a wrap never
            # leaves a dangling separator at the end of a line.
            parts.append(Content.styled(f"{_BLANK}{_BLANK}\u2502{_BLANK}{_BLANK}", "dim"))
        parts.append(key_group(*group))
    return Content.assemble(*parts)


def brand_lockup(title: str, version: str) -> Content:
    """The centred brand mark of the top bar: a lens, the name, the version.

    The name is set in capitals and bold, with the letters spaced out -- in a
    terminal grid that is what a larger, more deliberate title looks like.
    """
    spaced = " ".join(title.upper())
    return Content.assemble(
        Content.styled("\u25c9", f"bold {PRIMARY}"),
        Content.styled(f"  {spaced}", "bold"),
        Content.styled(f"   {version}", "dim"),
    )


def _is_section_heading(line: str) -> bool:
    """True for a Help section heading: an upper-case line with no indent."""
    if not line or line[:1].isspace():
        return False
    letters = [character for character in line if character.isalpha()]
    return bool(letters) and all(character.isupper() for character in letters)


class KeyBar(Footer):
    """The key bar of a screen: its own keys, then the session keys.

    It is a Textual :class:`Footer`, so it keeps the standard position and
    geometry, but it draws the keys itself: grouped by purpose, with the key
    on a chip and the action beside it.

    The keys come from the screen's own declarations plus the app's, with the
    screen winning a key both of them show.  The *live* binding chain must not
    be used: a focused widget can shadow a screen key (a table binds ``enter``
    for itself) and a modal cuts the chain before the app's keys, so the live
    chain silently hides keys the screen really answers to.
    """

    def compose(self) -> ComposeResult:
        yield Static(self._bar(), classes="key-bar", markup=False)

    def _bar(self) -> Content:
        screen_bindings = [
            binding for binding in self.screen.BINDINGS if isinstance(binding, Binding)
        ]
        screen_keys = {binding.key for binding in screen_bindings}
        own = [
            (binding.key, binding.description or binding.key)
            for binding in screen_bindings
            if binding.show
        ]
        session = [
            (binding.key, binding.description or binding.key)
            for binding in self.app.BINDINGS
            if isinstance(binding, Binding) and binding.show and binding.key not in screen_keys
        ]
        groups = [tuple(group) for group in (own, session) if group]
        return key_bar(*groups)


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
    border-bottom: solid $rule;
    color: $muted;
    height: 2;
    text-style: bold;
}
HeaderIcon {
    display: none;
}
HeaderTitle {
    color: $foreground;
    content-align: center middle;
    padding: 0 2;
    text-style: bold;
}
HeaderClockSpace {
    display: none;
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
KeyBar {
    background: $background;
    height: auto;
}
KeyBar > .key-bar {
    width: 1fr;
    height: auto;
}
KeyGroup {
    border-left: solid $rule;
    margin: 0 1 0 0;
    padding-left: 1;
}
FooterLabel {
    margin: 0;
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
    border-bottom: solid $rule;
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
    "KeyBar",
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
    "brand_lockup",
    "fact_block",
    "field",
    "help_block",
    "keycap",
    "state_cell",
    "styled_line",
]
