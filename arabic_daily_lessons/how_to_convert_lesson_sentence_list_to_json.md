# How to Convert a Lesson Sentence List into the JSON Lesson File  

## 1) What you start with (Input)

You have:

1. `lesson_id` (single number)  
2. A list of rows, each row contains **three columns** in this exact order:

- **Column A:** Hebrew sentence (`prompt_he`)
- **Column B:** Hebrew transliteration of the Arabic sentence (`answer_he_tatiq`)
- **Column C:** Arabic sentence in Arabic script (`accepted_answers`)

Rows may be tab-separated, CSV-like, or line-based with clear column separation.

---

## 2) What you need to produce (Output)

A JSON **array** of objects.

Each object **must** follow this format:

```json
{
  "lesson_id": 4,
  "sentence_id": 1,
  "prompt_he": "…",
  "accepted_answers": "…",
  "answer_he_tatiq": "…",
  "tips_for_hebrew_speaking": [
    {
      "word": "…",
      "issue": "…",
      "guidance_he": "…"
    }
  ]
}
```

- `tips_for_hebrew_speaking` is **mandatory**
- Empty array is allowed **only if no valid tips pass all rules**
- Arabic script is allowed **only** in `accepted_answers`

---

## 3) Conversion Rules

### 3.1 Row cleaning
- Trim whitespace in all columns
- Remove empty rows
- Preserve punctuation and spelling

### 3.2 sentence_id
- First row → `sentence_id = 1`
- Increment sequentially

### 3.3 Field mapping
- `prompt_he` ← Column A
- `answer_he_tatiq` ← Column B
- `accepted_answers` ← Column C
- `lesson_id` ← global input value

---

## 4) Mandatory tips_for_hebrew_speaking Population

For **every sentence**, you must attempt to populate `tips_for_hebrew_speaking`
**strictly and exclusively** based on:

`hebrew_speaking_arabic_mistakes.md`

No other source is permitted.

---

## 5) Hard Rules (Fail-Closed)

### 5.1 Source restriction
- Every tip must map directly to a mistake category explicitly listed in the MD
- No invention, inference, generalization, or reinforcement

### 5.2 Grapheme + Phoneme-Class validation (Fail-Closed)
A tip is allowed **only if all three conditions hold**:

1. **Exact Arabic grapheme appears in `accepted_answers`**  
2. **A matching validated phoneme class is explicitly represented in `answer_he_tatiq`**  
3. The issue is explicitly defined in `hebrew_speaking_arabic_mistakes.md`

If any condition fails → **no tip** (fail closed).

#### 5.2.1 Validated phoneme classes (required legend)
To make rule (2) mechanical, `answer_he_tatiq` must use a **validated transliteration legend**.

A phoneme class match is valid only if the transliteration contains an explicit marker from the legend
that uniquely identifies the class.

**Approved classes (minimum set):**
- **{HAA vs KHAA}**: ح vs خ  
- **{AYN}**: ع  
- **{QAAF}**: ق  
- **{EMPHATIC TAA}**: ط  
- **{EMPHATIC SAAD}**: ص  
- **{EMPHATIC DAD}**: ض  
- **{SHEEN}**: ش  
- **{LONG AA}**: ـا (long /aa/)

**Legend requirement (non-negotiable):**
- The project must define a small legend that maps **each phoneme class → one or more allowed markers** in `answer_he_tatiq`.
- A tip may be created only when the marker is present in the exact `word` extracted from `answer_he_tatiq`.

**Examples (illustrative — your project’s legend is the authority):**
- Khāʾ (خ) might be marked as `ח'` in the transliteration word
- ʿAyn (ع) might be marked as `ע` in the transliteration word
- Qāf (ق) might be marked as `ק̣` / `q` / another unique marker you standardize

If the transliteration does not contain an explicit legend marker → **no tip**.

### 5.3 Word anchoring
- `word` must appear **verbatim** in `answer_he_tatiq`
- No normalization, fixing, or reconstruction

### 5.4 Tip scope
- 2–3 tips per sentence
- If fewer than 2 valid tips exist: output only valid tips
- Never exceed 3 tips
- Multiple tips may reference the same word if each passes all rules

### 5.5 Forbidden content
- General pronunciation advice
- Hebrew-only phonetic explanations
- IPA or linguistic theory
- Teacher intuition or helpful additions

---

## 6) Output Discipline
- Apply to **all sentences**
- Maintain strict JSON structure
- No explanatory text outside JSON

---

## Design Principle

If a tip cannot be mechanically verified against:
- the Arabic grapheme,
- the **validated phoneme-class marker** in the transliteration,
- and the mistakes MD,

it must not exist.

Fail closed. Guessing is forbidden.
