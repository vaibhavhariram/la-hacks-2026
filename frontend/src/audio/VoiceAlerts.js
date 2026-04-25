const VOICE_ID = 'pNInz6obpgDQGcFmaJgB'; // Adam

// read from URL param ?apikey=XXX for demo convenience
const params = new URLSearchParams(window.location.search);
let ELEVEN_API_KEY = params.get('apikey') ?? '';

export function setApiKey(key) {
  ELEVEN_API_KEY = key;
}

export async function speak(text) {
  console.log('[VoiceAlerts]', text);

  if (!ELEVEN_API_KEY) return;

  try {
    const res = await fetch(`https://api.elevenlabs.io/v1/text-to-speech/${VOICE_ID}`, {
      method: 'POST',
      headers: {
        'xi-api-key': ELEVEN_API_KEY,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        text,
        model_id: 'eleven_monolingual_v1',
        voice_settings: { stability: 0.5, similarity_boost: 0.75 },
      }),
    });

    if (!res.ok) throw new Error(`ElevenLabs HTTP ${res.status}`);

    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const audio = new Audio(url);
    audio.onended = () => URL.revokeObjectURL(url);
    audio.play();
  } catch (e) {
    console.warn('[VoiceAlerts] TTS failed, silent fallback:', e.message);
  }
}
