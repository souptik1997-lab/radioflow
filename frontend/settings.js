async function saveSettings() {

    const payload = {

        SMTP_HOST:
            document.getElementById('smtp-host').value,

        SMTP_USER:
            document.getElementById('smtp-user').value,

        SMTP_PASSWORD:
            document.getElementById('smtp-password').value,

        GOOGLE_DRIVE_CLIENT_ID:
            document.getElementById('google-client').value,

        GOOGLE_DRIVE_CLIENT_SECRET:
            document.getElementById('google-secret').value
    };

    await fetch('/api/settings', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(payload)
    });

    alert('Settings saved securely');
}
