"""
JSON Data Source Connector with JSONPath Support
=================================================

Handles JSON file loading with JSONPath queries for extracting data
from nested structures.

Dependencies:
    pip install jsonpath-ng

YARRRML Example:
```yaml
sources:
  json-source:
    access: data/api_response.json
    referenceFormulation: jsonpath
    iterator: $.data.users[*]
```
"""

import json
import polars as pl
from typing import Any, List, Dict, Optional

from . import FileSource, SourceConfig, register_source


def flatten_json(nested_json: Dict[str, Any], prefix: str = '') -> Dict[str, Any]:
    """
    Flatten a nested JSON object into a single-level dictionary.

    Example:
        {"user": {"name": "John", "age": 30}}
        -> {"user_name": "John", "user_age": 30}
    """
    flat = {}
    for key, value in nested_json.items():
        new_key = f"{prefix}_{key}" if prefix else key
        if isinstance(value, dict):
            flat.update(flatten_json(value, new_key))
        elif isinstance(value, list):
            # Handle lists of primitives
            if all(not isinstance(v, (dict, list)) for v in value):
                flat[new_key] = value
            else:
                # Lists of objects get indexed
                for i, item in enumerate(value):
                    if isinstance(item, dict):
                        flat.update(flatten_json(item, f"{new_key}_{i}"))
                    else:
                        flat[f"{new_key}_{i}"] = item
        else:
            flat[new_key] = value
    return flat


def extract_jsonpath(data: Any, path: str) -> List[Dict[str, Any]]:
    """
    Extract data using JSONPath expression.

    Supports common JSONPath syntax:
    - $ : root object
    - .key : child key
    - [*] : all array elements
    - [0] : specific array index
    - .. : recursive descent (limited support)
    """
    try:
        from jsonpath_ng import parse as jsonpath_parse
        from jsonpath_ng.ext import parse as jsonpath_parse_ext

        try:
            # Try extended parser first (supports more features)
            expr = jsonpath_parse_ext(path)
        except:
            expr = jsonpath_parse(path)

        matches = expr.find(data)
        results = []
        for match in matches:
            value = match.value
            if isinstance(value, dict):
                results.append(value)
            elif isinstance(value, list):
                for item in value:
                    if isinstance(item, dict):
                        results.append(item)
                    else:
                        results.append({'value': item})
            else:
                results.append({'value': value})
        return results

    except ImportError:
        # Fallback: simple path parsing without jsonpath-ng
        return _simple_jsonpath(data, path)


def _simple_jsonpath(data: Any, path: str) -> List[Dict[str, Any]]:
    """
    Simple JSONPath parser for basic paths when jsonpath-ng is not installed.

    Supports: $, .key, [*], [n]
    """
    if not path or path == '$':
        if isinstance(data, list):
            return [item if isinstance(item, dict) else {'value': item} for item in data]
        elif isinstance(data, dict):
            return [data]
        return [{'value': data}]

    # Remove leading $
    if path.startswith('$.'):
        path = path[2:]
    elif path.startswith('$'):
        path = path[1:]

    current = data
    parts = []

    # Parse path into parts
    i = 0
    while i < len(path):
        if path[i] == '.':
            i += 1
        elif path[i] == '[':
            end = path.index(']', i)
            parts.append(path[i:end+1])
            i = end + 1
        else:
            # Find end of key
            end = i
            while end < len(path) and path[end] not in '.[]':
                end += 1
            parts.append(path[i:end])
            i = end

    # Navigate path
    for part in parts:
        if current is None:
            return []

        if part == '[*]':
            if isinstance(current, list):
                # Continue with all items
                results = []
                remaining = '.'.join(parts[parts.index(part)+1:])
                for item in current:
                    results.extend(_simple_jsonpath(item, '$.' + remaining if remaining else '$'))
                return results
            return []
        elif part.startswith('[') and part.endswith(']'):
            # Array index
            try:
                idx = int(part[1:-1])
                current = current[idx] if isinstance(current, list) else None
            except (ValueError, IndexError):
                return []
        else:
            # Object key
            if isinstance(current, dict):
                current = current.get(part)
            else:
                return []

    # Return result
    if isinstance(current, list):
        return [item if isinstance(item, dict) else {'value': item} for item in current]
    elif isinstance(current, dict):
        return [current]
    elif current is not None:
        return [{'value': current}]
    return []


@register_source('jsonpath')
@register_source('json')
class JSONSource(FileSource):
    """
    JSON file data source with JSONPath support.

    YARRRML Example:
    ```yaml
    sources:
      json-source:
        access: data/users.json
        referenceFormulation: jsonpath
        iterator: $.users[*]
    ```

    JSON Structure:
    ```json
    {
      "users": [
        {"id": 1, "name": "Alice", "email": "alice@example.com"},
        {"id": 2, "name": "Bob", "email": "bob@example.com"}
      ]
    }
    ```

    Result DataFrame:
    | id | name  | email             |
    |----|-------|-------------------|
    | 1  | Alice | alice@example.com |
    | 2  | Bob   | bob@example.com   |
    """

    def fetch_data(self) -> pl.DataFrame:
        """Load JSON file and extract data using JSONPath."""
        if not self._connected:
            self.connect()

        # Load JSON file
        with open(self.resolved_path, 'r', encoding=self.config.encoding) as f:
            data = json.load(f)

        # Apply JSONPath iterator if specified
        if self.config.iterator:
            records = extract_jsonpath(data, self.config.iterator)
        else:
            # No iterator - use root
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

        # Convert to DataFrame
        return pl.DataFrame(flat_records)

