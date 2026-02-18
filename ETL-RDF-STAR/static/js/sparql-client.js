/**
 * SPARQL Client - Interactive Graph Visualization
 * Neo4j-style interface for RDF knowledge graphs
 */

class SPARQLClient {
    constructor() {
        this.endpoint = '/sparql';
        this.currentResults = null;
        this.selectedNode = null;
        this.graphData = { nodes: [], edges: [] };
        this.simulation = null;
        this.svg = null;
        this.zoom = null;
        this.transform = d3.zoomIdentity;

        this.init();
    }

    init() {
        this.bindEvents();
        this.initGraph();
        this.loadQueryTemplates();
        this.updateStatus('Ready', 'success');
    }

    bindEvents() {
        // Run query button
        document.getElementById('run-query').addEventListener('click', () => this.runQuery());

        // Clear button
        document.getElementById('clear-query').addEventListener('click', () => this.clearQuery());

        // Keyboard shortcut (Ctrl+Enter to run)
        document.getElementById('query-input').addEventListener('keydown', (e) => {
            if (e.ctrlKey && e.key === 'Enter') {
                this.runQuery();
            }
        });

        // Tab switching
        document.querySelectorAll('.tab').forEach(tab => {
            tab.addEventListener('click', () => this.switchTab(tab.dataset.tab));
        });

        // Query template selection
        document.getElementById('query-templates').addEventListener('change', (e) => {
            if (e.target.value) {
                document.getElementById('query-input').value = e.target.value;
            }
        });

        // Close details panel
        document.getElementById('close-details').addEventListener('click', () => {
            document.querySelector('.details-panel').classList.add('collapsed');
            this.selectedNode = null;
        });

        // Graph controls
        document.getElementById('zoom-in').addEventListener('click', () => this.zoomGraph(1.3));
        document.getElementById('zoom-out').addEventListener('click', () => this.zoomGraph(0.7));
        document.getElementById('zoom-fit').addEventListener('click', () => this.fitGraph());
    }

