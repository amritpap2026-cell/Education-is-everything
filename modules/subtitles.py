"""Generate TikTok-style ASS subtitles with word highlighting."""
ASS_HEADER = """[Script Info]
ScriptType: v4.00+
PlayResX: 1920
PlayResY: 1080
WrapStyle: 0
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Noto Sans Devanagari,48,&H00FFFFFF,&H0000FFFF,&H00000000,&H80000000,-1,0,0,0,100,100,2,0,1,3,2,2,80,80,100,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""

def _fmt(seconds):
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    cs = int((seconds % 1) * 100)
    return f"{h}:{m:02d}:{s:02d}.{cs:02d}"

def build_ass(script_text, output_path, audio_duration, max_words_per_phrase=5):
    import re
    text = re.sub(r"\s+", " ", script_text).strip()
    sentences = re.split(r"(?<=[.!?।])\s+", text)

    phrases = []
    for sentence in sentences:
        words = sentence.split()
        if not words: continue
        for i in range(0, len(words), max_words_per_phrase):
            phrases.append(words[i:i + max_words_per_phrase])

    total_words = sum(len(p) for p in phrases)
    if audio_duration <= 0: audio_duration = 1.0
    wps = total_words / audio_duration

    events = []
    t = 0.5
    for phrase in phrases:
        phrase_duration = max(0.8, len(phrase) / wps)
        word_duration = phrase_duration / len(phrase)

        for i, word in enumerate(phrase):
            start = t + i * word_duration
            end = start + word_duration
            before = " ".join(phrase[:i])
            current = word
            after = " ".join(phrase[i + 1:])
            parts = []
            if before: parts.append(before + " ")
            parts.append(f"{{\\c&H0000FFFF&}}{current}{{\\c&H00FFFFFF&}}")
            if after: parts.append(" " + after)
            line = "".join(parts)
            events.append(f"Dialogue: 0,{_fmt(start)},{_fmt(end)},Default,,0,0,0,,{line}")

        t += phrase_duration

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(ASS_HEADER)
        f.write("\n".join(events))
        f.write("\n")
    return output_path
