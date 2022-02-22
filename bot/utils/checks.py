import json
from pathlib import Path

import youtube_dl

# Get all supported ffmpeg input formats.
with open(Path("bot/resources/supported_extensions.json"), "r") as f:
    SUPPORTED_EXTENSIONS = json.load(f)


def is_url_supported(url: str) -> bool:
    """Check if the url is supported by youtube-dl."""
    # Check if the extension of the url is supported.
    if url.endswith(tuple(SUPPORTED_EXTENSIONS)):
        return True

    # Check if the url provider is supported.
    extractors = youtube_dl.extractor.gen_extractors()
    for e in extractors:
        if e.suitable(url) and e.IE_NAME != 'generic':
            return True

    return False
