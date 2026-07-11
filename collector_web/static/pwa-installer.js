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

function shareAppLink(title, path) {
  const url = window.location.origin + path;
  if (navigator.share) {
    navigator.share({
      title: title,
      text: `Install the Sky Exchange ${title} application:`,
      url: url
    })
    .catch((error) => console.log('Error sharing', error));
  } else {
    // Fallback: Clipboard copy
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(url)
        .then(() => alert(`Link copied to clipboard!\n\nYou can now paste and share this link via WhatsApp or other apps:\n${url}`))
        .catch(() => fallbackCopy(url));
    } else {
      fallbackCopy(url);
    }
  }
}

function fallbackCopy(text) {
  const input = document.createElement('input');
  input.value = text;
  document.body.appendChild(input);
  input.select();
  try {
    document.execCommand('copy');
    alert(`Link copied to clipboard!\n\nYou can now paste and share this link via WhatsApp:\n${text}`);
  } catch (err) {
    alert(`Copy this link to share:\n${text}`);
  }
  document.body.removeChild(input);
}
