#!/usr/bin/env python3
"""
Run comprehensive benchmark suite for AI Counsel local models.

This script provides a convenient interface to run different types of benchmarks
for local models, with options for different test categories and reporting.
"""

import asyncio
import argparse
import subprocess
import sys
from pathlib import Path


def run_pytest(args):
    """Run pytest with specified arguments."""
    cmd = ["python3", "-m", "pytest", "-v"] + args
    
    print(f"🚀 Running: {' '.join(cmd)}")
    print("=" * 60)
    
    result = subprocess.run(cmd, cwd=Path(__file__).parent.parent)
    return result.returncode


def check_local_models():
    """Check if local models are available."""
    print("🔍 Checking local model availability...")
    
    # Check Ollama
    try:
        import subprocess
        result = subprocess.run(
            ["curl", "-s", "http://localhost:11434/api/tags"],
            capture_output=True, text=True
        )
        if result.returncode == 0:
            print("✅ Ollama is running")
            return True
        else:
            print("❌ Ollama is not running on localhost:11434")
            return False
    except Exception as e:
        print(f"❌ Error checking Ollama: {e}")
        return False
    
    # Check LM Studio
    try:
        result = subprocess.run(
            ["curl", "-s", "http://localhost:1234/v1/models"],
            capture_output=True, text=True
        )
        if result.returncode == 0:
            print("✅ LM Studio is running")
            return True
        else:
            print("❌ LM Studio is not running on localhost:1234")
            return False
    except Exception as e:
        print(f"❌ Error checking LM Studio: {e}")
        return False


async def main():
    """Main benchmark runner."""
    parser = argparse.ArgumentParser(
        description="Run AI Counsel local model benchmarks",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run all local model benchmarks
  python scripts/run_local_model_benchmarks.py --all

  # Run only performance benchmarks
  python scripts/run_local_model_benchmarks.py --performance

  # Run only legal domain tests
  python scripts/run_local_model_benchmarks.py --legal

  # Run specific test file
  python scripts/run_local_model_benchmarks.py --file test_local_models_benchmark.py

  # Run with coverage report
  python scripts/run_local_model_benchmarks.py --all --coverage
        """
    )
    
    # Test categories
    test_group = parser.add_mutually_exclusive_group()
    test_group.add_argument("--all", action="store_true", help="Run all local model benchmarks")
    test_group.add_argument("--performance", action="store_true", help="Run performance benchmarks only")
    test_group.add_argument("--legal", action="store_true", help="Run legal domain tests only")
    test_group.add_argument("--technical", action="store_true", help="Run technical decision tests only")
    test_group.add_argument("--comparison", action="store_true", help="Run local vs cloud comparisons only")
    test_group.add_argument("--file", help="Run specific test file")
    
    # Additional options
    parser.add_argument("--coverage", action="store_true", help="Generate coverage report")
    parser.add_argument("--no-check", action="store_true", help="Skip local model availability check")
    parser.add_argument("--parallel", "-n", type=int, default=1, help="Number of parallel workers")
    
    args = parser.parse_args()
    
    # Check local models unless explicitly skipped
    if not args.no_check:
        if not check_local_models():
            if not args.no_check:
                print("\n⚠️  Local models not detected. Use --no-check to proceed anyway.")
                print("💡 Make sure Ollama or LM Studio is running before running benchmarks.")
                sys.exit(1)
    
    # Build pytest arguments
    pytest_args = []
    
    if args.coverage:
        pytest_args.extend(["--cov= deliberation", "--cov-report=html", "--cov-report=term"])
    
    if args.parallel > 1:
        pytest_args.extend(["-n", str(args.parallel)])
    
    # Determine which tests to run
    if args.all:
        pytest_args.extend(["-m", "local_model"])
    elif args.performance:
        pytest_args.extend(["tests/benchmark/test_local_models_benchmark.py"])
    elif args.legal:
        pytest_args.extend(["tests/benchmark/test_legal_domain_quality.py"])
    elif args.technical:
        pytest_args.extend(["tests/benchmark/test_technical_decisions_quality.py"])
    elif args.comparison:
        pytest_args.extend(["tests/benchmark/test_local_vs_cloud_comparison.py"])
    elif args.file:
        pytest_args.append(f"tests/benchmark/{args.file}")
    else:
        # Default to running a quick performance test
        pytest_args.extend(["tests/benchmark/test_local_models_benchmark.py::TestLocalModelBenchmark::test_ollama_performance_benchmark"])
    
    # Run the tests
    exit_code = run_pytest(pytest_args)
    
    # Print summary
    if exit_code == 0:
        print("\n" + "="*60)
        print("✅ BENCHMARKS COMPLETED SUCCESSFULLY")
        print("="*60)
        print("\n📊 Results Summary:")
        print("   • Performance metrics: Response times, throughput, memory usage")
        print("   • Quality assessments: Legal reasoning, technical analysis")
        print("   • Cost analysis: Local vs cloud cost comparison")
        print("   • Privacy evaluation: Data security and compliance analysis")
        print("\n💡 Next steps:")
        print("   • Review detailed results in pytest output above")
        print("   • Check HTML coverage report if --coverage was used")
        print("   • Consider optimizing based on performance bottlenecks identified")
    else:
        print("\n" + "="*60)
        print("❌ BENCHMARKS FAILED")
        print("="*60)
        print("\n🔍 Troubleshooting:")
        print("   • Check if local models are running")
        print("   • Verify configuration files")
        print("   • Review error messages above for specific issues")
    
    return exit_code


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
