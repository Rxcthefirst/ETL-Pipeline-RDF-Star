#!/usr/bin/env python3
"""
Generate benchmark datasets for RDF-star ETL pipeline testing.

This script generates data_products and lineage CSV files with matching dataset_ids
to ensure proper join operations during RDF-star annotation generation.

Usage:
    python generate_benchmark_data.py --size 100k
    python generate_benchmark_data.py --size 500k
    python generate_benchmark_data.py --custom 250000
"""

import argparse
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent))

from generate_large_dataset import DataGenerator
import json


def get_data_products_config(num_rows: int) -> dict:
    """Configuration for data_products.csv"""
    return {
        "num_rows": num_rows,
        "seed": 42,
        "columns": [
            {"name": "dataset_id", "type": "id", "format": "DS"},
            {
                "name": "title",
                "type": "enum",
                "values": [
                    "Customer Segmentation Dataset",
                    "Mortgage Risk Analysis",
                    "Product Catalog Master",
                    "Sales Performance Metrics",
                    "Supply Chain Optimization",
                    "Financial Transaction Records",
                    "Marketing Campaign Analytics",
                    "Employee Performance Data",
                    "Inventory Management System",
                    "Customer Feedback Analysis",
                    "Real Estate Portfolio Data",
                    "Healthcare Patient Records",
                    "E-commerce Order History",
                    "Social Media Engagement Metrics",
                    "Network Traffic Analytics",
                    "IoT Sensor Data Collection",
                    "Credit Scoring Models",
                    "Fraud Detection Dataset",
                    "Regulatory Compliance Data",
                    "Business Intelligence Dashboard Data"
                ]
            },
            {"name": "issued", "type": "date", "format": "2023-01-01:2025-12-31"},
            {
                "name": "owner",
                "type": "enum",
                "values": [
                    "DataGovernanceTeam", "RiskManagement", "ProductTeam", "SalesOps",
                    "OperationsTeam", "FinanceTeam", "MarketingAnalytics", "HRDepartment",
                    "ITOperations", "CustomerInsights", "ComplianceTeam", "SecurityOps",
                    "DataEngineering", "BusinessIntelligence", "ResearchAndDevelopment"
                ]
            },
            {
                "name": "theme_uri",
                "type": "enum",
                "values": [
                    "http://example.org/themes/CustomerAnalytics",
                    "http://example.org/themes/fibo/MortgageRisk",
                    "http://example.org/themes/ProductData",
                    "http://example.org/themes/SalesAnalytics",
                    "http://example.org/themes/SupplyChain",
                    "http://example.org/themes/FinancialServices",
                    "http://example.org/themes/Marketing",
                    "http://example.org/themes/HumanResources",
                    "http://example.org/themes/Operations",
                    "http://example.org/themes/CustomerExperience",
                    "http://example.org/themes/RealEstate",
                    "http://example.org/themes/Healthcare",
                    "http://example.org/themes/Ecommerce",
                    "http://example.org/themes/SocialMedia",
                    "http://example.org/themes/NetworkSecurity",
                    "http://example.org/themes/IoT",
                    "http://example.org/themes/CreditRisk",
                    "http://example.org/themes/FraudDetection",
                    "http://example.org/themes/Compliance",
                    "http://example.org/themes/BusinessIntelligence"
                ]
            }
        ]
    }


def get_lineage_config(num_rows: int) -> dict:
    """Configuration for lineage.csv"""
    return {
        "num_rows": num_rows,
        "seed": 42,  # Same seed ensures matching dataset_ids
        "columns": [
            {"name": "dataset_id", "type": "id", "format": "DS"},
            {
                "name": "source_system",
                "type": "enum",
                "values": [
                    "COLLIBRA", "ALATION", "INFORMATICA", "TALEND", "AZURE_PURVIEW",
                    "AWS_GLUE", "DATABRICKS", "SNOWFLAKE", "APACHE_ATLAS", "ERWIN",
                    "IBM_IGC", "SAP_MDG", "ORACLE_EDQ", "ALTERYX", "TABLEAU_CATALOG"
                ]
            },
            {
                "name": "extract_time",
                "type": "enum",
                "values": [
                    "2025-02-15T10:30:00Z", "2025-02-15T10:35:00Z", "2025-02-15T10:40:00Z",
                    "2025-02-15T11:00:00Z", "2025-02-15T11:30:00Z", "2025-02-15T12:00:00Z",
                    "2025-02-15T13:00:00Z", "2025-02-15T14:00:00Z", "2025-02-15T15:00:00Z",
                    "2025-02-15T16:00:00Z"
                ]
            },
            {
                "name": "run_id",
                "type": "enum",
                "values": [
                    "RUN_20250215_001", "RUN_20250215_002", "RUN_20250215_003",
                    "RUN_20250215_004", "RUN_20250215_005", "RUN_20250215_006",
                    "RUN_20250215_007", "RUN_20250215_008", "RUN_20250215_009",
                    "RUN_20250215_010"
                ]
            },
            {"name": "confidence", "type": "float", "min": 0.75, "max": 0.99, "decimals": 2},
            {
                "name": "rule_id",
                "type": "enum",
                "values": [
                    "RULE_001", "RULE_002", "RULE_003", "RULE_004", "RULE_005",
                    "RULE_006", "RULE_007", "RULE_008", "RULE_009", "RULE_010"
                ]
            }
        ]
    }


