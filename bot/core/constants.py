from pydantic import BaseModel


class Colours(BaseModel):
    """Colour codes."""

    blue = 0x0279FD
    bright_green = 0x01D277
    dark_green = 0x1F8B4C
    gold = 0xE6C200
    grass_green = 0x66FF00
    light_blue = 0x68A4FF
    orange = 0xE67E22
    pink = 0xCF84E0
    purple = 0xB734EB
    python_blue = 0x4B8BBE
    python_yellow = 0xFFD43B
    red = 0xFF0000
    soft_green = 0x68C290
    soft_orange = 0xF9CB54
    soft_red = 0xCD6D6D
    yellow = 0xF8E500


class Emojis(BaseModel):
    """Emoji codes."""

    arrow_left = "\u2B05"  # ⬅
    arrow_right = "\u27A1"  # ➡
    clock = "\U0001F552"
    lock = "\U0001F512"  # 🔒
    partying_face = "\U0001F973"  # 🥳
    track_next = "\u23ED"  # ⏭
    track_previous = "\u23EE"  # ⏮
    tools = "\U0001F6E0"  # 🛠


class Pagination(BaseModel):
    """Pagination default settings."""

    max_size = 500
    timeout = 300  # In seconds.


class Images(BaseModel):
    """Image links."""

    youtube = "https://upload.wikimedia.org/wikipedia/commons/thumb/e/ec/" \
              "YouTube_play_button_circular_%282013-2017%29.svg/240px-YouTube_play_button_circular_" \
              "%282013-2017%29.svg.png"


class Constants(BaseModel):
    """The app constants."""

    colours: Colours = Colours()
    emojis: Emojis = Emojis()
    images: Images = Images()
    pagination: Pagination = Pagination()

    low_latency: int = 200
    high_latency: int = 400


constants = Constants()
