import youtube_dl


def is_url_supported(url: str) -> bool:
    """Check if the url is supported by youtube-dl."""
    extractors = youtube_dl.extractor.gen_extractors()
    for e in extractors:
        if e.suitable(url) and e.IE_NAME != 'generic':
            return True
    return False
