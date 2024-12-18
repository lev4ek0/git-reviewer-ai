import os
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Set


def add_line_numbers(file_content: str) -> str:
    """
    Add line numbers to each line of the given file content.

    Parameters:
        file_content (str): The content of the file as a single string.

    Returns:
        str: The file content with line numbers added.
    """
    lines = file_content.splitlines()
    numbered_lines = [f"{idx + 1}: {line}" for idx, line in enumerate(lines)]
    return "\n".join(numbered_lines)


class DirectoryTreeGenerator:
    """Generate ASCII tree representation of directory structure."""

    def __init__(
        self,
        root_dir: str,
        max_level: Optional[int] = None,
        sort_order: str = "standard",
        dirs_only: bool = False,
        ignore_hidden: bool = False,
        exclude: Optional[List[str]] = None,
    ):
        """
        Initialize the tree generator.

        Args:
            root_dir: Root directory path
            max_level: Maximum depth level to traverse (None for unlimited)
            sort_order: Sorting order ('asc', 'desc', or 'standard')
            dirs_only: If True, only show directories
            ignore_hidden: If True, ignore hidden files and directories
            exclude: List of file/directory names to exclude
        """
        self.root_dir = Path(root_dir)
        self.max_level = max_level
        self.sort_order = sort_order
        self.dirs_only = dirs_only
        self.ignore_hidden = ignore_hidden
        self.exclude = set(exclude or [])
        self.tree_str = []

    def is_hidden(self, path: Path) -> bool:
        """Check if a file or directory is hidden."""
        return path.name.startswith(".")

    def should_exclude(self, path: Path) -> bool:
        """Check if a file or directory should be excluded."""
        return path.name in self.exclude

    def filter_items(self, items: List[Path]) -> List[Path]:
        """Filter items based on settings."""
        filtered_items = items

        # Apply all filters
        filtered_items = [
            item
            for item in filtered_items
            if not (
                (self.ignore_hidden and self.is_hidden(item))
                or self.should_exclude(item)
                or (self.dirs_only and not item.is_dir())
            )
        ]

        return filtered_items

    def sort_items(self, items: List[Path]) -> List[Path]:
        """Sort items based on the specified sort order."""
        items = self.filter_items(items)

        if self.sort_order == "standard":
            # Separate directories and files
            dirs = sorted([item for item in items if item.is_dir()])
            files = (
                []
                if self.dirs_only
                else sorted([item for item in items if item.is_file()])
            )
            return dirs + files
        else:
            # Sort all items together
            return sorted(items, reverse=(self.sort_order == "desc"))

    def generate_tree(self, directory: Path, prefix: str = "", level: int = 0) -> None:
        """
        Recursively generate the tree structure.

        Args:
            directory: Current directory path
            prefix: Prefix for the current line
            level: Current depth level
        """
        if self.max_level is not None and level > self.max_level:
            return

        # Add current directory to tree
        if level == 0:
            self.tree_str.append(directory.name + "/")

        # Get all items in the directory
        try:
            items = list(directory.iterdir())
            items = self.sort_items(items)
        except PermissionError:
            self.tree_str.append(f"{prefix}├── [Permission Denied]")
            return
        except OSError as e:
            self.tree_str.append(f"{prefix}├── [Error: {str(e)}]")
            return

        # Process each item
        for i, item in enumerate(items):
            is_last = i == len(items) - 1
            item_prefix = prefix + ("└── " if is_last else "├── ")
            next_prefix = prefix + ("    " if is_last else "│   ")

            if item.is_dir():
                self.tree_str.append(f"{item_prefix}{item.name}/")
                self.generate_tree(item, next_prefix, level + 1)
            elif not self.dirs_only:
                self.tree_str.append(f"{item_prefix}{item.name}")

    def get_tree(self) -> str:
        """Generate and return the tree as a string."""
        self.tree_str = []
        self.generate_tree(self.root_dir)
        return "\n".join(self.tree_str)

    def save_tree(self, output_file: str) -> None:
        """Save the tree to a file."""
        tree_content = self.get_tree()
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Root directory: {self.root_dir.absolute()}\n")
            f.write(f"Options: depth={self.max_level or 'unlimited'}, ")
            f.write(f"sort={self.sort_order}, ")
            f.write(f"dirs_only={self.dirs_only}, ")
            f.write(f"ignore_hidden={self.ignore_hidden}, ")
            f.write(f"excluded={list(self.exclude) or 'none'}\n")
            f.write("-" * 50 + "\n\n")
            f.write(tree_content)
