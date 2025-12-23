// ============================================
// Background Service Worker (HTTP Version)
// Communicates with Flask server via HTTP
// ============================================

// Constants
const CONFIG = {
  SERVER_URL: 'http://localhost:5001',
  CACHE_DURATION: 60 * 60 * 1000, // 1 hour
  LOG_PREFIX: '[Background]',
  REQUEST_TIMEOUT: 60000 // 60 seconds
};

// ============================================
// Utility Functions
// ============================================

/**
 * Log message with prefix
 * @param {string} message - Message to log
 * @param {string} level - Log level (log, warn, error)
 */
function log(message, level = 'log') {
  console[level](`${CONFIG.LOG_PREFIX} ${message}`);
}

// ============================================
// HTTP API Communication
// ============================================

/**
 * Get current settings from storage
 * @returns {Promise<Object>} Current settings
 */
async function getSettings() {
  try {
    const result = await chrome.storage.local.get('highlighterSettings');
    return result.highlighterSettings || { mode: 'single', providers: ['gemini'] };
  } catch (error) {
    log(`Failed to get settings: ${error.message}`, 'warn');
    return { mode: 'single', providers: ['gemini'] };
  }
}

/**
 * Fetch highlight sentences from HTTP server
 * Uses single or consensus mode based on settings
 * @param {string} url - Article URL
 * @returns {Promise<Object>} Response with sentences or error
 */
async function fetchHighlightSentences(url) {
  log(`Analysis request: ${url}`);

  try {
    // Get current settings
    const settings = await getSettings();
    log(`Using ${settings.mode} mode with providers: ${settings.providers.join(', ')}`);

    let endpoint, body;

    if (settings.mode === 'consensus') {
      // Consensus mode: use multiple providers
      endpoint = `${CONFIG.SERVER_URL}/analyze_consensus`;
      body = {
        url,
        providers: settings.providers
      };
    } else {
      // Single mode: use original analyze endpoint
      endpoint = `${CONFIG.SERVER_URL}/analyze`;
      body = { url };
    }

    log(`Calling ${endpoint}`);

    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), CONFIG.REQUEST_TIMEOUT);

    const response = await fetch(endpoint, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(body),
      signal: controller.signal
    });

    clearTimeout(timeoutId);

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }

    const result = await response.json();

    if (result.success) {
      log(`Analysis complete: ${result.count} sentences`);
      return result;
    } else {
      throw new Error(result.error || 'Analysis failed');
    }

  } catch (error) {
    if (error.name === 'AbortError') {
      log('Request timeout', 'error');
      return {
        success: false,
        error: 'Request timeout - server took too long to respond'
      };
    }

    log(`Error: ${error.message}`, 'error');
    return {
      success: false,
      error: error.message
    };
  }
}

/**
 * Check server health status
 * @returns {Promise<boolean>} True if server is healthy
 */
async function checkServerHealth() {
  try {
    const response = await fetch(`${CONFIG.SERVER_URL}/health`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      }
    });

    if (!response.ok) {
      return false;
    }

    const result = await response.json();
    return result.status === 'ok' && result.gemini_ready;

  } catch (error) {
    log(`Health check failed: ${error.message}`, 'warn');
    return false;
  }
}

// ============================================
// Cache Management
// ============================================

/**
 * Generate cache key from URL and settings
 * @param {string} url - Article URL
 * @param {Object} settings - Current settings
 * @returns {string} Cache key
 */
function getCacheKey(url, settings) {
  const providersKey = settings.providers.sort().join('_');
  return `cache_${settings.mode}_${providersKey}_${url}`;
}

/**
 * Check if cached data is still valid
 * @param {number} timestamp - Cache timestamp
 * @returns {boolean} True if cache is still valid
 */
function isCacheValid(timestamp) {
  return (Date.now() - timestamp) < CONFIG.CACHE_DURATION;
}

