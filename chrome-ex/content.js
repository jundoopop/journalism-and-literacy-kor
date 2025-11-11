// ============================================
// 하이라이트 대상 (나중에 LLM api 리턴값으로 교체)
// ============================================
const for_highlight = [
  "대통령",
  "여당",
  "달러",
  "트럼프",
  "관세",
];

// ============================================
// 설정
// ============================================
const CONFIG = {
  target_color: "#ffff00",
  opacity: 0.5,
  sentence_delimiters: /[.!?…]/
};

// ============================================
// 상태 변수
// ============================================
let isActivated = false;
let highlightedNodes = [];

// ============================================
// 유틸리티 함수
// ============================================

/**
 * 텍스트 정규화 (소문자 + 공백 정리)
 */
function normalize(text) {
  return text.toLowerCase().replace(/\s+/g, ' ').trim();
}

/**
 * 텍스트를 문장으로 분리
 */
function splitIntoSentences(text) {
  const sentences = [];
  let currentSentence = '';

  for (let i = 0; i < text.length; i++) {
    const char = text[i];
    currentSentence += char;

    // 문장 구분자를 만나면
    if (CONFIG.sentence_delimiters.test(char)) {
      // 다음 공백도 포함
      while (i + 1 < text.length && /\s/.test(text[i + 1])) {
        currentSentence += text[i + 1];
        i++;
      }

      if (currentSentence.trim()) {
        sentences.push(currentSentence);
      }
      currentSentence = '';
    }
  }

  // 남은 문장
  if (currentSentence.trim()) {
    sentences.push(currentSentence);
  }

  return sentences;
}

/**
 * 문장이 하이라이트 대상인지 확인
 */
function shouldHighlight(sentence) {
  const normalizedSentence = normalize(sentence);

  for (let keyword of for_highlight) {
    const normalizedKeyword = normalize(keyword);

    if (normalizedSentence.includes(normalizedKeyword)) {
      return true;
    }
  }

  return false;
}

// ============================================
// DOM 수집
// ============================================

/**
 * 텍스트 노드만 수집
 */
function collectTextNodes(root) {
  const textNodes = [];
  const walker = document.createTreeWalker(
    root,
    NodeFilter.SHOW_TEXT,
    {
      acceptNode: function (node) {
        // 빈 텍스트 제외
        if (!node.textContent.trim()) {
          return NodeFilter.FILTER_REJECT;
        }

        // script, style, mark 태그 내부 제외
        const parent = node.parentElement;
        if (!parent) return NodeFilter.FILTER_REJECT;

        const tagName = parent.tagName.toLowerCase();
        if (['script', 'style', 'noscript', 'mark'].includes(tagName)) {
          return NodeFilter.FILTER_REJECT;
        }

        return NodeFilter.FILTER_ACCEPT;
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
// 하이라이트 적용
// ============================================

/**
 * 텍스트 노드에 하이라이트 적용
 */
function highlightTextNode(textNode) {
  const text = textNode.textContent;
  const sentences = splitIntoSentences(text);

  // 하이라이트 대상이 없으면 종료
  const hasTarget = sentences.some(s => shouldHighlight(s));
  if (!hasTarget) {
    return;
  }

  // 새로운 HTML 생성
  const fragment = document.createDocumentFragment();
  let lastIndex = 0;

  sentences.forEach(sentence => {
    const index = text.indexOf(sentence, lastIndex);

    if (index === -1) return;

    // 문장 앞의 텍스트
    if (index > lastIndex) {
      const before = text.substring(lastIndex, index);
      fragment.appendChild(document.createTextNode(before));
    }

    // 문장 (하이라이트 여부에 따라)
    if (shouldHighlight(sentence)) {
      const mark = document.createElement('mark');
      mark.style.backgroundColor = CONFIG.target_color;
      mark.style.opacity = CONFIG.opacity;
      mark.style.padding = '2px 0';
      mark.setAttribute('data-highlighter', 'active');
      mark.textContent = sentence;
      fragment.appendChild(mark);

      // 제거용으로 저장
      highlightedNodes.push(mark);
    } else {
      fragment.appendChild(document.createTextNode(sentence));
    }

    lastIndex = index + sentence.length;
  });

  // 남은 텍스트
  if (lastIndex < text.length) {
    fragment.appendChild(document.createTextNode(text.substring(lastIndex)));
  }

  // 원본 교체
  textNode.parentNode.replaceChild(fragment, textNode);
}

// ============================================
// 메인 로직
// ============================================

/**
 * 전체 하이라이팅 실행
 */
function mainHighlight() {
  if (isActivated) {
    console.log('[하이라이터] 이미 활성화됨');
    return;
  }

  console.log('[하이라이터] 시작...');
  console.log('[하이라이터] 대상 키워드:', for_highlight);

  const startTime = performance.now();

  // 텍스트 노드 수집
  const textNodes = collectTextNodes(document.body);
  console.log(`[하이라이터] 텍스트 노드 수: ${textNodes.length}`);

  // 각 노드에 하이라이트 적용
  textNodes.forEach(node => {
    highlightTextNode(node);
  });

  const endTime = performance.now();
  console.log(`[하이라이터] 완료! (${(endTime - startTime).toFixed(2)}ms)`);
  console.log(`[하이라이터] 하이라이트된 문장: ${highlightedNodes.length}개`);

  isActivated = true;
}

/**
 * 하이라이트 제거
 */
function removeHighlights() {
  console.log('[하이라이터] 하이라이트 제거 중...');

  highlightedNodes.forEach(mark => {
    if (mark.parentNode) {
      const text = mark.textContent;
      const textNode = document.createTextNode(text);
      mark.parentNode.replaceChild(textNode, mark);
    }
  });

  highlightedNodes = [];
  isActivated = false;

  console.log('[하이라이터] 제거 완료');
}

// ============================================
// 메시지 리스너
// ============================================

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  console.log('[하이라이터] 메시지 수신:', message);

  if (message.action === 'activate') {
    mainHighlight();
    sendResponse({ success: true, count: highlightedNodes.length });
  } else if (message.action === 'deactivate') {
    removeHighlights();
    sendResponse({ success: true });
  }

  return true;
});

console.log('[하이라이터] Content script 로드 완료 (대기 중)');