#!/usr/bin/env python3
"""
Simple voice cloning test script
Upload an audio file, clone the voice, and generate speech with that voice.
"""
import requests
import os

def test_voice_cloning():
    base_url = "http://localhost:8000"
    
    # Hardcoded test values
    # audio_file_path = "echos_voice_sample.wav"  # Change this to your audio file
    audio_file_path = "voice_samples/beks_voice_sample.wav"
    # audio_file_path = "voice_samples/charade_confide.wav"
    voice_name = "bek"
    test_text = """
    What's up you sexy hunk of man meat!?
    """

    # Check if file exists
    if not os.path.exists(audio_file_path):
        print(f"Error: Audio file '{audio_file_path}' not found")
        print("Please place your audio file in the current directory and update the 'audio_file_path' variable")
        return
    
    print(f"🎤 Testing voice cloning with:")
    print(f"   Audio file: {audio_file_path}")
    print(f"   Voice name: {voice_name}")
    print(f"   Test text: {test_text}")
    print()
    
    try:
        # Step 1: Upload and clone the voice
        print("📤 Uploading and cloning voice...")
        
        with open(audio_file_path, 'rb') as f:
            files = {'audio_file': f}
            data = {
                'voice_name': voice_name,
                'description': f'Cloned from {os.path.basename(audio_file_path)}'
            }
            
            response = requests.post(f'{base_url}/voices/clone', files=files, data=data)
        
        if response.status_code != 200:
            print(f"❌ Voice cloning failed: {response.status_code}")
            print(f"   Response: {response.text}")
            return
        
        clone_result = response.json()
        print(f"✅ Voice cloned successfully!")
        print(f"   Voice: {clone_result['voice_name']}")
        print(f"   Description: {clone_result['description']}")
        print()
        
        # Step 2: List available voices to confirm
        print("📋 Available voices:")
        voices_response = requests.get(f'{base_url}/voices')
        if voices_response.status_code == 200:
            voices = voices_response.json()
            for voice in voices:
                status = "🔊 (cloned)" if voice.get('is_cloned') else "🎯 (default)"
                print(f"   - {voice['voice_name']} {status}")
        print()
        
        # Step 3: Generate speech with the cloned voice
        print("🗣️  Generating speech with cloned voice...")

        """
        Here are the parameters you can adjust:
        🎛️ Speed Control Parameters
        1. cfg_weight (0.0 to 1.0):
        - Lower values (0.2-0.4): Faster, more natural speech
        - Higher values (0.6-0.8): Slower, more deliberate pace

        2. exaggeration (0.0 to 2.0):
        Higher exaggeration tends to speed up speech
        - Lower values (0.2-0.4): More monotone, potentially slower
        - Higher values (0.7-1.2): More expressive, potentially faster
        """
        
        synthesis_payload = {
            'text': test_text,
            'voice_name': voice_name,
            'cfg_weight': 0.1,
            'exaggeration': 0.2,  # More expressive
            
        }
        
        synthesis_response = requests.post(f'{base_url}/synthesize', json=synthesis_payload)
        
        if synthesis_response.status_code != 200:
            print(f"❌ Synthesis failed: {synthesis_response.status_code}")
            print(f"   Response: {synthesis_response.text}")
            return
        
        synthesis_result = synthesis_response.json()
        audio_file_id = synthesis_result['audio_file_id']
        duration = synthesis_result.get('duration', 0)
        
        print(f"✅ Speech generated successfully!")
        print(f"   Duration: {duration:.2f} seconds")
        print()
        
        # Step 4: Download the generated audio
        print("💾 Downloading cloned voice audio...")
        
        audio_response = requests.get(f'{base_url}/audio/{audio_file_id}')
        
        if audio_response.status_code != 200:
            print(f"❌ Download failed: {audio_response.status_code}")
            return
        
        # Save with descriptive filename
        output_filename = f'cloned_voice_{voice_name.lower().replace(" ", "_")}.wav'
        with open(output_filename, 'wb') as f:
            f.write(audio_response.content)
        
        print(f"✅ Audio saved as: {output_filename}")
        print(f"   File size: {len(audio_response.content):,} bytes")
        print()

        
    except requests.exceptions.ConnectionError:
        print("❌ Could not connect to the TTS API")
        print("   Make sure the server is running at http://localhost:8000")
    except Exception as e:
        print(f"❌ An error occurred: {e}")

if __name__ == "__main__":
    test_voice_cloning()