    loadQueryTemplates() {
        const templates = [
            {
                name: 'All Customers (Batch 1)',
                query: `SELECT ?customer ?name ?score
FROM <http://example.org/batch/2026-02-15T10:00:00Z>
WHERE {
    ?customer a <http://schema.org/Person> ;
              <http://xmlns.com/foaf/0.1/name> ?name ;
              <http://schema.org/creditScore> ?score .
}
ORDER BY ?name`
            },
            {
                name: 'All Customers (Batch 2 - Current)',
                query: `SELECT ?customer ?name ?score
FROM <http://example.org/batch/2026-02-17T10:00:00Z>
WHERE {
    ?customer a <http://schema.org/Person> ;
              <http://xmlns.com/foaf/0.1/name> ?name ;
              <http://schema.org/creditScore> ?score .
}
ORDER BY ?name`
            },
            {
                name: 'Customer with Provenance',
                query: `SELECT ?customer ?name ?score ?source ?confidence ?timestamp
WHERE {
    GRAPH ?g {
        ?customer a <http://schema.org/Person> ;
                  <http://xmlns.com/foaf/0.1/name> ?name ;
                  <http://schema.org/creditScore> ?score .

        ?reifier <http://www.w3.org/1999/02/22-rdf-syntax-ns#reifies> ?triple ;
                 <http://www.w3.org/ns/prov#wasDerivedFrom> ?source ;
                 <http://www.w3.org/ns/prov#generatedAtTime> ?timestamp .
        OPTIONAL { ?reifier <http://example.org/confidence> ?confidence }
    }
}
ORDER BY ?name`
            },
            {
                name: 'Score Changes Between Batches',
                query: `SELECT ?customer ?name ?oldScore ?newScore
WHERE {
    GRAPH <http://example.org/batch/2026-02-15T10:00:00Z> {
        ?customer <http://xmlns.com/foaf/0.1/name> ?name ;
                  <http://schema.org/creditScore> ?oldScore .
    }
    GRAPH <http://example.org/batch/2026-02-17T10:00:00Z> {
        ?customer <http://schema.org/creditScore> ?newScore .
    }
    FILTER(?oldScore != ?newScore)
}
ORDER BY ?name`
            },
            {
                name: 'AS OF Feb 15 (Provenance-Based)',
                query: `SELECT DISTINCT ?customer ?name ?score ?timestamp ?source
WHERE {
    GRAPH ?g {
        ?customer a <http://schema.org/Person> ;
                  <http://xmlns.com/foaf/0.1/name> ?name ;
                  <http://schema.org/creditScore> ?score .

        ?reifier <http://www.w3.org/1999/02/22-rdf-syntax-ns#reifies> ?triple ;
                 <http://www.w3.org/ns/prov#generatedAtTime> ?timestamp ;
                 <http://www.w3.org/ns/prov#wasDerivedFrom> ?source .
    }
    FILTER(?timestamp <= "2026-02-15T23:59:59Z"^^<http://www.w3.org/2001/XMLSchema#dateTime>)
}
ORDER BY ?name`
            },
            {
                name: 'All Batches',
                query: `SELECT ?batch ?batchNumber ?status ?created
WHERE {
    GRAPH <http://example.org/graph/metadata> {
        ?batch a <http://example.org/Batch> ;
               <http://example.org/batchNumber> ?batchNumber ;
               <http://example.org/status> ?status .
        OPTIONAL { ?batch <http://purl.org/dc/terms/created> ?created }
    }
}
ORDER BY DESC(?batchNumber)`
            },
            {
                name: 'Alice Score History',
                query: `SELECT ?score ?timestamp ?source ?confidence
WHERE {
    GRAPH ?g {
        <http://example.org/customer/C001> <http://schema.org/creditScore> ?score .

        ?reifier <http://www.w3.org/1999/02/22-rdf-syntax-ns#reifies> ?triple ;
                 <http://www.w3.org/ns/prov#generatedAtTime> ?timestamp ;
                 <http://www.w3.org/ns/prov#wasDerivedFrom> ?source .
        OPTIONAL { ?reifier <http://example.org/confidence> ?confidence }
    }
}
ORDER BY ?timestamp`
            }
        ];

        const select = document.getElementById('query-templates');
        templates.forEach(t => {
            const option = document.createElement('option');
            option.value = t.query;
            option.textContent = t.name;
            select.appendChild(option);
        });
    }

