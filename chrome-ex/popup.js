// DOM 요소
const activateBtn = document.getElementById('activateBtn');
const deactivateBtn = document.getElementById('deactivateBtn');
const statusDiv = document.getElementById('status');

// 지원하는 언론사 도메인 목록
const SUPPORTED_DOMAINS = [
  'chosun.com',
  'hani.co.kr',
  'hankookilbo.com',
  'joongang.co.kr'
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