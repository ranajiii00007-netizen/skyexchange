let deferredPrompt = null;

window.addEventListener('beforeinstallprompt', (e) => {
  // Prevent Chrome 67 and earlier from automatically showing the prompt
  e.preventDefault();
  // Stash the event so it can be triggered later.
  deferredPrompt = e;
  
  // Show all install button elements
  const installBtns = document.querySelectorAll('.pwa-install-btn');
  installBtns.forEach(btn => {
    btn.style.display = 'inline-flex';
  });
});

window.addEventListener('appinstalled', (evt) => {
  console.log('PWA was installed');
  const installBtns = document.querySelectorAll('.pwa-install-btn');
  installBtns.forEach(btn => {
    btn.style.display = 'none';
  });
});

function triggerPwaInstall() {
  if (deferredPrompt) {
    deferredPrompt.prompt();
    deferredPrompt.userChoice.then((choiceResult) => {
      if (choiceResult.outcome === 'accepted') {
        console.log('User accepted the install prompt');
      } else {
        console.log('User dismissed the install prompt');
      }
      deferredPrompt = null;
    });
  } else {
    // User-friendly popup explanation when standard programmatic trigger isn't supported (e.g. iOS Safari)
    alert(
      "To download/install this app directly on your device:\n\n" +
      "• Apple iOS (Safari): Tap the 'Share' icon at the bottom of the screen, scroll down, and tap 'Add to Home Screen'.\n\n" +
      "• Android (Chrome): Tap the menu icon (3 dots) in the top-right corner and select 'Install app' or 'Add to Home screen'.\n\n" +
      "• Desktop (Chrome/Edge): Click the install icon inside the browser address bar at the top."
    );
  }
}
