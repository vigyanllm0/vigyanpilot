/**
 * VigyanLLM Analytics Module
 * Centralized event tracking for GA4 + dataLayer
 */
(function() {
    'use strict';
    
    const VLAnalytics = {
        _initialized: false,
        
        init() {
            if (this._initialized) return;
            this._initialized = true;
            this._setupScrollTracking();
            this._setupTimeTracking();
            this._setupOutboundLinks();
        },
        
        track(event, params = {}) {
            // Push to dataLayer for GTM
            if (window.dataLayer) {
                window.dataLayer.push({ event, ...params });
            }
            // Also push via gtag if available
            if (window.gtag) {
                gtag('event', event, params);
            }
            console.debug('[VL Analytics]', event, params);
        },
        
        trackToolRun(tool, inputSize, durationMs, success = true) {
            this.track('tool_run', {
                tool_name: tool,
                input_size: inputSize,
                duration_ms: durationMs,
                success: success
            });
        },
        
        trackSignup(method = 'email') {
            this.track('sign_up', { method });
        },
        
        trackLogin(method = 'email') {
            this.track('login', { method });
        },
        
        trackPurchase(transactionId, value, plan, currency = 'INR') {
            this.track('purchase', {
                transaction_id: transactionId,
                value: value,
                currency: currency,
                plan_name: plan
            });
        },
        
        trackCTAClick(location, variant, target) {
            this.track('cta_click', {
                cta_location: location,
                cta_variant: variant,
                cta_target: target
            });
        },
        
        trackUpgradePrompt(feature, currentTier, requiredTier) {
            this.track('upgrade_prompt', {
                feature_name: feature,
                current_tier: currentTier,
                required_tier: requiredTier
            });
        },
        
        trackReviewSubmit(rating, hasInstitution) {
            this.track('review_submit', {
                rating: rating,
                has_institution: hasInstitution
            });
        },
        
        trackExport(tool, format) {
            this.track('export_download', { tool_name: tool, format: format });
        },
        
        _setupScrollTracking() {
            const milestones = [25, 50, 75, 100];
            const tracked = new Set();
            const handler = () => {
                const scrollPercent = Math.round(
                    (window.scrollY / (document.body.scrollHeight - window.innerHeight)) * 100
                );
                milestones.forEach(m => {
                    if (scrollPercent >= m && !tracked.has(m)) {
                        tracked.add(m);
                        this.track('scroll_depth', { percent: m });
                    }
                });
            };
            window.addEventListener('scroll', handler, { passive: true, threshold: milestones.map(m => m / 100) });
        },
        
        _setupTimeTracking() {
            const milestones = [30, 60, 120];
            const tracked = new Set();
            milestones.forEach(s => {
                setTimeout(() => {
                    if (!tracked.has(s)) {
                        tracked.add(s);
                        this.track('time_on_page', { seconds: s });
                    }
                }, s * 1000);
            });
        },
        
        _setupOutboundLinks() {
            document.addEventListener('click', (e) => {
                const link = e.target.closest('a[href]');
                if (link && link.hostname !== window.location.hostname) {
                    this.track('outbound_click', {
                        url: link.href,
                        text: link.textContent.trim().substring(0, 50)
                    });
                }
            });
        }
    };
    
    window.VLAnalytics = VLAnalytics;
    document.addEventListener('DOMContentLoaded', () => VLAnalytics.init());
})();