/**
 * Get cached result for URL with current settings
 * @param {string} url - Article URL
 * @param {Object} settings - Current settings
 * @returns {Promise<Object|null>} Cached data or null if not found/expired
 */
async function getCachedResult(url, settings) {
  try {
    const cacheKey = getCacheKey(url, settings);
    const result = await chrome.storage.local.get(cacheKey);

    if (result[cacheKey]) {
      const cached = result[cacheKey];

      if (isCacheValid(cached.timestamp)) {
        log(`Cache hit: ${url}`);
        return cached.data;
      } else {
        // Remove expired cache
        await chrome.storage.local.remove(cacheKey);
        log(`Cache expired: ${url}`, 'warn');
      }
    }

    return null;

  } catch (error) {
    log(`Cache retrieval error: ${error.message}`, 'error');
    return null;
  }
}

/**
 * Save result to cache with current settings
 * @param {string} url - Article URL
 * @param {Object} data - Data to cache
 * @param {Object} settings - Current settings
 */
async function setCachedResult(url, data, settings) {
  try {
    const cacheKey = getCacheKey(url, settings);
    const cacheEntry = {
      timestamp: Date.now(),
      data
    };

    await chrome.storage.local.set({ [cacheKey]: cacheEntry });
    log(`Cache saved: ${url}`);

  } catch (error) {
    log(`Cache save error: ${error.message}`, 'error');
  }
}

/**
 * Clear all cache entries
 */
async function clearAllCache() {
  try {
    await chrome.storage.local.clear();
    log('All cache cleared');
  } catch (error) {
    log(`Cache clear error: ${error.message}`, 'error');
  }
}

// ============================================
// Message Handlers
// ============================================

/**
 * Handle 'getHighlightSentences' action
 * @param {string} url - Article URL
 * @param {Function} sendResponse - Response callback
 */
async function handleGetHighlightSentences(url, sendResponse) {
  try {
    log(`Request for: ${url}`);

    // Get current settings
    const settings = await getSettings();

    // Step 1: Check cache
    const cached = await getCachedResult(url, settings);
    if (cached) {
      sendResponse(cached);
      return;
    }

    // Step 2: Fetch from server (will use consensus mode if enabled)
    const result = await fetchHighlightSentences(url);

    // Step 3: Save to cache if successful
    if (result.success) {
      await setCachedResult(url, result, settings);
    }

    sendResponse(result);

  } catch (error) {
    log(`Processing error: ${error.message}`, 'error');
    sendResponse({
      success: false,
      error: error.message
    });
  }
}

/**
 * Handle 'checkServer' action
 * @param {Function} sendResponse - Response callback
 */
async function handleCheckServer(sendResponse) {
  const isHealthy = await checkServerHealth();
  sendResponse({ healthy: isHealthy });
}

/**
 * Handle 'clearCache' action
 * @param {Function} sendResponse - Response callback
 */
async function handleClearCache(sendResponse) {
  await clearAllCache();
  sendResponse({ success: true });
}

// ============================================
// Message Listener
// ============================================

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  log(`Message received: ${message.action}`);

  const { action, url } = message;

  switch (action) {
    case 'getHighlightSentences':
      handleGetHighlightSentences(url, sendResponse);
      return true; // Keep message channel open for async response

    case 'checkServer':
      handleCheckServer(sendResponse);
      return true;

    case 'clearCache':
      handleClearCache(sendResponse);
      return true;

    default:
      log(`Unknown action: ${action}`, 'warn');
      sendResponse({
        success: false,
        error: `Unknown action: ${action}`
      });
      return false;
  }
});

// ============================================
// Initialization
// ============================================

log('Service Worker loaded successfully (HTTP mode)');

// Check server health after startup
setTimeout(async () => {
  const isHealthy = await checkServerHealth();

  if (isHealthy) {
    log('✓ Flask server is healthy and ready');
  } else {
    log('✗ Flask server not ready - Please start the server on port 5001', 'warn');
  }
}, 1000);
