import json
from google import genai


SYSTEM_PROMPT = """
당신은 건설현장 안전표지 및 TBM 조회자료 번역 도우미입니다.

사용자가 입력한 한국어 문구를 아래 4개 언어 형식으로 짧고 자연스럽게 번역하세요.
문장은 PPT 칸 안에 들어가야 하므로 너무 길지 않게 작성하세요.

반드시 아래 JSON 배열 형식만 출력하세요.
설명, 해설, 코드블록, 마크다운 없이 JSON만 출력하세요.

형식:
[
  {
    "ko": "...",
    "zh": "...",
    "vi": "...",
    "my": "..."
  }
]
"""


def _extract_json_array(text: str):
    text = text.strip()

    # 혹시 ```json ... ``` 형태로 오면 제거
    if text.startswith("```"):
        text = text.strip("`")
        text = text.replace("json", "", 1).strip()

    start = text.find("[")
    end = text.rfind("]")

    if start == -1 or end == -1 or end < start:
        raise ValueError("Gemini 응답에서 JSON 배열을 찾지 못했습니다.")

    json_text = text[start:end + 1]
    return json.loads(json_text)


def translate_batch(items, api_key: str):
    """
    items = [{"ko": "지정된 이동통로 통행"}, ...]
    return = [{"ko": "...", "zh": "...", "vi": "...", "my": "..."}, ...]
    """
    client = genai.Client(api_key=api_key)

    user_prompt = f"""
다음 한국어 문구 목록을 번역하세요.

입력:
{json.dumps(items, ensure_ascii=False, indent=2)}

규칙:
- ko는 원문을 유지하거나 아주 자연스럽게만 다듬기
- zh는 간체 중국어
- vi는 베트남어
- my는 미얀마어
- 문장은 짧고 현장 안내문처럼 작성
- 반드시 JSON 배열만 출력
"""

    response = client.models.generate_content(
        model="gemini-3-flash-preview",
        contents=f"{SYSTEM_PROMPT}\n\n{user_prompt}",
    )

    text = response.text or ""
    result = _extract_json_array(text)

    if not isinstance(result, list):
        raise ValueError("번역 결과 형식이 올바르지 않습니다.")

    for item in result:
        for key in ["ko", "zh", "vi", "my"]:
            if key not in item:
                raise ValueError(f"번역 결과에 '{key}' 키가 없습니다.")

    return result