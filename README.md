# Xiaomi MiMo ASR — Home Assistant STT Integration

Turn Xiaomi's MiMo-V2.5-ASR into a Home Assistant Assist pipeline Speech-to-Text engine.
將小米 MiMo-V2.5-ASR 接進 Home Assistant Assist Pipeline 作為語音辨識引擎。

Based on / 基於 [hass-cortex/xiaomi-mimo-tts](https://github.com/hass-cortex/xiaomi-mimo-tts) (client, config-flow & sensor design reference / 用作用戶端、設定流程與感測器設計參考)

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

[English](#english) | [繁體中文](#繁體中文)

---

<a id="english"></a>
## English

### What is this

A custom STT (speech-to-text) integration that registers **MiMo-V2.5-ASR** as a Speech-to-Text provider in Home Assistant. Any Assist satellite (Voice Satellite browser card, phones, tablets, Wyoming devices) can use it in a voice pipeline.

```
Assist satellite (tablet mic) → wake word → PCM stream → this integration
  → WAV + Base64 → MiMo ASR API (chat.completions + input_audio)
  → transcript → Assist pipeline → conversation agent → TTS
```

### Features

- Full UI setup (Config Flow): paste API key, validated live via `GET /v1/models`
- Replace key from the UI anytime (reconfigure) — expired keys trigger the reauth flow automatically
- Languages: `zh` / `en` / `auto`; `zh-tw` and friends are advertised for HA intents and mapped to API `zh`
- 13 diagnostic sensors (transcript, latency, request counters, token usage, estimated cost, last error)
- Diagnostics download with `api_key` redaction

### Input / Output audio formats

| Direction / 方向 | Format / 格式 |
|---|---|
| HA → integration | raw PCM stream (s16le, 16-bit) from Assist pipeline |
| Integration → MiMo API | PCM wrapped in **WAV** → Base64 → `data:audio/wav;base64,...` in `input_audio` (10 MB base64 cap) |
| MiMo → integration | transcript at `choices[0].message.content`, tokens at `usage.total_tokens` |
| Integration → HA | `SpeechResult(text, SUCCESS)` back to the pipeline |

### Installation (HACS custom repository)

1. HACS → top-right menu → **Custom repositories**
2. Paste `https://github.com/Nyquist1992/xiaomi-mimo-stt`, category **Integration**
3. Click **Download**, then **restart Home Assistant**
4. Settings → Devices & Services → Add Integration → search **Xiaomi MiMo ASR** → paste API key

### Voice pipeline setup

Settings → Voice assistants → your pipeline → Speech-to-Text → **Xiaomi MiMo ASR**.

### API key

Get one at [mimo.mi.com](https://mimo.mi.com). Model: `mimo-v2.5-asr`, billing **CNY 0.5 per audio hour**.

### License

MIT — see [LICENSE](LICENSE). Design inspired by [xiaomi-mimo-tts](https://github.com/hass-cortex/xiaomi-mimo-tts) by parkghost.

---

<a id="繁體中文"></a>
## 繁體中文

### 這是什麼

自訂 STT（語音辨識）整合，把 **MiMo-V2.5-ASR** 註冊為 Home Assistant 的語音轉文字提供者。任何 Assist 衛星（Voice Satellite 瀏覽器卡片、手機、平板、Wyoming 裝置）都能在語音管線中使用。

```
Assist 衛星（平板收音）→ 喚醒詞 → PCM 串流 → 本整合
  → WAV + Base64 → MiMo ASR API（chat.completions + input_audio）
  → 轉錄文字 → Assist 管線 → 對話 agent → TTS
```

### 功能

- 完整 UI 設定（Config Flow）：貼上 API Key，建立前先經 `GET /v1/models` 即時驗證
- 隨時從 UI 更換 key（重新設定）——key 失效自動觸發 reauth 流程
- 支援語言：`zh` / `en` / `auto`；`zh-tw` 等會宣告給 HA intent 系統，API 端自動映射為 `zh`
- 13 顆診斷感測器（轉錄文字、延遲、請求計數、Token 用量、預估費用、最後錯誤）
- 整合頁「下載診斷」，自動遮蔽 `api_key`

### 診斷實體

| Sensor / 實體 | 說明 / 說明 |
|---|---|
| 最後轉錄文字 | ★ 失準診斷核心——當場看 MiMo 聽成什麼 |
| 最後耗時 / 平均耗時 | API 延遲（ms，平均取近 20 次） |
| 請求總數 / 成功 / 失敗 / 今日請求數 | 成功率統計 |
| 今日 Token / 累計 Token / 最後請求 Token | usage token 口徑 |
| 今日音訊秒數 / 今日預估費用 | 計費口徑（官方費率 **¥0.5/小時**） |
| 最後錯誤 | ok / auth / api / connection / timeout / empty |

### 語音格式（輸入 / 輸出）

| 方向 | 格式 |
|---|---|
| HA → 整合 | Assist pipeline 串流的原始 PCM（s16le, 16-bit） |
| 整合 → MiMo API | PCM 包成 **WAV** → Base64 → `data:audio/wav;base64,...` 放進 `input_audio`（上限 10 MB base64） |
| MiMo → 整合 | `choices[0].message.content` 純文字 + `usage.total_tokens` |
| 整合 → HA | `SpeechResult(text, SUCCESS)` 交回 pipeline |

### 安裝（HACS 自訂儲存庫）

1. HACS → 右上角三點 → **自訂儲存庫（Custom repositories）**
2. 貼上 repo URL：`https://github.com/Nyquist1992/xiaomi-mimo-stt`，類別選 **Integration（整合）**
3. 點**下載**，然後**重啟 Home Assistant**
4. 設定 → 裝置與服務 → 新增整合 → 搜尋「Xiaomi MiMo ASR」→ 貼上 API Key

> HACS 之後有新版本時，同樣從 HACS 頁面點更新即可。

### 設定到 Voice Pipeline

設定 → 語音助理 → 你的 pipeline → Speech-to-Text 選 **Xiaomi MiMo ASR**。

### 取得 API Key

到 [mimo.mi.com](https://mimo.mi.com) 控制台申請（模型：`mimo-v2.5-asr`，計費 **¥0.5 / 音訊小時**）。

### 授權

MIT — 見 [LICENSE](LICENSE)。設計參考 parkghost 的 [xiaomi-mimo-tts](https://github.com/hass-cortex/xiaomi-mimo-tts)。
