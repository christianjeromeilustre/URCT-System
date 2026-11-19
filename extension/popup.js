const API_URL = "http://127.0.0.1:8000/translate";

const source = document.getElementById("source");
const target = document.getElementById("target");
const result = document.getElementById("result");
const status = document.getElementById("status");

const translateButton = document.getElementById("translate");
const copyButton = document.getElementById("copy");

translateButton.addEventListener("click", async () => {
  const text = source.value.trim();

  if (!text) {
    status.textContent = "먼저 문장을 입력하세요.";
    return;
  }

  translateButton.disabled = true;
  copyButton.disabled = true;
  result.value = "";
  status.textContent = "번역 중...";

  try {
    const response = await fetch(API_URL, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        text: text,
        target_language: target.value
      })
    });

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }

    const data = await response.json();

    result.value = data.translated_text || "";
    copyButton.disabled = !data.translated_text;

    status.textContent = data.translated_text
      ? "데모 번역 완료"
      : "데모 사전에 없는 문장입니다.";
  } catch (error) {
    status.textContent = `서버 연결 오류: ${error.message}`;
  } finally {
    translateButton.disabled = false;
  }
});

copyButton.addEventListener("click", async () => {
  try {
    await navigator.clipboard.writeText(result.value);
    status.textContent = "번역문을 복사했습니다.";
  } catch {
    status.textContent = "복사하지 못했습니다.";
  }
});