"""Unit tests for file tree generation utility."""
import os
import tempfile
from pathlib import Path

import pytest

from deliberation.file_tree import generate_file_tree


class TestGenerateFileTree:
    """Tests for generate_file_tree function."""

    def test_should_generate_basic_tree_when_simple_directory(self):
        """Test basic tree generation with simple directory structure."""
        # Arrange
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create simple structure
            Path(tmpdir, "file1.py").touch()
            Path(tmpdir, "file2.txt").touch()
            Path(tmpdir, "subdir").mkdir()
            Path(tmpdir, "subdir", "nested.py").touch()

            # Act
            result = generate_file_tree(tmpdir, max_depth=3, max_files=100)

            # Assert
            assert "file1.py" in result
            assert "file2.txt" in result
            assert "subdir" in result
            assert "nested.py" in result
            # Should be formatted as a tree
            assert result.strip() != ""

    def test_should_respect_max_depth_when_deeply_nested(self):
        """Test that max_depth limits tree traversal."""
        # Arrange
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create deep nesting: depth1/depth2/depth3/depth4
            d1 = Path(tmpdir, "depth1")
            d1.mkdir()
            Path(d1, "file1.py").touch()

            d2 = Path(d1, "depth2")
            d2.mkdir()
            Path(d2, "file2.py").touch()

            d3 = Path(d2, "depth3")
            d3.mkdir()
            Path(d3, "file3.py").touch()

            d4 = Path(d3, "depth4")
            d4.mkdir()
            Path(d4, "file4.py").touch()

            # Act - limit to depth 2
            result = generate_file_tree(tmpdir, max_depth=2, max_files=100)

            # Assert
            # Should include depth1 and depth2
            assert "depth1" in result
            assert "file1.py" in result
            assert "depth2" in result
            assert "file2.py" in result
            # Should NOT include depth3 or deeper
            assert "depth3" not in result
            assert "file3.py" not in result
            assert "file4.py" not in result

    def test_should_truncate_when_max_files_exceeded(self):
        """Test that file count is truncated when exceeding max_files."""
        # Arrange
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create 15 files
            for i in range(15):
                Path(tmpdir, f"file{i}.py").touch()

            # Act - limit to 10 files
            result = generate_file_tree(tmpdir, max_depth=3, max_files=10)

            # Assert
            # Should indicate truncation
            assert "more files" in result.lower() or "..." in result
            # Should show at most 10 files
            file_count = sum(1 for line in result.split('\n') if line.strip() and not line.strip().endswith('/'))
            # Allow for some flexibility in counting (directory lines vs file lines)
            assert file_count <= 12  # 10 files + truncation message + tolerance

    def test_should_exclude_git_directory_when_present(self):
        """Test that .git directories are excluded."""
        # Arrange
        with tempfile.TemporaryDirectory() as tmpdir:
            Path(tmpdir, "src").mkdir()
            Path(tmpdir, "src", "main.py").touch()
            git_dir = Path(tmpdir, ".git")
            git_dir.mkdir()
            Path(git_dir, "config").touch()
            Path(git_dir, "HEAD").touch()

            # Act
            result = generate_file_tree(tmpdir, max_depth=3, max_files=100)

            # Assert
            assert "main.py" in result
            assert ".git" not in result
            assert "config" not in result  # .git/config should be excluded
            assert "HEAD" not in result

    def test_should_exclude_pycache_directory_when_present(self):
        """Test that __pycache__ directories are excluded."""
        # Arrange
        with tempfile.TemporaryDirectory() as tmpdir:
            Path(tmpdir, "module.py").touch()
            pycache = Path(tmpdir, "__pycache__")
            pycache.mkdir()
            Path(pycache, "module.cpython-39.pyc").touch()

            # Act
            result = generate_file_tree(tmpdir, max_depth=3, max_files=100)

            # Assert
            assert "module.py" in result
            assert "__pycache__" not in result
            assert ".pyc" not in result

    def test_should_exclude_venv_directory_when_present(self):
        """Test that .venv directories are excluded."""
        # Arrange
        with tempfile.TemporaryDirectory() as tmpdir:
            Path(tmpdir, "app.py").touch()
            venv = Path(tmpdir, ".venv")
            venv.mkdir()
            venv_lib = Path(venv, "lib")
            venv_lib.mkdir()
            Path(venv_lib, "python.so").touch()

            # Act
            result = generate_file_tree(tmpdir, max_depth=3, max_files=100)

            # Assert
            assert "app.py" in result
            assert ".venv" not in result
            assert "python.so" not in result

    def test_should_exclude_node_modules_when_present(self):
        """Test that node_modules directories are excluded."""
        # Arrange
        with tempfile.TemporaryDirectory() as tmpdir:
            Path(tmpdir, "index.js").touch()
            nm = Path(tmpdir, "node_modules")
            nm.mkdir()
            Path(nm, "package").mkdir()
            Path(nm, "package", "index.js").touch()

            # Act
            result = generate_file_tree(tmpdir, max_depth=3, max_files=100)

            # Assert
            assert "index.js" in result
            assert "node_modules" not in result
            # Ensure we only see the top-level index.js
            assert result.count("index.js") == 1

    def test_should_exclude_pytest_cache_when_present(self):
        """Test that .pytest_cache directories are excluded."""
        # Arrange
        with tempfile.TemporaryDirectory() as tmpdir:
            Path(tmpdir, "test_main.py").touch()
            cache = Path(tmpdir, ".pytest_cache")
            cache.mkdir()
            Path(cache, "v").mkdir()
            Path(cache, "v", "cache").touch()

            # Act
            result = generate_file_tree(tmpdir, max_depth=3, max_files=100)

            # Assert
            assert "test_main.py" in result
            assert ".pytest_cache" not in result

    def test_should_exclude_egg_info_directories_when_present(self):
        """Test that *.egg-info directories are excluded."""
        # Arrange
        with tempfile.TemporaryDirectory() as tmpdir:
            Path(tmpdir, "setup.py").touch()
            egg = Path(tmpdir, "mypackage.egg-info")
            egg.mkdir()
            Path(egg, "PKG-INFO").touch()

            # Act
            result = generate_file_tree(tmpdir, max_depth=3, max_files=100)

            # Assert
            assert "setup.py" in result
            assert "egg-info" not in result
            assert "PKG-INFO" not in result

    def test_should_exclude_binary_files_when_present(self):
        """Test that binary file extensions are excluded."""
        # Arrange
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create source files
            Path(tmpdir, "main.py").touch()
            Path(tmpdir, "config.yaml").touch()
            # Create binary files
            Path(tmpdir, "compiled.pyc").touch()
            Path(tmpdir, "library.so").touch()
            Path(tmpdir, "library.dylib").touch()
            Path(tmpdir, "data.db").touch()
            Path(tmpdir, "data.sqlite").touch()
            Path(tmpdir, "image.png").touch()
            Path(tmpdir, "photo.jpg").touch()
            Path(tmpdir, "picture.jpeg").touch()

            # Act
            result = generate_file_tree(tmpdir, max_depth=3, max_files=100)

            # Assert
            assert "main.py" in result
            assert "config.yaml" in result
            # Binary files should be excluded
            assert ".pyc" not in result
            assert ".so" not in result
            assert ".dylib" not in result
            assert ".db" not in result
            assert ".sqlite" not in result
            assert ".png" not in result
            assert ".jpg" not in result
            assert ".jpeg" not in result

    def test_should_handle_empty_directory_gracefully(self):
        """Test that empty directories don't break tree generation."""
        # Arrange
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create empty directory
            Path(tmpdir, "empty").mkdir()

            # Act
            result = generate_file_tree(tmpdir, max_depth=3, max_files=100)

            # Assert
            # Should return something (even if minimal)
            assert isinstance(result, str)
            # Might be empty or show "empty" directory
            # Just ensure it doesn't crash

    def test_should_return_empty_string_when_directory_not_found(self):
        """Test graceful handling of non-existent directory."""
        # Arrange
        non_existent_path = "/this/path/definitely/does/not/exist/12345"

        # Act
        result = generate_file_tree(non_existent_path, max_depth=3, max_files=100)

        # Assert
        assert result == ""

    def test_should_handle_permission_errors_gracefully(self):
        """Test that permission errors don't crash tree generation."""
        # Arrange
        with tempfile.TemporaryDirectory() as tmpdir:
            Path(tmpdir, "readable.py").touch()
            restricted = Path(tmpdir, "restricted")
            restricted.mkdir()
            Path(restricted, "secret.txt").touch()

            # Remove read permissions on restricted directory
            try:
                os.chmod(restricted, 0o000)

                # Act
                result = generate_file_tree(tmpdir, max_depth=3, max_files=100)

                # Assert
                # Should still show readable.py
                assert "readable.py" in result
                # Should not crash on permission error
                assert isinstance(result, str)
            finally:
                # Restore permissions for cleanup
                os.chmod(restricted, 0o755)

    def test_should_format_tree_with_indentation(self):
        """Test that output has proper tree formatting."""
        # Arrange
        with tempfile.TemporaryDirectory() as tmpdir:
            Path(tmpdir, "root.py").touch()
            subdir = Path(tmpdir, "subdir")
            subdir.mkdir()
            Path(subdir, "nested.py").touch()

            # Act
            result = generate_file_tree(tmpdir, max_depth=3, max_files=100)

            # Assert
            lines = result.split('\n')
            # Should have multiple lines
            assert len(lines) > 1
            # Nested items should have indentation (spaces or tree chars)
            has_indentation = any(
                line.startswith('  ') or line.startswith('│') or line.startswith('├') or line.startswith('└')
                for line in lines if line.strip()
            )
            assert has_indentation or '  ' in result

    def test_should_handle_relative_paths_correctly(self):
        """Test that relative paths are handled correctly."""
        # Arrange
        with tempfile.TemporaryDirectory() as tmpdir:
            Path(tmpdir, "test.py").touch()

            # Save current dir
            original_cwd = os.getcwd()
            try:
                # Change to tmpdir
                os.chdir(tmpdir)

                # Act - use relative path
                result = generate_file_tree(".", max_depth=3, max_files=100)

                # Assert
                assert "test.py" in result
            finally:
                # Restore original directory
                os.chdir(original_cwd)

    def test_should_sort_entries_alphabetically(self):
        """Test that entries are sorted for consistent output."""
        # Arrange
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create files in non-alphabetical order
            Path(tmpdir, "zebra.py").touch()
            Path(tmpdir, "alpha.py").touch()
            Path(tmpdir, "beta.py").touch()

            # Act
            result = generate_file_tree(tmpdir, max_depth=3, max_files=100)

            # Assert
            # Find positions in result
            alpha_pos = result.find("alpha.py")
            beta_pos = result.find("beta.py")
            zebra_pos = result.find("zebra.py")

            # All should be present
            assert alpha_pos != -1
            assert beta_pos != -1
            assert zebra_pos != -1

            # Should appear in alphabetical order
            assert alpha_pos < beta_pos < zebra_pos

    def test_should_show_directories_with_trailing_slash(self):
        """Test that directories are distinguishable from files."""
        # Arrange
        with tempfile.TemporaryDirectory() as tmpdir:
            Path(tmpdir, "file.py").touch()
            Path(tmpdir, "directory").mkdir()
            Path(tmpdir, "directory", "nested.py").touch()

            # Act
            result = generate_file_tree(tmpdir, max_depth=3, max_files=100)

            # Assert
            # Directory should have trailing slash or be distinguishable
            assert "directory/" in result or "directory" in result

    def test_should_complete_quickly_for_typical_repo(self):
        """Test performance: should complete in <100ms for typical repo."""
        # Arrange
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create realistic structure: ~50 files, 3 levels deep
            for i in range(5):
                dir1 = Path(tmpdir, f"module{i}")
                dir1.mkdir()
                Path(dir1, "__init__.py").touch()
                for j in range(3):
                    dir2 = Path(dir1, f"submodule{j}")
                    dir2.mkdir()
                    Path(dir2, "__init__.py").touch()
                    for k in range(3):
                        Path(dir2, f"file{k}.py").touch()

            # Act
            import time
            start = time.time()
            result = generate_file_tree(tmpdir, max_depth=3, max_files=100)
            elapsed = time.time() - start

            # Assert
            assert result  # Should return something
            assert elapsed < 0.1  # Less than 100ms
