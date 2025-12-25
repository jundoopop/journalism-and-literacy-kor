// ============================================
// Article Sentence Highlighter - Content Script
// Automatically highlights literacy-enhancing sentences in articles
// ============================================

// Constants
const CONFIG = {
  // Consensus-based color scheme
  COLORS: {
    high: { bg: "#00ff00", opacity: 0.6, text: "#111" },    // Green - all models agree
    medium: { bg: "#ffff00", opacity: 0.5, text: "#111" },  // Yellow - 2 models
    low: { bg: "#87ceeb", opacity: 0.4, text: "#111" }      // Sky blue - 1 model
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
// Custom Tooltip Manager
// ============================================

/**
 * Custom Tooltip Manager
 * Single-instance tooltip for all highlights
 */
class TooltipManager {
  constructor() {
    this.tooltipElement = null;
    this.currentTarget = null;
    this.hideTimeout = null;
  }

  createTooltipElement() {
    const tooltip = document.createElement('div');
    tooltip.id = 'highlighter-custom-tooltip';

    // Inline styles to avoid page CSS conflicts
    tooltip.style.cssText = `
      position: absolute;
      z-index: 999999;
      background: white;
      border-radius: 8px;
      box-shadow: 0 4px 12px rgba(0,0,0,0.15);
      padding: 12px 16px;
      max-width: 350px;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      font-size: 13px;
      line-height: 1.5;
      color: #333;
      pointer-events: none;
      opacity: 0;
      transition: opacity 0.2s ease;
      border: 2px solid #667eea;
    `;

    document.body.appendChild(tooltip);
    this.tooltipElement = tooltip;
  }

  show(targetElement, metadata) {
    if (!this.tooltipElement) this.createTooltipElement();

    // Cancel pending hide
    if (this.hideTimeout) {
      clearTimeout(this.hideTimeout);
      this.hideTimeout = null;
    }

    const content = this.buildTooltipContent(metadata);
    this.tooltipElement.innerHTML = content;
    this.positionTooltip(targetElement);
    this.tooltipElement.style.opacity = '1';
    this.currentTarget = targetElement;
  }

  hide() {
    // Delay hide to prevent flickering
    this.hideTimeout = setTimeout(() => {
      if (this.tooltipElement) {
        this.tooltipElement.style.opacity = '0';
      }
      this.currentTarget = null;
    }, 100);
  }

  buildTooltipContent(metadata) {
    const levelColors = {
      high: '#4CAF50',
      medium: '#FFC107',
      low: '#2196F3'
    };

    const levelLabels = {
      high: '높은 합의',
      medium: '중간 합의',
      low: '낮은 합의'
    };

    const providerIcons = {
      gemini: '🔷',
      openai: '🟢',
      claude: '🟣',
      mistral: '🔶'
    };

    const consensusLevel = metadata.consensus_level || 'medium';
    const color = levelColors[consensusLevel];
    const label = levelLabels[consensusLevel];

    let html = '';

    if (metadata.consensus_score) {
      // Consensus mode: Show full details
      html += `
        <div style="display: flex; align-items: center; margin-bottom: 10px; padding-bottom: 8px; border-bottom: 1px solid #eee;">
          <div style="background: ${color}; color: white; padding: 4px 10px; border-radius: 4px; font-weight: 600; font-size: 11px; margin-right: 8px;">
            ${label}
          </div>
          <div style="font-size: 12px; color: #666;">
            ${metadata.consensus_score}개 모델 선택
          </div>
        </div>
      `;

      // LLM providers
      html += '<div style="margin-bottom: 10px;">';
      html += '<div style="font-weight: 600; font-size: 11px; color: #888; margin-bottom: 6px;">선택한 LLM</div>';

      metadata.selected_by.forEach(provider => {
        const icon = providerIcons[provider] || '🤖';
        html += `
          <span style="display: inline-block; background: #f5f5f5; padding: 3px 8px; border-radius: 3px; margin-right: 4px; font-size: 11px;">
            ${icon} ${provider}
          </span>
        `;
      });
      html += '</div>';

      // Reasons
      if (metadata.reasons && Object.keys(metadata.reasons).length > 0) {
        html += '<div>';
        html += '<div style="font-weight: 600; font-size: 11px; color: #888; margin-bottom: 6px;">선택 이유</div>';

        for (const [provider, reason] of Object.entries(metadata.reasons)) {
          const icon = providerIcons[provider] || '🤖';
          html += `
            <div style="margin-bottom: 8px; padding: 8px; background: #f9f9f9; border-radius: 4px; border-left: 3px solid ${color};">
              <div style="font-weight: 600; font-size: 11px; color: #667eea; margin-bottom: 4px;">
                ${icon} ${provider.toUpperCase()}
              </div>
              <div style="font-size: 12px; color: #555; line-height: 1.4;">
                ${reason}
              </div>
            </div>
          `;
        }
        html += '</div>';
      }
    } else {
      // Single mode: Display actual reason from LLM
      const provider = metadata.provider || 'gemini';
      const providerIcon = providerIcons[provider] || '🤖';
      const reason = metadata.reason || '문해력 향상에 도움이 되는 문장입니다.';

      html += `
        <div style="padding: 12px 0; border-top: 1px solid #e0e0e0;">
          <div style="font-weight: 600; margin-bottom: 6px; color: #333; display: flex; align-items: center; gap: 6px;">
            ${providerIcon} 선택 이유
          </div>
          <div style="font-size: 13px; color: #555; line-height: 1.5;">
            ${reason}
          </div>
        </div>
      `;
    }

    return html;
  }

  positionTooltip(targetElement) {
    const rect = targetElement.getBoundingClientRect();
    const tooltipRect = this.tooltipElement.getBoundingClientRect();

    // Position below target by default
    let top = rect.bottom + window.scrollY + 8;
    let left = rect.left + window.scrollX;

    // Adjust if off-screen
    if (left + tooltipRect.width > window.innerWidth) {
      left = window.innerWidth - tooltipRect.width - 10;
    }

    // Show above if no room below
    if (rect.bottom + tooltipRect.height + 8 > window.innerHeight) {
      top = rect.top + window.scrollY - tooltipRect.height - 8;
    }

    this.tooltipElement.style.top = `${top}px`;
    this.tooltipElement.style.left = `${left}px`;
  }

  destroy() {
    if (this.tooltipElement && this.tooltipElement.parentNode) {
      this.tooltipElement.parentNode.removeChild(this.tooltipElement);
    }
    this.tooltipElement = null;
  }
}

// Global tooltip instance
const tooltipManager = new TooltipManager();

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
      // Legacy fallback: simple string array (shouldn't happen anymore)
      sentenceText = target;
      metadata = { consensus_level: 'medium' };
    } else {
      // Object with metadata (both single and consensus modes)
      sentenceText = target.text;

      if (target.consensus_score !== undefined) {
        // Consensus mode: multiple providers
        metadata = {
          consensus_level: target.consensus_level || 'medium',
          consensus_score: target.consensus_score,
          selected_by: target.selected_by || [],
          reasons: target.reasons || {}
        };
      } else {
        // Single mode: one provider with single reason
        metadata = {
          consensus_level: target.consensus_level || 'medium',
          reason: target.reason,
          provider: 'gemini'  // Track which provider (for display)
        };
      }
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

  // Debug: Log metadata structure
  console.log('[Tooltip Debug] Creating highlight with metadata:', {
    consensus_level: metadata.consensus_level,
    consensus_score: metadata.consensus_score,
    selected_by: metadata.selected_by,
    reasons: metadata.reasons ? Object.keys(metadata.reasons) : 'undefined',
    reason: metadata.reason ? metadata.reason.substring(0, 50) + '...' : 'undefined',
    provider: metadata.provider || 'undefined',
    text_preview: text.substring(0, 50) + '...'
  });

  // Apply consensus-based color
  const consensusLevel = metadata.consensus_level || 'medium';
  const colors = CONFIG.COLORS[consensusLevel];

  mark.style.backgroundColor = colors.bg;
  mark.style.color = colors.text || 'inherit';
  mark.style.opacity = colors.opacity;
  mark.style.padding = CONFIG.HIGHLIGHT_PADDING;
  mark.style.cursor = 'help'; // Show help cursor on hover
  mark.setAttribute(CONFIG.DATA_ATTRIBUTE, 'active');
  mark.setAttribute('data-consensus-level', consensusLevel);

  // Store metadata for tooltip access
  mark.dataset.metadata = JSON.stringify(metadata);

  // Detect touch vs hover device
  const isTouchDevice = window.matchMedia('(hover: none)').matches;

  if (isTouchDevice) {
    // Touch: Click to toggle tooltip
    mark.addEventListener('click', function(e) {
      e.preventDefault();
      const storedMetadata = JSON.parse(this.dataset.metadata);

      if (tooltipManager.currentTarget === this) {
        tooltipManager.hide();
      } else {
        tooltipManager.show(this, storedMetadata);
      }
    });
  } else {
    // Hover: Show/hide tooltip
    mark.addEventListener('mouseenter', function() {
      const storedMetadata = JSON.parse(this.dataset.metadata);
      tooltipManager.show(this, storedMetadata);
    });

    mark.addEventListener('mouseleave', function() {
      tooltipManager.hide();
    });
  }

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

  // Destroy custom tooltip
  tooltipManager.destroy();

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

      // Debug: Log loaded targets structure
      console.log('[Tooltip Debug] Loaded targets:', state.highlightTargets);
      if (state.highlightTargets.length > 0) {
        console.log('[Tooltip Debug] First target sample:', state.highlightTargets[0]);
      }

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
