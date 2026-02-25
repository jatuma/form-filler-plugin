#!/usr/bin/env python3
"""Manage personal data for PDF form filling.

Usage:
    python manage_data.py init [--data-file PATH]
        Initialize a new personal_data.json from template.

    python manage_data.py show [--data-file PATH] [--member ID]
        Show stored data. Optionally filter by member ID.

    python manage_data.py update --member ID --field FIELD --value VALUE [--data-file PATH]
        Update a single field for a member.
        Nested fields use dot notation: "permanent_address.city", "health.allergies"

    python manage_data.py add-member --id ID --role ROLE [--data-file PATH]
        Add a new family member from template.

    python manage_data.py batch-update --member ID --updates JSON [--data-file PATH]
        Update multiple fields at once. JSON is a dict of field:value pairs.
        Example: --updates '{"first_name":"Jan","last_name":"Novák","date_of_birth":"2015-03-12"}'

    python manage_data.py find-gaps --member ID [--fields FIELD1,FIELD2,...] [--data-file PATH]
        Show null/missing fields for a member. Optionally filter to specific fields.
"""

import argparse
import json
import os
import sys
from copy import deepcopy
from pathlib import Path

DEFAULT_DATA_DIR = os.path.expanduser("~/.config/pdf-form-filler")
DEFAULT_DATA_FILE = os.environ.get(
    "PDF_FORM_FILLER_DATA",
    os.path.join(DEFAULT_DATA_DIR, "personal_data.json")
)
TEMPLATE_FILE = os.path.join(os.path.dirname(__file__), "..", "references", "personal_data_template.json")


def load_data(data_file):
    if not os.path.exists(data_file):
        print(f"ERROR: Data file not found: {data_file}", file=sys.stderr)
        print(f"Run 'python manage_data.py init' to create it.", file=sys.stderr)
        sys.exit(1)
    with open(data_file, "r", encoding="utf-8") as f:
        return json.load(f)


def save_data(data, data_file):
    os.makedirs(os.path.dirname(data_file), exist_ok=True)
    with open(data_file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"Saved: {data_file}")


def get_nested(obj, dotted_key):
    keys = dotted_key.split(".")
    for k in keys:
        if isinstance(obj, dict) and k in obj:
            obj = obj[k]
        else:
            return None
    return obj


def set_nested(obj, dotted_key, value):
    keys = dotted_key.split(".")
    for k in keys[:-1]:
        if k not in obj or not isinstance(obj[k], dict):
            obj[k] = {}
        obj = obj[k]
    obj[keys[-1]] = value


def find_member(data, member_id):
    for m in data.get("members", []):
        if m.get("id") == member_id:
            return m
    return None


def collect_null_fields(obj, prefix=""):
    """Recursively find all null fields."""
    gaps = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k.startswith("_"):
                continue
            full_key = f"{prefix}.{k}" if prefix else k
            if v is None:
                gaps.append(full_key)
            elif isinstance(v, dict):
                gaps.extend(collect_null_fields(v, full_key))
    return gaps


def cmd_init(args):
    if os.path.exists(args.data_file):
        print(f"Data file already exists: {args.data_file}")
        print("Use 'show' to view or 'update' to modify.")
        return

    template_path = TEMPLATE_FILE
    if not os.path.exists(template_path):
        # Fallback: look relative to script location
        template_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                      "..", "references", "personal_data_template.json")
    if not os.path.exists(template_path):
        print("ERROR: Template file not found.", file=sys.stderr)
        sys.exit(1)

    with open(template_path, "r", encoding="utf-8") as f:
        template = json.load(f)

    save_data(template, args.data_file)
    print(f"Initialized personal data at: {args.data_file}")


def cmd_show(args):
    data = load_data(args.data_file)
    if args.member:
        member = find_member(data, args.member)
        if not member:
            print(f"ERROR: Member '{args.member}' not found.", file=sys.stderr)
            print(f"Available: {[m['id'] for m in data.get('members', [])]}", file=sys.stderr)
            sys.exit(1)
        print(json.dumps(member, indent=2, ensure_ascii=False))
    else:
        print(json.dumps(data, indent=2, ensure_ascii=False))


