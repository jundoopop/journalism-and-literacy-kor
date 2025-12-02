// DOM 요소
const activateBtn = document.getElementById('activateBtn');
const deactivateBtn = document.getElementById('deactivateBtn');
const reloadBtn = document.getElementById('reloadBtn');
const settingsBtn = document.getElementById('settingsBtn');
const statusDiv = document.getElementById('status');
const serverStatusDiv = document.getElementById('serverStatus');
const providerInfoDiv = document.getElementById('providerInfo');

// 지원하는 언론사 도메인 목록
const SUPPORTED_DOMAINS = [
  'chosun.com',
  'hani.co.kr',
  'hankookilbo.com',
  'joongang.co.kr',
  'khan.co.kr'
];

/**
 * 지원하는 사이트인지 확인
 */
function isSupportedSite(url) {
  return SUPPORTED_DOMAINS.some(domain => url.includes(domain));
}

/**
 * 상태 메시지 표시
 */
function showStatus(message, type = 'success') {
  statusDiv.textContent = message;
  statusDiv.className = `status ${type} show`;

  setTimeout(() => {
    statusDiv.classList.remove('show');
  }, 3000);
}

/**
 * Activate 버튼 핸들러
 */
activateBtn.addEventListener('click', async () => {
  try {
    // 현재 활성 탭 가져오기
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });

    if (!tab) {
      showStatus('활성 탭을 찾을 수 없습니다', 'error');
      return;
    }

    // 지원하는 사이트인지 확인
    if (!isSupportedSite(tab.url)) {
      showStatus('지원하지 않는 사이트입니다', 'error');
      return;
    }

    // Content script에 메시지 전송
    const response = await chrome.tabs.sendMessage(tab.id, {
      action: 'activate'
    });

    if (response && response.success) {
      showStatus(`✓ ${response.count}개 문장 하이라이트됨`, 'success');
    } else {
      showStatus('하이라이트 실패', 'error');
    }

  } catch (error) {
    console.error('Activate error:', error);
    showStatus('페이지를 새로고침 후 다시 시도해주세요', 'error');
  }
});

/**
 * Deactivate 버튼 핸들러
 */
deactivateBtn.addEventListener('click', async () => {
  try {
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });

    if (!tab) {
      showStatus('활성 탭을 찾을 수 없습니다', 'error');
      return;
    }

    // Content script에 메시지 전송
    const response = await chrome.tabs.sendMessage(tab.id, {
      action: 'deactivate'
    });

    if (response && response.success) {
      showStatus('✓ 하이라이트 제거됨', 'success');
    } else {
      showStatus('제거 실패', 'error');
    }

  } catch (error) {
    console.error('Deactivate error:', error);
    showStatus('오류 발생', 'error');
  }
});

/**
 * Reload 버튼 핸들러 (강제 재분석)
 */
reloadBtn.addEventListener('click', async () => {
  try {
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });

    if (!tab) {
      showStatus('활성 탭을 찾을 수 없습니다', 'error');
      return;
    }

    if (!isSupportedSite(tab.url)) {
      showStatus('지원하지 않는 사이트입니다', 'error');
      return;
    }

    showStatus('재분석 중...', 'success');

    // Content script에 재로딩 메시지 전송
    const response = await chrome.tabs.sendMessage(tab.id, {
      action: 'reload'
    });

    if (response && response.success) {
      showStatus(`✓ 재분석 완료: ${response.count}개 문장`, 'success');
    } else {
      showStatus('재분석 실패', 'error');
    }

  } catch (error) {
    console.error('Reload error:', error);
    showStatus('페이지를 새로고침 후 다시 시도해주세요', 'error');
  }
});

/**
 * 네이티브 호스트 상태 확인 및 표시
 */
async function checkServerStatus() {
  try {
    const response = await chrome.runtime.sendMessage({ action: 'checkServer' });

    if (response && response.healthy) {
      serverStatusDiv.textContent = '✓ 네이티브 호스트 연결됨';
      serverStatusDiv.className = 'server-status connected';
    } else {
      serverStatusDiv.textContent = '✗ 설치 프로그램을 실행하세요';
      serverStatusDiv.className = 'server-status disconnected';
    }
  } catch (error) {
    console.error('Server check error:', error);
    serverStatusDiv.textContent = '✗ 설치 프로그램을 실행하세요';
    serverStatusDiv.className = 'server-status disconnected';
  }
}

/**
 * Settings 버튼 핸들러
 */
settingsBtn.addEventListener('click', () => {
  chrome.tabs.create({ url: 'settings.html' });
});

/**
 * 현재 설정 불러와서 표시
 */
async function loadAndDisplaySettings() {
  try {
    const result = await chrome.storage.local.get('highlighterSettings');
    const settings = result.highlighterSettings || { mode: 'single', providers: ['gemini'] };

    const modeText = settings.mode === 'single' ? '단일 모드' : '합의 모드';
    const providerCount = settings.providers.length;
    const providerText = settings.providers.join(', ');

    providerInfoDiv.textContent = `${modeText} (${providerCount}개: ${providerText})`;
  } catch (error) {
    console.error('Failed to load settings:', error);
    providerInfoDiv.textContent = '설정 로드 실패';
  }
}

// 팝업 열릴 때 서버 상태 및 설정 확인
checkServerStatus();
loadAndDisplaySettings();