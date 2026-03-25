#!/usr/bin/env python
"""Medical knowledge base ingestion CLI.

Usage:
    python scripts/ingest_medical.py --path ./data/medical_knowledge
    python scripts/ingest_medical.py --path ./data --collection my_collection
    python scripts/ingest_medical.py --path ./data --force
"""

import argparse
import sys
import time
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.core.settings import load_settings
from src.ingestion.pipeline import IngestionPipeline
from src.libs.embedding.embedding_factory import EmbeddingFactory
from src.libs.vector_store.vector_store_factory import VectorStoreFactory


def main():
    parser = argparse.ArgumentParser(
        description="Ingest medical knowledge base documents."
    )
    parser.add_argument(
        "--path",
        type=str,
        required=True,
        help="Path to source documents directory.",
    )
    parser.add_argument(
        "--collection",
        type=str,
        default="default",
        help="Collection name for vector store (default: default).",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force re-processing of all files, ignoring integrity cache.",
    )
    parser.add_argument(
        "--config",
        type=str,
        default="config/settings.yaml",
        help="Path to settings.yaml (default: config/settings.yaml).",
    )

    args = parser.parse_args()

    # Load settings
    config_path = Path(args.config)
    if not config_path.exists():
        print(f"Error: Config file not found: {config_path}")
        sys.exit(1)

    try:
        settings = load_settings(str(config_path))
    except Exception as e:
        print(f"Error loading settings: {e}")
        sys.exit(1)

    # Validate source path
    source_path = Path(args.path)
    if not source_path.exists():
        print(f"Error: Source path does not exist: {source_path}")
        sys.exit(1)

    # Create components
    try:
        embedding_client = EmbeddingFactory.create(settings)
        vector_store = VectorStoreFactory.create(settings)
    except Exception as e:
        print(f"Error creating components: {e}")
        sys.exit(1)

    # Progress callback
    def on_progress(stage: str, current: int, total: int):
        pct = (current / total * 100) if total > 0 else 0
        print(f"  [{stage}] {current}/{total} ({pct:.1f}%)")

    # Run pipeline
    pipeline = IngestionPipeline(
        settings=settings,
        vector_store=vector_store,
        embedding_client=embedding_client,
        on_progress=on_progress,
    )

    print(f"\nIngesting from: {source_path}")
    print(f"Collection: {args.collection}")
    print(f"Force reload: {args.force}")
    print("-" * 50)

    start_time = time.time()
    result = pipeline.run(
        source_path=str(source_path),
        collection=args.collection,
        force=args.force,
    )
    duration = time.time() - start_time

    # Print results
    print("-" * 50)
    print(f"Done in {duration:.2f}s")
    print(f"  Total files:   {result.total_files}")
    print(f"  Processed:     {result.processed_files}")
    print(f"  Skipped:       {result.skipped_files}")
    print(f"  Failed:        {result.failed_files}")
    print(f"  Total chunks:  {result.total_chunks}")

    if result.errors:
        print("\nErrors:")
        for error in result.errors:
            print(f"  - {error}")

    # Exit with error code if any failures
    sys.exit(0 if result.failed_files == 0 else 1)


if __name__ == "__main__":
    main()
