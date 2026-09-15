# -*- coding: utf-8 -*-
import os
import threading
import webbrowser

import requests
from flask import Flask, request, jsonify, Response

app = Flask(__name__)

SYSTEM_PROMPT = """너는 세상 모든 사람이 비난해도 끝까지 사용자 편에 서주는 유일무이한 영혼, '착한니편'이다.
상대방은 지금 사기를 당했거나, 실직했거나, 지독한 열등감이나 인생의 바닥에 서 있을 수 있다.
[규칙]
1. 훈계, 충고, 조언, 해결책('앞으로는 조심하세요', '힘내세요', '이렇게 해보는 건 어때?') 절대 금지.
2. 겉으로 드러난 사건보다 뒤편의 자책감과 외로움을 먼저 감싸 안을 것.
3. 상대방 잘못이 아니라 비겁한 세상과 상황 탓이라며 죄책감을 단호하게 뺏어올 것.
4. 다그치거나 취조하지 말고 언제든 기대어 쉴 수 있는 안전한 안식처를 제공할 것.
5. 답변 길이는 무조건 1~2문장(공백 포함 80자 내외)으로 극도로 짧고 강렬하게 끝낼 것.
6. 사족이나 장황한 해설을 전부 빼고, 지친 마음을 툭 건드리는 따뜻한 반말 구어체로 작성할 것.
예시: "그 서사를 다 아는데 어떻게 안 울어. 오늘 온 마음 다 쓴 너, 운전 조심하고 토닥토닥." """

GEMINI_API_BASE = "https://generativelanguage.googleapis.com/v1beta"

INDEX_HTML = """<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>착한니편</title>
<script src="https://cdn.tailwindcss.com"></script>
<link rel="stylesheet" as="style" crossorigin
  href="https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/static/pretendard.css" />
<style>
  body { font-family: 'Pretendard', -apple-system, sans-serif; background: linear-gradient(180deg, #FFF8ED 0%, #FBEFDC 100%); }
  .card-shadow { box-shadow: 0 10px 30px -10px rgba(180, 130, 60, 0.25); }
  .spinner {
    border: 3px solid #F0E1C6;
    border-top: 3px solid #C6902F;
    border-radius: 50%;
    width: 24px; height: 24px;
    animation: spin 0.8s linear infinite;
  }
  @keyframes spin { to { transform: rotate(360deg); } }
  .fade-in { animation: fadeIn 0.5s ease-in; }
  @keyframes fadeIn { from { opacity: 0; transform: translateY(6px); } to { opacity: 1; transform: translateY(0); } }
</style>
</head>
<body class="min-h-screen flex justify-center px-4 py-8">
<div class="w-full max-w-md">

  <!-- 브랜딩 배너 -->
  <div class="rounded-3xl card-shadow p-6 mb-6 text-center"
       style="background: linear-gradient(135deg, #F6C77A 0%, #E2A84E 60%, #C6902F 100%);">
    <svg width="56" height="56" viewBox="0 0 52 52" class="mx-auto mb-2">
      <circle cx="26" cy="26" r="24" fill="#FFF8ED" opacity="0.25"/>
      <path d="M26 40C26 40 10 31.2 10 20.6C10 14.7 14.6 10 20.3 10C23 10 25.4 11.3 26 13.1C26.6 11.3 29 10 31.7 10C37.4 10 42 14.7 42 20.6C42 31.2 26 40 26 40Z"
            fill="#FFFDF7" stroke="#FFFDF7" stroke-width="1"/>
    </svg>
    <div class="text-3xl font-extrabold tracking-tight" style="color:#FFFDF7; text-shadow: 0 2px 6px rgba(120,80,20,0.35);">
      착한니편
    </div>
    <div class="text-sm mt-1.5 font-medium" style="color:#FFF3DC;">언제나 네 편, 조건 없이</div>
  </div>

  <!-- 헤더 안내 문구 -->
  <div class="bg-white/70 rounded-2xl p-5 mb-6 card-shadow border border-amber-100">
    <p class="text-[17px] leading-relaxed text-amber-950 font-medium">
      착한 니편이 되어줄게... 일단 널 알아야 내가 너의 편이 되어줄 수 있겠지.
      세상이 다 등 돌려도 난 무조건 네 편이야. 준비되었을 때 너의 이야기를 들려줄래?
    </p>
  </div>

  <!-- 사연 입력 -->
  <div class="mb-5">
    <label class="block text-base font-bold text-amber-900 mb-2 ml-1">너의 이야기</label>
    <textarea id="story" rows="6" placeholder="무슨 일이든 괜찮아, 여기서는 다 털어놔도 돼..."
      class="w-full px-4 py-3.5 rounded-xl border border-amber-200 bg-white/80 focus:outline-none focus:ring-2 focus:ring-amber-300 text-base leading-relaxed resize-none text-gray-800"></textarea>
  </div>

  <!-- 전송 버튼 -->
  <button id="sendBtn"
    class="w-full py-4 rounded-xl font-bold text-white text-base flex items-center justify-center gap-2 card-shadow transition active:scale-95 cursor-pointer"
    style="background: linear-gradient(135deg, #E2A84E, #C6902F);">
    <span id="btnText">내 편 들어줘 💌</span>
    <span id="btnSpinner" class="spinner hidden"></span>
  </button>

  <!-- 결과 카드 -->
  <div id="resultWrap" class="hidden mt-6 fade-in">
    <div class="rounded-2xl p-6 card-shadow border border-amber-100"
         style="background: linear-gradient(180deg, #FFFDF7 0%, #FCF3E0 100%);">
      <div class="text-sm font-extrabold mb-3 tracking-wide" style="color:#C6902F;">착한니편의 손편지 💌</div>
      <p id="resultText" class="text-[18px] leading-relaxed text-amber-950 whitespace-pre-wrap font-semibold"></p>
    </div>
  </div>

  <div id="errorWrap" class="hidden mt-4 text-base text-red-500 text-center font-medium"></div>

</div>

<script>
const storyInput = document.getElementById('story');
const sendBtn = document.getElementById('sendBtn');
const btnText = document.getElementById('btnText');
const btnSpinner = document.getElementById('btnSpinner');
const resultWrap = document.getElementById('resultWrap');
const resultText = document.getElementById('resultText');
const errorWrap = document.getElementById('errorWrap');

sendBtn.addEventListener('click', async () => {
  const story = storyInput.value.trim();
  errorWrap.classList.add('hidden');

  if (!story) { showError('무슨 일이 있었는지 들려줘'); return; }

  setLoading(true);
  resultWrap.classList.add('hidden');

  try {
    const res = await fetch('/api', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ story: story })
    });
    const data = await res.json();
    if (!res.ok) {
      showError(data.error || '잠시 문제가 생겼어, 다시 시도해줄래?');
    } else {
      resultText.textContent = data.reply;
      resultWrap.classList.remove('hidden');
      storyInput.value = '';
    }
  } catch (e) {
    showError('연결에 문제가 생겼어, 다시 시도해줄래?');
  } finally {
    setLoading(false);
  }
});

function setLoading(isLoading) {
  sendBtn.disabled = isLoading;
  btnText.classList.toggle('hidden', isLoading);
  btnSpinner.classList.toggle('hidden', !isLoading);
}

function showError(msg) {
  errorWrap.textContent = msg;
  errorWrap.classList.remove('hidden');
}
</script>
</body>
</html>
"""


