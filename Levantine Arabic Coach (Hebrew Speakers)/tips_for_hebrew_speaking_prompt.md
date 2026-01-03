Use the provided MD files as the **sole authoritative references**.


---

## **Task**

For each of the sentences, populate `tips_for_hebrew_speaking` **strictly and exclusively** based on
`hebrew_speaking_arabic_mistakes.md`.


---

## **Hard rules (non-negotiable)**

### 1. **Source restriction**

* Every tip **must map directly** to a mistake category **explicitly listed** in
  `hebrew_speaking_arabic_mistakes.md`.
* **No phonetic, pedagogical, or linguistic rules may be invented, inferred, generalized, or reinforced.**


---

### 2. **Grapheme validation — HARD FAIL**

A tip is allowed **only if all three conditions hold**:

* The **exact Arabic grapheme** appears in `accepted_answers`
* The **same phonetic feature** is explicitly represented in `answer_he_tatiq`
* The issue is **explicitly defined** in `hebrew_speaking_arabic_mistakes.md`

🚫 **No grapheme → hard fail**

* If the Arabic grapheme does not exist in `accepted_answers`, the tip **must not be generated**.
* Do **not** replace it with a “nearby”, “implicit”, or “commonly confused” feature.


---

### 3. **Word anchoring**

* `word` must appear **verbatim** in `answer_he_tatiq`
* No normalization, paraphrasing, or reconstruction


---

### 4. **Tip scope**

* Provide **2–3 tips per sentence**
* If fewer than 2 guideline-compliant tips exist:
  * **Do not fabricate**
  * Output **only the valid tips**
* Never exceed 3 tips
* Multiple tips **may** refer to the same word, provided each meets all rules


---

### 5. **Forbidden content**

* ❌ General pronunciation advice
* ❌ Hebrew-only phonetic guidance
* ❌ Reinforcement rules (e.g., “כּ סגורה”, “ב רפה”) unless explicitly listed
* ❌ IPA, linguistic theory, teacher intuition, or “helpful” additions


---

### 6. **Output discipline**

* Apply this process to **all 15 sentences**
* Maintain **strict JSON structure** as defined in
  `how_to_convert_input_to_lesson_json.md`
* No explanatory text outside the JSON


---

## **Goal**

Produce a lesson file where **every tip is mechanically verifiable**,
**auditable against the MD**, and **fails closed rather than guessing**.


---

אם תרצי, השלב הבא הטבעי הוא:

* 🔐 **Validator rule**: `if grapheme not in accepted_answers → throw error`
* 🧠 **System prompt** שמונע ממודל לנסות “להיות חכם”

זה כבר לא Prompt.
זה **spec**.
