#!/usr/bin/env python3
"""Replace ~/.kube/config with a new kubeconfig file, backing up the current one."""

import argparse
import pathlib
import shutil
import sys
from datetime import datetime


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Replace ~/.kube/config with a new kubeconfig file"
    )
    parser.add_argument("path", help="Path to the new kubeconfig YAML file")
    args = parser.parse_args()

    src = pathlib.Path(args.path).expanduser().resolve()
    kube_dir = pathlib.Path.home() / ".kube"
    dest = kube_dir / "config"

    if not src.exists():
        sys.exit(f"Error: file not found: {src}")
    if not src.is_file():
        sys.exit(f"Error: not a file: {src}")
    if src.resolve() == dest.resolve():
        sys.exit("Error: source is already ~/.kube/config")

    kube_dir.mkdir(parents=True, exist_ok=True)

    backup_path = None
    if dest.exists():
        ts = datetime.now().strftime("%Y%m%d-%H%M%S")
        backup_path = kube_dir / f"config.bkp.{ts}"
        shutil.copy2(dest, backup_path)

    shutil.copy2(src, dest)

    print("Kubeconfig updated successfully")
    print("-" * 50)
    print(f"  Source:  {src}")
    print(f"  Backup:  {backup_path or '(none — no existing config)'}")
    print(f"  Applied: {dest}")
    if backup_path:
        print(f"\nTo rollback: cp {backup_path} {dest}")


if __name__ == "__main__":
    main()
