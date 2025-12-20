# 🎤 Audio Debug Feature - Summary

## What Was Built

A **complete audio debugging system** to diagnose and fix Hindi transcription issues by letting you see exactly what the microphone captures.

## The Problem
> "Hindi is not correctly transcribed in interactive mode"

## The Solution
**Save and inspect all recorded audio files** with automatic quality analysis.

---

## 3-Step Workflow

### 1. Record Hindi Voice
```bash
python src/main.py --mode interactive
```
- Speak in Hindi
- Audio saved automatically: `audio_debug/raw_audio_*.wav`
- Statistics logged: Volume, Peak, Silence

### 2. Analyze Quality
```bash
python inspect_audio.py
```
- RMS Volume: Is it too quiet/loud?
- Peak: Is it clipping?
- Silence: Too many pauses?
- Quality assessment: GOOD or NEEDS IMPROVEMENT

### 3. Listen & Verify
```bash
open audio_debug/
```
- Play `raw_audio_*.wav` (original)
- Play `normalized_audio_*.wav` (after normalization)
- Ask: **"Can I clearly hear the Hindi?"**

---

## Key Questions You Can Now Answer

| Question | How to Check |
|----------|--------------|
| **Can you clearly hear Hindi?** | Open `raw_audio_*.wav` and listen |
| **Is volume normal?** | Run `inspect_audio.py` → check RMS Volume |
| **No clipping?** | Check Peak Amplitude (should be < 30000) |
| **No silence?** | Check Silence Ratio (should be < 50%) |
| **If you can't hear clear Hindi, can Whisper?** | **NO!** → Fix audio first |

---

## What Gets Saved

For each utterance:
- `raw_audio_<timestamp>.wav` - Direct microphone input
- `normalized_audio_<timestamp>.wav` - After volume normalization

Example:
```
audio_debug/
├── raw_audio_1702501234567.wav (45.3 KB)
├── normalized_audio_1702501234567.wav (45.3 KB)
├── raw_audio_1702501234890.wav (42.1 KB)
├── normalized_audio_1702501234890.wav (42.1 KB)
└── ...
```

---

## Audio Quality Indicators

### RMS Volume (0-1 scale)
- `< 0.05`: ⚠️ TOO QUIET → Speak LOUDER
- `0.05-0.8`: ✅ GOOD → Normal volume
- `> 0.8`: ⚠️ TOO LOUD → Check for clipping

### Peak Amplitude
- `> 30000`: ⚠️ CLIPPING → Move away from mic
- `< 30000`: ✅ GOOD → No distortion

### Silence Ratio
- `> 50%`: ⚠️ TOO MUCH SILENCE → Speak continuously
- `< 50%`: ✅ GOOD → Continuous speech

---

## Example Output

### During Recording:
```
🎤 Listening... (attempt 1/3)
   Speak clearly in Hindi. Maximum duration: 10 seconds

[STT-DEBUG] Raw audio saved: audio_debug/raw_audio_1702501234567.wav
[STT-DEBUG] Raw Audio Stats - RMS Volume: 0.1234, Peak: 0.5678
[STT-DEBUG] Normalized audio saved: audio_debug/normalized_audio_1702501234567.wav
[STT] Transcribed text: 'मुझे सरकारी योजना चाहिए'
```

### From Inspector:
```
1. raw_audio_1702501234567.wav (45.3 KB) [Raw]
──────────────────────────────────────────────
   Duration:       2.15s
   RMS Volume:     0.1234 (0-1 scale)
   Peak Amplitude: 18456 (56.3% of max)
   Silence Ratio:  12.5%

   🔍 QUALITY CHECK:
      ✓ GOOD volume level
      ✓ No clipping detected
      ✓ Good speech continuity

   📈 OVERALL:
      ✅ GOOD - Whisper should transcribe correctly!
```

---

## Troubleshooting Flowchart

