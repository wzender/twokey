That's a great start! To maximize the effectiveness of `GEMINI.md`, we need to structure it clearly and add specific technical and architectural details. The AI needs to know *how* this is built, not just *what* it does.

Here is an improved version of your `GEMINI.md`, broken down into key sections:

---

## 🚀 GEMINI.md: Language Practice Bot

### 🎯 1. Project Goal & Scope

The core purpose of this project is to create an interactive virtual language practice teacher via **WhatsApp**. It focuses specifically on conversational practice in non-standardized dialects, starting with **Levantine Arabic**.

### 🛠️ 2. Technology Stack & Architecture

This section is crucial for code assistance.

| Component | Technology | Role/Details |
| :--- | :--- | :--- |
| **Backend** | **Python (v3.10+)** | Primary language for all logic, grading, and API calls. |
| **Framework** | **FastAPI** | Used to handle incoming webhooks and manage internal APIs. |
| **Messaging** | **Twilio (WhatsApp API)** | Handles all incoming/outgoing messages (text and voice notes). |
| **AI/LLM** | **Google Gemini API** | Used for conversation flow management, grading, and linguistic analysis. |
| **Database** | **SQLite** | Simple storage for user session data and conversation history. |

### 🗣️ 3. Main User Flow (User Story)

The entire conversation flow is driven by **Twilio webhooks** triggering the FastAPI backend.

1.  **Start Session:** User sends a message containing the keyword "**START**" (case-insensitive).
2.  **Initial Prompt:** The virtual teacher sends a random, short phrase or sentence **in Levantine Arabic (text)**.
3.  **User Response:** The student records a **voice note** in Levantine Arabic.
    * *System Note:* The voice note must be transcribed using a suitable ASR service before being sent to the Gemini API.
4.  **Teacher Feedback (Grading):**
    * The teacher sends a grade (e.g., A+, B-, C).
    * The teacher provides **1-2 sentences of specific dialect feedback**, focusing on pronunciation, vocabulary errors, or grammatical structures specific to the Levantine dialect.

### ✨ 4. Coding Standards & Conventions

The code agent must adhere to the following style guidelines:

* **Language:** Python (v3.10+).
* **Variable/Function Naming:** Use **`snake_case`** for all Python identifiers.
    * *Example:* `handle_incoming_message(message_sid)`
* **Type Hinting:** All new Python functions must use **standard Python type hints**.
* **Dependencies:** Manage dependencies using **`pipenv`**. Check the `Pipfile` before adding new packages.
* **File Structure:** All core logic related to the WhatsApp interactions resides in **`app/routes.py`**.

### 🛑 5. Constraints & Exclusions

* **Sensitive Data:** Never hardcode API keys or secrets. Reference environment variables only (e.g., `os.environ["TWILIO_AUTH_TOKEN"]`).
* **Dialect Focus:** All LLM prompts must explicitly instruct the model to use **Levantine Arabic (Shami)** dialect for feedback and conversational prompts.
* **Testing:** New feature contributions must include corresponding tests in the **`tests/`** directory using the `pytest` framework.

---

This improved version gives Gemini Code Assist the **architectural, technical, and stylistic context** it needs to write high-quality, relevant code suggestions.

Is there a specific part of the code you are working on right now (e.g., the Twilio webhook handler or the grading logic) that I can help you with?