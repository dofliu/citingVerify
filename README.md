# CitingVerify - AI-Powered Citation Verification System

CitingVerify is a web-based tool designed to automatically verify the authenticity of academic references within a paper, helping to uphold academic integrity.

This system leverages Large Language Models (LLMs) to parse and analyze citation data, offering a flexible and powerful alternative to traditional rule-based engines. Users can upload a PDF document, and the system will extract, parse, and attempt to verify each reference against multiple online databases.

## ✨ Key Features (Implemented)

*   **PDF Upload & Text Extraction**: Handles PDF file uploads and extracts the full text content.
*   **AI-Powered Parsing**: Utilizes LLMs (like Google's Gemini and DeepSeek) to parse unstructured reference strings into structured data (authors, year, title, source).
*   **Multi-Model Support**: Allows users to choose from different LLM providers and models directly in the user interface for comparative analysis.
*   **Multi-Step Verification**:
    1.  **Direct DOI Check**: Validates references that contain a DOI.
    2.  **API-based Search**: Queries external academic databases like CrossRef, Semantic Scholar, and OpenAlex.
    3.  **AI-based Analysis**: For unverified references, an LLM provides a likely reason for the failure (e.g., "Incomplete Information", "Non-Academic Source").
*   **Real-time Progress**: The frontend displays the verification status of each reference in real-time using a streaming connection.
*   **Multilingual UI**: Supports both English and Chinese.
*   **Containerized Environment**: The entire application stack is managed with Docker and Docker Compose for easy setup and consistent deployment.

## 🛠️ Tech Stack

*   **Backend**: Python, FastAPI
*   **Frontend**: React, TypeScript
*   **Database**: PostgreSQL (for data persistence), Redis (for caching and task queues)
*   **PDF Processing**: `PyPDF2`
*   **AI Integration**: `google-generativeai` (for Gemini), `openai` (for DeepSeek)
*   **Deployment**: Docker, Docker Compose

## 🚀 Getting Started

### Prerequisites

*   Docker and Docker Compose installed on your machine.
*   Git for cloning the repository.
*   API keys for the desired language models (Google Gemini, DeepSeek).

### 1. Clone the Repository

```bash
git clone <your-repository-url>
cd citingVerify
```

### 2. Set Up Environment Variables

The system requires API keys to function. You will need to create a `.env` file in the project root directory.

```bash
# Create the .env file
touch .env
```

Now, open the `.env` file and add your API keys. This file is listed in `.gitignore` and will not be committed to the repository.

```
# .env file

# Required: Get your key from Google AI Studio
GEMINI_API_KEY=your_google_gemini_api_key

# Optional: Get your key from DeepSeek's platform
DEEPSEEK_API_KEY=your_deepseek_api_key
```

### 3. Build and Run the Application

With Docker running, use Docker Compose to build the images and start the services in the background.

```bash
docker-compose up -d --build
```

*   `up -d`: Starts the services in detached mode.
*   `--build`: Forces a rebuild of the Docker images, which is necessary after code changes (like adding new Python packages).

The services will be available at:
*   **Frontend**: [http://localhost:3000](http://localhost:3000)
*   **Backend API**: [http://localhost:8000/docs](http://localhost:8000/docs)

### 4. Using the Application

1.  Open your web browser and navigate to `http://localhost:3000`.
2.  Select the AI model you wish to use from the dropdown menu.
3.  Click "Choose a PDF File" to upload your academic paper.
4.  Click "Start Verification" to begin the process.
5.  Observe the real-time log and results table as the system processes your document.

### 5. Stopping the Application

To stop all running services, execute:

```bash
docker-compose down
```
