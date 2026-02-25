# PDF Form Filler

Claude Code plugin for filling PDF forms with stored personal/family data. Designed for Czech school forms but works with any PDF.

## Install

Clone this repo and add it as a local plugin in Claude Code:

```bash
git clone https://github.com/<your-username>/form-filler-plugin.git
```

Then add the cloned directory as a local plugin in **Claude Code Settings → Plugins → Add local plugin**.

Claude Code will detect `.claude-plugin/plugin.json` and register the `pdf-form-filler` skill automatically.

## Use

Drop a PDF and say "fill this for my son" or "fill with my info". Claude asks for missing data once and remembers it.

## Data

Stored at `~/.config/pdf-form-filler/personal_data.json` by default. To use a synced location (Dropbox, OneDrive, iCloud, etc.), set the `PDF_FORM_FILLER_DATA` environment variable — add it to your shell profile and Claude Code will pick it up automatically:

```bash
export PDF_FORM_FILLER_DATA="$HOME/Dropbox/personal_data.json"
```

Manage data with (replace `$PLUGIN_ROOT` with the path to this directory):

```bash
python "$PLUGIN_ROOT/skills/pdf-form-filler/scripts/manage_data.py" show                    # view all
python "$PLUGIN_ROOT/skills/pdf-form-filler/scripts/manage_data.py" show --member child_1   # view one member
python "$PLUGIN_ROOT/skills/pdf-form-filler/scripts/manage_data.py" add-member --id child_2 --role child
python "$PLUGIN_ROOT/skills/pdf-form-filler/scripts/manage_data.py" batch-update --member child_1 --updates '{"first_name":"Jan"}'
```

## Structure

```text
form-filler-plugin/
├── .claude-plugin/
│   └── plugin.json                  # Plugin manifest
├── skills/
│   └── pdf-form-filler/
│       ├── SKILL.md                 # Skill instructions
│       ├── scripts/
│       │   └── manage_data.py       # Data management CLI
│       └── references/
│           └── personal_data_template.json
└── README.md
```
