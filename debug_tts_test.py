#!/usr/bin/env python3
# debug_tts_test.py
"""
Debug script to test TTS models individually.
Run this to diagnose TTS issues.
"""

import os
import sys
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


def test_basic_tts():
    """Test basic TTS functionality."""
    print("🔍 Testing Basic TTS Functionality")
    print("=" * 50)

    try:
        from TTS.api import TTS
        print("✅ TTS library imported successfully")
    except ImportError as e:
        print(f"❌ Failed to import TTS library: {e}")
        return False

    # Test with basic model
    try:
        print("\n📦 Testing basic TTS model...")
        tts = TTS(model_name="tts_models/en/ljspeech/tacotron2-DDC")
        print("✅ Basic model loaded successfully")

        # Test synthesis
        test_text = "Hello, this is a test."
        output_path = "debug_test_basic.wav"

        print(f"🔄 Synthesizing: '{test_text}'")
        tts.tts_to_file(text=test_text, file_path=output_path)

        if os.path.exists(output_path):
            size = os.path.getsize(output_path)
            print(f"✅ Basic synthesis successful! File size: {size} bytes")
            os.remove(output_path)  # Clean up
            return True
        else:
            print("❌ Output file was not created")
            return False

    except Exception as e:
        print(f"❌ Basic TTS test failed: {e}")
        return False


def test_xtts_model():
    """Test XTTS model specifically."""
    print("\n🎯 Testing XTTS Model")
    print("=" * 50)

    try:
        from TTS.api import TTS

        print("📦 Loading XTTS model...")
        tts = TTS(model_name="tts_models/multilingual/multi-dataset/xtts_v2")
        print("✅ XTTS model loaded successfully")

        # Test without speaker cloning
        test_text = "Hello, this is a test of XTTS without speaker cloning."
        output_path = "debug_test_xtts_no_speaker.wav"

        print(f"🔄 Testing XTTS without speaker: '{test_text}'")

        # Method 1: Try tts_to_file without speaker
        try:
            tts.tts_to_file(text=test_text, language="en", file_path=output_path)
            if os.path.exists(output_path):
                size = os.path.getsize(output_path)
                print(f"✅ XTTS without speaker successful! File size: {size} bytes")
                os.remove(output_path)
                return True
        except Exception as e1:
            print(f"⚠️  Method 1 failed: {e1}")

            # Method 2: Try tts method and save manually
            try:
                print("🔄 Trying alternative method...")
                wav = tts.tts(text=test_text, language="en")

                import soundfile as sf
                sf.write(output_path, wav, 22050)

                if os.path.exists(output_path):
                    size = os.path.getsize(output_path)
                    print(f"✅ XTTS alternative method successful! File size: {size} bytes")
                    os.remove(output_path)
                    return True

            except Exception as e2:
                print(f"❌ Method 2 also failed: {e2}")
                return False

    except Exception as e:
        print(f"❌ XTTS test failed: {e}")
        return False


def test_with_our_engine():
    """Test with our custom engine."""
    print("\n🔧 Testing Our Custom Engine")
    print("=" * 50)

    try:
        # Add current directory to path
        sys.path.insert(0, '.')

        from tts_engines import xtts_engine
        print("✅ Custom engine imported successfully")

        # Test synthesis
        test_text = "Hello, this is a test with our custom engine."
        output_path = "debug_test_custom_engine.wav"

        print(f"🔄 Testing custom engine: '{test_text}'")
        success, message = xtts_engine.synthesize_xtts(
            text=test_text,
            speaker_wav_path=None,
            language="en",
            output_path=output_path,
            model_key="xtts_v2"
        )

        if success:
            print(f"✅ Custom engine test successful!")
            print(f"📝 Message: {message}")
            if os.path.exists(output_path):
                os.remove(output_path)  # Clean up
            return True
        else:
            print(f"❌ Custom engine test failed: {message}")
            return False

    except Exception as e:
        print(f"❌ Custom engine test failed: {e}")
        import traceback
        print(f"🔍 Traceback: {traceback.format_exc()}")
        return False


def check_config():
    """Check configuration."""
    print("\n⚙️  Checking Configuration")
    print("=" * 50)

    try:
        from config.tts_models_config import get_enabled_models
        models = get_enabled_models()
        print(f"✅ Configuration loaded. Enabled models: {list(models.keys())}")
        return True
    except ImportError:
        print("❌ Configuration not found. Please create config/tts_models_config.py")
        return False
    except Exception as e:
        print(f"❌ Configuration error: {e}")
        return False


def main():
    """Run all tests."""
    print("🎙️  Multi TTS Debug Tool")
    print("=" * 60)

    # Create output directory
    os.makedirs("audio_output", exist_ok=True)

    # Run tests
    results = {}
    results['config'] = check_config()
    results['basic_tts'] = test_basic_tts()
    results['xtts'] = test_xtts_model()
    results['custom_engine'] = test_with_our_engine()

    # Summary
    print("\n📊 TEST SUMMARY")
    print("=" * 60)
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{test_name.upper()}: {status}")

    if all(results.values()):
        print("\n🎉 All tests passed! Your TTS setup should work correctly.")
    else:
        print("\n⚠️  Some tests failed. Check the output above for details.")

        # Provide specific recommendations
        if not results['config']:
            print("\n💡 RECOMMENDATION: Run the setup script to create configuration:")
            print("   python setup_models.py")

        if not results['basic_tts']:
            print("\n💡 RECOMMENDATION: Check your TTS library installation:")
            print("   pip install --upgrade TTS")

        if not results['xtts']:
            print("\n💡 RECOMMENDATION: XTTS model might need specific handling.")
            print("   Try using speaker samples or different synthesis method.")


if __name__ == "__main__":
    main()