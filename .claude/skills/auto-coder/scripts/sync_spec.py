#!/usr/bin/env python3
"""
Spec Sync — splits DEV_SPEC.md into chapter files under auto-coder/references/.

Also auto-updates the overall progress table (### 📈 总体进度) based on
task completion markers found in the schedule section.

Usage:
    python scripts/sync_spec.py [--force]
"""

import hashlib
import re
import sys
from pathlib import Path
from typing import List, Tuple, NamedTuple, Dict


class Chapter(NamedTuple):
    number: int
    cn_title: str
    filename: str
    start_line: int
    end_line: int
    line_count: int


# Chapter number -> English slug (encoding-independent)
NUMBER_SLUG_MAP = {
    1: "overview",
    2: "features",
    3: "tech-stack",
    4: "testing",
    5: "architecture",
    6: "schedule",
    7: "future",
}


def _slug(chapter_num: int, title: str) -> str:
    if chapter_num in NUMBER_SLUG_MAP:
        return NUMBER_SLUG_MAP[chapter_num]
    # Fallback: sanitize whatever title text we have
    clean = re.sub(r'[^\w]+', '-', title, flags=re.ASCII).strip('-').lower()
    return clean or f"chapter-{chapter_num}"


def detect_chapters(content: str) -> List[Chapter]:
    lines = content.split('\n')
    starts: List[Tuple[int, str, int]] = []
    for i, line in enumerate(lines):
        m = re.match(r'^## (\d+)\.\s+(.+)$', line)
        if m:
            starts.append((int(m.group(1)), m.group(2).strip(), i))
    if not starts:
        raise ValueError("No chapters found. Expected '## N. Title'")
    chapters = []
    for idx, (num, title, start) in enumerate(starts):
        end = starts[idx + 1][2] if idx + 1 < len(starts) else len(lines)
        chapters.append(Chapter(num, title, f"{num:02d}-{_slug(num, title)}.md", start, end, end - start))
    return chapters


def sync(force: bool = False):
    skill_dir = Path(__file__).parent.parent          # auto-coder/
    repo_root = skill_dir.parent.parent.parent        # project root
    dev_spec  = repo_root / "DEV_SPEC.md"
    specs_dir = skill_dir / "references"
    hash_file = skill_dir / ".spec_hash"

    if not dev_spec.exists():
        print(f"ERROR: {dev_spec} not found"); sys.exit(1)

    # Hash check
    current_hash = hashlib.sha256(dev_spec.read_bytes()).hexdigest()
    if not force and hash_file.exists() and hash_file.read_text().strip() == current_hash:
        print("specs up-to-date"); return

    content = dev_spec.read_text(encoding='utf-8')
    chapters = detect_chapters(content)
    lines = content.split('\n')

    specs_dir.mkdir(parents=True, exist_ok=True)

    # Clean orphans
    old = {f.name for f in specs_dir.glob("*.md")}
    new = {ch.filename for ch in chapters}
    for f in old - new:
        (specs_dir / f).unlink()

    # Write chapters
    for ch in chapters:
        (specs_dir / ch.filename).write_text('\n'.join(lines[ch.start_line:ch.end_line]), encoding='utf-8')

    # Auto-update overall progress table
    updated_content = update_overall_progress(content)
    if updated_content != content:
        dev_spec.write_text(updated_content, encoding='utf-8')
        content = updated_content
        print(f"updated overall progress table")

    hash_file.write_text(current_hash)
    print(f"synced {len(chapters)} chapters")


def update_overall_progress(content: str) -> str:
    """Auto-update the 总体进度 table based on task completion markers.

    Parses all task tables in the schedule section and calculates
    completed vs total per stage, then updates the progress table.
    """
    completed_pattern = re.compile(r'\[x\]|\[✅\]')

    # Find the 总体进度 section
    progress_start = content.find('### 📈 总体进度')
    if progress_start == -1:
        return content

    # Find next section or end of file
    next_section = re.search(r'\n## [123456789]', content[progress_start + 10:])
    progress_end = progress_start + 10 + next_section.start() if next_section else len(content)

    # Count tasks per stage from all task tables
    stage_task_counts: Dict[str, Dict[str, int]] = {f"阶段 {c}": {'total': 0, 'completed': 0}
                                                      for c in 'ABCDEFGHIJKL'}
    current_stage = None

    for line in content[:progress_start].split('\n'):
        stage_match = re.match(r'#### 阶段 ([A-Z])：', line)
        if stage_match:
            current_stage = f"阶段 {stage_match.group(1)}"
        elif current_stage and '| ' in line:
            # Check if it's a task row (starts with | letter followed by digit)
            if re.match(r'\|\s*[A-Z]\d\s\|', line):
                stage_task_counts[current_stage]['total'] += 1
                if completed_pattern.search(line):
                    stage_task_counts[current_stage]['completed'] += 1

    # Parse existing progress table and update with new counts
    lines = content[progress_start:progress_end].split('\n')
    total_tasks = 0
    total_completed = 0

    new_lines = []
    i = 0
    while i < len(lines):
        line = lines[i]
        # Match stage progress row: | 阶段 X | total | completed | pct% |
        row_match = re.match(r'(\| 阶段 ([A-Z]) \| )(\d+)( \| )(\d+)( \| )(\d+% \|)', line)
        if row_match:
            stage_letter = row_match.group(2)
            stage_name = f"阶段 {stage_letter}"
            total = int(row_match.group(3))
            completed = int(row_match.group(5))

            # Use newly counted values if available
            if stage_name in stage_task_counts and stage_task_counts[stage_name]['total'] > 0:
                total = stage_task_counts[stage_name]['total']
                completed = stage_task_counts[stage_name]['completed']

            pct = int(completed / total * 100) if total > 0 else 0
            new_lines.append(f"| 阶段 {stage_letter} | {total} | {completed} | {pct}% |")
            total_tasks += total
            total_completed += completed
        else:
            # Match total row: | **总计** | **X** | **Y** | **Z%** |
            total_match = re.match(r'(\| \*\*总计\*\* \| \*\*)\d+(\*\* \| \*\*)\d+(\*\* \| \*\*)\d+(\*\* \|)', line)
            if total_match:
                total_pct = int(total_completed / total_tasks * 100) if total_tasks > 0 else 0
                new_lines.append(f"| **总计** | **{total_tasks}** | **{total_completed}** | **{total_pct}%** |")
            else:
                new_lines.append(line)
        i += 1

    new_section = '\n'.join(new_lines)
    if new_section == content[progress_start:progress_end]:
        return content  # No changes needed

    return content[:progress_start] + new_section + content[progress_end:]


if __name__ == "__main__":
    sync(force="--force" in sys.argv)
