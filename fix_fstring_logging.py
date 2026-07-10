"""
Fix f-string logging calls across the Python codebase.
Converts:
    logger.info("...%s...", var)
to:
    logger.info("...%s...", var)
Handles f-strings with multiple variables, expressions, and method calls.
"""

import re
import os
import ast
import sys

LOGGER_CALLS = ["logger.info", "logger.debug", "logger.warning", "logger.error",
                "logger.critical", "logger.exception"]


def fix_file(filepath):
    with open(filepath, encoding="utf-8") as f:
        content = f.read()

    original = content
    lines = content.split("\n")
    new_lines = []
    changed = 0

    for line in lines:
        new_line = fix_line(line)
        if new_line != line:
            changed += 1
        new_lines.append(new_line)

    if changed > 0:
        with open(filepath, "w", encoding="utf-8") as f:
            f.write("\n".join(new_lines))

    return changed


def fix_line(line):
    """Convert a single-line f-string logging call to %s formatting."""
    stripped = line.strip()

    # Match: logger.info(f"...")  or  logger.debug(f"...")
    # Only handle single-line calls
    for logger_call in LOGGER_CALLS:
        # Pattern: logger.info(f"..."...) or logger.info(f'...'...)
        pattern = rf'({logger_call})\s*\(\s*f(["\'])(.*?)\2\s*(.*?)\)\s*$'
        m = re.match(pattern, stripped)
        if m:
            prefix = m.group(1)  # logger.info
            quote = m.group(2)   # " or '
            template = m.group(3)  # content inside f-string
            suffix = m.group(4)   # anything after the f-string (normally "," then args)

            # Parse f-string expressions in the template
            parts = re.split(r'\{([^}]+)\}', template)

            new_template_parts = []
            args = []

            for i, part in enumerate(parts):
                if i % 2 == 0:
                    # literal text
                    new_template_parts.append(part)
                else:
                    # expression - replace with %s
                    expr = part.strip()
                    new_template_parts.append("%s")
                    args.append(expr.replace('"', "'"))

            new_template = "".join(new_template_parts)

            # Build the new call
            if args:
                # Combine existing suffix args with extracted args
                existing_args = suffix.strip()
            if existing_args:
                # There are already args after the f-string (e.g. ", exc_info=True")
                new_args = ", ".join(args) + existing_args
            else:
                    new_args = ", ".join(args)

                indent = line[:len(line) - len(line.lstrip())]
                new_line = f'{indent}{prefix}("{new_template}", {new_args})'
            else:
                # No expressions - just remove the f prefix
                new_line = line.replace(f"f{quote}", quote, 1)

            return new_line

    return line


def main():
    root = sys.argv[1] if len(sys.argv) > 1 else "/Users/macbookpro/Desktop/vigyanpilot"
    total_changed = 0
    total_files = 0

    for dirpath, _, filenames in os.walk(root):
        # Skip venv, .git, __pycache__
        if "/.venv/" in dirpath or "/.git/" in dirpath or "/__pycache__/" in dirpath:
            continue
        for fn in filenames:
            if fn.endswith(".py"):
                fp = os.path.join(dirpath, fn)
                changed = fix_file(fp)
                if changed > 0:
                    print(f"  {fp}: {changed} fix(es)")
                    total_changed += changed
                    total_files += 1

    print(f"\nFixed {total_changed} f-string logging calls in {total_files} files.")


if __name__ == "__main__":
    main()
