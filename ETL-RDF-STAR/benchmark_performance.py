"""
Performance Benchmark: Original vs Optimized ETL Engine
=======================================================

This script compares the performance of:
1. Original engine (rdf_star_etl_engine_dynamic.py)
2. Optimized engine (rdf_star_etl_engine_optimized.py)

Runs multiple iterations and reports timing statistics.
"""

import time
import sys
from pathlib import Path

# Import both engines
from rdf_star_etl_engine_dynamic import RDFStarETLEngine as OriginalEngine
from rdf_star_etl_engine_optimized import RDFStarETLEngineOptimized as OptimizedEngine


def benchmark_engine(engine_class, name, iterations=3):
    """Benchmark an engine class"""
    print(f"\n{'='*80}")
    print(f"Benchmarking: {name}")
    print(f"{'='*80}")

    times = []

    for i in range(iterations):
        print(f"\nIteration {i+1}/{iterations}...")

        # Create engine instance
        engine = engine_class("etl_pipeline_config.yaml")

        # Time the execution
        start = time.perf_counter()
        engine.run()
        end = time.perf_counter()

        elapsed = end - start
        times.append(elapsed)

        print(f"  → Time: {elapsed:.4f} seconds")

    # Calculate statistics
    avg_time = sum(times) / len(times)
    min_time = min(times)
    max_time = max(times)

    print(f"\n{'='*80}")
    print(f"{name} - Summary")
    print(f"{'='*80}")
    print(f"Average time: {avg_time:.4f} seconds")
    print(f"Min time:     {min_time:.4f} seconds")
    print(f"Max time:     {max_time:.4f} seconds")
    print(f"{'='*80}")

    return {
        'name': name,
        'times': times,
        'avg': avg_time,
        'min': min_time,
        'max': max_time
    }


def compare_results(original_stats, optimized_stats):
    """Compare and report performance differences"""
    print(f"\n{'='*80}")
    print(f"PERFORMANCE COMPARISON")
    print(f"{'='*80}")

    speedup = original_stats['avg'] / optimized_stats['avg']
    time_saved = original_stats['avg'] - optimized_stats['avg']
    percent_faster = ((original_stats['avg'] - optimized_stats['avg']) / original_stats['avg']) * 100

    print(f"\nOriginal Engine:")
    print(f"  Average: {original_stats['avg']:.4f} seconds")

    print(f"\nOptimized Engine:")
    print(f"  Average: {optimized_stats['avg']:.4f} seconds")

    print(f"\nPerformance Gain:")
    print(f"  Speedup:      {speedup:.2f}x faster")
    print(f"  Time saved:   {time_saved:.4f} seconds")
    print(f"  Improvement:  {percent_faster:.1f}% faster")

    print(f"\n{'='*80}")
    print(f"VERDICT")
    print(f"{'='*80}")

    if speedup > 1.5:
        print(f"✅ SIGNIFICANT improvement! Optimized version is {speedup:.2f}x faster.")
    elif speedup > 1.1:
        print(f"✅ MODERATE improvement. Optimized version is {speedup:.2f}x faster.")
    elif speedup > 0.95:
        print(f"⚠️  MINIMAL difference. Performance is similar.")
    else:
        print(f"❌ SLOWER. Optimized version is actually slower.")

    print(f"{'='*80}\n")

    return {
        'speedup': speedup,
        'time_saved': time_saved,
        'percent_faster': percent_faster
    }


def main():
    """Run the benchmark"""
    print(f"\n{'#'*80}")
    print(f"# RDF-STAR ETL ENGINE PERFORMANCE BENCHMARK")
    print(f"{'#'*80}")

    iterations = 3

    try:
        # Benchmark original engine
        original_stats = benchmark_engine(
            OriginalEngine,
            "Original Engine (Python loops)",
            iterations=iterations
        )

        # Benchmark optimized engine
        optimized_stats = benchmark_engine(
            OptimizedEngine,
            "Optimized Engine (Vectorized)",
            iterations=iterations
        )

        # Compare results
        comparison = compare_results(original_stats, optimized_stats)

        # Save results
        with open("benchmark_results.txt", "w") as f:
            f.write(f"RDF-star ETL Engine Performance Benchmark\n")
            f.write(f"{'='*80}\n\n")
            f.write(f"Original Engine (Python loops):\n")
            f.write(f"  Average: {original_stats['avg']:.4f} seconds\n")
            f.write(f"  Min:     {original_stats['min']:.4f} seconds\n")
            f.write(f"  Max:     {original_stats['max']:.4f} seconds\n\n")
            f.write(f"Optimized Engine (Vectorized):\n")
            f.write(f"  Average: {optimized_stats['avg']:.4f} seconds\n")
            f.write(f"  Min:     {optimized_stats['min']:.4f} seconds\n")
            f.write(f"  Max:     {optimized_stats['max']:.4f} seconds\n\n")
            f.write(f"Performance Gain:\n")
            f.write(f"  Speedup:     {comparison['speedup']:.2f}x\n")
            f.write(f"  Time saved:  {comparison['time_saved']:.4f} seconds\n")
            f.write(f"  Improvement: {comparison['percent_faster']:.1f}%\n")

        print(f"\n✅ Benchmark results saved to benchmark_results.txt")

        return 0

    except Exception as e:
        print(f"\n❌ Benchmark failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit(main())

