# Add `phoneme_key` per sentence (industrial-grade Voice Mode)

## What you’re adding
For every sentence record, add a new field:

- `phoneme_key`: a **consonant skeleton** (plus a few stable markers) that is robust to:
  - Hebrew-accent substitutions (ق→ك, ع dropped, emphatics softened)
  - ASR spelling variability
  - Optional الـ / عالـ surface forms
  - Small word-order noise

You’ll use `phoneme_key` **only for evaluation**, never for display.

---

## Updated JSON schema (per sentence)
```json
{
  "lesson_id": 2,
  "sentence_id": 3,
  "prompt_he": "הוא ישב על הכיסא ואכל פלאפל",
  "accepted_answers": "هو قعد على الكرسي وأكل فلافل",
  "answer_he_tatiq": "הוּّ קַעַד עַלַא אֵלְכֻּרְסִי וּאַכַּל פַלַאפֵל",
  "phoneme_key": "HW|Q3D|3L|KRSY|W|AKL|FLFL"
}
```

Notes:
- The delimiter format is intentionally simple: `|` between tokens.
- Example above shows **conceptual** output; your generator defines the exact mapping rules below.

---

## Generator: how to compute `phoneme_key`

### Input preference order
1) If `accepted_answers` is available (Arabic script) → use it (best)
2) Else fall back to `answer_he_tatiq` (Hebrew transliteration) → use translit rules

### Step 1 — Normalize text
Apply to input text before tokenizing:
- Remove punctuation, tatweel, diacritics
- Normalize Alef: أ/إ/آ → ا
- Normalize Ya: ى → ي
- Remove definite article effect for keying:
  - Strip leading `ال` from nouns (comparison-only)
- Expand/normalize clitics:
  - `عال` → `على ال` (comparison-only)
- Collapse whitespace

### Step 2 — Tokenize
Split on whitespace into tokens.

### Step 3 — Drop weak tokens (optional but recommended)
Remove tokens that ASR frequently mangles and don’t carry meaning:
- Coordinators and fillers if desired: و, يا (keep `و` only if you want sequencing stability)
- If you keep `و`, keep it as token `W`.

### Step 4 — Map each token to a consonant key
For each token, create a canonical consonant skeleton:

#### 4.1 Consonant extraction (Arabic script)
- Keep only letters from: ب ت ث ج ح خ د ذ ر ز س ش ص ض ط ظ ع غ ف ق ك ل م ن ه و ي ء
- Drop short vowels (diacritics already removed)
- Optionally keep long-vowel carriers only if they are consonantal in context:
  - Keep و / ي when they are part of the stem (practical rule: always keep them; it’s fine)

#### 4.2 Phoneme tolerance mapping (collapse confusables)
Apply these canonicalizations **inside the key**:
- ق → K
- ك → K
- ع → A (or drop entirely; choose one and stick to it)
- ء → (drop)
- ح → H
- ه → H
- خ → KH (or H if you want heavier tolerance)
- ث → T
- ذ → D
- ظ → Z
- ص → S
- ض → D
- ط → T
- غ → GH (or R if you want heavy Hebrew tolerance)
- ش → SH (or S if you want heavier tolerance)

Everything else maps to its Latin-ish mnemonic:
- ب B, ت T, ج J, د D, ر R, ز Z, س S, ف F, ل L, م M, ن N, و W, ي Y

### Step 5 — Token compaction
To keep keys stable and short:
- Remove repeated identical letters: `KKRRSY` → `KRSY`
- Keep at least 2 characters per token unless it is a pronoun/particle you intentionally keep

### Step 6 — Preserve meaning-critical anchors (recommended)
Always preserve separate tokens for:
- Pronouns: هو/هي/إنت/إحنا/هم…
- Prepositions: في/على/مع/لـ
- Main verbs: فتح/قعد/أكل/سأل…

This prevents the key from accepting “wrong meaning but similar sound.”

### Step 7 — Join into `phoneme_key`
Join mapped tokens with `|`.

---

## Using `phoneme_key` in EVALUATE

### Evaluation pipeline (replace raw-string compare)
1) Compute `student_key` from student ASR transcript using the **same generator**
2) Compare `student_key` to `expected phoneme_key` with:
   - Sliding token window (±2 tokens)
   - Must-pass anchors (pronouns, verb, prepositions)
   - Overall token match threshold (e.g., ≥70%)

### Pass rules
CORRECT if:
- All anchors match
- Token match ≥ threshold

INCORRECT if:
- Any anchor fails
- Token match below threshold

### Coaching
If anchors pass but a mapped phoneme indicates accent drift (e.g., KH→H), accept but coach briefly in Hebrew.

---

## Practical threshold recommendations
- Short sentences (≤5 tokens): require ≥80% token match
- Medium (6–9 tokens): ≥70%
- Long (10+ tokens): ≥65%

Always enforce anchors strictly regardless of length.

---

## Implementation note (no fluff)
If you ever change the mapping rules, you must **recompute phoneme_key for all sentences**,
or you’ll get silent false negatives. The machine will not forgive you. 🙂

---

### END OF FILE
