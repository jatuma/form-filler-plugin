---
name: pdf-form-filler
description: Fill PDF forms automatically using stored personal and family information. Use this skill when the user wants to fill out a PDF form (school enrollment, medical forms, government documents, permission slips, etc.) with their own or a family member's data. Triggers on phrases like "fill this form", "fill out this PDF", "fill for my son/daughter/child/wife/husband", or when a PDF form is provided with a request to complete it. Handles both fillable PDF forms (with interactive fields) and flat/scanned forms. Remembers personal data across sessions — asks for unknown info and saves it for future use.
---

# PDF Form Filler

Fill PDF forms using stored personal and family data. Ask for anything unknown and save it.

## Data Storage

Personal data is stored at `~/.config/pdf-form-filler/personal_data.json` by default.
Override by setting the `PDF_FORM_FILLER_DATA` environment variable to any path (useful for synced/shared storage):
```bash
export PDF_FORM_FILLER_DATA="/path/to/Dropbox/personal_data.json"
```
Management script: `${CLAUDE_PLUGIN_ROOT}/skills/pdf-form-filler/scripts/manage_data.py`

### First-time Setup

If the data file does not exist, **ask the user where they want to store it before initializing**:

> I need to create a file to store your personal data. Where should I save it?
> - **Default** – `~/.config/pdf-form-filler/personal_data.json` (local only)
> - **Synced** – a path inside Dropbox, OneDrive, iCloud Drive, etc. (shared across devices)
>
> If you choose a synced path, also add `export PDF_FORM_FILLER_DATA="<path>"` to your shell profile so it's used automatically in future sessions.

Then initialize with the chosen path (use `--data-file` if not the default):
```bash
# Default path
python "${CLAUDE_PLUGIN_ROOT}/skills/pdf-form-filler/scripts/manage_data.py" init

# Custom/synced path
python "${CLAUDE_PLUGIN_ROOT}/skills/pdf-form-filler/scripts/manage_data.py" init --data-file "/path/to/synced/personal_data.json"
```
Then ask the user for basic info about themselves and family members before proceeding with the form.

### Data Operations

```bash
# Show all data or a specific member
python "${CLAUDE_PLUGIN_ROOT}/skills/pdf-form-filler/scripts/manage_data.py" show
python "${CLAUDE_PLUGIN_ROOT}/skills/pdf-form-filler/scripts/manage_data.py" show --member child_1

# Update one field (dot notation for nested fields)
python "${CLAUDE_PLUGIN_ROOT}/skills/pdf-form-filler/scripts/manage_data.py" update --member child_1 --field first_name --value "Jan"
python "${CLAUDE_PLUGIN_ROOT}/skills/pdf-form-filler/scripts/manage_data.py" update --member child_1 --field health.allergies --value "pollen"

# Update multiple fields at once
python "${CLAUDE_PLUGIN_ROOT}/skills/pdf-form-filler/scripts/manage_data.py" batch-update --member parent_1 --updates '{"first_name":"Petr","last_name":"Novák"}'

# Add a new family member
python "${CLAUDE_PLUGIN_ROOT}/skills/pdf-form-filler/scripts/manage_data.py" add-member --id child_2 --role child

# Find what's missing for a member
python "${CLAUDE_PLUGIN_ROOT}/skills/pdf-form-filler/scripts/manage_data.py" find-gaps --member child_1
python "${CLAUDE_PLUGIN_ROOT}/skills/pdf-form-filler/scripts/manage_data.py" find-gaps --member child_1 --fields "first_name,last_name,date_of_birth,health"
```

## Workflow

Follow these steps in order for every form-filling request:

### Step 1: Load Personal Data

1. Run `python "${CLAUDE_PLUGIN_ROOT}/skills/pdf-form-filler/scripts/manage_data.py" show` to load all stored data.
2. If the command fails (file not found), this is the first use — follow the **First-time Setup** procedure above (ask about storage location, then `init`), then collect basic family info before continuing.

