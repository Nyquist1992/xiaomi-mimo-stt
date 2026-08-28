# MiMo ASR 請求格式驗證紀錄（2026-08-27）

## 來源對照
- 官方文件：https://mimo.mi.com/docs/zh-CN/quick-start/usage-guide/audio/Speech-Recognition
- 參考專案：hass-cortex/xiaomi-mimo-tts（同家族 TTS 整合，同樣用 `api-key` header + chat.completions + audio.data Base64）

## 確認的格式（依官方 curl 範例，非 SDK 範例）

```
POST https://api.xiaomimimo.com/v1/chat/completions
Header: api-key: $MIMO_API_KEY          ← 不是 Authorization: Bearer
Header: Content-Type: application/json

{
  "model": "mimo-v2.5-asr",
  "messages": [{
    "role": "user",
    "content": [{
      "type": "input_audio",
      "input_audio": { "data": "data:audio/wav;base64,$BASE64_AUDIO" }
    }]
  }],
  "asr_options": { "language": "zh" }    ← 頂層欄位！
}
```

## 關鍵陷阱：extra_body ≠ JSON 欄位
官方 Python SDK 範例寫 `extra_body={"asr_options": ...}` —— 這是 OpenAI SDK
的客戶端行為（SDK 會把 extra_body 的內容攤平到 request body 頂層）。
直接打 HTTP API 時必須把 `asr_options` 放在 body 頂層，不能包 `extra_body`。

## 音訊格式
- 輸入：僅 wav / mp3，Base64 編碼，上限 10 MB（base64 字串）
- MIME：`audio/wav`、`audio/mpeg`（或 `audio/mp3`）
- 語種：`auto` / `zh` / `en`；指定語種比 auto 準
- 回應：`choices[0].message.content` 純文字轉錄

## HA STT 端對接（stt.py）
- HA Assist 餵原始 PCM（s16le 16-bit）串流 → `wave` 模組包 WAV 容器
  → Base64 → data URL
- metadata.language（zh-tw 等）→ 映射為 API 的 `zh`（保留 zh-tw 宣告讓
  HA intent 系統載入繁中意圖，同 Whisper 社群整合做法）
- 7MB raw PCM 上限（遠低於 10MB b64 限制，留 SAFETY margin）
