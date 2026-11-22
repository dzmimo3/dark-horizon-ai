# DARK HORIZON AI - Project Guidelines

## Mandatory Rules

1. **UI Integrity & Button Operation:** Maintain absolute preservation of design and functionality for all UI elements in `index.html`:
   - Send button (`btnSend`)
   - Plus menu button (`btnPlus`)
   - Microphone button (`btnMic`)
   - Dimension selector (`aspectSel`)
   - New chat button (`btnNew`)

2. **Syntax & Health Check:** Always run `node --check engine.js` before any deployment, build, or commit to ensure zero syntax or compilation errors.

3. **Automated Git Deployment:** When deploying or updating the project, execute:
   ```bash
   git add -A
   git commit -m "omni_full_upgrade"
   git push -u org main --force
   ```

4. **Features & Capabilities:**
   - Multi-modal support (Images, Files `.txt`/`.py`/`.json`).
   - 8K Image generation across all styles (Realistic, Anime, Cinematic) respecting selected aspect ratios (1:1, 16:9, 9:16).
   - Cinematic Anime/Video production with multi-character dialogues, character-specific voice tones (soft/manly/deep via Web Audio / TTS), smooth camera motion (Zoom & Pan), particle lighting effects, colored character name badges, and symbol/punctuation cleaning before speech synthesis.
   - Live code execution preview buttons embedded directly into AI responses for generated HTML/JS/CSS code blocks.
   - PWA support via `manifest.json` and `sw.js`.
