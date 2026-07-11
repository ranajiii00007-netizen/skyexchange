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

function triggerAndroidInstall() {
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
    alert(
      "To install this app on Android:\n\n" +
      "1. Open this page in Google Chrome.\n" +
      "2. Tap the menu icon (3 dots) in the top-right corner.\n" +
      "3. Select 'Install app' or 'Add to Home screen'."
    );
  }
}

function triggerIosInstall() {
  alert(
    "To install this app on iPhone/iPad (iOS):\n\n" +
    "1. Open this page in Safari.\n" +
    "2. Tap the 'Share' button at the bottom of the screen (square icon with an arrow pointing up).\n" +
    "3. Scroll down and tap 'Add to Home Screen'."
  );
}