### Step 2: Identify the Target Person

Determine who the form is for based on the user's request:
- "fill this for my son" → match to a child member
- "fill this form" (no specification) → ask who it's for
- "fill with my info" → use the parent member (usually parent_1)

If the family has multiple children and the request is ambiguous (e.g., "for my kid"), ask which child.

### Step 3: Analyze the PDF Form

Use the PDF skill's form analysis workflow. Read `/mnt/skills/public/pdf/FORMS.md` and follow its instructions to determine whether the PDF has fillable fields or needs annotation-based filling.

**Key steps from FORMS.md:**
1. Check for fillable fields: `python /mnt/skills/public/pdf/scripts/check_fillable_fields.py <file.pdf>`
2. If fillable → use `extract_form_field_info.py` + `fill_fillable_fields.py`
3. If not fillable → use `extract_form_structure.py` or visual approach + `fill_pdf_form_with_annotations.py`

### Step 4: Map Form Fields to Personal Data

After analyzing the form fields, map each field to the corresponding personal data:

**Common Czech school form mappings:**
- Jméno / Křestní jméno → first_name
- Příjmení → last_name
- Datum narození → date_of_birth
- Rodné číslo → birth_number
- Místo narození → place_of_birth
- Státní občanství → citizenship
- Národnost → nationality
- Trvalé bydliště / Adresa → permanent_address.*
- Zdravotní pojišťovna → health.insurance_company
- Číslo pojištěnce → health.insurance_number
- Registrující lékař → health.pediatrician
- Alergie → health.allergies
- Zákonný zástupce / Rodič → parent member data
- Telefon → phone
- E-mail → email
- Zaměstnavatel → employer
- Škola / Třída → school.name / school.class

Also recognize common fields in English: Name, Date of birth, Address, Phone, etc.

### Step 5: Ask for Missing Data

1. Run `find-gaps` for the target member, filtered to only the fields needed by this form.
2. Compile a list of what's needed but missing.
3. Ask the user for ALL missing values in a **single grouped question** — do not ask one field at a time.

**Example prompt to user:**
> To fill this form for Jan, I need a few things I don't have yet:
> - Birth number (rodné číslo)
> - Health insurance company
> - Insurance number
>
> Could you provide these?

### Step 6: Save New Data

After the user provides missing values, **immediately save them** using `batch-update` before filling the form. This ensures the data is available for future forms.

```bash
python "${CLAUDE_PLUGIN_ROOT}/skills/pdf-form-filler/scripts/manage_data.py" batch-update --member child_1 --updates '{"birth_number":"1503151234","health.insurance_company":"VZP","health.insurance_number":"1503151234"}'
```

If the user provides info about a new family member not yet in the data (e.g., mentions a second child for the first time), add the member first with `add-member`, then `batch-update`.

### Step 7: Fill the Form

Follow the appropriate path from FORMS.md (fillable or non-fillable) using the mapped data to create the filled PDF.

### Step 8: Verify and Deliver

1. Convert the filled PDF to images and visually verify placement.
2. Present the filled PDF to the user.
3. If anything looks off, adjust and re-fill.

## Important Notes

- **Czech diacritics**: Always preserve characters like č, ř, ž, š, ě, á, í, etc. in all data and form filling.
- **Date format**: Czech forms typically use DD.MM.YYYY. Store dates as YYYY-MM-DD internally but format for output as the form expects.
- **Address format**: Czech format is typically "Ulice číslo, PSČ Město" (e.g., "Květná 15, 150 00 Praha 5").
- **Birth number format**: Rodné číslo is XXXXXX/XXXX (6+4 digits). Some forms use the slash, some don't.
- **Multiple parents on form**: Many school forms have fields for both parents/guardians. Fill both parent_1 and parent_2 data when the form requires it.
- **Signature fields**: Leave signature fields empty and note to the user they need to sign manually.
- **Today's date**: When the form has a "Datum" or "Date" field for when the form is filled, use today's date.
