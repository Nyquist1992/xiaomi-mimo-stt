# Xiaomi MiMo ASR — Home Assistant STT Integration

把小米 MiMo-V2.5-ASR 接進 Home Assistant Assist Pipeline 的自訂 STT 整合。
參考 [hass-cortex/xiaomi-mimo-tts](https://github.com/hass-cortex/xiaomi-mimo-tts)（同家族 TTS 整合）的 client / config flow / sensor 設計。

## 功能

- 完整 UI 設定（Config Flow）：貼上 API Key 即完成，**金鑰即時驗證**（`GET /v1/models`）。
- 換 key 不用碰 YAML：整合頁「重新設定」可更換 key 與預設語言；key 失效自動觸發 reauth。
- 支援語言：`zh` / `en` / `auto`（HA 端另宣告 `zh-tw` 等讓繁中 intent 正確載入，API 端自動映射 `zh`）。
- **13 顆診斷 sensor**（見下表）+ 整合頁「下載診斷」。

## 診斷實體

| Sensor | 說明 |
|---|---|
| 最後轉錄文字 | ★ 失準診斷核心——當場看 MiMo 聽成什麼 |
| 最後耗時 / 平均耗時 | API 延遲（ms） |
| 請求總數 / 成功 / 失敗 / 今日請求數 | 成功率統計 |
| 今日 Token 消耗 / 累計 Token / 最後請求 Token | usage token 口徑 |
| 今日音訊秒數 / 今日預估費用 | 計費口徑（**¥0.5/小時**，官方費率） |
| 最後錯誤 | ok / auth / api / connection / timeout / empty |

## 語音格式（輸入 / 輸出）

| 方向 | 格式 |
|---|---|
| HA → 整合 | Assist pipeline 串流的原始 PCM（s16le, 16-bit） |
| 整合 → MiMo API | PCM 包成 **WAV** → Base64 → `data:audio/wav;base64,...` 放進 `input_audio`（上限 10 MB base64） |
| MiMo → 整合 | `choices[0].message.content` 純文字 + `usage.total_tokens` |
| 整合 → HA | `SpeechResult(text, SUCCESS)` 交回 pipeline |

## 安裝（HACS 自訂儲存庫）

1. HACS → 右上角三點 → **自訂儲存庫（Custom repositories）**
2. 貼上 repo URL：`https://github.com/Nyquist1992/xiaomi-mimo-stt`，類別選 **Integration（整合）**
3. HACS 清單出現「Xiaomi MiMo ASR (Speech-to-Text)」→ 點**下載**
4. **重啟 Home Assistant**
5. 設定 → 裝置與服務 → 新增整合 → 搜尋「Xiaomi MiMo ASR」→ 貼上 API Key

> HACS 之後有新版本時，同樣從 HACS 頁面點更新即可。

## 設定到 Voice Pipeline

設定 → 語音助理 → 你的 pipeline → Speech-to-Text 選 **Xiaomi MiMo ASR**。

## 取得 API Key

到 [mimo.mi.com](https://mimo.mi.com) 控制台申請（模型：`mimo-v2.5-asr`，計費 **¥0.5 / 音訊小時**）。
