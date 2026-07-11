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
  
  // Create off-screen textarea for synchronous copy (essential for iOS/Android click handler context)
  const textarea = document.createElement('textarea');
  textarea.value = url;
  textarea.style.position = 'fixed';
  textarea.style.left = '-9999px';
  textarea.style.top = '0';
  textarea.setAttribute('readonly', ''); // Prevent keyboard popup on iOS
  document.body.appendChild(textarea);
  
  // Select text
  textarea.focus();
  textarea.select();
  textarea.setSelectionRange(0, 99999); // For iOS selection compatibility
  
  let copied = false;
  try {
    copied = document.execCommand('copy');
  } catch (err) {
    copied = false;
  }
  
  document.body.removeChild(textarea);
  
  if (copied) {
    alert(`Link copied to clipboard!\n\nYou can now paste and share this link via WhatsApp:\n${url}`);
    triggerNativeShare(title, url);
  } else {
    // Async fallback if execCommand fails
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(url)
        .then(() => {
          alert(`Link copied to clipboard!\n\nYou can now paste and share this link via WhatsApp:\n${url}`);
          triggerNativeShare(title, url);
        })
        .catch(() => {
          window.prompt("Could not copy automatically. Please copy the link below manually to share:", url);
        });
    } else {
      window.prompt("Could not copy automatically. Please copy the link below manually to share:", url);
    }
  }
}

function triggerNativeShare(title, url) {
  if (navigator.share) {
    // Small timeout to allow the alert dialog to close first
    setTimeout(() => {
      navigator.share({
        title: title,
        text: `Install the Sky Exchange ${title} application:`,
        url: url
      }).catch((err) => {
        console.log('Native share cancelled or failed:', err);
      });
    }, 200);
  }
}
