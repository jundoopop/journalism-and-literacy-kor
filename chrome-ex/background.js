// ============================================
// Background Service Worker (Native Messaging Version)
// Communicates with Python native host via chrome.runtime
// ============================================

// Constants
const CONFIG = {
  HOST_NAME: 'com.highright.analyzer',
  CACHE_DURATION: 60 * 60 * 1000, // 1 hour
  LOG_PREFIX: '[Background]',
  RECONNECT_DELAY: 1000, // 1 second
  MAX_RECONNECT_ATTEMPTS: 3
};

// Global state
let nativePort = null;
let isConnecting = false;
let reconnectAttempts = 0;
let pendingRequests = new Map(); // Track pending requests by ID
let requestIdCounter = 0;

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

/**
 * Generate unique request ID
 * @returns {number} Unique request ID
 */
function generateRequestId() {
  return ++requestIdCounter;
}

// ============================================
// Native Messaging Connection
// ============================================

/**
 * Connect to native messaging host
 * @returns {Port|null} Native messaging port or null if failed
 */
function connectToNativeHost() {
  if (isConnecting) {
    log('Already connecting to native host', 'warn');
    return null;
  }

  if (nativePort) {
    log('Already connected to native host');
    return nativePort;
  }

  try {
    isConnecting = true;
    log(`Connecting to native host: ${CONFIG.HOST_NAME}`);

    nativePort = chrome.runtime.connectNative(CONFIG.HOST_NAME);

    nativePort.onMessage.addListener(handleNativeMessage);
    nativePort.onDisconnect.addListener(handleNativeDisconnect);

    log('✓ Connected to native host');
    reconnectAttempts = 0;
    isConnecting = false;

    return nativePort;
  } catch (error) {
    log(`Failed to connect to native host: ${error.message}`, 'error');
    nativePort = null;
    isConnecting = false;
    return null;
  }
}

/**
 * Handle message from native host
 * @param {Object} message - Message from native host
 */
function handleNativeMessage(message) {
  log(`Received from native host: ${JSON.stringify(message).substring(0, 100)}...`);

  // Find pending request by ID
  const requestId = message.requestId;

  if (requestId && pendingRequests.has(requestId)) {
    const { resolve } = pendingRequests.get(requestId);
    pendingRequests.delete(requestId);
    resolve(message);
  } else {
    log(`Received message with unknown request ID: ${requestId}`, 'warn');
  }
}

/**
 * Handle native host disconnect
 */
function handleNativeDisconnect() {
  const error = chrome.runtime.lastError;

  if (error) {
    log(`Native host disconnected: ${error.message}`, 'error');
  } else {
    log('Native host disconnected normally');
  }

  nativePort = null;
  isConnecting = false;

  // Reject all pending requests
  for (const [requestId, { reject }] of pendingRequests.entries()) {
    reject(new Error('Native host disconnected'));
  }
  pendingRequests.clear();

  // Attempt to reconnect
  if (reconnectAttempts < CONFIG.MAX_RECONNECT_ATTEMPTS) {
    reconnectAttempts++;
    log(`Attempting to reconnect (${reconnectAttempts}/${CONFIG.MAX_RECONNECT_ATTEMPTS})...`);

    setTimeout(() => {
      connectToNativeHost();
    }, CONFIG.RECONNECT_DELAY);
  } else {
    log('Max reconnect attempts reached', 'error');
  }
}

/**
 * Send message to native host
 * @param {Object} message - Message to send
 * @returns {Promise<Object>} Response from native host
 */
function sendToNativeHost(message) {
  return new Promise((resolve, reject) => {
    // Ensure connection
    if (!nativePort) {
      connectToNativeHost();
    }

    if (!nativePort) {
      reject(new Error('Failed to connect to native host. Please run the installer.'));
      return;
    }

    // Add request ID
    const requestId = generateRequestId();
    message.requestId = requestId;

    // Store pending request
    pendingRequests.set(requestId, { resolve, reject });

    // Set timeout
    const timeout = setTimeout(() => {
      if (pendingRequests.has(requestId)) {
        pendingRequests.delete(requestId);
        reject(new Error('Request timeout'));
      }
    }, 60000); // 60 second timeout

    // Clear timeout on resolve/reject
    const originalResolve = resolve;
    const originalReject = reject;

    pendingRequests.set(requestId, {
      resolve: (value) => {
        clearTimeout(timeout);
        originalResolve(value);
      },
      reject: (error) => {
        clearTimeout(timeout);
        originalReject(error);
      }
    });

    // Send message
    try {
      nativePort.postMessage(message);
      log(`Sent to native host: ${message.action}`);
    } catch (error) {
      clearTimeout(timeout);
      pendingRequests.delete(requestId);
      reject(error);
    }
  });
}

// ============================================
// Native Host API
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
 * Get highlight sentences from native host
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

    let response;

    if (settings.mode === 'consensus') {
      // Consensus mode: use multiple providers
      response = await sendToNativeHost({
        action: 'getConsensusHighlights',
        url,
        providers: settings.providers
      });
    } else {
      // Single mode: use original getHighlightSentences
      response = await sendToNativeHost({
        action: 'getHighlightSentences',
        url
      });
    }

    if (response.success) {
      log(`Analysis complete: ${response.count} sentences`);
      return response;
    } else {
      throw new Error(response.error || 'Analysis failed');
    }
  } catch (error) {
    log(`Error: ${error.message}`, 'error');
    return {
      success: false,
      error: error.message
    };
  }
}

/**
 * Check native host health status
 * @returns {Promise<boolean>} True if host is healthy
 */
async function checkNativeHostHealth() {
  try {
    const response = await sendToNativeHost({
      action: 'checkHealth'
    });

    return response.status === 'ok' && response.gemini_ready;
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
  const isHealthy = await checkNativeHostHealth();
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

log('Service Worker loaded successfully');

// Connect to native host on startup
connectToNativeHost();

// Check health after connection
setTimeout(async () => {
  const isHealthy = await checkNativeHostHealth();

  if (isHealthy) {
    log('✓ Native host is healthy and ready');
  } else {
    log('✗ Native host not ready - Please run the installer', 'warn');
  }
}, 1000);
