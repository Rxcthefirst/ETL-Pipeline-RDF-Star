"""
XML Data Source Connector with XPath Support
=============================================

Handles XML file loading with XPath queries for extracting data.

Dependencies:
    pip install lxml (optional, falls back to xml.etree)

YARRRML Example:
```yaml
sources:
  xml-source:
    access: data/catalog.xml
    referenceFormulation: xpath
    iterator: //product
```
"""

import polars as pl
from typing import Any, List, Dict, Optional
from xml.etree import ElementTree as ET

from . import FileSource, SourceConfig, register_source


def element_to_dict(element, include_attribs: bool = True) -> Dict[str, Any]:
    """
    Convert an XML element to a dictionary.

    Attributes are prefixed with '@'.
    Text content is stored under '#text'.
    """
    result = {}

    # Add attributes
    if include_attribs and element.attrib:
        for key, value in element.attrib.items():
            result[f"@{key}"] = value

    # Add text content
    if element.text and element.text.strip():
        if len(element) == 0:  # No children
            result['#text'] = element.text.strip()
        else:
            result['#text'] = element.text.strip()

    # Add children
    for child in element:
        child_dict = element_to_dict(child, include_attribs)
        child_name = child.tag

        # Remove namespace prefix for cleaner keys
        if '}' in child_name:
            child_name = child_name.split('}', 1)[1]

        if child_name in result:
            # Multiple children with same name -> make list
            if not isinstance(result[child_name], list):
                result[child_name] = [result[child_name]]
            result[child_name].append(child_dict if child_dict else child.text)
        else:
            result[child_name] = child_dict if child_dict else child.text

    # If only text content, return just the text
    if len(result) == 1 and '#text' in result:
        return result['#text']

    return result


def flatten_xml_dict(d: Dict[str, Any], prefix: str = '') -> Dict[str, Any]:
    """Flatten nested XML dictionary for DataFrame conversion."""
    flat = {}

    for key, value in d.items():
        # Clean up key
        clean_key = key.lstrip('@').replace('#text', 'text')
        new_key = f"{prefix}_{clean_key}" if prefix else clean_key

        if isinstance(value, dict):
            flat.update(flatten_xml_dict(value, new_key))
        elif isinstance(value, list):
            # For lists, just take first or join
            if all(isinstance(v, str) for v in value):
                flat[new_key] = ', '.join(str(v) for v in value)
            elif len(value) > 0:
                flat[new_key] = str(value[0])
        else:
            flat[new_key] = value

    return flat


def extract_xpath(root: ET.Element, xpath: str, namespaces: Optional[Dict[str, str]] = None) -> List[ET.Element]:
    """
    Extract elements using XPath expression.

    Note: Python's built-in ElementTree has limited XPath support.
    For full XPath, use lxml.
    """
    try:
        # Try lxml first for full XPath support
        from lxml import etree

        if isinstance(root, ET.Element):
            # Convert to lxml element
            xml_string = ET.tostring(root, encoding='unicode')
            root = etree.fromstring(xml_string.encode())

        return root.xpath(xpath, namespaces=namespaces or {})

    except ImportError:
        # Fall back to built-in ElementTree (limited XPath)
        # Only supports: tag, *, ., .., @attrib, [tag], [position], //
        try:
            return list(root.findall(xpath, namespaces))
        except SyntaxError:
            # Try simplified path
            simplified = xpath.replace('//', './/').lstrip('/')
            return list(root.findall(simplified, namespaces))


@register_source('xpath')
@register_source('xml')
class XMLSource(FileSource):
    """
    XML file data source with XPath support.

    YARRRML Example:
    ```yaml
    sources:
      xml-source:
        access: data/catalog.xml
        referenceFormulation: xpath
        iterator: //product
    ```

    XML Structure:
    ```xml
    <catalog>
      <product id="1">
        <name>Widget</name>
        <price>9.99</price>
      </product>
      <product id="2">
        <name>Gadget</name>
        <price>19.99</price>
      </product>
    </catalog>
    ```

    Result DataFrame:
    | id | name   | price |
    |----|--------|-------|
    | 1  | Widget | 9.99  |
    | 2  | Gadget | 19.99 |
    """

    def fetch_data(self) -> pl.DataFrame:
        """Load XML file and extract data using XPath."""
        if not self._connected:
            self.connect()

        # Parse XML file
        tree = ET.parse(self.resolved_path)
        root = tree.getroot()

        # Extract namespace mappings from root
        namespaces = {}
        for key, value in root.attrib.items():
            if key.startswith('{'):
                ns_uri = key[1:key.index('}')]
                namespaces['ns'] = ns_uri

        # Apply XPath iterator if specified
        if self.config.iterator:
            elements = extract_xpath(root, self.config.iterator, namespaces)
        else:
            # No iterator - use all direct children
            elements = list(root)

        if not elements:
            return pl.DataFrame()

        # Convert elements to dictionaries
        records = []
        for elem in elements:
            # Handle lxml elements
            if hasattr(elem, 'tag'):
                elem_dict = element_to_dict(elem)
                if isinstance(elem_dict, dict):
                    flat_dict = flatten_xml_dict(elem_dict)
                    records.append(flat_dict)
                else:
                    records.append({'value': elem_dict})

        if not records:
            return pl.DataFrame()

        # Convert to DataFrame
        return pl.DataFrame(records)

