"""
CSV Data Source Connector
=========================

Handles CSV file loading with various options:
- Custom delimiters
- Encoding support
- Header handling
- Type inference
"""

import polars as pl
from typing import Optional

from . import FileSource, SourceConfig, register_source


@register_source('csv')
class CSVSource(FileSource):
    """
    CSV file data source.

    YARRRML Example:
    ```yaml
    sources:
      csv-source:
        access: data/people.csv
        referenceFormulation: csv
        delimiter: ","
        encoding: utf-8
    ```
    """

    def fetch_data(self) -> pl.DataFrame:
        """Load CSV file into a Polars DataFrame."""
        if not self._connected:
            self.connect()

        return pl.read_csv(
            self.resolved_path,
            separator=self.config.delimiter,
            encoding=self.config.encoding if self.config.encoding != 'utf-8' else 'utf8',
            ignore_errors=True,
            try_parse_dates=True
        )


@register_source('tsv')
class TSVSource(CSVSource):
    """Tab-separated values source."""

    def __init__(self, config: SourceConfig, base_path: Optional[str] = None):
        super().__init__(config, base_path)
        # Override delimiter for TSV
        self.config.delimiter = '\t'

