#!/usr/bin/env python3
"""
Migrate Claude Code local project session folders after a folder re-org.

Claude Code stores session jsonl files under:
  ~/.claude/projects/<eu(projectPath)>/<sessionId>.jsonl

Where eu() replaces any non [a-zA-Z0-9] character with '-'.

If you move a project folder (e.g. Desktop cleanup), Claude Code will look in a
different ~/.claude/projects/<encoded>/ directory and `claude --resume <id>`
will fail with:
  No conversation found with session ID: ...

This script:
  1) Reads Desktop re-org logs (moves.csv + optional moves_corrections.csv)
  2) For each moved directory that has an existing ~/.claude/projects/<old> dir,
     migrates it to the new encoded directory name (creating/merging as needed)
  3) Rewrites "cwd" fields inside *.jsonl to the new path (prefix replace)
  4) Optionally archives symlinks under ~/.claude/projects (not used by Claude)

Safe-by-default:
  - Dry-run unless --apply is provided
  - Creates backups of any jsonl file before rewriting
  - Never overwrites an existing destination file; conflicts get renamed

Usage:
  python3 ~/.claude/migrate-claude-project-paths.py --apply

  # manual single move (repeat --pair as needed)
  python3 ~/.claude/migrate-claude-project-paths.py \\
    --pair "/Users/joon/Desktop/old_project" "/Users/joon/Desktop/10_프로젝트/개발/old_project" \\
    --apply

  # custom log paths
  python3 ~/.claude/migrate-claude-project-paths.py \\
    --moves "/Users/joon/Desktop/99_보관/_정리로그/2025-12-15_001817_desktop_cleanup/moves.csv" \\
    --corrections "/Users/joon/Desktop/99_보관/_정리로그/2025-12-15_001817_desktop_cleanup/moves_corrections.csv" \\
    --apply
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import re
import shutil
from dataclasses import dataclass
from datetime import datetime
from hashlib import sha256
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple


def eu(value: str) -> str:
    return re.sub(r"[^a-zA-Z0-9]", "-", value)


def default_claude_dir() -> Path:
    return Path(os.environ.get("CLAUDE_CONFIG_DIR", str(Path.home() / ".claude")))


def now_stamp() -> str:
    return datetime.now().strftime("%Y-%m-%d_%H%M%S")


def safe_mkdir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def file_sha256(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


@dataclass(frozen=True)
class Move:
    src: str
    dst: str
    kind: str
    reason: str


def write_moves_csv(moves: Iterable[Move], path: Path) -> None:
    safe_mkdir(path.parent)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["src", "dst", "kind", "reason"])
        for m in moves:
            writer.writerow([m.src, m.dst, m.kind, m.reason])


def read_moves_csv(path: Path) -> List[Move]:
    moves: List[Move] = []
    with path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            src = (row.get("src") or "").strip()
            dst = (row.get("dst") or "").strip()
            kind = (row.get("kind") or "").strip()
            reason = (row.get("reason") or "").strip()
            if not src or not dst or not kind:
                continue
            moves.append(Move(src=src.rstrip("/"), dst=dst.rstrip("/"), kind=kind, reason=reason))
    return moves


def build_dir_mapping(moves: Iterable[Move]) -> Dict[str, str]:
    mapping: Dict[str, str] = {}
    for m in moves:
        if m.kind != "dir":
            continue
        mapping[m.src] = m.dst
    return mapping


def apply_prefix_mapping(value: str, src: str, dst: str) -> str:
    if value == src:
        return dst
    prefix = src + "/"
    if value.startswith(prefix):
        return dst + value[len(src) :]
    return value


def rewrite_jsonl_cwds(
    jsonl_path: Path,
    src: str,
    dst: str,
    *,
    backup_root: Path,
    dry_run: bool,
) -> bool:
    try:
        original = jsonl_path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        original = jsonl_path.read_text(encoding="utf-8", errors="replace")

    lines = original.splitlines(keepends=True)
    changed = False
    out_lines: List[str] = []

    for line in lines:
        stripped = line.strip()
        if not stripped:
            out_lines.append(line)
            continue
        try:
            obj = json.loads(stripped)
        except Exception:
            out_lines.append(line)
            continue

        cwd = obj.get("cwd")
        if isinstance(cwd, str):
            new_cwd = apply_prefix_mapping(cwd, src, dst)
            if new_cwd != cwd:
                obj["cwd"] = new_cwd
                changed = True
                out_lines.append(json.dumps(obj, ensure_ascii=False) + ("\n" if line.endswith("\n") else ""))
                continue

        out_lines.append(line)

    if not changed:
        return False

    if dry_run:
        return True

    rel = jsonl_path.relative_to(default_claude_dir())
    backup_path = backup_root / rel
    safe_mkdir(backup_path.parent)
    if not backup_path.exists():
        shutil.copy2(jsonl_path, backup_path)

    jsonl_path.write_text("".join(out_lines), encoding="utf-8")
    return True


def move_file_no_overwrite(src: Path, dst: Path) -> Path:
    """
    Move src to dst, but never overwrite dst. If dst exists, pick a new name.
    Returns the final destination path.
    """
    if not dst.exists():
        src.rename(dst)
        return dst

    stem = dst.stem
    suffix = dst.suffix
    parent = dst.parent
    for i in range(1, 10_000):
        candidate = parent / f"{stem}.conflict{i:04d}{suffix}"
        if not candidate.exists():
            src.rename(candidate)
            return candidate
    raise RuntimeError(f"Too many conflicts while moving into {dst}")


def merge_project_dirs(old_dir: Path, new_dir: Path, *, dry_run: bool) -> List[Tuple[str, str]]:
    moves: List[Tuple[str, str]] = []
    for entry in sorted(old_dir.iterdir(), key=lambda p: p.name):
        if entry.name.startswith("."):
            continue
        dst = new_dir / entry.name
        if dry_run:
            moves.append((str(entry), str(dst)))
            continue
        safe_mkdir(new_dir)
        final_dst = move_file_no_overwrite(entry, dst)
        moves.append((str(entry), str(final_dst)))
    return moves


def archive_symlinks(projects_dir: Path, archive_dir: Path, *, dry_run: bool) -> List[Tuple[str, str]]:
    moved: List[Tuple[str, str]] = []
    for entry in sorted(projects_dir.iterdir(), key=lambda p: p.name):
        if entry.name.startswith("."):
            continue
        if not entry.is_symlink():
            continue
        dst = archive_dir / entry.name
        if dry_run:
            moved.append((str(entry), str(dst)))
            continue
        safe_mkdir(archive_dir)
        final_dst = move_file_no_overwrite(entry, dst)
        moved.append((str(entry), str(final_dst)))
    return moved


def main() -> int:
    parser = argparse.ArgumentParser(description="Migrate Claude Code project session folders after path moves.")
    parser.add_argument(
        "--moves",
        default="/Users/joon/Desktop/99_보관/_정리로그/2025-12-15_001817_desktop_cleanup/moves.csv",
        help="Path to moves.csv from the Desktop cleanup log.",
    )
    parser.add_argument(
        "--corrections",
        default="/Users/joon/Desktop/99_보관/_정리로그/2025-12-15_001817_desktop_cleanup/moves_corrections.csv",
        help="Path to moves_corrections.csv (optional; overrides moves.csv).",
    )
    parser.add_argument(
        "--pair",
        nargs=2,
        action="append",
        metavar=("SRC", "DST"),
        help="Manual mapping pair for a moved directory (repeatable).",
    )
    parser.add_argument("--apply", action="store_true", help="Apply changes (default is dry-run).")
    parser.add_argument(
        "--archive-project-symlinks",
        action="store_true",
        help="Move symlinks under ~/.claude/projects into a hidden archive dir (recommended).",
    )
    args = parser.parse_args()

    dry_run = not args.apply
    claude_dir = default_claude_dir()
    projects_dir = claude_dir / "projects"

    moves_path = Path(args.moves)
    corrections_path = Path(args.corrections)

    moves: List[Move] = []
    if moves_path.exists():
        moves = read_moves_csv(moves_path)

    mapping = build_dir_mapping(moves)

    if corrections_path.exists():
        corrections = read_moves_csv(corrections_path)
        mapping.update(build_dir_mapping(corrections))

    pair_moves: List[Move] = []
    if args.pair:
        for src, dst in args.pair:
            pair_moves.append(Move(src=src.rstrip("/"), dst=dst.rstrip("/"), kind="dir", reason="cli --pair"))
        mapping.update(build_dir_mapping(pair_moves))

    if not moves_path.exists() and not pair_moves:
        raise SystemExit(f"moves.csv not found: {moves_path} (and no --pair provided)")

    candidates: List[Tuple[str, str, Path, Path]] = []
    for src, dst in sorted(mapping.items(), key=lambda kv: kv[0]):
        old_dir = projects_dir / eu(src)
        if not old_dir.exists() or not old_dir.is_dir():
            continue
        # Only migrate if destination exists as a directory (avoid bad mappings)
        if not Path(dst).exists():
            continue
        candidates.append((src, dst, old_dir, projects_dir / eu(dst)))

    stamp = now_stamp()
    migration_dir = claude_dir / "_migrations" / f"{stamp}_project_path_migration"
    backup_root = migration_dir / "backups"
    log_path = migration_dir / "actions.jsonl"

    if not dry_run:
        safe_mkdir(migration_dir)
        safe_mkdir(backup_root)
        if moves_path.exists():
            shutil.copy2(moves_path, migration_dir / "moves.csv")
        if corrections_path.exists():
            shutil.copy2(corrections_path, migration_dir / "moves_corrections.csv")
        if pair_moves:
            write_moves_csv(pair_moves, migration_dir / "pairs.csv")

    def log(obj: dict) -> None:
        if dry_run:
            return
        with log_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(obj, ensure_ascii=False) + "\n")

    print(f"Claude dir: {claude_dir}")
    print(f"Projects dir: {projects_dir}")
    print(f"Mode: {'DRY-RUN' if dry_run else 'APPLY'}")
    print(f"Move mappings loaded: {len(mapping)} (dir-only)")
    if pair_moves:
        print(f"Manual pairs: {len(pair_moves)}")
    print(f"Migration candidates (existing old project dirs): {len(candidates)}")
    if not candidates:
        return 0

    for src, dst, old_dir, new_dir in candidates:
        print("\n" + "=" * 80)
        print(f"SRC: {src}")
        print(f"DST: {dst}")
        print(f"OLD: {old_dir}")
        print(f"NEW: {new_dir}")

        if not dry_run:
            safe_mkdir(new_dir)

        moved_files = merge_project_dirs(old_dir, new_dir, dry_run=dry_run)
        print(f"Moved entries: {len(moved_files)}")
        log(
            {
                "type": "project_dir_merge",
                "src": src,
                "dst": dst,
                "old_dir": str(old_dir),
                "new_dir": str(new_dir),
                "moved": moved_files,
            }
        )

        # Update cwd values inside jsonl files now living in new_dir.
        changed_files = 0
        jsonl_files = sorted(new_dir.glob("*.jsonl"), key=lambda p: p.name)
        for jsonl_file in jsonl_files:
            changed = rewrite_jsonl_cwds(
                jsonl_file,
                src,
                dst,
                backup_root=backup_root,
                dry_run=dry_run,
            )
            if changed:
                changed_files += 1
                log(
                    {
                        "type": "rewrite_cwd",
                        "file": str(jsonl_file),
                        "src": src,
                        "dst": dst,
                    }
                )
        print(f"Rewritten jsonl files (cwd updates): {changed_files}")

        # Best-effort: remove old_dir if empty.
        if not dry_run:
            try:
                next(old_dir.iterdir())
            except StopIteration:
                try:
                    old_dir.rmdir()
                    log({"type": "rmdir_empty_project_dir", "dir": str(old_dir)})
                    print("Removed empty old project dir.")
                except OSError:
                    pass

    if args.archive_project_symlinks:
        archive_dir = projects_dir / f".archived_symlinks_{stamp}"
        moved = archive_symlinks(projects_dir, archive_dir, dry_run=dry_run)
        print("\n" + "=" * 80)
        print(f"Symlinks archived: {len(moved)}")
        log({"type": "archive_symlinks", "archive_dir": str(archive_dir), "moved": moved})

    print("\nDone.")
    if not dry_run:
        print(f"Migration log: {log_path}")
        print(f"Backups: {backup_root}")
    else:
        print("Re-run with --apply to make changes.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
