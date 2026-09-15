@app.route("/api", methods=["POST"])
def api():
    data = request.get_json(silent=True) or {}
    api_key = os.environ.get("GEMINI_API_KEY", "").strip()
    story = (data.get("story") or "").strip()

    if not api_key:
        return jsonify({"error": "서버에 API Key가 설정되어 있지 않아"}), 500
    if not story:
        return jsonify({"error": "이야기를 들려줘야 안아줄 수 있어"}), 400

    payload = {
        "systemInstruction": {"parts": [{"text": SYSTEM_PROMPT}]},
        "contents": [{"role": "user", "parts": [{"text": story}]}],
    }

    # 1. 구글 서버에서 현재 지원 중인 모델 목록을 실시간으로 조회
    target_model = None
    try:
        models_url = f"{GEMINI_API_BASE}?key={api_key}"
        list_res = requests.get(models_url, timeout=10)
        if list_res.status_code == 200:
            models_data = list_res.json().get("models", [])
            # generateContent를 지원하는 모델 중 'flash' 모델 우선 탐색
            valid_models = [
                m["name"] for m in models_data 
                if "generateContent" in m.get("supportedGenerationMethods", [])
            ]
            flash_models = [m for m in valid_models if "flash" in m]
            if flash_models:
                target_model = flash_models[-1] # 가장 최신 버전 선택
            elif valid_models:
                target_model = valid_models[-1]
    except Exception:
        pass

    # 조회가 실패할 경우를 대비한 기본 백업 모델
    if not target_model:
        target_model = "models/gemini-2.5-flash"

    # 모델 이름 포맷 정리
    if not target_model.startswith("models/"):
        target_model = f"models/{target_model}"

    url = f"https://generativelanguage.googleapis.com/v1beta/{target_model}:generateContent"
    try:
        resp = requests.post(
            url,
            params={"key": api_key},
            json=payload,
            timeout=30,
        )
    except requests.RequestException:
        return jsonify({"error": "Gemini 서버에 연결하지 못했어"}), 502

    if resp.status_code != 200:
        try:
            err_msg = resp.json().get("error", {}).get("message", "알 수 없는 오류")
        except Exception:
            err_msg = "알 수 없는 오류"
        return jsonify({"error": "Gemini 오류: " + err_msg}), 502

    try:
        result = resp.json()
        reply = result["candidates"][0]["content"]["parts"][0]["text"]
    except (KeyError, IndexError, TypeError):
        return jsonify({"error": "응답을 해석하지 못했어"}), 502

    return jsonify({"reply": reply})
