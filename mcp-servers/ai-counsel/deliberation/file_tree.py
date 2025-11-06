"""File tree generation utility for repository structure visualization."""
import logging
from pathlib import Path
from typing import Optional, Set

logger = logging.getLogger(__name__)

# Common files/directories to ignore in tree generation
DEFAULT_IGNORE_PATTERNS = {
    # Version control
    '.git', '.svn', '.hg',
    # Python
    '__pycache__', '*.pyc', '*.pyo', '*.pyd', '.Python',
    '.venv', 'venv', 'env', 'ENV',
    # Node.js
    'node_modules', 'npm-debug.log', 'yarn-error.log',
    # Build artifacts
    'build', 'dist', '*.egg-info', '.eggs',
    # IDE
    '.vscode', '.idea', '.DS_Store',
    # Misc
    '.coverage', 'htmlcov', '.pytest_cache', '.mypy_cache',
    '.ruff_cache', '.tox',
    # Deliberation outputs (prevents context contamination)
    'transcripts',
    # Binary files
    '*.so', '*.dylib', '*.db', '*.sqlite',
    '*.png', '*.jpg', '*.jpeg', '*.gif', '*.bmp', '*.ico',
}


def generate_file_tree(
    root_path: str,
    max_depth: int = 3,
    max_files: int = 100,
    ignore_patterns: Optional[Set[str]] = None,
    ascii_only: bool = False,
) -> str:
    """
    Generate a text-based file tree representation of a directory.

    Args:
        root_path: Path to the root directory to scan
        max_depth: Maximum depth to traverse (default: 3)
        max_files: Maximum number of files to include (default: 100)
        ignore_patterns: Set of patterns to ignore (defaults to common VCS/build dirs)
        ascii_only: Use ASCII characters instead of Unicode box-drawing (better for JSON)

    Returns:
        String representation of the file tree, or empty string if generation fails

    Example output (Unicode):
        project/
        ├── src/
        │   ├── main.py
        │   └── utils.py
        └── README.md

    Example output (ASCII):
        project/
        |-- src/
        |   |-- main.py
        |   `-- utils.py
        `-- README.md
    """
    try:
        # Validate root path
        root = Path(root_path).resolve()
        if not root.exists():
            logger.warning(f"Root path does not exist: {root_path}")
            return ""
        if not root.is_dir():
            logger.warning(f"Root path is not a directory: {root_path}")
            return ""

        # Use default ignore patterns if none provided
        if ignore_patterns is None:
            ignore_patterns = DEFAULT_IGNORE_PATTERNS

        # Build the tree
        lines = []
        file_count = [0]  # Use list to allow mutation in nested function

        def should_ignore(path: Path) -> bool:
            """Check if path should be ignored."""
            name = path.name
            # Check exact matches
            if name in ignore_patterns:
                return True
            # Check wildcard patterns
            for pattern in ignore_patterns:
                if '*' in pattern and name.endswith(pattern.replace('*', '')):
                    return True
            return False

        def walk_tree(path: Path, prefix: str = "", depth: int = 0):
            """Recursively walk directory tree."""
            # Check file count limit
            if file_count[0] >= max_files:
                if file_count[0] == max_files:
                    lines.append(f"{prefix}... (truncated at {max_files} files)")
                    file_count[0] += 1
                return

            try:
                # Get directory contents and filter in one pass
                # Sort: directories first, then alphabetically
                entries = sorted(path.iterdir(), key=lambda p: (not p.is_dir(), p.name))

                # Filter ignored entries and directories exceeding max_depth
                entries = [
                    e for e in entries
                    if not should_ignore(e)
                    and not (e.is_dir() and depth + 1 > max_depth)
                ]

                for i, entry in enumerate(entries):
                    # Check file count limit
                    if file_count[0] >= max_files:
                        lines.append(f"{prefix}... (truncated at {max_files} files)")
                        file_count[0] += 1
                        break

                    is_last = i == len(entries) - 1

                    # Use ASCII or Unicode box-drawing characters
                    if ascii_only:
                        connector = "`-- " if is_last else "|-- "
                        extension = "    " if is_last else "|   "
                    else:
                        connector = "└── " if is_last else "├── "
                        extension = "    " if is_last else "│   "

                    if entry.is_dir():
                        lines.append(f"{prefix}{connector}{entry.name}/")
                        file_count[0] += 1

                        # Recurse into directory
                        walk_tree(entry, prefix + extension, depth + 1)
                    else:
                        lines.append(f"{prefix}{connector}{entry.name}")
                        file_count[0] += 1

            except PermissionError:
                lines.append(f"{prefix}... (permission denied)")
            except Exception as e:
                logger.warning(f"Error reading directory {path}: {e}")

        # Start with root directory name
        lines.append(f"{root.name}/")
        walk_tree(root, "", 0)

        tree_str = "\n".join(lines)
        logger.info(f"Generated file tree: {file_count[0]} entries, {len(lines)} lines")
        return tree_str

    except Exception as e:
        logger.error(f"Failed to generate file tree for {root_path}: {e}", exc_info=True)
        return ""
