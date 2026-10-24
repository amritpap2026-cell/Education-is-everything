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

def build_ass(script_text, output_path, word_timestamps, max_words_per_phrase=5):
    """Build ASS subtitle file using exact word timestamps from forced alignment."""
    import re
    
    # Group words into phrases
    phrases = []
    current_phrase = []
    for word_data in word_timestamps:
        current_phrase.append(word_data)
        if len(current_phrase) >= max_words_per_phrase or word_data['word'].endswith(('.', '!', '?', '।')):
            phrases.append(current_phrase)
            current_phrase = []
    if current_phrase:
        phrases.append(current_phrase)

    events = []
    for phrase in phrases:
        start_time = phrase[0]['start']
        end_time = phrase[-1]['end']
        
        # Build the text with word highlighting
        parts = []
        for i, word_data in enumerate(phrase):
            word = word_data['word']
            # Highlight the current word in yellow
            parts.append(f"{{\\c&H0000FFFF&}}{word}{{\\c&H00FFFFFF&}}")
            if i < len(phrase) - 1:
                parts.append(" ")
        
        line = "".join(parts)
        events.append(f"Dialogue: 0,{_fmt(start_time)},{_fmt(end_time)},Default,,0,0,0,,{line}")

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(ASS_HEADER)
        f.write("\n".join(events))
        f.write("\n")
    return output_path