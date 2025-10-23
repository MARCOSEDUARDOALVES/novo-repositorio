"""Utility to export the current Git repository when outbound pushes are blocked.

The script creates a Git bundle containing the complete history of the branch
and a ZIP snapshot of the working tree so you can download the project even
from restricted environments.
"""
from __future__ import annotations

import argparse
import base64
import shutil
import subprocess
from pathlib import Path
from typing import Iterable, Sequence

ROOT = Path(__file__).resolve().parent
DEFAULT_OUTPUT_DIR = ROOT / "transfer"
DEFAULT_BUNDLE = DEFAULT_OUTPUT_DIR / "work.bundle"
DEFAULT_ZIP = DEFAULT_OUTPUT_DIR / "worktree_snapshot.zip"
DEFAULT_BRANCH = "work"


def run_command(cmd: Sequence[str]) -> None:
    """Run a subprocess command, surfacing stdout/stderr on failure."""
    try:
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError as exc:
        raise SystemExit(exc.returncode) from exc


def ensure_directory(path: Path) -> None:
    if not path.exists():
        path.mkdir(parents=True, exist_ok=True)


def create_bundle(bundle_path: Path, ref: str) -> None:
    print(f"Creating Git bundle at {bundle_path} for ref '{ref}'...")
    ensure_directory(bundle_path.parent)
    run_command(["git", "bundle", "create", str(bundle_path), ref])



def create_zip(zip_path: Path) -> None:
    print(f"Creating ZIP archive at {zip_path}...")
    ensure_directory(zip_path.parent)
    base_name = zip_path.with_suffix("")
    # Remove any pre-existing archive created in a previous run so make_archive
    # does not append an additional extension.
    if zip_path.exists():
        zip_path.unlink()
    shutil.make_archive(str(base_name), "zip", ROOT)


def emit_base64(bundle_path: Path, *, output_path: Path | None = None) -> None:
    data = bundle_path.read_bytes()
    encoded = base64.b64encode(data).decode("ascii")

    if output_path is not None:
        ensure_directory(output_path.parent)
        print(f"Writing Base64 bundle to {output_path}...")
        with output_path.open("w", encoding="utf-8") as target:
            target.write("-----BEGIN GIT BUNDLE BASE64-----\n")
            for chunk in chunk_string(encoded, 80):
                target.write(f"{chunk}\n")
            target.write("-----END GIT BUNDLE BASE64-----\n")

    print("\nBase64 bundle (copy everything between the markers):")
    print("-----BEGIN GIT BUNDLE BASE64-----")
    for chunk in chunk_string(encoded, 80):
        print(chunk)
    print("-----END GIT BUNDLE BASE64-----")


def chunk_string(value: str, size: int) -> Iterable[str]:
    for index in range(0, len(value), size):
        yield value[index : index + size]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--branch",
        default=DEFAULT_BRANCH,
        help="Branch or ref to bundle (default: %(default)s)",
    )
    parser.add_argument(
        "--bundle-path",
        type=Path,
        default=DEFAULT_BUNDLE,
        help="Destination for the Git bundle",
    )
    parser.add_argument(
        "--zip-path",
        type=Path,
        default=DEFAULT_ZIP,
        help="Destination for the working tree ZIP archive",
    )
    parser.add_argument(
        "--skip-bundle",
        action="store_true",
        help="Do not generate a Git bundle",
    )
    parser.add_argument(
        "--skip-zip",
        action="store_true",
        help="Do not generate the working tree ZIP archive",
    )
    parser.add_argument(
        "--print-base64",
        action="store_true",
        help="Print a Base64 version of the bundle so it can be copied as text",
    )
    parser.add_argument(
        "--base64-output",
        type=Path,
        help="Save the Base64 bundle to the provided file",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    bundle_path: Path = args.bundle_path
    zip_path: Path = args.zip_path
    ref: str = args.branch

    if not args.skip_bundle:
        create_bundle(bundle_path, ref)
        if args.print_base64:
            emit_base64(bundle_path, output_path=args.base64_output)
    elif args.print_base64:
        raise SystemExit("Cannot print Base64 when bundle generation is skipped")

    if not args.skip_zip:
        create_zip(zip_path)

    print("\nExport completed.")
    if not args.skip_bundle:
        print(f"Git bundle saved to: {bundle_path}")
    if not args.skip_zip:
        print(f"Working tree ZIP saved to: {zip_path}")


if __name__ == "__main__":
    main()
