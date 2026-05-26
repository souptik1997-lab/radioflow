self.addEventListener('install', event => {

    event.waitUntil(
        caches.open('rt-cache-v1').then(cache => {

            return cache.addAll([
                '/',
                '/app.js',
                '/styles.css'
            ]);
        })
    );
});
