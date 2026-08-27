#!/usr/bin/env python3
import os
import sys
import re
import subprocess

POSTS_DIR = "content/posts"

def parse_front_matter_from_text(content):
    match = re.match(r'^---\s*\n(.*?)\n---\s*\n', content, re.DOTALL)
    if not match:
        return {}

    yaml_text = match.group(1)
    meta = {}
    for line in yaml_text.splitlines():
        if ':' in line and not line.strip().startswith('#'):
            key, val = line.split(':', 1)
            key = key.strip()
            val = val.strip().strip('"').strip("'")
            meta[key] = val
    return meta

def parse_front_matter_from_file(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return parse_front_matter_from_text(f.read())
    except FileNotFoundError:
        return {}

def was_previously_published(file_path):
    """Checks git log to see if this file was ever committed with draft: false (or missing draft key)."""
    try:
        commits = subprocess.check_output(
            ["git", "log", "--follow", "--format=%H", "--", file_path],
            stderr=subprocess.DEVNULL
        ).decode('utf-8').strip().splitlines()

        for commit in commits:
            old_content = subprocess.check_output(
                ["git", "show", f"{commit}:{file_path}"],
                stderr=subprocess.DEVNULL
            ).decode('utf-8')

            meta = parse_front_matter_from_text(old_content)
            if meta and meta.get('draft', 'false').lower() != 'true':
                return True
    except subprocess.CalledProcessError:
        pass

    return False

def validate():
    slugs = {}
    post_nums = {}
    errors = []

    for root, _, files in os.walk(POSTS_DIR):
        for file in files:
            if not file.endswith('.md'):
                continue

            path = os.path.join(root, file)
            meta = parse_front_matter_from_file(path)
            if not meta:
                continue

            is_current_draft = meta.get('draft', 'false').lower() == 'true'

            # 1. Disallow published posts from turning into drafts
            if is_current_draft and was_previously_published(path):
                errors.append(
                    f"Forbidden operation in '{path}':\n"
                    f"  Cannot set 'draft: true' on a post that was previously published."
                )
                continue

            # Skip draft files for uniqueness and contiguity checks
            if is_current_draft:
                continue

            # 2. Check post_num presence & uniqueness
            num_str = meta.get('post_num')
            if not num_str:
                errors.append(f"Missing 'post_num' in non-draft post: {path}")
            else:
                try:
                    num = int(num_str)
                    if num in post_nums:
                        errors.append(f"Duplicate post_num #{num} in:\n  - {path}\n  - {post_nums[num]}")
                    else:
                        post_nums[num] = path
                except ValueError:
                    errors.append(f"Invalid integer 'post_num' ({num_str}) in: {path}")

            # 3. Check slug presence & uniqueness
            slug = meta.get('slug')
            if not slug:
                errors.append(f"Missing 'slug' in non-draft post: {path}")
            elif slug in slugs:
                errors.append(f"Duplicate slug '{slug}' in:\n  - {path}\n  - {slugs[slug]}")
            else:
                slugs[slug] = path

    # 4. Check strict contiguity of post_num (1, 2, 3...)
    if post_nums:
        sorted_nums = sorted(post_nums.keys())
        expected_seq = list(range(1, len(sorted_nums) + 1))

        if sorted_nums != expected_seq:
            missing = set(expected_seq) - set(sorted_nums)
            errors.append(
                f"Non-contiguous post_num sequence! Found numbers: {sorted_nums}. "
                f"Missing expected: {sorted(list(missing))}"
            )

    if errors:
        print("\033[31m=== Post Validation Failed ===\033[0m")
        for err in errors:
            print(f"- {err}\n")
        sys.exit(1)

    print("\033[32m✓ All non-draft post slugs and post_nums are valid, unique, contiguous, and non-reverted.\033[0m")

if __name__ == '__main__':
    validate()
