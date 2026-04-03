# Design Notes - Additional Specs

---

## ⭐ FEATURE: Custom System Prompt

In Settings → Translation tab, add:
- **Textarea** for custom system prompt (multiline, ~5 rows)
- Default value:
  ```
  You are a game translator. Translate the following {source_lang} text to {target_lang}. 
  Return ONLY the translation, nothing else.
  ```
- User can edit it freely. Variables supported: `{source_lang}`, `{target_lang}`, `{context}`
- "Reset to Default" button
- Small hint text: "Use {source_lang}, {target_lang}, {context} as variables"

---

## ⭐ FEATURE: Translation Context Memory

Gemini should remember previous translations to maintain story/game context.

### How it works:
- Keep a rolling history of last **N exchanges** (configurable: 5-20, default 10)
- Each exchange: `{ "source": "original text", "translated": "translated text" }`
- Send history as part of Gemini API `contents` array (multi-turn conversation)
- The `{context}` variable in the system prompt gets replaced with recent history summary

### Implementation in `gemini_client.py`:
```python
class GeminiClient:
    def __init__(self):
        self.context_history = []  # list of {"source": str, "translated": str}
        self.max_context = 10      # configurable
    
    def translate(self, text):
        # Build contents array with history
        contents = []
        
        # Add history as prior turns
        for item in self.context_history[-self.max_context:]:
            contents.append({"role": "user", "parts": [{"text": item["source"]}]})
            contents.append({"role": "model", "parts": [{"text": item["translated"]}]})
        
        # Add current text
        contents.append({"role": "user", "parts": [{"text": text}]})
        
        # Send to Gemini with system_instruction = custom_prompt
        result = gemini_api_call(system_instruction=custom_prompt, contents=contents)
        
        # Save to history
        self.context_history.append({"source": text, "translated": result})
        return result
    
    def clear_context(self):
        self.context_history = []
```

### Settings for context (in Settings → Translation tab):
- **Enable Context Memory** toggle (ON by default)
- **Context Size** slider: 1-20 exchanges (default 10)
- **Clear Context** button (with confirmation) — resets history
- Small info text: "LunaLite remembers previous translations for better accuracy"

### Main window:
- Show small context indicator: "💾 Context: 7/10" 
- Quick "Clear Context" button (🗑️ icon)

---

## Dark Mode Color
- Main background: `rgb(23, 23, 23)` = `#171717`
- Panel background: `#1e1e1e`
- Accent: `#0f3460`
- Highlight: `#e94560`

## Power Button Toggle - Complete CSS (bounceIn animations)

The start/stop button must implement these EXACT keyframe animations in PyQt6 via QPropertyAnimation:

### States:
- **Unchecked (OFF)**: Blue border ring, X mark (two lines at ±45deg), bounceIn animation
- **Checked (ON)**: SVG stroke-dasharray animates to checkmark, X lines bounce OUT

### Keyframes to replicate in Qt:
```
bounceInBefore: 0%→opacity:0,scale:0.3 | 50%→opacity:0.9,scale:1.1 | 80%→opacity:1,scale:0.89 | 100%→opacity:1,scale:1
bounceInAfter: same but rotate(-45deg)
bounceInBeforeDont: reverse (fade out)
bounceInAfterDont: reverse (fade out)
```

### SVG stroke-dasharray animation:
- OFF state: `stroke-dashoffset: 124.6; stroke-dasharray: 0 162.6 133 29.6`
- ON state: `stroke-dashoffset: 162.6; stroke-dasharray: 0 162.6 28 134.6`
- Transition: 0.4s ease, delay 0.2s on check

## Dark/Light Mode Toggle - Complete CSS

### Colors:
- Dark mode slider bg: `#20262c`
- Light mode slider bg: `#5494de`  
- Moon shadow: `box-shadow: inset 8px -4px 0px 0px #ececd9, -4px 1px 4px 0px #dadada`
- Sun glow: `box-shadow: inset 15px -4px 0px 15px #efdf2b, 0 0 10px 0px #efdf2b`

### Stars decoration (dark mode):
`box-shadow: -7px 10px 0 #e5f041e6, 8px 15px 0 #e5f041e6, -17px 1px 0 #e5f041e6, -20px 10px 0 #e5f041e6, -7px 23px 0 #e5f041e6, -15px 25px 0 #e5f041e6`

### Light mode - cloud dots:
`box-shadow: -12px 0 0 white, -6px 0 0 1.6px white, 5px 15px 0 1px white, 1px 17px 0 white, 10px 17px 0 white`

### Toggle size: font-size:17px, width:3.5em, height:2em

## Service Toggle Buttons (any ON/OFF service)
Use the circular power button style (checkbox-wrapper) described in the main prompt.
Border: `3px solid rgba(0, 89, 255, 0.288)`
Size: 44x44px
