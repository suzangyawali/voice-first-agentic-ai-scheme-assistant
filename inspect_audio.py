#!/usr/bin/env python3
"""
Audio Debug Inspector - Analyze recorded audio files for quality
"""

import os
import sys
from pathlib import Path
import numpy as np

def inspect_audio_directory():
    """List and analyze all recorded audio files"""
    
    audio_dir = Path("audio_debug")
    
    if not audio_dir.exists():
        print("❌ audio_debug/ directory not found")
        print("   Run interactive mode first: python src/main.py --mode interactive")
        return
    
    audio_files = sorted(audio_dir.glob("*.wav"), reverse=True)
    
    if not audio_files:
        print("❌ No audio files found in audio_debug/")
        return
    
    print("\n" + "="*80)
    print("🎤 AUDIO DEBUG INSPECTOR")
    print("="*80)
    print(f"\n📁 Location: {audio_dir.absolute()}")
    print(f"📊 Total files: {len(audio_files)}\n")
    
    try:
        import scipy.io.wavfile as wav
        import matplotlib.pyplot as plt
    except ImportError:
        print("⚠️  scipy/matplotlib not available - showing basic info only\n")
        scipy = None
        wav = None
    
    # Analyze each file
    for i, audio_file in enumerate(audio_files, 1):
        file_size_kb = audio_file.stat().st_size / 1024
        file_type = "Raw" if "raw_audio" in audio_file.name else "Normalized"
        
        print(f"\n{'─'*80}")
        print(f"{i}. {audio_file.name} ({file_size_kb:.1f} KB) [{file_type}]")
        print(f"{'─'*80}")
        
        if wav is not None:
            try:
                sample_rate, audio_data = wav.read(str(audio_file))
                
                # Handle stereo/mono
                if len(audio_data.shape) > 1:
                    audio_data = audio_data[:, 0]
                
                duration = len(audio_data) / sample_rate
                
                # Statistics
                rms_volume = np.sqrt(np.mean(audio_data.astype(float) ** 2))
                peak = np.max(np.abs(audio_data))
                min_val = np.min(np.abs(audio_data))
                
                # Normalize to -1..1 for analysis
                normalized = audio_data.astype(float) / 32768.0
                rms_norm = np.sqrt(np.mean(normalized ** 2))
                
                print(f"   Duration:       {duration:.2f}s ({len(audio_data)} samples @ {sample_rate}Hz)")
                print(f"   RMS Volume:     {rms_norm:.4f} (0-1 scale)")
                print(f"   Peak Amplitude: {peak} ({(peak/32768)*100:.1f}% of max)")
                print(f"   Min Amplitude:  {min_val}")
                
                # Quality assessment
                print(f"\n   🔍 QUALITY CHECK:")
                
                # Volume check
                if rms_norm < 0.05:
                    print(f"      ⚠️  QUIET - Volume very low (RMS {rms_norm:.4f})")
                    print(f"          → Speak LOUDER next time")
                elif rms_norm > 0.8:
                    print(f"      ⚠️  LOUD - Volume very high (RMS {rms_norm:.4f})")
                    print(f"          → Check for clipping (peak might be distorted)")
                else:
                    print(f"      ✓ GOOD volume level (RMS {rms_norm:.4f})")
                
                # Clipping check (if peak near max)
                if peak > 30000:
                    print(f"      ⚠️  CLIPPING - Peak too high ({peak}, may cause distortion)")
                    print(f"          → Speak further from mic or lower microphone level")
                else:
                    print(f"      ✓ No clipping detected")
                
                # Silence check
                silent_frames = np.sum(np.abs(audio_data) < 1000)
                silence_ratio = silent_frames / len(audio_data)
                
                if silence_ratio > 0.5:
                    print(f"      ⚠️  SILENCE - {silence_ratio*100:.1f}% of recording is silence")
                    print(f"          → Too much pauses; speak continuously")
                else:
                    print(f"      ✓ Good speech continuity ({silence_ratio*100:.1f}% silence)")
                
                # Overall assessment
                print(f"\n   📈 OVERALL:")
                issues = []
                if rms_norm < 0.05:
                    issues.append("too quiet")
                if peak > 30000:
                    issues.append("clipping")
                if silence_ratio > 0.5:
                    issues.append("too much silence")
                
                if not issues:
                    print(f"      ✅ GOOD - Audio quality looks fine!")
                    print(f"         Whisper should transcribe this correctly")
                else:
                    print(f"      ❌ ISSUES FOUND: {', '.join(issues)}")
                    print(f"         If transcription failed, these could be the reasons")
                
            except Exception as e:
                print(f"   ❌ Error reading file: {e}")
        else:
            print(f"   File size: {file_size_kb:.1f} KB")
            print(f"   (Install scipy.io to see detailed analysis)")
    
    # Summary
    print(f"\n{'='*80}")
    print("📋 NEXT STEPS:")
    print("="*80)
    print("""
1. LISTEN TO THE FILES:
   • Open audio_debug/ folder
   • Play each WAV file to hear what was recorded
   • Check if you can understand the Hindi clearly

2. COMPARE RAW vs NORMALIZED:
   • raw_audio_*.wav     = Direct microphone input
   • normalized_audio_*  = After audio normalization
   • See which sounds better

3. IF TRANSCRIPTION FAILED:
   • Check the issues above
   • Try again with LOUDER voice
   • Move CLOSER to microphone
   • Check microphone is not muted

4. VIEW WITH TOOLS:
   • macOS: open audio_debug/
   • Audacity: Import WAV files for detailed waveform analysis
   • Command: ffprobe audio_debug/raw_audio_*.wav

5. FINAL TEST:
   • Once audio quality looks good, transcription should work!
   • Run: python src/main.py --mode interactive
""")
    print("="*80 + "\n")

if __name__ == "__main__":
    inspect_audio_directory()
