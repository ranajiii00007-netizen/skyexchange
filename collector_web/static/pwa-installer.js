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
  
  // Always copy to clipboard first
  copyTextToClipboard(url, () => {
    // If native share is supported, try opening it as well
    if (navigator.share) {
      // Small timeout to let the alert close first
      setTimeout(() => {
        navigator.share({
          title: title,
          text: `Install the Sky Exchange ${title} application:`,
          url: url
        }).catch((err) => {
          console.log('Native share cancelled or failed:', err);
        });
      }, 100);
    }
  });
}

function copyTextToClipboard(text, callback) {
  if (navigator.clipboard && navigator.clipboard.writeText) {
    navigator.clipboard.writeText(text)
      .then(() => {
        alert(`Link copied to clipboard!\n\nYou can now paste and share this link via WhatsApp:\n${text}`);
        if (callback) callback();
      })
      .catch(() => {
        fallbackCopyText(text, callback);
      });
  } else {
    fallbackCopyText(text, callback);
  }
}

function fallbackCopyText(text, callback) {
  const textarea = document.createElement('textarea');
  textarea.value = text;
  textarea.style.top = '0';
  textarea.style.left = '0';
  textarea.style.position = 'fixed';
  document.body.appendChild(textarea);
  textarea.focus();
  textarea.select();
  
  let successful = false;
  try {
    successful = document.execCommand('copy');
  } catch (err) {
    successful = false;
  }
  
  document.body.removeChild(textarea);
  
  if (successful) {
    alert(`Link copied to clipboard!\n\nYou can now paste and share this link via WhatsApp:\n${text}`);
    if (callback) callback();
  } else {
    window.prompt("Could not copy automatically. Please copy the link below manually to share:", text);
  }
}