def cmd_update(args):
    data = load_data(args.data_file)
    member = find_member(data, args.member)
    if not member:
        print(f"ERROR: Member '{args.member}' not found.", file=sys.stderr)
        sys.exit(1)

    # Try to parse value as JSON for complex types, fall back to string
    try:
        value = json.loads(args.value)
    except (json.JSONDecodeError, TypeError):
        value = args.value

    old_value = get_nested(member, args.field)
    set_nested(member, args.field, value)
    save_data(data, args.data_file)
    print(f"Updated {args.member}.{args.field}: {old_value} -> {value}")


def cmd_batch_update(args):
    data = load_data(args.data_file)
    member = find_member(data, args.member)
    if not member:
        print(f"ERROR: Member '{args.member}' not found.", file=sys.stderr)
        sys.exit(1)

    try:
        updates = json.loads(args.updates)
    except json.JSONDecodeError as e:
        print(f"ERROR: Invalid JSON for --updates: {e}", file=sys.stderr)
        sys.exit(1)

    for field, value in updates.items():
        old_value = get_nested(member, field)
        set_nested(member, field, value)
        print(f"  {args.member}.{field}: {old_value} -> {value}")

    save_data(data, args.data_file)
    print(f"Updated {len(updates)} field(s).")


def cmd_add_member(args):
    data = load_data(args.data_file)
    if find_member(data, args.id):
        print(f"ERROR: Member '{args.id}' already exists.", file=sys.stderr)
        sys.exit(1)

    # Build new member from template based on role
    template_path = TEMPLATE_FILE
    if os.path.exists(template_path):
        with open(template_path, "r", encoding="utf-8") as f:
            template = json.load(f)
        # Find a template member with matching role
        tmpl_member = None
        for m in template.get("members", []):
            if m.get("role") == args.role:
                tmpl_member = deepcopy(m)
                break
        if not tmpl_member:
            # Use first member as base
            tmpl_member = deepcopy(template["members"][0])
            tmpl_member["role"] = args.role
    else:
        tmpl_member = {"role": args.role}

    tmpl_member["id"] = args.id
    data["members"].append(tmpl_member)
    save_data(data, args.data_file)
    print(f"Added member '{args.id}' with role '{args.role}'.")


def cmd_find_gaps(args):
    data = load_data(args.data_file)
    member = find_member(data, args.member)
    if not member:
        print(f"ERROR: Member '{args.member}' not found.", file=sys.stderr)
        sys.exit(1)

    all_gaps = collect_null_fields(member)

    if args.fields:
        requested = [f.strip() for f in args.fields.split(",")]
        all_gaps = [g for g in all_gaps if any(g == r or g.startswith(r + ".") for r in requested)]

    if all_gaps:
        print(f"Missing fields for '{args.member}':")
        for g in all_gaps:
            print(f"  - {g}")
    else:
        print(f"No missing fields for '{args.member}'" +
              (f" (filtered: {args.fields})" if args.fields else ""))


def main():
    parser = argparse.ArgumentParser(description="Manage personal data for PDF form filling")
    parser.add_argument("--data-file", default=DEFAULT_DATA_FILE, help="Path to personal_data.json")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("init", help="Initialize data file from template")

    show_p = sub.add_parser("show", help="Show stored data")
    show_p.add_argument("--member", help="Filter by member ID")

    upd_p = sub.add_parser("update", help="Update a field")
    upd_p.add_argument("--member", required=True)
    upd_p.add_argument("--field", required=True)
    upd_p.add_argument("--value", required=True)

    batch_p = sub.add_parser("batch-update", help="Update multiple fields")
    batch_p.add_argument("--member", required=True)
    batch_p.add_argument("--updates", required=True, help="JSON dict of field:value pairs")

    add_p = sub.add_parser("add-member", help="Add a new family member")
    add_p.add_argument("--id", required=True)
    add_p.add_argument("--role", required=True, help="parent, child, or other")

    gaps_p = sub.add_parser("find-gaps", help="Find null/missing fields")
    gaps_p.add_argument("--member", required=True)
    gaps_p.add_argument("--fields", help="Comma-separated field filter")

    args = parser.parse_args()

    cmd_map = {
        "init": cmd_init,
        "show": cmd_show,
        "update": cmd_update,
        "batch-update": cmd_batch_update,
        "add-member": cmd_add_member,
        "find-gaps": cmd_find_gaps,
    }
    cmd_map[args.command](args)


if __name__ == "__main__":
    main()
