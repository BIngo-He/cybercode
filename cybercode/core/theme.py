from dataclasses import dataclass
import os


@dataclass(frozen=True)
class ThemePalette:
    name: str
    display_name: str
    background: str
    surface: str
    primary: str
    accent: str
    info: str
    text: str
    muted: str
    success: str
    warning: str
    error: str

    @staticmethod
    def _hex_to_truecolor(hex_color: str) -> str:
        clean = hex_color.lstrip("#")
        red = int(clean[0:2], 16)
        green = int(clean[2:4], 16)
        blue = int(clean[4:6], 16)
        return f"\033[38;2;{red};{green};{blue}m"

    @property
    def ansi_primary(self) -> str:
        return self._hex_to_truecolor(self.primary)

    @property
    def ansi_accent(self) -> str:
        return self._hex_to_truecolor(self.accent)

    @property
    def ansi_info(self) -> str:
        return self._hex_to_truecolor(self.info)

    @property
    def ansi_text(self) -> str:
        return self._hex_to_truecolor(self.text)

    @property
    def ansi_muted(self) -> str:
        return self._hex_to_truecolor(self.muted)

    @property
    def ansi_success(self) -> str:
        return self._hex_to_truecolor(self.success)

    @property
    def ansi_warning(self) -> str:
        return self._hex_to_truecolor(self.warning)

    @property
    def ansi_error(self) -> str:
        return self._hex_to_truecolor(self.error)


THEMES = {
    "acid-pulse": ThemePalette(
        name="acid-pulse",
        display_name="Acid Pulse",
        background="#07090D",
        surface="#0C1012",
        primary="#B7FF00",
        accent="#FF2D95",
        info="#00F5D4",
        text="#EAFBF2",
        muted="#95A89C",
        success="#7CFF6B",
        warning="#FFD166",
        error="#FF4D6D",
    ),
    "neon-grid": ThemePalette(
        name="neon-grid",
        display_name="Neon Grid",
        background="#07090D",
        surface="#0D1117",
        primary="#00E5FF",
        accent="#FF2BD6",
        info="#8B5CF6",
        text="#E6F1FF",
        muted="#8FA3B8",
        success="#39FF88",
        warning="#FFC857",
        error="#FF4D6D",
    ),
    "signal-burn": ThemePalette(
        name="signal-burn",
        display_name="Signal Burn",
        background="#07090D",
        surface="#10141B",
        primary="#00D1FF",
        accent="#FFB000",
        info="#4C6FFF",
        text="#E8F1F8",
        muted="#93A4B7",
        success="#2EE59D",
        warning="#FFB000",
        error="#FF5C77",
    ),
}

DEFAULT_THEME = "acid-pulse"
_current_theme_name = os.getenv("CYBERCODE_THEME", DEFAULT_THEME)
if _current_theme_name not in THEMES:
    _current_theme_name = DEFAULT_THEME


def list_themes() -> list[ThemePalette]:
    return list(THEMES.values())


def get_theme_name() -> str:
    return _current_theme_name


def get_theme() -> ThemePalette:
    return THEMES[_current_theme_name]


def set_theme(theme_name: str) -> ThemePalette:
    global _current_theme_name
    normalized = theme_name.strip().lower()
    if normalized not in THEMES:
        raise ValueError(f"Unknown theme: {theme_name}")
    _current_theme_name = normalized
    return THEMES[_current_theme_name]
