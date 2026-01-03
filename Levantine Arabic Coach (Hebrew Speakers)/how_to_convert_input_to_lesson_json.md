# How to Convert a Day/Lesson Sentence List into the JSON Lesson File

## Input → JSON (v1)

This guide describes how to convert a user-provided lesson list into a JSON array of sentence objects.


---

## 1) What you start with (Input)

You have:


1. `day_id` (single number)
2. `lesson_id` (single number)
3. A list of rows, each row contains **three columns** in this exact order:

* **Column A:** Hebrew sentence (`prompt_he`)
* **Column B:** Hebrew transliteration of the Arabic sentence (`answer_he_tatiq`)
* **Column C:** Arabic sentence in Arabic script (`accepted_answers`)

Rows may be tab-separated, CSV-like, or line-based with clear column separation.


---

## 2) What you need to produce (Output)

A JSON **array** of objects.

Each object must follow this format:

```json
{
  "day_id": 2,
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

Notes:

* `accepted_answers` is stored as a **string** (not an array) unless you explicitly support multiple alternatives later.
* `tips_for_hebrew_speaking` is an **array** (may be empty `[]`).
* Arabic script is allowed in `accepted_answers` only.


---

## 3) Step-by-step conversion rules

### Step 3.1 — Clean the rows

For each row:

* Trim leading/trailing whitespace in all three columns
* Remove completely empty rows
* Keep punctuation as-is (do not “fix” spelling)

### Step 3.2 — Assign `sentence_id`

* The first row is `sentence_id = 1`
* Increase by 1 for each subsequent row

### Step 3.3 — Map columns to fields

For each row:

* `prompt_he` = Column A (Hebrew sentence)
* `answer_he_tatiq` = Column B (Hebrew transliteration)
* `accepted_answers` = Column C (Arabic script sentence)
* `day_id` and `lesson_id` = the global input values (same for all rows)

### Step 3.4 — Add tips

For each sentence object, add:

```json
"tips_for_hebrew_speaking": []
```

Then (optional) populate tips with **sentence-specific** items.

#### Tip item rules (strict)

A tip item is a dictionary with:

* `word`: must appear **verbatim** inside `answer_he_tatiq`
* `issue`: short label of the common mistake (e.g., "خ", "סיומת ֵין")
* `guidance_he`: short Hebrew guidance

If you are not adding tips yet, keep the array empty.


---

## 4) Example conversion

### Example input

* `day_id = 2`
* `lesson_id = 4`

List rows (3 columns per row):

```
לפני שבועיים הדוד שלי ישב בבית ושאל אותי איפה אמא שלי.	קַבֵּל אֻסְבּוּעֵין חַ'אלִי קַעַד פִי אֵלְבֵּית וּסַאַלְנִי וֵין אִמִّי.	قبل أسبوعين خالي قعد في البيت وسألني وين أمي.
שמי פאטמה, מה שמך? נעים להכיר, אני איבתיסאם.	אִסְמִי פַאטְמֵה, שוּ אִסְמֵכּ? תַשַרַّפְנַא, אַנַא אִבְּתִסַאן.	اسمي فاطمة، شو اسمِك؟ تشرفنا، أنا ابتسام.
```

### Example output JSON

```json
[
  {
    "day_id": 2,
    "lesson_id": 4,
    "sentence_id": 1,
    "prompt_he": "לפני שבועיים הדוד שלי ישב בבית ושאל אותי איפה אמא שלי.",
    "accepted_answers": "قبل أسبوعين خالي قعد في البيت وسألني وين أمي.",
    "answer_he_tatiq": "קַבֵּל אֻסְבּוּעֵין חַ'אלִי קַעַד פִי אֵלְבֵּית וּסַאַלְנִי וֵין אִמִّי.",
    "tips_for_hebrew_speaking": [
      {
        "word": "אֻסְבּוּעֵין",
        "issue": "סיומת ֵין",
        "guidance_he": "לסיים ״ֵין״ ארוך וברור"
      },
      {
        "word": "חַ'אלִי",
        "issue": "خ",
        "guidance_he": "ח׳/خ גרונית, לא ח׳ עברית"
      }
    ]
  },
  {
    "day_id": 2,
    "lesson_id": 4,
    "sentence_id": 2,
    "prompt_he": "שמי פאטמה, מה שמך? נעים להכיר, אני איבתיסאם.",
    "accepted_answers": "اسمي فاطمة، شو اسمِك؟ تشرفنا، أنا ابتسام.",
    "answer_he_tatiq": "אִסְמִי פַאטְמֵה, שוּ אִסְמֵכּ? תַשַרַّפְנַא, אַנַא אִבְּתִסַאן.",
    "tips_for_hebrew_speaking": []
  }
]
```


---

## 5) Common mistakes to avoid

* Do not swap the transliteration and Arabic columns
* Do not skip `sentence_id` numbering
* Do not put Arabic script in `answer_he_tatiq`
* Every `tips_for_hebrew_speaking.word` must appear in `answer_he_tatiq` exactly (otherwise remove that tip)


---

## 6) Output file naming suggestion

Use a consistent name pattern, for example:

* `day_2_lesson_4.json`


