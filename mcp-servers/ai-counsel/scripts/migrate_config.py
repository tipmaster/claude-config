#!/usr/bin/env python3
"""
Migration script: cli_tools → adapters

Migrates config.yaml from legacy cli_tools format to new adapters format
with explicit type fields.

Usage:
    python scripts/migrate_config.py [path/to/config.yaml]

If no path provided, defaults to ./config.yaml
"""

import shutil
import sys
from pathlib import Path
from typing import Any, Dict

import yaml


def migrate_config_dict(config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Migrate config dictionary from cli_tools to adapters format.

    Args:
        config: Config dictionary with cli_tools section

    Returns:
        Migrated config with adapters section
    """
    # If already migrated (has adapters, no cli_tools), return as-is
    if "adapters" in config and "cli_tools" not in config:
        print("Info: Config already migrated (has 'adapters' section)")
        return config

    # If no cli_tools, nothing to migrate
    if "cli_tools" not in config:
        print("Warning: No 'cli_tools' section found, nothing to migrate")
        return config

    # Create new config with adapters
    migrated = config.copy()

    # Transform cli_tools → adapters
    adapters = {}
    for name, cli_config in config["cli_tools"].items():
        adapters[name] = {
            "type": "cli",  # Add explicit type
            "command": cli_config["command"],
            "args": cli_config["args"],
            "timeout": cli_config["timeout"],
        }

    migrated["adapters"] = adapters
    del migrated["cli_tools"]

    print(f"Success: Migrated {len(adapters)} CLI tools to adapters format")

    return migrated


def migrate_config_file(path: str) -> None:
    """
    Migrate config file from cli_tools to adapters format.

    Creates a backup at {path}.bak before modifying.

    Args:
        path: Path to config.yaml file

    Raises:
        FileNotFoundError: If config file doesn't exist
    """
    config_path = Path(path)

    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {path}")

    # Create backup
    backup_path = Path(f"{path}.bak")
    shutil.copy2(config_path, backup_path)
    print(f"Created backup: {backup_path}")

    # Load config
    with open(config_path, "r") as f:
        config = yaml.safe_load(f)

    # Migrate
    migrated = migrate_config_dict(config)

    # Write migrated config
    with open(config_path, "w") as f:
        yaml.dump(migrated, f, default_flow_style=False, sort_keys=False)

    print(f"Migrated config written to: {config_path}")
    print(f"\nInfo: Review the changes and delete {backup_path} when satisfied.")


def main():
    """Main entry point."""
    if len(sys.argv) > 1:
        config_path = sys.argv[1]
    else:
        config_path = "config.yaml"

    print(f"Migrating config: {config_path}")
    print("-" * 50)

    try:
        migrate_config_file(config_path)
        print("\nMigration complete!")
        print("\nNext steps:")
        print("1. Review the migrated config.yaml")
        print(
            "2. Test loading: python -c 'from models.config import load_config; load_config()'"
        )
        print("3. Delete backup if satisfied: rm config.yaml.bak")

    except Exception as e:
        print(f"\nError: Migration failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
