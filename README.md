# Xiaomi MiMo ASR — Home Assistant STT Integration

把小米 MiMo-V2.5-ASR 接進 Home Assistant Assist Pipeline 的自訂 STT 整合。
參考 [hass-cortex/xiaomi-mimo-tts](https://github.com/hass-cortex/xiaomi-mimo-tts)（同家族 TTS 整合）的 client / config flow 設計。

## 功能

- 完整 UI 設定（Config Flow）：安裝後在「設定 → 裝置與服務 → 新增整合」搜尋 **Xiaomi MiMo ASR**，貼上 API Key 即完成，**金鑰即時驗證**（`GET /v1/models`）。
- 換 key 不用碰 YAML：整合頁面「重新設定」可更換 API Key 與預設語言；key 失效會觸發 reauth 流程。
- 支援語言：`zh` / `en` / `auto`（HA 端另宣告 `zh-tw`、`zh-hk`、`zh-hant`，讓繁中 intent 正確載入，API 端自動映射為 `zh`）。

## 語音格式（輸入 / 輸出）

| 方向 | 格式 |
|---|---|
| HA → 整合 | Assist pipeline 串流的原始 PCM（s16le, 16-bit） |
| 整合 → MiMo API | PCM 包成 **WAV** 容器 → Base64 → `data:audio/wav;base64,...` 放進 `input_audio`（上限 10 MB base64） |
| MiMo → 整合 | `choices[0].message.content` 純文字 |
| 整合 → HA | `SpeechResult(text, SUCCESS)` 交回 pipeline |

## 安裝（HACS 自訂儲存庫）

1. 把這個 repo 推到你的 GitHub（例如 `Nyquist1992/xiaomi-mimo-stt`）
2. HACS → 右上角三點 → **自訂儲存庫（Custom repositories）**
3. 貼上 repo URL：`https://github.com/Nyquist1992/xiaomi-mimo-stt`，類別選 **Integration（整合）**
4. HACS 清單會出現「Xiaomi MiMo ASR (Speech-to-Text)」→ 點**下載**
5. **重啟 Home Assistant**
6. 設定 → 裝置與服務 → 新增整合 → 搜尋「Xiaomi MiMo ASR」→ 貼上 API Key

> HACS 之後有新版本時，同樣從 HACS 頁面點更新即可。

## 手動安裝（備用）

把 `custom_components/xiaomi_mimo_stt/` 整個資料夾複製到 HA 的 `config/custom_components/` 下，重啟 HA。

## 設定到 Voice Pipeline

1. 設定 → 語音助理 → 你的 pipeline（例如 EGMI）
2. Speech-to-Text 選 **Xiaomi MiMo ASR**
3. 完成 — 平板 Voice Satellite、手機瀏覽器、任何 Assist 衛星都會改用它

## 取得 API Key

到 [mimo.mi.com](https://mimo.mi.com) 控制台申請（模型：`mimo-v2.5-asr`，按量計費）。

## 檔案結構

```
custom_components/xiaomi_mimo_stt/
├── manifest.json      # 整合清單
├── const.py           # 常數 / 語言映射
├── client.py          # MiMo ASR API client（純 Python，不依賴 HA 框架）
├── config_flow.py     # UI 設定流程（首次設定 / 換 key / 重新設定）
├── stt.py             # STT entity（PCM→WAV→Base64→API→文字）
├── strings.json       # 字串來源
└── translations/      # en.json / zh-Hant.json
```
