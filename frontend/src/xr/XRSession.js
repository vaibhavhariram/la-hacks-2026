export async function initXR(renderer) {
  const btn = document.getElementById('enter-vr-btn');
  if (!btn) return;

  if (!navigator.xr) {
    btn.textContent = 'WebXR not supported — open on Quest 2 browser';
    btn.disabled = true;
    return;
  }

  const supported = await navigator.xr.isSessionSupported('immersive-vr').catch(() => false);
  if (!supported) {
    btn.textContent = 'WebXR not supported — open on Quest 2 browser';
    btn.disabled = true;
    return;
  }

  renderer.xr.enabled = true;

  btn.addEventListener('click', async () => {
    try {
      const session = await navigator.xr.requestSession('immersive-vr', {
        requiredFeatures: ['local-floor'],
        optionalFeatures: ['hand-tracking'],
      });
      renderer.xr.setSession(session);
      btn.style.display = 'none';
    } catch (e) {
      console.error('[XRSession] Failed to start session:', e);
    }
  });
}