    async runQuery() {
        const query = document.getElementById('query-input').value.trim();
        if (!query) {
            this.showError('Please enter a SPARQL query');
            return;
        }

        this.showLoading(true);
        this.updateStatus('Executing query...', 'loading');

        try {
            const startTime = performance.now();

            const response = await fetch(this.endpoint, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/sparql-query'
                },
                body: query
            });

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.detail || 'Query failed');
            }

            const data = await response.json();
            const elapsed = ((performance.now() - startTime) / 1000).toFixed(3);

            this.currentResults = data;
            this.renderResults(data);
            this.updateStatus(`${data.results?.bindings?.length || 0} results in ${elapsed}s`, 'success');

        } catch (error) {
            this.showError(error.message);
            this.updateStatus('Query failed', 'error');
        } finally {
            this.showLoading(false);
        }
    }

    renderResults(data) {
        this.renderTable(data);
        this.renderJSON(data);
        this.renderGraph(data);
    }

    renderTable(data) {
        const container = document.getElementById('table-container');

        if (!data.results?.bindings?.length) {
            container.innerHTML = this.getEmptyState('No results found');
            return;
        }

        const vars = data.head.vars;
        const bindings = data.results.bindings;

        let html = '<table class="results-table"><thead><tr>';
        vars.forEach(v => {
            html += `<th>${v}</th>`;
        });
        html += '</tr></thead><tbody>';

        bindings.forEach((row, idx) => {
            html += '<tr>';
            vars.forEach(v => {
                const cell = row[v];
                if (cell) {
                    if (cell.type === 'uri') {
                        const shortUri = this.shortenUri(cell.value);
                        html += `<td><a class="uri-link" data-uri="${cell.value}" title="${cell.value}">${shortUri}</a></td>`;
                    } else {
                        html += `<td title="${cell.value}">${cell.value}</td>`;
                    }
                } else {
                    html += '<td>-</td>';
                }
            });
            html += '</tr>';
        });

        html += '</tbody></table>';
        container.innerHTML = html;

        // Bind click events for URIs
        container.querySelectorAll('.uri-link').forEach(link => {
            link.addEventListener('click', () => {
                this.selectNode(link.dataset.uri);
            });
        });
    }

    renderJSON(data) {
        const container = document.getElementById('json-output');
        container.innerHTML = this.syntaxHighlight(JSON.stringify(data, null, 2));
    }

    initGraph() {
        const container = document.getElementById('graph-container');
        const width = container.clientWidth;
        const height = container.clientHeight;

        this.svg = d3.select('#graph-canvas')
            .attr('width', width)
            .attr('height', height);

        // Add zoom behavior
        this.zoom = d3.zoom()
            .scaleExtent([0.1, 4])
            .on('zoom', (event) => {
                this.transform = event.transform;
                this.svg.select('g').attr('transform', event.transform);
            });

        this.svg.call(this.zoom);

        // Create main group
        this.svg.append('g').attr('class', 'graph-content');

        // Add arrow marker
        this.svg.append('defs').append('marker')
            .attr('id', 'arrowhead')
            .attr('viewBox', '-0 -5 10 10')
            .attr('refX', 25)
            .attr('refY', 0)
            .attr('orient', 'auto')
            .attr('markerWidth', 6)
            .attr('markerHeight', 6)
            .append('path')
            .attr('d', 'M 0,-5 L 10,0 L 0,5')
            .attr('fill', '#7c7c9c');
    }

    renderGraph(data) {
        if (!data.results?.bindings?.length) {
            return;
        }

        // Extract nodes and edges from results
        this.graphData = this.extractGraphData(data);

        if (this.graphData.nodes.length === 0) {
            return;
        }

        const g = this.svg.select('g');
        g.selectAll('*').remove();

        const width = this.svg.attr('width');
        const height = this.svg.attr('height');

        // Create simulation
        this.simulation = d3.forceSimulation(this.graphData.nodes)
            .force('link', d3.forceLink(this.graphData.edges).id(d => d.id).distance(150))
            .force('charge', d3.forceManyBody().strength(-400))
            .force('center', d3.forceCenter(width / 2, height / 2))
            .force('collision', d3.forceCollide().radius(50));

        // Draw edges
        const edges = g.append('g')
            .selectAll('line')
            .data(this.graphData.edges)
            .enter()
            .append('line')
            .attr('stroke', '#7c7c9c')
            .attr('stroke-width', 2)
            .attr('marker-end', 'url(#arrowhead)');

        // Draw edge labels
        const edgeLabels = g.append('g')
            .selectAll('text')
            .data(this.graphData.edges)
            .enter()
            .append('text')
            .attr('font-size', 10)
            .attr('fill', '#9e9e9e')
            .attr('text-anchor', 'middle')
            .text(d => d.label);

        // Draw nodes
        const nodes = g.append('g')
            .selectAll('g')
            .data(this.graphData.nodes)
            .enter()
            .append('g')
            .attr('class', 'node')
            .style('cursor', 'pointer')
            .call(d3.drag()
                .on('start', (event, d) => this.dragStarted(event, d))
                .on('drag', (event, d) => this.dragged(event, d))
                .on('end', (event, d) => this.dragEnded(event, d)))
            .on('click', (event, d) => this.selectNode(d.id));

        // Node circles
        nodes.append('circle')
            .attr('r', 25)
            .attr('fill', d => d.type === 'Person' ? '#4fc3f7' : '#ff9800')
            .attr('stroke', '#fff')
            .attr('stroke-width', 2);

        // Node labels
        nodes.append('text')
            .attr('dy', 40)
            .attr('text-anchor', 'middle')
            .attr('fill', '#e0e0e0')
            .attr('font-size', 12)
            .text(d => d.label);

        // Node icons
        nodes.append('text')
            .attr('dy', 5)
            .attr('text-anchor', 'middle')
            .attr('fill', '#1a1a2e')
            .attr('font-size', 16)
            .attr('font-weight', 'bold')
            .text(d => d.label.charAt(0).toUpperCase());

        // Update positions on tick
        this.simulation.on('tick', () => {
            edges
                .attr('x1', d => d.source.x)
                .attr('y1', d => d.source.y)
                .attr('x2', d => d.target.x)
                .attr('y2', d => d.target.y);

            edgeLabels
                .attr('x', d => (d.source.x + d.target.x) / 2)
                .attr('y', d => (d.source.y + d.target.y) / 2);

            nodes.attr('transform', d => `translate(${d.x},${d.y})`);
        });
    }

    extractGraphData(data) {
        const nodes = new Map();
        const edges = [];

        const vars = data.head.vars;
        const bindings = data.results.bindings;

        bindings.forEach(row => {
            // Find URI variables (potential nodes)
            vars.forEach(v => {
                const cell = row[v];
                if (cell?.type === 'uri' && !cell.value.includes('schema.org') &&
                    !cell.value.includes('w3.org') && !cell.value.includes('xmlns.com')) {
                    if (!nodes.has(cell.value)) {
                        const label = this.extractLabel(cell.value);
                        nodes.set(cell.value, {
                            id: cell.value,
                            label: label,
                            type: this.inferType(v, row),
                            properties: this.extractProperties(row, vars)
                        });
                    }
                }
            });

            // Look for relationships (subject-predicate-object patterns)
            if (row.customer && row.source) {
                edges.push({
                    source: row.customer.value,
                    target: row.source.value,
                    label: 'derivedFrom'
                });
            }
        });

        return {
            nodes: Array.from(nodes.values()),
            edges: edges.filter(e => nodes.has(e.source) && nodes.has(e.target))
        };
    }

    extractLabel(uri) {
        const parts = uri.split(/[#/]/);
        return parts[parts.length - 1] || uri;
    }

    inferType(varName, row) {
        if (varName === 'customer' || row.name) return 'Person';
        if (varName === 'source') return 'Source';
        if (varName === 'batch') return 'Batch';
        return 'Resource';
    }

    extractProperties(row, vars) {
        const props = {};
        vars.forEach(v => {
            if (row[v] && row[v].type === 'literal') {
                props[v] = {
                    value: row[v].value,
                    datatype: row[v].datatype
                };
            }
        });
        return props;
    }

    async selectNode(uri) {
        this.selectedNode = uri;
        const panel = document.querySelector('.details-panel');
        panel.classList.remove('collapsed');

        // Query for full node details with provenance
        const query = `
SELECT ?predicate ?object ?source ?confidence ?timestamp
WHERE {
    GRAPH ?g {
        <${uri}> ?predicate ?object .
        OPTIONAL {
            ?reifier <http://www.w3.org/1999/02/22-rdf-syntax-ns#reifies> ?triple ;
                     <http://www.w3.org/ns/prov#wasDerivedFrom> ?source .
            OPTIONAL { ?reifier <http://example.org/confidence> ?confidence }
            OPTIONAL { ?reifier <http://www.w3.org/ns/prov#generatedAtTime> ?timestamp }
        }
    }
}
ORDER BY ?predicate`;

        try {
            const response = await fetch(this.endpoint, {
                method: 'POST',
                headers: { 'Content-Type': 'application/sparql-query' },
                body: query
            });

            const data = await response.json();
            this.renderNodeDetails(uri, data);
        } catch (error) {
            console.error('Error loading node details:', error);
        }
    }

    renderNodeDetails(uri, data) {
        const content = document.querySelector('.details-content');
        const label = this.extractLabel(uri);

        // Group properties by predicate
        const properties = new Map();
        const provenanceMap = new Map();

        if (data.results?.bindings) {
            data.results.bindings.forEach(row => {
                const pred = row.predicate?.value;
                const obj = row.object;

                if (pred && obj) {
                    const predLabel = this.extractLabel(pred);

                    // Skip RDF type predicates in object properties
                    if (pred.includes('rdf-syntax-ns#type') ||
                        pred.includes('reifies')) {
                        if (pred.includes('type') && obj.type === 'uri') {
                            // Store type separately
                            properties.set('_type', obj.value);
                        }
                        return;
                    }

                    // Data properties (literals)
                    if (obj.type === 'literal') {
                        if (!properties.has(predLabel)) {
                            properties.set(predLabel, {
                                value: obj.value,
                                datatype: obj.datatype,
                                provenance: []
                            });
                        }

                        // Add provenance if available
                        if (row.source?.value) {
                            properties.get(predLabel).provenance.push({
                                source: row.source.value,
                                confidence: row.confidence?.value,
                                timestamp: row.timestamp?.value
                            });
                        }
                    }
                }
            });
        }

        // Render HTML
        let html = `
            <div class="node-info">
                <div class="node-uri">${uri}</div>
                ${properties.has('_type') ? `<span class="node-type">${this.extractLabel(properties.get('_type'))}</span>` : ''}
            </div>
            <div class="properties-section">
                <h4>Data Properties</h4>
        `;

        properties.forEach((prop, name) => {
            if (name === '_type') return;

            const hasProvenance = prop.provenance && prop.provenance.length > 0;

            html += `
                <div class="property-item ${hasProvenance ? 'has-provenance' : ''}">
                    <div class="property-header" onclick="sparqlClient.toggleProperty(this)">
                        <div>
                            <div class="property-name">${name}</div>
                            <div class="property-value">${prop.value}</div>
                        </div>
                        ${hasProvenance ? '<span class="property-expand-icon">▼</span>' : ''}
                    </div>
                    ${hasProvenance ? this.renderProvenancePanel(prop.provenance) : ''}
                </div>
            `;
        });

        html += '</div>';

        // Object Properties section
        html += `
            <div class="properties-section" style="margin-top: 20px;">
                <h4>Relationships</h4>
                <p style="color: var(--text-secondary); font-size: 12px;">
                    Select connected nodes in the graph view to explore relationships.
                </p>
            </div>
        `;

        content.innerHTML = html;
    }

    renderProvenancePanel(provenance) {
        // Deduplicate provenance entries
        const unique = [];
        const seen = new Set();
        provenance.forEach(p => {
            const key = `${p.source}-${p.timestamp}`;
            if (!seen.has(key)) {
                seen.add(key);
                unique.push(p);
            }
        });

        let html = '<div class="provenance-panel">';

        unique.forEach(p => {
            html += `
                <div class="provenance-item">
                    <div class="provenance-icon source">⬢</div>
                    <div class="provenance-details">
                        <div class="provenance-label">Source</div>
                        <div class="provenance-value">${this.extractLabel(p.source)}</div>
                    </div>
                </div>
            `;

            if (p.confidence) {
                html += `
                    <div class="provenance-item">
                        <div class="provenance-icon confidence">◉</div>
                        <div class="provenance-details">
                            <div class="provenance-label">Confidence</div>
                            <div class="provenance-value">${(parseFloat(p.confidence) * 100).toFixed(0)}%</div>
                        </div>
                    </div>
                `;
            }

            if (p.timestamp) {
                html += `
                    <div class="provenance-item">
                        <div class="provenance-icon timestamp">◷</div>
                        <div class="provenance-details">
                            <div class="provenance-label">Timestamp</div>
                            <div class="provenance-value">${new Date(p.timestamp).toLocaleString()}</div>
                        </div>
                    </div>
                `;
            }
        });

        html += '</div>';
        return html;
    }

    toggleProperty(header) {
        const item = header.parentElement;
        if (item.classList.contains('has-provenance')) {
            item.classList.toggle('expanded');
        }
    }

    // Graph interaction methods
    dragStarted(event, d) {
        if (!event.active) this.simulation.alphaTarget(0.3).restart();
        d.fx = d.x;
        d.fy = d.y;
    }

    dragged(event, d) {
        d.fx = event.x;
        d.fy = event.y;
    }

    dragEnded(event, d) {
        if (!event.active) this.simulation.alphaTarget(0);
        d.fx = null;
        d.fy = null;
    }

    zoomGraph(factor) {
        const newTransform = this.transform.scale(factor);
        this.svg.transition().duration(300).call(this.zoom.transform, newTransform);
    }

    fitGraph() {
        this.svg.transition().duration(300).call(this.zoom.transform, d3.zoomIdentity);
    }

    // Utility methods
    switchTab(tabName) {
        document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
        document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));

        document.querySelector(`.tab[data-tab="${tabName}"]`).classList.add('active');
        document.getElementById(`${tabName}-content`).classList.add('active');
    }

    clearQuery() {
        document.getElementById('query-input').value = '';
        document.getElementById('query-templates').value = '';
    }

    shortenUri(uri) {
        const prefixes = {
            'http://example.org/': 'ex:',
            'http://schema.org/': 'schema:',
            'http://xmlns.com/foaf/0.1/': 'foaf:',
            'http://www.w3.org/ns/prov#': 'prov:',
            'http://www.w3.org/1999/02/22-rdf-syntax-ns#': 'rdf:'
        };

        for (const [prefix, short] of Object.entries(prefixes)) {
            if (uri.startsWith(prefix)) {
                return short + uri.substring(prefix.length);
            }
        }
        return uri;
    }

    syntaxHighlight(json) {
        json = json.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
        return json.replace(/("(\\u[a-zA-Z0-9]{4}|\\[^u]|[^\\"])*"(\s*:)?|\b(true|false|null)\b|-?\d+(?:\.\d*)?(?:[eE][+\-]?\d+)?)/g,
            function (match) {
                let cls = 'json-number';
                if (/^"/.test(match)) {
                    if (/:$/.test(match)) {
                        cls = 'json-key';
                    } else {
                        cls = 'json-string';
                    }
                } else if (/true|false/.test(match)) {
                    cls = 'json-boolean';
                }
                return '<span class="' + cls + '">' + match + '</span>';
            });
    }

    getEmptyState(message) {
        return `
            <div class="empty-state">
                <svg viewBox="0 0 24 24" fill="currentColor">
                    <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 15l-5-5 1.41-1.41L10 14.17l7.59-7.59L19 8l-9 9z"/>
                </svg>
                <h3>${message}</h3>
                <p>Enter a SPARQL query and click Run to see results.</p>
            </div>
        `;
    }

    showLoading(show) {
        const overlay = document.querySelector('.loading-overlay');
        if (show) {
            overlay.classList.remove('hidden');
        } else {
            overlay.classList.add('hidden');
        }
    }

    showError(message) {
        // Could implement a toast notification here
        console.error(message);
        alert('Error: ' + message);
    }

    updateStatus(message, type) {
        const statusText = document.querySelector('.status-text');
        const indicator = document.querySelector('.status-indicator');

        statusText.textContent = message;
        indicator.className = 'status-indicator';

        if (type === 'error') {
            indicator.classList.add('error');
        } else if (type === 'loading') {
            indicator.classList.add('loading');
        }
    }
}

// Initialize on DOM ready
let sparqlClient;
document.addEventListener('DOMContentLoaded', () => {
    sparqlClient = new SPARQLClient();
});

