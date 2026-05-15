SUPPORTED_LANGUAGES = {"en", "hi", "te", "ta"}

PHRASES = {
    "suspicious_movement": {
        "en": "Suspicious movement detected near {location}. Please verify the live camera feed.",
        "hi": "{location} ke paas sandigdh gatividhi mili hai. Kripya live camera feed dekhein.",
        "te": "{location} daggara anumanaspada kadalika kanipinchindi. Live camera feed ni pariseelinchandi.",
        "ta": "{location} arugil sandhega iyakkam kandupidikkappattathu. Live camera feed-ai saripaarungal.",
    },
    "camera_selected": {
        "en": "{camera} selected for target near {location}.",
        "hi": "{location} ke paas target ke liye {camera} chuna gaya hai.",
        "te": "{location} daggara target kosam {camera} empika chesaru.",
        "ta": "{location} arugil ull target-kku {camera} therndheduthullathu.",
    },
}


def build_operator_guidance(event_type, location, camera=None, language="hi"):
    language = language if language in SUPPORTED_LANGUAGES else "en"
    template = PHRASES.get(event_type, PHRASES["suspicious_movement"]).get(language)

    return {
        "event_type": event_type,
        "language": language,
        "text": template.format(
            location=location or "selected location",
            camera=camera or "selected camera",
        ),
    }
