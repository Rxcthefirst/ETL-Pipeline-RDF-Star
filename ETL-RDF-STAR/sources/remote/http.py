"""
HTTP/REST API Data Source Connector
====================================

Fetches data from HTTP endpoints (REST APIs).

Dependencies:
    pip install requests

YARRRML Example:
```yaml
sources:
  api-source:
    type: remotefile
    access: https://api.example.com/v1/users
    referenceFormulation: jsonpath
    iterator: $.data[*]
    headers:
      Authorization: Bearer ${API_TOKEN}
      Accept: application/json
    contentType: application/json
```
"""

import json
import polars as pl
from typing import Optional, List, Dict, Any

from .. import RemoteSource, SourceConfig, register_source, interpolate_dict_env_vars
from ..json_source import extract_jsonpath, flatten_json


@register_source('remotefile')
@register_source('http')
@register_source('https')
@register_source('rest')
@register_source('api')
class HTTPSource(RemoteSource):
    """
    HTTP/REST API data source.

    Supports:
    - GET requests to REST endpoints
    - Custom headers (including authentication)
    - JSON and CSV response parsing
    - JSONPath for extracting nested data
    """

    def __init__(self, config: SourceConfig):
        super().__init__(config)
        self.response_data = None

    def validate_config(self) -> List[str]:
        errors = super().validate_config()
        return errors

    def connect(self) -> None:
        """Validate URL and prepare headers."""
        try:
            import requests
            self.session = requests.Session()
        except ImportError:
            raise ImportError(
                "requests library required for HTTP sources. "
                "Install with: pip install requests"
            )

        # Set up headers
        headers = self.config.headers or {}

        # Interpolate environment variables in headers
        if headers:
            headers = interpolate_dict_env_vars(headers)

        # Set default content type
        if 'Accept' not in headers:
            content_type = self.config.contentType or 'application/json'
            headers['Accept'] = content_type

        self.session.headers.update(headers)
        self._connected = True

    def close(self) -> None:
        """Close HTTP session."""
        if self.session:
            self.session.close()
            self.session = None
        self._connected = False

    def fetch_data(self) -> pl.DataFrame:
        """Fetch data from HTTP endpoint."""
        if not self._connected:
            self.connect()

        url = self.config.access

        # Make request
        response = self.session.get(
            url,
            timeout=self.config.timeout
        )
        response.raise_for_status()

        # Parse response based on content type
        content_type = response.headers.get('Content-Type', '').lower()

        if 'json' in content_type or self.config.reference_formulation == 'jsonpath':
            return self._parse_json_response(response.text)
        elif 'csv' in content_type or self.config.reference_formulation == 'csv':
            return self._parse_csv_response(response.text)
        else:
            # Default to JSON
            return self._parse_json_response(response.text)

    def _parse_json_response(self, text: str) -> pl.DataFrame:
        """Parse JSON response with optional JSONPath."""
        data = json.loads(text)

        # Apply JSONPath iterator if specified
        if self.config.iterator:
            records = extract_jsonpath(data, self.config.iterator)
        else:
            if isinstance(data, list):
                records = [item if isinstance(item, dict) else {'value': item} for item in data]
            elif isinstance(data, dict):
                records = [data]
            else:
                records = [{'value': data}]

        if not records:
            return pl.DataFrame()

        # Flatten nested structures
        flat_records = [flatten_json(r) if isinstance(r, dict) else r for r in records]

        return pl.DataFrame(flat_records)

    def _parse_csv_response(self, text: str) -> pl.DataFrame:
        """Parse CSV response."""
        from io import StringIO
        return pl.read_csv(
            StringIO(text),
            separator=self.config.delimiter,
            ignore_errors=True
        )