```
Transcription Failed?
│
├─→ Check Audio Quality
│   $ python inspect_audio.py
│   
│   ├─→ RMS < 0.05?
│   │   └─→ Speak LOUDER
│   │
│   ├─→ Peak > 30000?
│   │   └─→ Move away from mic
│   │
│   └─→ Silence > 50%?
│       └─→ Speak continuously
│
├─→ Listen to Files
│   $ open audio_debug/
│   
│   ├─→ Audio GOOD but transcription still failed?
│   │   └─→ Whisper issue (try medium model)
│   │
│   └─→ Audio BAD?
│       └─→ Fix above issues first
│
└─→ Try Again
    $ python src/main.py --mode interactive
    └─→ Repeat with improved conditions
```

---

## Files Added

### Scripts:
- **`inspect_audio.py`** - Analyzes recorded audio quality
  ```bash
  python inspect_audio.py
  ```
  Shows: Duration, Volume, Peak, Silence, Quality Assessment

### Documentation:
- **`AUDIO_DEBUG_QUICK_START.md`** - Quick reference guide
- **`AUDIO_DEBUG_GUIDE.md`** - Comprehensive guide with advanced tips
- **`AUDIO_DEBUG_IMPLEMENTATION.md`** - Technical implementation details

### Modified Files:
- **`src/voice/stt.py`**
  - Saves raw audio before normalization
  - Saves normalized audio after normalization
  - Logs RMS volume, peak, minimum amplitude
  - Added `get_audio_debug_report()` method
  - Enabled by default: `debug_audio=True`

- **`src/main.py`**
  - Initialized STT with `debug_audio=True`
  - Display debug report on exit
  - Message: "Voice recordings will be saved to: audio_debug/"

---

## Key Features

✅ **Automatic Audio Saving**
  - Every recording saved as WAV file
  - Both raw and normalized versions

✅ **Statistical Analysis**
  - RMS Volume calculation
  - Peak amplitude detection
  - Silence ratio measurement
  - Auto-logged to console

✅ **Quality Inspector**
  - Analyzes all recorded files
  - Provides assessment: GOOD/QUIET/LOUD/CLIPPING/SILENCE
  - Actionable recommendations

✅ **Debug Report**
  - Summary on exit
  - File list with sizes
  - Guidance for inspection

✅ **Easy Workflow**
  - Record → Analyze → Listen
  - Compare raw vs normalized
  - Make improvements

---

## How It Helps

### Before This Feature:
❌ Transcription failed → No idea why
❌ Is the audio bad? Unknown
❌ Is Whisper the problem? Unknown
❌ Can't listen to what was recorded

### After This Feature:
✅ Transcription failed → Check audio quality with inspector
✅ Audio saved → Can listen and verify
✅ Raw + Normalized → See effect of normalization
✅ Statistics logged → Know exact volume/peak/silence
✅ Quality assessment → Actionable improvements

---

## Complete Setup Checklist

- ✅ Audio recording with float32 format (high precision)
- ✅ Automatic saving to WAV files
- ✅ Raw audio before normalization
- ✅ Normalized audio after normalization
- ✅ Statistics logging (RMS, Peak, Min, Silence)
- ✅ Debug report on exit
- ✅ Inspector tool for analysis
- ✅ Quality thresholds defined
- ✅ Troubleshooting guide provided
- ✅ Quick start documentation

---

## Now You Can...

1. **See** exactly what your microphone captures
2. **Analyze** audio quality (volume, clipping, silence)
3. **Listen** to both raw and normalized versions
4. **Understand** why transcription might be failing
5. **Fix** audio quality issues systematically
6. **Verify** improvements before trying Whisper again

---

## Next Steps

```bash
# 1. Test with your voice
python src/main.py --mode interactive

# 2. Inspect the quality
python inspect_audio.py

# 3. Listen to the files
open audio_debug/

# 4. Based on results:
# - Good audio? → Transcription should work
# - Bad audio? → Make improvements and retry
```

---

## Remember

> **"If you can't clearly hear the Hindi, Whisper can't either!"**

This feature lets you verify this fundamental truth and diagnose exactly what needs to be fixed.

**Good Audio Quality = Successful Transcription** 🎉