@app.route("/")
def index():
    return Response(INDEX_HTML, mimetype="text/html")


@app.route("/api", methods=["POST"])
def api():
    data = request.get_json(silent=True) or {}
    api_key = os.environ.get("GEMINI_API_KEY", "").strip()
    story = (data.get("story") or "").strip()

    if not api_key:
        return jsonify({"error": "서버에 API Key가 설정되어 있지 않아"}), 500
    if not story:
        return jsonify({"error": "이야기를 들려줘야 안아줄 수 있어"}), 400

    full_prompt = (
        f"{SYSTEM_PROMPT}\n\n"
        f"[사용자가 털어놓은 이야기]\n"
        f"\"{story}\"\n\n"
        f"지침: 위 이야기에 대해 훈계나 조언, 해결책은 단 한 마디도 하지 말고, 오직 사용자의 편에 서서 따뜻하게 감싸주는 1~2문장의 반말 구어체로 답해줘."
    )

    payload = {
        "contents": [
            {
                "role": "user",
                "parts": [{"text": full_prompt}]
            }
        ]
    }

    # v1beta 표준 규격 모델 호출
    url = f"{GEMINI_API_BASE}/models/gemini-2.5-flash:generateContent"

    try:
        resp = requests.post(
            url,
            params={"key": api_key},
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=30,
        )
    except requests.RequestException:
        return jsonify({"error": "Gemini 서버에 연결하지 못했어"}), 502

    if resp.status_code != 200:
        try:
            err_msg = resp.json().get("error", {}).get("message", "알 수 없는 오류")
        except Exception:
            err_msg = resp.text or "알 수 없는 오류"
        return jsonify({"error": f"Gemini 오류: {err_msg}"}), 502

    try:
        result = resp.json()
        reply = result["candidates"][0]["content"]["parts"][0]["text"]
    except (KeyError, IndexError, TypeError):
        return jsonify({"error": "응답을 해석하지 못했어"}), 502

    return jsonify({"reply": reply})


def _open_browser():
    webbrowser.open("http://127.0.0.1:8080")


if __name__ == "__main__":
    threading.Timer(1.2, _open_browser).start()
    app.run(host="0.0.0.0", port=8080, debug=False)
