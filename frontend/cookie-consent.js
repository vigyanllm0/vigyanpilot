/**
 * VigyanLLM DPDP Cookie Consent Banner
 * ====================================
 * DPDP Act 2023 compliance requires explicit consent before tracking scripts
 * (e.g., Google Tag Manager, Analytics) can be executed.
 *
 * This script injects a banner, handles user consent (Accept/Reject),
 * stores the preference in localStorage, and only loads tracking scripts
 * if consent is explicitly granted.
 */

(function () {
    const CONSENT_KEY = 'vigyanllm_cookie_consent';
    const GTM_ID = ''; // Set to your GTM container ID (e.g., 'GTM-ABC123') when using Google Tag Manager

    function loadGTM() {
        if (!GTM_ID) return;
        if (window.gtmLoaded) return;
        window.gtmLoaded = true;

        (function(w,d,s,l,i){w[l]=w[l]||[];w[l].push({'gtm.start':
        new Date().getTime(),event:'gtm.js'});var f=d.getElementsByTagName(s)[0],
        j=d.createElement(s),dl=l!='dataLayer'?'&l='+l:'';j.async=true;j.src=
        'https://www.googletagmanager.com/gtm.js?id='+i+dl;f.parentNode.insertBefore(j,f);
        })(window,document,'script','dataLayer',GTM_ID);
    }

    function removeBanner() {
        const banner = document.getElementById('dpdp-cookie-banner');
        if (banner) {
            banner.remove();
        }
    }

    function showBanner() {
        const bannerHTML = `
            <div id="dpdp-cookie-banner" style="position: fixed; bottom: 0; left: 0; right: 0; background: #1f2937; color: #fff; padding: 1rem; z-index: 9999; display: flex; flex-direction: column; md:flex-row; justify-content: space-between; align-items: center; box-shadow: 0 -4px 6px -1px rgba(0, 0, 0, 0.1); font-family: sans-serif;">
                <div style="flex: 1; margin-bottom: 1rem; md:margin-bottom: 0;">
                    <p style="margin: 0; font-size: 0.875rem;">
                        We use cookies to improve your experience and analyze traffic.
                        By clicking "Accept", you consent to our use of cookies per the DPDP Act 2023.
                        <a href="/privacy.html" style="color: #60a5fa; text-decoration: underline;">Read our Privacy Policy</a>.
                    </p>
                </div>
                <div style="display: flex; gap: 0.5rem;">
                    <button id="btn-reject-cookies" style="background: transparent; color: #9ca3af; border: 1px solid #4b5563; padding: 0.5rem 1rem; border-radius: 0.25rem; cursor: pointer; font-size: 0.875rem; transition: background 0.2s;">Reject All</button>
                    <button id="btn-accept-cookies" style="background: #3b82f6; color: #fff; border: none; padding: 0.5rem 1rem; border-radius: 0.25rem; cursor: pointer; font-size: 0.875rem; transition: background 0.2s;">Accept All</button>
                </div>
            </div>
        `;
        document.body.insertAdjacentHTML('beforeend', bannerHTML);

        document.getElementById('btn-accept-cookies').addEventListener('click', function () {
            localStorage.setItem(CONSENT_KEY, 'accepted');
            loadGTM();
            removeBanner();
            syncConsentWithBackend(true);
        });

        document.getElementById('btn-reject-cookies').addEventListener('click', function () {
            localStorage.setItem(CONSENT_KEY, 'rejected');
            removeBanner();
            syncConsentWithBackend(false);
        });
    }

    function syncConsentWithBackend(accepted) {
        const token = localStorage.getItem('pf_token') || getCookie('pf_token');
        if (!token) return;

        fetch('/api/consent/record', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': 'Bearer ' + token
            },
            body: JSON.stringify({
                consent_type: 'cookies',
                accepted: accepted
            })
        }).catch(err => console.error('Failed to sync consent:', err));
    }

    function getCookie(name) {
        const value = `; ${document.cookie}`;
        const parts = value.split(`; ${name}=`);
        if (parts.length === 2) return parts.pop().split(';').shift();
        return null;
    }

    // Main execution
    const consent = localStorage.getItem(CONSENT_KEY);
    if (consent === 'accepted') {
        loadGTM();
    } else if (consent !== 'rejected') {
        // Delay showing banner slightly so it doesn't block initial render
        setTimeout(showBanner, 1000);
    }
})();
