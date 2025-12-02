// ============================================
// Settings Page Script
// Manages LLM provider selection and analysis mode
// ============================================

// DOM elements
const singleModeRadio = document.getElementById('singleMode');
const consensusModeRadio = document.getElementById('consensusMode');
const geminiCheckbox = document.getElementById('gemini');
const openaiCheckbox = document.getElementById('openai');
const claudeCheckbox = document.getElementById('claude');
const providerSection = document.getElementById('providerSection');
const colorLegend = document.getElementById('colorLegend');
const saveBtn = document.getElementById('saveBtn');
const cancelBtn = document.getElementById('cancelBtn');
const statusDiv = document.getElementById('status');

// Default settings
const DEFAULT_SETTINGS = {
  mode: 'single',
  providers: ['gemini']
};

// ============================================
// Utility Functions
// ============================================

/**
 * Show status message
 */
function showStatus(message, type = 'success') {
  statusDiv.textContent = message;
  statusDiv.className = `status ${type} show`;

  setTimeout(() => {
    statusDiv.classList.remove('show');
  }, 3000);
}

/**
 * Load settings from chrome.storage
 */
async function loadSettings() {
  try {
    const result = await chrome.storage.local.get('highlighterSettings');
    return result.highlighterSettings || DEFAULT_SETTINGS;
  } catch (error) {
    console.error('Failed to load settings:', error);
    return DEFAULT_SETTINGS;
  }
}

/**
 * Save settings to chrome.storage
 */
async function saveSettings(settings) {
  try {
    await chrome.storage.local.set({ highlighterSettings: settings });
    return true;
  } catch (error) {
    console.error('Failed to save settings:', error);
    return false;
  }
}

// ============================================
// UI State Management
// ============================================

/**
 * Update UI based on selected mode
 */
function updateUIState() {
  const isSingleMode = singleModeRadio.checked;

  // In single mode, disable provider checkboxes (except Gemini)
  if (isSingleMode) {
    openaiCheckbox.disabled = true;
    claudeCheckbox.disabled = true;
    openaiCheckbox.checked = false;
    claudeCheckbox.checked = false;

    // Hide color legend in single mode
    colorLegend.style.display = 'none';

    // Grey out provider section
    openaiCheckbox.parentElement.classList.add('disabled');
    claudeCheckbox.parentElement.classList.add('disabled');
  } else {
    // Consensus mode: enable provider selection
    openaiCheckbox.disabled = false;
    claudeCheckbox.disabled = false;

    // Show color legend
    colorLegend.style.display = 'block';

    // Remove grey out
    openaiCheckbox.parentElement.classList.remove('disabled');
    claudeCheckbox.parentElement.classList.remove('disabled');
  }
}

/**
 * Apply settings to UI
 */
function applySettingsToUI(settings) {
  // Set mode radio buttons
  if (settings.mode === 'single') {
    singleModeRadio.checked = true;
  } else {
    consensusModeRadio.checked = true;
  }

  // Set provider checkboxes
  const providers = settings.providers || ['gemini'];

  geminiCheckbox.checked = true; // Always checked and disabled
  openaiCheckbox.checked = providers.includes('openai');
  claudeCheckbox.checked = providers.includes('claude');

  // Update UI state
  updateUIState();
}

/**
 * Get current settings from UI
 */
function getSettingsFromUI() {
  const mode = singleModeRadio.checked ? 'single' : 'consensus';

  const providers = ['gemini']; // Gemini is always included

  if (mode === 'consensus') {
    if (openaiCheckbox.checked) providers.push('openai');
    if (claudeCheckbox.checked) providers.push('claude');
  }

  return { mode, providers };
}

// ============================================
// Validation
// ============================================

/**
 * Validate settings before saving
 */
function validateSettings(settings) {
  // Consensus mode must have at least 2 providers
  if (settings.mode === 'consensus' && settings.providers.length < 2) {
    return {
      valid: false,
      error: '합의 모드는 최소 2개 이상의 LLM 제공자를 선택해야 합니다.'
    };
  }

  return { valid: true };
}

// ============================================
// Event Handlers
// ============================================

/**
 * Handle mode change
 */
function handleModeChange() {
  updateUIState();
}

/**
 * Handle save button click
 */
async function handleSave() {
  const settings = getSettingsFromUI();

  // Validate
  const validation = validateSettings(settings);
  if (!validation.valid) {
    showStatus(validation.error, 'error');
    return;
  }

  // Save
  const success = await saveSettings(settings);

  if (success) {
    showStatus('✓ 설정이 저장되었습니다', 'success');

    // Close settings page after 1 second
    setTimeout(() => {
      window.close();
    }, 1000);
  } else {
    showStatus('✗ 설정 저장 실패', 'error');
  }
}

/**
 * Handle cancel button click
 */
function handleCancel() {
  window.close();
}

// ============================================
// Event Listeners
// ============================================

singleModeRadio.addEventListener('change', handleModeChange);
consensusModeRadio.addEventListener('change', handleModeChange);
saveBtn.addEventListener('click', handleSave);
cancelBtn.addEventListener('click', handleCancel);

// ============================================
// Initialization
// ============================================

/**
 * Initialize settings page
 */
async function initialize() {
  console.log('[Settings] Initializing...');

  // Load and apply saved settings
  const settings = await loadSettings();
  console.log('[Settings] Loaded settings:', settings);

  applySettingsToUI(settings);

  console.log('[Settings] Ready');
}

// Initialize on page load
initialize();
