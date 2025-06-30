# CitingVerify - AI 驅動的引用文獻驗證系統

CitingVerify 是一個網頁工具，旨在自動驗證學術論文中參考文獻的真實性，以協助維護學術誠信。

本系統利用大型語言模型（LLM）來解析與分析引用文獻資料，提供了一個比傳統規則引擎更具彈性且強大的解決方案。使用者可以上傳 PDF 文件，系統將會擷取、解析並嘗試透過多個線上資料庫來驗證每一條參考文獻。

## ✨ 主要功能 (已實作)

*   **PDF 上傳與文字擷取**: 處理 PDF 檔案上傳並從中擷取全文內容。
*   **AI 驅動的解析**: 利用大型語言模型（如 Google 的 Gemini 和 DeepSeek）將非結構化的參考文獻字串解析為結構化資料（作者、年份、標題、來源）。
*   **支援多種模型**: 允許使用者直接在操作介面中選擇不同的 LLM 供應商和模型，以便進行比較分析。
*   **多步驟驗證流程**:
    1.  **直接 DOI 檢��**: 驗證包含 DOI 的參考文獻。
    2.  **API 搜尋**: 查詢如 CrossRef、Semantic Scholar 和 OpenAlex 等外部學術資料庫。
    3.  **AI 分析**: 對於無法驗證的文獻，由 LLM 提供最可能的失敗原因（例如「資訊不完整」、「非學術來源」）。
*   **即時進度顯示**: 前端透過串流連線，即時顯示每條參考文獻的驗證狀態。
*   **多語言介面**: 支援英文與中文。
*   **容器化環境**: 整個應用程式堆疊由 Docker 和 Docker Compose 管理，便於設定與實現一致的部署。

## 🛠️ 技術棧

*   **後端**: Python, FastAPI
*   **前端**: React, TypeScript
*   **資料庫**: PostgreSQL (用於資料持久化), Redis (用於快取與任務佇列)
*   **PDF 處理**: `PyPDF2`
*   **AI 整合**: `google-generativeai` (用於 Gemini), `openai` (用於 DeepSeek)
*   **部署**: Docker, Docker Compose

## 🚀 開始使用

### 環境需求

*   您的電腦上已安裝 Docker 和 Docker Compose。
*   已安裝 Git 用於複製專案。
*   擁有您想使用的語言模型（Google Gemini, DeepSeek）的 API 金鑰。

### 1. 複製專案

```bash
git clone <your-repository-url>
cd citingVerify
```

### 2. 設定環境變數

本系統需要 API 金鑰才能運作。您需要在專案的根目錄下建立一個 `.env` 檔案。

```bash
# 建立 .env 檔案 (Windows 使用者可以在檔案總管中手動建立)
touch .env
```

接著，打開 `.env` 檔案並填入您的 API 金鑰。此檔案已被列在 `.gitignore` 中，不會被提交到版本庫。

```
# .env 檔案內容

# 必要：請從 Google AI Studio 取得您的金鑰
GEMINI_API_KEY=your_google_gemini_api_key

# 選用：請從 DeepSeek 平台取得您的金鑰
DEEPSEEK_API_KEY=your_deepseek_api_key
```

### 3. 建置並執行應用程式

在 Docker 正在運行的狀態下，使用 Docker Compose 來建置映像檔並在背景啟動所有服務。

```bash
docker-compose up -d --build
```

*   `up -d`: 在分離模式（detached mode）下啟動服務。
*   `--build`: 強制重新建置 Docker 映像檔，這在修改程式碼（例如新增 Python 套件）後是必要的步驟。

服務啟動後，您可以透過以下網址存取：
*   **前端介面**: [http://localhost:3000](http://localhost:3000)
*   **後端 API 文件**: [http://localhost:8000/docs](http://localhost:8000/docs)

### 4. 使用應用程式

1.  打開您的網頁瀏覽器，前往 `http://localhost:3000`。
2.  從下拉選單中選擇您想使用的 AI 模型。
3.  點擊「選擇 PDF 檔案」以上傳您的學術論文。
4.  點擊「開始驗證」以啟動流程。
5.  觀察即時日誌和結果表格，系統將會開始處理您的文件。

### 5. 停止應用程式

若要停止所有正在運行的服務，請執行：

```bash
docker-compose down
```
