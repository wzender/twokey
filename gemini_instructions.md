# **Project Specification: WhatsApp Levantine Arabic Tutor Bot**

## **1\. Project Overview**

We are building a Python-based WhatsApp Chatbot using the Meta Cloud API and Google Gemini 1.5 Flash.  
The bot acts as a language tutor. It gives the user a sentence in Hebrew, waits for the user to record a voice note translating it into Palestinian Arabic, and then uses AI to grade the pronunciation and grammar.

## **2\. Tech Stack**

* **Language:** Python 3.10+  
* **Web Framework:**  Fast api (to handle Webhooks)  
* **AI Model:** Google Gemini 1.5 Flash (via google-generativeai SDK)  
* **Messaging Platform:** WhatsApp Cloud API (Meta)  
* **Audio Handling:** Standard requests library to download WhatsApp media.  
* **State Management:** Simple in-memory Python dictionary (for MVP simplicity).

## **3\. Environment Variables**

The code must load the following from a .env file:

* WHATSAPP\_TOKEN: Meta Cloud API Access Token.  
* PHONE\_NUMBER\_ID: The Phone Number ID from the Meta Dashboard.  
* VERIFY\_TOKEN: A custom string for verifying the Webhook connection.  
* GEMINI\_API\_KEY: Google AI Studio API key.

## **4\. Application Logic & User Flow**

### **A. The Curriculum Data**

Create a hardcoded list of dictionaries in the code, acting as the "Database".  
Example structure:  
CURRICULUM \= \[  
    {"hebrew": "אני רוצה קפה", "target\_arabic": "בדי קהוה", "phonetic": "Bidi Kahwa"},  
    {"hebrew": "איפה השירותים?", "target\_arabic": "וין אל חמאם?", "phonetic": "Wein al hammam?"},  
    \# Add 2-3 more examples  
\]

### **B. State Management**

Maintain a global dictionary user\_state \= {}.  
Key: User's Phone Number.  
Value: {"current\_index": 0, "waiting\_for\_audio": False}.

### **C. Interactions**

1. **Command: "Start"**  
   * Bot checks if user exists in state. If not, create entry at index 0\.  
   * Bot retrieves the Hebrew sentence at current\_index.  
   * Bot sends WhatsApp Text: "Translate this to Palestinian Arabic: \[Hebrew Sentence\]".  
   * Update state: waiting\_for\_audio \= True.  
2. **User sends Audio (Voice Note)**  
   * Check if waiting\_for\_audio is True for this user.  
   * **Download:** Retrieve the audio file from WhatsApp (get URL via Media ID, then download binary). Save as .ogg or .mp3 temporarily.  
   * **Process (The AI Core):**  
     * Upload the audio file to Gemini 1.5 Flash.  
     * Send the Prompt (defined in Section 5 below).  
   * **Reply:** Send the AI's feedback text back to the user on WhatsApp.  
   * **Advance:** Increment current\_index.  
   * **Prompt Next:** Automatically send the *next* Hebrew sentence.  
3. **Command: "Reset"**  
   * Set current\_index to 0\.  
   * Send the first sentence.

## **5\. The Gemini AI Prompt Strategy**

When sending the audio to Gemini, use this specific system instruction/prompt structure:

Role: You are a friendly, encouraging Palestinian Arabic tutor.  
Task: The student is trying to translate the Hebrew phrase: "{hebrew\_phrase}" into Palestinian Arabic (Levantine dialect). The expected target is roughly "{target\_arabic}".  
Input: An audio file of the student speaking.  
Output: \> 1\. Transcribe what they actually said (in Arabic script).  
2\. Give a Score (0-100).  
3\. If the score is \< 100, explain the mistake (pronunciation or grammar) in simple English.  
4\. Be lenient with synonyms (e.g., 'Bidi' vs 'Haabeb' are both okay for 'want').

## **6\. Detailed Implementation Requirements**

### **file: requirements.txt**

Must include: flask, requests, google-generativeai, python-dotenv.

### **file: app.py**

* **Webhook Verification:** Implement the GET /webhook route to handle the hub.challenge from Meta.  
* **Message Handler:** Implement the POST /webhook route.  
  * Extract entry \-\> changes \-\> value \-\> messages.  
  * Handle text messages (for "Start" and "Reset").  
  * Handle audio messages (for the practice).  
* **Helper Functions:**  
  * send\_whatsapp\_message(to, body): Standard POST request to Meta Graph API.  
  * download\_media(media\_id): Logic to get the media URL and then download bytes.  
  * get\_ai\_feedback(audio\_path, target\_sentence): Function to interface with Gemini.

## **7\. Constraint Checklist**

* Do NOT use complex database setups (SQL/Mongo). Keep it in memory.  
* Ensure temporary audio files are deleted (os.remove) after processing.  
* Handle the case where the user sends audio *before* clicking Start (reply with "Type 'Start' to begin").