def main():
    parser = argparse.ArgumentParser(
        description='Generate benchmark data for RDF-star ETL pipeline',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  # Generate 10K rows (quick test)
  python generate_benchmark_data.py --size 10k

  # Generate 100K rows (medium benchmark)
  python generate_benchmark_data.py --size 100k

  # Generate 500K rows (large benchmark)
  python generate_benchmark_data.py --size 500k

  # Generate custom size
  python generate_benchmark_data.py --custom 250000

  # Specify output directory
  python generate_benchmark_data.py --size 100k --output ../ETL-RDF-STAR/benchmark_data
        '''
    )
    parser.add_argument('--size', choices=['10k', '100k', '500k', '1m'],
                        help='Predefined dataset size')
    parser.add_argument('--custom', type=int,
                        help='Custom number of rows')
    parser.add_argument('--output', type=str, default='../ETL-RDF-STAR/benchmark_data',
                        help='Output directory for generated files')
    parser.add_argument('--save-configs', action='store_true',
                        help='Save the configuration files used')

    args = parser.parse_args()

    # Determine number of rows
    if args.custom:
        num_rows = args.custom
        size_label = f"{num_rows//1000}k"
    elif args.size:
        size_map = {'10k': 10000, '100k': 100000, '500k': 500000, '1m': 1000000}
        num_rows = size_map[args.size]
        size_label = args.size
    else:
        print("Error: Must specify --size or --custom")
        parser.print_help()
        return 1

    # Create output directory
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"\n{'='*80}")
    print(f"GENERATING BENCHMARK DATA: {num_rows:,} rows ({size_label})")
    print(f"{'='*80}\n")

    # Generate data_products.csv
    print("1. Generating data_products.csv...")
    dp_config = get_data_products_config(num_rows)
    dp_generator = DataGenerator(dp_config)
    df_products = dp_generator.generate()

    products_file = output_dir / f"data_products_{size_label}.csv"
    df_products.write_csv(products_file)
    print(f"   ✓ Saved to: {products_file}")
    print(f"   ✓ File size: {products_file.stat().st_size / (1024*1024):.2f} MB\n")

    # Generate lineage.csv
    print("2. Generating lineage.csv...")
    lineage_config = get_lineage_config(num_rows)
    lineage_generator = DataGenerator(lineage_config)
    df_lineage = lineage_generator.generate()

    lineage_file = output_dir / f"lineage_{size_label}.csv"
    df_lineage.write_csv(lineage_file)
    print(f"   ✓ Saved to: {lineage_file}")
    print(f"   ✓ File size: {lineage_file.stat().st_size / (1024*1024):.2f} MB\n")

    # Save configurations if requested
    if args.save_configs:
        dp_config_file = Path(f"config_data_products_{size_label}.json")
        with open(dp_config_file, 'w') as f:
            json.dump(dp_config, f, indent=2)
        print(f"   ✓ Saved config: {dp_config_file}")

        lineage_config_file = Path(f"config_lineage_{size_label}.json")
        with open(lineage_config_file, 'w') as f:
            json.dump(lineage_config, f, indent=2)
        print(f"   ✓ Saved config: {lineage_config_file}\n")

    # Summary
    total_size_mb = (products_file.stat().st_size + lineage_file.stat().st_size) / (1024*1024)

    print(f"{'='*80}")
    print(f"BENCHMARK DATA GENERATION COMPLETE")
    print(f"{'='*80}")
    print(f"Files generated:")
    print(f"  - {products_file.name}")
    print(f"  - {lineage_file.name}")
    print(f"\nTotal size: {total_size_mb:.2f} MB")
    print(f"Total rows: {num_rows * 2:,} (across both files)")
    print(f"\nExpected RDF-star output:")
    print(f"  - Base triples: {num_rows * 8:,}")
    print(f"  - Quoted triple annotations: {num_rows * 25:,}")
    print(f"  - Total quads: ~{num_rows * 33:,}")
    print(f"{'='*80}\n")

    return 0


if __name__ == '__main__':
    exit(main())

