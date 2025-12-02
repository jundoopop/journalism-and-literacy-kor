// ============================================
// Article Sentence Highlighter - Content Script
// Automatically highlights literacy-enhancing sentences in articles
// ============================================

// Constants
const CONFIG = {
  // Consensus-based color scheme
  COLORS: {
    high: { bg: "#00ff00", opacity: 0.6 },    // Green - all models agree
    medium: { bg: "#ffff00", opacity: 0.5 },  // Yellow - 2 models
    low: { bg: "#87ceeb", opacity: 0.4 }      // Sky blue - 1 model
  },
  HIGHLIGHT_PADDING: "2px 0",
  AUTO_TRIGGER_DELAY: 300, // milliseconds
  EXCLUDED_TAGS: ['script', 'style', 'noscript', 'mark'],
  LOG_PREFIX: '[Highlighter]',
  DATA_ATTRIBUTE: 'data-highlighter'
};

// State management
const state = {
  highlightTargets: [],      // Array of strings (legacy) or objects (consensus)
  isConsensusMode: false,     // Whether using consensus data
  isActivated: false,
  isLoading: false,
  highlightedNodes: []
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

/**
 * Normalize text (remove extra whitespace)
 * @param {string} text - Text to normalize
 * @returns {string} Normalized text
 */
function normalizeText(text) {
  return text.replace(/\s+/g, ' ').trim();
}

// ============================================
// DOM Collection
// ============================================

/**
 * Check if node should be excluded from highlighting
 * @param {Node} node - Text node to check
 * @returns {boolean} True if node should be excluded
 */
function shouldExcludeNode(node) {
  if (!node.textContent.trim()) {
    return true;
  }

  const parent = node.parentElement;
  if (!parent) {
    return true;
  }

  const tagName = parent.tagName.toLowerCase();
  return CONFIG.EXCLUDED_TAGS.includes(tagName);
}

/**
 * Collect all text nodes in the document
 * @param {Element} root - Root element to search from
 * @returns {Array<Node>} Array of text nodes
 */
function collectTextNodes(root) {
  const textNodes = [];
  const walker = document.createTreeWalker(
    root,
    NodeFilter.SHOW_TEXT,
    {
      acceptNode(node) {
        return shouldExcludeNode(node)
          ? NodeFilter.FILTER_REJECT
          : NodeFilter.FILTER_ACCEPT;
      }
    }
  );

  let node;
  while (node = walker.nextNode()) {
    textNodes.push(node);
  }

  return textNodes;
}

// ============================================
// Highlight Matching
// ============================================

/**
 * Find matching targets in text
 * Supports both legacy (string array) and consensus (object array) modes
 * @param {string} text - Text to search in
 * @param {string} normalizedText - Normalized version of text
 * @returns {Array} Array of matches with metadata
 */
function findMatches(text, normalizedText) {
  const matchingTargets = [];

  for (const target of state.highlightTargets) {
    let sentenceText, metadata;

    if (typeof target === 'string') {
      // Legacy mode: simple string array
      sentenceText = target;
      metadata = { consensus_level: 'medium' }; // Default yellow
    } else {
      // Consensus mode: object with metadata
      sentenceText = target.text;
      metadata = {
        consensus_level: target.consensus_level || 'medium',
        consensus_score: target.consensus_score,
        selected_by: target.selected_by || [],
        reasons: target.reasons || {}
      };
    }

    const normalizedTarget = normalizeText(sentenceText);
    const index = normalizedText.indexOf(normalizedTarget);

    if (index !== -1) {
      matchingTargets.push({
        target: sentenceText,
        normalizedTarget,
        startIndex: index,
        endIndex: index + normalizedTarget.length,
        metadata
      });
    }
  }

  // Sort by start index
  matchingTargets.sort((a, b) => a.startIndex - b.startIndex);

  // Find actual positions in original text
  const matches = [];
  for (const match of matchingTargets) {
    const actualIndex = text.indexOf(match.target);
    if (actualIndex !== -1) {
      matches.push({
        text: match.target,
        startIndex: actualIndex,
        endIndex: actualIndex + match.target.length,
        metadata: match.metadata
      });
    }
  }

  return matches;
}

/**
 * Create highlight mark element with consensus-based styling
 * @param {string} text - Text to highlight
 * @param {Object} metadata - Consensus metadata (consensus_level, selected_by, reasons)
 * @returns {HTMLElement} Mark element
 */
function createHighlightMark(text, metadata) {
  const mark = document.createElement('mark');

  // Apply consensus-based color
  const consensusLevel = metadata.consensus_level || 'medium';
  const colors = CONFIG.COLORS[consensusLevel];

  mark.style.backgroundColor = colors.bg;
  mark.style.opacity = colors.opacity;
  mark.style.padding = CONFIG.HIGHLIGHT_PADDING;
  mark.style.cursor = 'help'; // Show help cursor on hover
  mark.setAttribute(CONFIG.DATA_ATTRIBUTE, 'active');
  mark.setAttribute('data-consensus-level', consensusLevel);

  // Build tooltip text
  let tooltipText = '';

  if (metadata.consensus_score) {
    tooltipText += `합의 점수: ${metadata.consensus_score}\n`;
    tooltipText += `선택한 모델: ${metadata.selected_by.join(', ')}\n\n`;

    // Add reasons from each model
    if (metadata.reasons && Object.keys(metadata.reasons).length > 0) {
      tooltipText += '선택 이유:\n';
      for (const [provider, reason] of Object.entries(metadata.reasons)) {
        tooltipText += `• ${provider}: ${reason}\n`;
      }
    }
  } else {
    // Legacy mode (single LLM)
    tooltipText = '문해력 향상에 도움이 되는 문장';
  }

  mark.title = tooltipText.trim();
  mark.textContent = text;

  return mark;
}

/**
 * Highlight matches in a text node
 * @param {Node} textNode - Text node to process
 * @param {Array} matches - Array of match objects with metadata
 */
function applyHighlightsToNode(textNode, matches) {
  const text = textNode.textContent;
  const fragment = document.createDocumentFragment();
  let lastIndex = 0;

  matches.forEach(match => {
    // Add text before match
    if (match.startIndex > lastIndex) {
      const before = text.substring(lastIndex, match.startIndex);
      fragment.appendChild(document.createTextNode(before));
    }

    // Add highlighted text with metadata
    const mark = createHighlightMark(match.text, match.metadata);
    fragment.appendChild(mark);
    state.highlightedNodes.push(mark);

    lastIndex = match.endIndex;
  });

  // Add remaining text
  if (lastIndex < text.length) {
    fragment.appendChild(document.createTextNode(text.substring(lastIndex)));
  }

  // Replace original node
  textNode.parentNode.replaceChild(fragment, textNode);
}

/**
 * Highlight text node if it contains target sentences
 * @param {Node} textNode - Text node to process
 */
function highlightTextNode(textNode) {
  const text = textNode.textContent;
  const normalizedText = normalizeText(text);

  const matches = findMatches(text, normalizedText);

  if (matches.length > 0) {
    applyHighlightsToNode(textNode, matches);
  }
}

// ============================================
// Main Highlighting Logic
// ============================================

/**
 * Execute highlighting on all text nodes
 */
function executeHighlighting() {
  if (state.isActivated) {
    log('Already activated');
    return;
  }

  if (state.highlightTargets.length === 0) {
    log('No highlight targets loaded', 'warn');
    return;
  }

  log(`Starting highlighting with ${state.highlightTargets.length} targets`);
  const startTime = performance.now();

  // Collect text nodes
  const textNodes = collectTextNodes(document.body);
  log(`Found ${textNodes.length} text nodes`);

  // Apply highlights
  textNodes.forEach(node => highlightTextNode(node));

  const duration = (performance.now() - startTime).toFixed(2);
  log(`Highlighting complete! (${duration}ms)`);
  log(`Highlighted ${state.highlightedNodes.length} sentences`);

  state.isActivated = true;
}

/**
 * Remove all highlights from the page
 */
function removeAllHighlights() {
  log('Removing highlights...');

  state.highlightedNodes.forEach(mark => {
    if (mark.parentNode) {
      const text = mark.textContent;
      const textNode = document.createTextNode(text);
      mark.parentNode.replaceChild(textNode, mark);
    }
  });

  state.highlightedNodes = [];
  state.isActivated = false;

  log('Highlights removed');
}

// ============================================
// API Communication
// ============================================

/**
 * Load highlight sentences from background script
 * @returns {Promise<Object>} Response from background script
 */
async function loadHighlightSentences() {
  const response = await chrome.runtime.sendMessage({
    action: 'getHighlightSentences',
    url: window.location.href
  });

  if (!response) {
    throw new Error('No response from background script');
  }

  return response;
}

/**
 * Auto-load highlight sentences and execute highlighting
 */
async function autoLoadAndHighlight() {
  if (state.isActivated || state.isLoading) {
    log('Already activated or loading');
    return;
  }

  state.isLoading = true;
  log('Auto-loading started...');

  try {
    const response = await loadHighlightSentences();

    if (response.success) {
      log(`Sentences loaded: ${response.count} items`);
      state.highlightTargets = response.sentences;
      executeHighlighting();
    } else {
      log(`Loading failed: ${response.error}`, 'error');
    }

  } catch (error) {
    log(`Error: ${error.message}`, 'error');

  } finally {
    state.isLoading = false;
  }
}

// ============================================
// Message Handlers
// ============================================

/**
 * Handle 'activate' message
 * @param {Function} sendResponse - Response callback
 */
async function handleActivate(sendResponse) {
  if (state.highlightTargets.length === 0) {
    // Load first if not loaded yet
    await autoLoadAndHighlight();
  } else {
    executeHighlighting();
  }

  sendResponse({
    success: true,
    count: state.highlightedNodes.length
  });
}

/**
 * Handle 'deactivate' message
 * @param {Function} sendResponse - Response callback
 */
function handleDeactivate(sendResponse) {
  removeAllHighlights();
  sendResponse({ success: true });
}

/**
 * Handle 'reload' message (force re-analysis)
 * @param {Function} sendResponse - Response callback
 */
async function handleReload(sendResponse) {
  removeAllHighlights();
  state.highlightTargets = [];
  await autoLoadAndHighlight();

  sendResponse({
    success: true,
    count: state.highlightedNodes.length
  });
}

// ============================================
// Message Listener
// ============================================

chrome.runtime.onMessage.addListener((message, _sender, sendResponse) => {
  log(`Message received: ${message.action}`);

  const { action } = message;

  switch (action) {
    case 'activate':
      handleActivate(sendResponse);
      return true; // Keep channel open for async response

    case 'deactivate':
      handleDeactivate(sendResponse);
      return false;

    case 'reload':
      handleReload(sendResponse);
      return true; // Keep channel open for async response

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

log('Content script loaded');

// Auto-trigger after delay
setTimeout(() => {
  log('Auto-trigger timer started');
  autoLoadAndHighlight();
}, CONFIG.AUTO_TRIGGER_DELAY);
