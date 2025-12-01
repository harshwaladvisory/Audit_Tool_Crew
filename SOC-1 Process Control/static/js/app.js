/**
 * SOC-1 Dashboard - Interactions & Animations
 * Handles UI enhancements, animations, and accessibility
 */

(function() {
  'use strict';

  // Check for reduced motion preference
  const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  /**
   * Initialize all functionality when DOM is ready
   */
  function init() {
    setupIntersectionObserver();
    setupScrollBehavior();
    setupFABInteraction();
    setupAccessibility();
    setupCardAnimations();
    setupResponsiveBehavior();
    setupErrorHandling();
    setupTooltips();
    checkBrowserSupport();
  }

  /**
   * Intersection Observer for fade-in animations on scroll
   */
  function setupIntersectionObserver() {
    if (prefersReducedMotion) return;

    const observerOptions = {
      root: null,
      rootMargin: '0px',
      threshold: 0.1
    };

    const observer = new IntersectionObserver((entries) => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          entry.target.style.opacity = '1';
          entry.target.style.transform = 'translateY(0)';
          observer.unobserve(entry.target);
        }
      });
    }, observerOptions);

    // Observe cards for fade-in effect
    const cardsToObserve = document.querySelectorAll('.card--large, .kpi-grid');
    cardsToObserve.forEach(card => {
      if (!prefersReducedMotion) {
        card.style.opacity = '0';
        card.style.transform = 'translateY(20px)';
        card.style.transition = 'opacity 0.6s ease-out, transform 0.6s ease-out';
      }
      observer.observe(card);
    });
  }

  /**
   * Setup smooth scroll behavior
   */
  function setupScrollBehavior() {
    // Handle all internal anchor links
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
      anchor.addEventListener('click', function(e) {
        const href = this.getAttribute('href');
        if (href === '#') return;
        
        const targetElement = document.querySelector(href);
        if (targetElement) {
          e.preventDefault();
          const yOffset = -100;
          const y = targetElement.getBoundingClientRect().top + window.pageYOffset + yOffset;
          
          window.scrollTo({
            top: y,
            behavior: prefersReducedMotion ? 'auto' : 'smooth'
          });
        }
      });
    });
  }

  /**
   * Setup Floating Action Button interactions
   */
  function setupFABInteraction() {
    const fab = document.querySelector('.fab');
    if (!fab) return;

    // Add ripple effect on click
    fab.addEventListener('click', function(e) {
      if (prefersReducedMotion) return;

      const ripple = document.createElement('span');
      const diameter = Math.max(this.clientWidth, this.clientHeight);
      const radius = diameter / 2;

      ripple.style.width = ripple.style.height = `${diameter}px`;
      ripple.style.left = `${e.clientX - this.offsetLeft - radius}px`;
      ripple.style.top = `${e.clientY - this.offsetTop - radius}px`;
      ripple.style.position = 'absolute';
      ripple.style.borderRadius = '50%';
      ripple.style.background = 'rgba(255, 255, 255, 0.6)';
      ripple.style.transform = 'scale(0)';
      ripple.style.animation = 'ripple 600ms ease-out';
      ripple.style.pointerEvents = 'none';

      this.appendChild(ripple);

      setTimeout(() => ripple.remove(), 600);
    });

    // Add CSS for ripple animation if not already present
    if (!document.getElementById('ripple-animation')) {
      const style = document.createElement('style');
      style.id = 'ripple-animation';
      style.textContent = `
        @keyframes ripple {
          to {
            transform: scale(4);
            opacity: 0;
          }
        }
      `;
      document.head.appendChild(style);
    }
  }

  /**
   * Setup accessibility enhancements
   */
  function setupAccessibility() {
    // Add keyboard navigation for custom interactive elements
    const interactiveElements = document.querySelectorAll('.drop-area, .file-item');
    
    interactiveElements.forEach(element => {
      if (!element.hasAttribute('tabindex')) {
        element.setAttribute('tabindex', '0');
      }
      
      element.addEventListener('keydown', function(e) {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          this.click();
        }
      });
    });

    // Announce dynamic content changes to screen readers
    setupAriaLiveRegions();
  }

  /**
   * Setup ARIA live regions for dynamic content
   */
  function setupAriaLiveRegions() {
    const alerts = document.querySelectorAll('.alert');
    alerts.forEach(alert => {
      alert.setAttribute('role', 'alert');
      alert.setAttribute('aria-live', 'polite');
    });
  }

  /**
   * Handle card hover animations
   */
  function setupCardAnimations() {
    if (prefersReducedMotion) return;

    const cards = document.querySelectorAll('.card:not(.card--kpi)');
    
    cards.forEach(card => {
      card.addEventListener('mouseenter', function() {
        this.style.transform = 'translateY(-2px)';
      });
      
      card.addEventListener('mouseleave', function() {
        this.style.transform = 'translateY(0)';
      });
    });
  }

  /**
   * Handle responsive behavior
   */
  function setupResponsiveBehavior() {
    let resizeTimer;
    
    window.addEventListener('resize', () => {
      clearTimeout(resizeTimer);
      resizeTimer = setTimeout(() => {
        handleResponsiveLayout();
      }, 250);
    });
    
    // Initial check
    handleResponsiveLayout();
  }

  /**
   * Handle layout adjustments based on viewport size
   */
  function handleResponsiveLayout() {
    const width = window.innerWidth;
    
    // Add mobile class for specific styling if needed
    if (width <= 768) {
      document.body.classList.add('mobile-view');
    } else {
      document.body.classList.remove('mobile-view');
    }
  }

  /**
   * Setup error handling
   */
  function setupErrorHandling() {
    window.addEventListener('error', (event) => {
      console.error('Global error:', event.error);
    });

    window.addEventListener('unhandledrejection', (event) => {
      console.error('Unhandled promise rejection:', event.reason);
    });
  }

  /**
   * Initialize tooltips if needed
   */
  function setupTooltips() {
    const elementsWithTitle = document.querySelectorAll('[title]');
    
    elementsWithTitle.forEach(element => {
      element.addEventListener('mouseenter', function() {
        const title = this.getAttribute('title');
        if (!title) return;
        
        // Store original title
        this.setAttribute('data-original-title', title);
        this.removeAttribute('title');
        
        // Create tooltip
        const tooltip = document.createElement('div');
        tooltip.className = 'custom-tooltip';
        tooltip.textContent = title;
        tooltip.style.cssText = `
          position: absolute;
          background: var(--color-text);
          color: white;
          padding: 8px 12px;
          border-radius: 8px;
          font-size: 12px;
          pointer-events: none;
          z-index: 10000;
          white-space: nowrap;
        `;
        
        document.body.appendChild(tooltip);
        
        const rect = this.getBoundingClientRect();
        tooltip.style.top = `${rect.top - tooltip.offsetHeight - 8}px`;
        tooltip.style.left = `${rect.left + (rect.width - tooltip.offsetWidth) / 2}px`;
        
        this.addEventListener('mouseleave', function removeTooltip() {
          tooltip.remove();
          this.setAttribute('title', this.getAttribute('data-original-title'));
          this.removeAttribute('data-original-title');
          this.removeEventListener('mouseleave', removeTooltip);
        });
      });
    });
  }

  /**
   * Check browser support and show warnings if needed
   */
  function checkBrowserSupport() {
    const features = {
      intersectionObserver: 'IntersectionObserver' in window,
      css_grid: CSS.supports('display', 'grid'),
      css_custom_properties: CSS.supports('--test', 'value')
    };

    const unsupported = Object.entries(features)
      .filter(([_, supported]) => !supported)
      .map(([feature]) => feature);

    if (unsupported.length > 0) {
      console.warn('Unsupported features:', unsupported);
    }
  }

  /**
   * Performance monitoring (development only)
   */
  function logPerformanceMetrics() {
    if (window.performance && window.performance.timing) {
      window.addEventListener('load', () => {
        setTimeout(() => {
          const perfData = window.performance.timing;
          const pageLoadTime = perfData.loadEventEnd - perfData.navigationStart;
          const connectTime = perfData.responseEnd - perfData.requestStart;
          
          console.log('Performance Metrics:', {
            pageLoadTime: `${pageLoadTime}ms`,
            connectTime: `${connectTime}ms`,
            domReady: `${perfData.domContentLoadedEventEnd - perfData.navigationStart}ms`
          });
        }, 0);
      });
    }
  }

  // Initialize everything when DOM is ready
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

  // Development mode performance logging
  if (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1') {
    logPerformanceMetrics();
    
    // Expose utilities for debugging
    window.dashboardDebug = {
      prefersReducedMotion,
      version: '1.0.0',
      reinitialize: init
    };
  }

})();