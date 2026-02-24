/**
 * SPARQL Client - Enhanced with Competing Claims & YARRRML Builder
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
        this.currentMode = 'explorer'; // 'explorer' or 'yarrrml'

        // Pagination state
        this.currentPage = 1;
        this.pageSize = 50;
        this.totalResults = 0;

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

        // Mode switching
        document.querySelectorAll('.mode-btn').forEach(btn => {
            btn.addEventListener('click', () => this.switchMode(btn.dataset.mode));
        });
    }

    switchMode(mode) {
        this.currentMode = mode;
        document.querySelectorAll('.mode-btn').forEach(b => b.classList.remove('active'));
        document.querySelector(`.mode-btn[data-mode="${mode}"]`).classList.add('active');

        document.getElementById('explorer-mode').style.display = mode === 'explorer' ? 'flex' : 'none';
        document.getElementById('class-explorer-mode').style.display = mode === 'class-explorer' ? 'flex' : 'none';
        document.getElementById('yarrrml-mode').style.display = mode === 'yarrrml' ? 'flex' : 'none';

        if (mode === 'yarrrml') {
            // Defer init until after DOM is updated and visible
            requestAnimationFrame(() => {
                yarrrmlBuilder.init();
            });
        }
        if (mode === 'class-explorer') {
            requestAnimationFrame(() => {
                if (typeof classExplorer !== 'undefined') {
                    classExplorer.onActivate();
                }
            });
        }
    }

    loadQueryTemplates() {
        const templates = [
            {
                name: '1.1 Count All Datasets',
                query: `PREFIX dcat: <http://www.w3.org/ns/dcat#>
PREFIX dct: <http://purl.org/dc/terms/>

SELECT (COUNT(?dataset) as ?count)
WHERE {
    ?dataset a dcat:Dataset .
}`
            },
            {
                name: '1.2 List First 10 Datasets',
                query: `PREFIX dcat: <http://www.w3.org/ns/dcat#>
PREFIX dct: <http://purl.org/dc/terms/>

SELECT ?dataset ?title ?issued
WHERE {
    ?dataset a dcat:Dataset ;
             dct:title ?title ;
             dct:issued ?issued .
}
ORDER BY ?dataset
LIMIT 10`
            },
            {
                name: '1.3 Count All Activities',
                query: `PREFIX prov: <http://www.w3.org/ns/prov#>

SELECT (COUNT(DISTINCT ?activity) as ?count)
WHERE {
    ?activity a prov:Activity .
}`
            },
            {
                name: '2.1 High-Confidence Theme Assignments',
                query: `PREFIX ex: <http://example.org/>
PREFIX dcat: <http://www.w3.org/ns/dcat#>
PREFIX dct: <http://purl.org/dc/terms/>
PREFIX prov: <http://www.w3.org/ns/prov#>

SELECT ?dataset ?title ?theme ?confidence ?source
WHERE {
    ?dataset dcat:theme ?theme ;
             dct:title ?title .

    <<?dataset dcat:theme ?theme>> ex:confidence ?confidence ;
                                    prov:wasDerivedFrom ?source .

    FILTER(?confidence > 0.90)
}
ORDER BY DESC(?confidence)
LIMIT 20`
            },
            {
                name: '2.2 Dataset Lineage Chain',
                query: `PREFIX dcat: <http://www.w3.org/ns/dcat#>
PREFIX dct: <http://purl.org/dc/terms/>
PREFIX prov: <http://www.w3.org/ns/prov#>

SELECT ?dataset ?title ?derivedFrom ?activity
WHERE {
    ?dataset a dcat:Dataset ;
             dct:title ?title ;
             prov:wasDerivedFrom ?derivedFrom .

    OPTIONAL { ?dataset prov:wasGeneratedBy ?activity }
}
LIMIT 20`
            },
            {
                name: '3.1 Quality Score Distribution',
                query: `PREFIX ex: <http://example.org/>
PREFIX dcat: <http://www.w3.org/ns/dcat#>
PREFIX dqv: <http://www.w3.org/ns/dqv#>

SELECT ?qualityLevel (COUNT(?dataset) as ?count)
WHERE {
    ?dataset a dcat:Dataset .
    ?dataset ex:qualityScore ?score .
    BIND(
        IF(?score >= 0.9, "Excellent",
        IF(?score >= 0.7, "Good",
        IF(?score >= 0.5, "Fair", "Poor")))
        AS ?qualityLevel
    )
}
GROUP BY ?qualityLevel
ORDER BY DESC(?count)`
            },
            {
                name: '4.1 Provenance with Confidence',
                query: `PREFIX ex: <http://example.org/>
PREFIX dcat: <http://www.w3.org/ns/dcat#>
PREFIX dct: <http://purl.org/dc/terms/>
PREFIX prov: <http://www.w3.org/ns/prov#>

SELECT ?dataset ?title ?source ?confidence ?timestamp
WHERE {
    ?dataset a dcat:Dataset ;
             dct:title ?title .

    <<?dataset prov:wasDerivedFrom ?source>> ex:confidence ?confidence ;
                                              prov:generatedAtTime ?timestamp .
}
ORDER BY DESC(?confidence)
LIMIT 20`
            },
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
                query: `SELECT ?batch ?batchNumber ?status ?created ?description
WHERE {
    GRAPH <http://example.org/graph/metadata> {
        ?batch a <http://example.org/Batch> ;
               <http://example.org/batchNumber> ?batchNumber ;
               <http://example.org/status> ?status .
        OPTIONAL { ?batch <http://purl.org/dc/terms/created> ?created }
        OPTIONAL { ?batch <http://purl.org/dc/terms/description> ?description }
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
        this.currentPage = 1; // Reset pagination on new results
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
        const allBindings = data.results.bindings;
        this.totalResults = allBindings.length;

        // Calculate pagination
        const totalPages = Math.ceil(this.totalResults / this.pageSize);
        const startIdx = (this.currentPage - 1) * this.pageSize;
        const endIdx = Math.min(startIdx + this.pageSize, this.totalResults);
        const bindings = allBindings.slice(startIdx, endIdx);

        let html = '<div class="table-wrapper"><table class="results-table"><thead><tr>';
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

        html += '</tbody></table></div>';

        // Add pagination controls
        html += `
            <div class="pagination">
                <div class="pagination-info">
                    Showing ${startIdx + 1}-${endIdx} of ${this.totalResults} results
                </div>
                <div class="pagination-controls">
                    <div class="page-size-selector">
                        <label>Rows:</label>
                        <select onchange="sparqlClient.changePageSize(this.value)">
                            <option value="25" ${this.pageSize === 25 ? 'selected' : ''}>25</option>
                            <option value="50" ${this.pageSize === 50 ? 'selected' : ''}>50</option>
                            <option value="100" ${this.pageSize === 100 ? 'selected' : ''}>100</option>
                            <option value="250" ${this.pageSize === 250 ? 'selected' : ''}>250</option>
                        </select>
                    </div>
                    <button onclick="sparqlClient.goToPage(1)" ${this.currentPage === 1 ? 'disabled' : ''}>
                        <svg width="12" height="12" viewBox="0 0 24 24" fill="currentColor"><path d="M18.41 16.59L13.82 12l4.59-4.59L17 6l-6 6 6 6zM6 6h2v12H6z"/></svg>
                    </button>
                    <button onclick="sparqlClient.goToPage(${this.currentPage - 1})" ${this.currentPage === 1 ? 'disabled' : ''}>
                        <svg width="12" height="12" viewBox="0 0 24 24" fill="currentColor"><path d="M15.41 7.41L14 6l-6 6 6 6 1.41-1.41L10.83 12z"/></svg>
                    </button>
                    <span class="page-info">Page ${this.currentPage} of ${totalPages}</span>
                    <button onclick="sparqlClient.goToPage(${this.currentPage + 1})" ${this.currentPage === totalPages ? 'disabled' : ''}>
                        <svg width="12" height="12" viewBox="0 0 24 24" fill="currentColor"><path d="M10 6L8.59 7.41 13.17 12l-4.58 4.59L10 18l6-6z"/></svg>
                    </button>
                    <button onclick="sparqlClient.goToPage(${totalPages})" ${this.currentPage === totalPages ? 'disabled' : ''}>
                        <svg width="12" height="12" viewBox="0 0 24 24" fill="currentColor"><path d="M5.59 7.41L10.18 12l-4.59 4.59L7 18l6-6-6-6zM16 6h2v12h-2z"/></svg>
                    </button>
                </div>
            </div>
        `;

        container.innerHTML = html;

        // Bind click events for URIs
        container.querySelectorAll('.uri-link').forEach(link => {
            link.addEventListener('click', () => {
                this.selectNodeWithCompetingClaims(link.dataset.uri);
            });
        });
    }

    goToPage(page) {
        const totalPages = Math.ceil(this.totalResults / this.pageSize);
        if (page >= 1 && page <= totalPages) {
            this.currentPage = page;
            this.renderTable(this.currentResults);
        }
    }

    changePageSize(size) {
        this.pageSize = parseInt(size);
        this.currentPage = 1; // Reset to first page
        this.renderTable(this.currentResults);
    }

    renderJSON(data) {
        const container = document.getElementById('json-container');
        const jsonContent = this.syntaxHighlight(JSON.stringify(data, null, 2));
        container.innerHTML = `<div class="json-wrapper"><pre id="json-output">${jsonContent}</pre></div>`;
    }

    initGraph() {
        const container = document.getElementById('graph-container');
        const width = container.clientWidth || 800;
        const height = container.clientHeight || 500;

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

        const width = parseInt(this.svg.attr('width')) || 800;
        const height = parseInt(this.svg.attr('height')) || 500;

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
            .on('click', (event, d) => this.selectNodeWithCompetingClaims(d.id));

        // Node circles
        nodes.append('circle')
            .attr('r', 25)
            .attr('fill', d => this.getNodeColor(d.type))
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

    getNodeColor(type) {
        const colors = {
            'Person': '#4fc3f7',
            'Source': '#ff9800',
            'Batch': '#9c27b0',
            'Dataset': '#e91e63',
            'Activity': '#ff5722',
            'Resource': '#4caf50'
        };
        return colors[type] || colors['Resource'];
    }

    extractGraphData(data) {
        const nodes = new Map();
        const edges = [];
        const edgeSet = new Set(); // Track unique edges

        const vars = data.head.vars;
        const bindings = data.results.bindings;

        // Check if this looks like an s/p/o query
        const hasSubject = vars.includes('s') || vars.includes('subject');
        const hasPredicate = vars.includes('p') || vars.includes('predicate');
        const hasObject = vars.includes('o') || vars.includes('object');
        const isSPOQuery = hasSubject && hasPredicate && hasObject;

        bindings.forEach(row => {
            // Handle s/p/o queries specially
            if (isSPOQuery) {
                const sVar = vars.includes('s') ? 's' : 'subject';
                const pVar = vars.includes('p') ? 'p' : 'predicate';
                const oVar = vars.includes('o') ? 'o' : 'object';

                const subject = row[sVar];
                const predicate = row[pVar];
                const object = row[oVar];

                // Add subject as node if it's a URI
                if (subject?.type === 'uri') {
                    if (!nodes.has(subject.value)) {
                        const label = this.extractLabel(subject.value);
                        nodes.set(subject.value, {
                            id: subject.value,
                            label: label,
                            type: this.inferTypeFromUri(subject.value),
                            properties: {}
                        });
                    }
                }

                // Add object as node if it's a URI (object property)
                if (object?.type === 'uri') {
                    if (!nodes.has(object.value)) {
                        const label = this.extractLabel(object.value);
                        nodes.set(object.value, {
                            id: object.value,
                            label: label,
                            type: this.inferTypeFromUri(object.value),
                            properties: {}
                        });
                    }

                    // Create edge between subject and object
                    if (subject?.type === 'uri' && predicate?.value) {
                        const predLabel = this.extractLabel(predicate.value);
                        // Skip rdf:type predicates for edges
                        if (!predicate.value.includes('rdf-syntax-ns#type')) {
                            const edgeKey = `${subject.value}|${predicate.value}|${object.value}`;
                            if (!edgeSet.has(edgeKey)) {
                                edgeSet.add(edgeKey);
                                edges.push({
                                    source: subject.value,
                                    target: object.value,
                                    label: predLabel
                                });
                            }
                        }
                    }
                }
            } else {
                // Generic handling for non-SPO queries
                vars.forEach(v => {
                    const cell = row[v];
                    if (cell?.type === 'uri' && !this.isCommonVocabUri(cell.value)) {
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

                // Look for relationships based on common patterns
                this.detectRelationships(row, vars, nodes, edges, edgeSet);
            }
        });

        return {
            nodes: Array.from(nodes.values()),
            edges: edges.filter(e => nodes.has(e.source) && nodes.has(e.target))
        };
    }

    isCommonVocabUri(uri) {
        const vocabs = ['schema.org', 'w3.org/1999', 'w3.org/2000', 'w3.org/2001', 'xmlns.com'];
        return vocabs.some(v => uri.includes(v));
    }

    inferTypeFromUri(uri) {
        if (uri.includes('customer') || uri.includes('person') || uri.includes('Person')) return 'Person';
        if (uri.includes('source') || uri.includes('Source')) return 'Source';
        if (uri.includes('batch') || uri.includes('Batch')) return 'Batch';
        if (uri.includes('dataset') || uri.includes('Dataset')) return 'Dataset';
        if (uri.includes('activity') || uri.includes('Activity')) return 'Activity';
        return 'Resource';
    }

    detectRelationships(row, vars, nodes, edges, edgeSet) {
        // Look for pairs of URI variables that might be related
        const uriVars = vars.filter(v => row[v]?.type === 'uri' && !this.isCommonVocabUri(row[v].value));

        // Common relationship patterns
        const patterns = [
            ['customer', 'source'],
            ['subject', 'object'],
            ['dataset', 'source'],
            ['entity', 'related'],
            ['from', 'to']
        ];

        patterns.forEach(([fromVar, toVar]) => {
            if (row[fromVar]?.type === 'uri' && row[toVar]?.type === 'uri') {
                const edgeKey = `${row[fromVar].value}|${row[toVar].value}`;
                if (!edgeSet.has(edgeKey)) {
                    edgeSet.add(edgeKey);
                    edges.push({
                        source: row[fromVar].value,
                        target: row[toVar].value,
                        label: 'relatedTo'
                    });
                }
            }
        });
    }

    extractLabel(uri) {
        const parts = uri.split(/[#/]/);
        return parts[parts.length - 1] || uri;
    }

    inferType(varName, row) {
        if (varName === 'customer' || varName === 'person' || row.name) return 'Person';
        if (varName === 'source') return 'Source';
        if (varName === 'batch') return 'Batch';
        if (varName === 'dataset') return 'Dataset';
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

    /**
     * Select a node and show ALL competing claims/values across batches
     */
    async selectNodeWithCompetingClaims(uri) {
        this.selectedNode = uri;
        const panel = document.querySelector('.details-panel');
        panel.classList.remove('collapsed');

        // Query for ALL values across ALL graphs with full provenance
        const query = `
SELECT ?graph ?predicate ?object ?source ?confidence ?timestamp
WHERE {
    GRAPH ?graph {
        <${uri}> ?predicate ?object .
        OPTIONAL {
            ?reifier <http://www.w3.org/1999/02/22-rdf-syntax-ns#reifies> ?triple ;
                     <http://www.w3.org/ns/prov#wasDerivedFrom> ?source .
            OPTIONAL { ?reifier <http://example.org/confidence> ?confidence }
            OPTIONAL { ?reifier <http://www.w3.org/ns/prov#generatedAtTime> ?timestamp }
        }
    }
    FILTER(?graph != <http://example.org/graph/metadata>)
}
ORDER BY ?predicate ?timestamp`;

        try {
            const response = await fetch(this.endpoint, {
                method: 'POST',
                headers: { 'Content-Type': 'application/sparql-query' },
                body: query
            });

            const data = await response.json();
            this.renderNodeDetailsWithCompetingClaims(uri, data);
        } catch (error) {
            console.error('Error loading node details:', error);
        }
    }

    /**
     * Render node details showing competing claims for each property
     */
    renderNodeDetailsWithCompetingClaims(uri, data) {
        const content = document.querySelector('.details-content');
        const label = this.extractLabel(uri);

        // Group by predicate, then collect ALL values with provenance
        const propertyMap = new Map();
        let nodeType = null;

        if (data.results?.bindings) {
            data.results.bindings.forEach(row => {
                const pred = row.predicate?.value;
                const obj = row.object;
                const graph = row.graph?.value;

                if (!pred || !obj) return;

                const predLabel = this.extractLabel(pred);

                // Handle type separately
                if (pred.includes('rdf-syntax-ns#type') && obj.type === 'uri') {
                    nodeType = this.extractLabel(obj.value);
                    return;
                }

                // Skip reification predicates
                if (pred.includes('reifies')) return;

                // Only show data properties (literals)
                if (obj.type !== 'literal') return;

                if (!propertyMap.has(predLabel)) {
                    propertyMap.set(predLabel, {
                        predicate: pred,
                        claims: []
                    });
                }

                // Add this claim
                propertyMap.get(predLabel).claims.push({
                    value: obj.value,
                    datatype: obj.datatype,
                    graph: graph,
                    graphLabel: this.extractLabel(graph),
                    source: row.source?.value,
                    sourceLabel: row.source ? this.extractLabel(row.source.value) : null,
                    confidence: row.confidence?.value,
                    timestamp: row.timestamp?.value
                });
            });
        }

        // Render HTML
        let html = `
            <div class="node-info">
                <div class="node-label">${label}</div>
                <div class="node-uri">${uri}</div>
                ${nodeType ? `<span class="node-type">${nodeType}</span>` : ''}
            </div>
            <div class="properties-section">
                <h4>Data Properties <span class="claims-badge">with competing claims</span></h4>
        `;

        propertyMap.forEach((propData, name) => {
            const claims = propData.claims;
            const uniqueValues = [...new Set(claims.map(c => c.value))];
            const hasConflict = uniqueValues.length > 1;

            html += `
                <div class="property-item has-provenance ${hasConflict ? 'has-conflict' : ''}">
                    <div class="property-header" onclick="sparqlClient.toggleProperty(this)">
                        <div class="property-main">
                            <div class="property-name">
                                ${name}
                                ${hasConflict ? '<span class="conflict-indicator" title="Multiple different values found">⚠</span>' : ''}
                            </div>
                            <div class="property-value-summary">
                                ${uniqueValues.length} value${uniqueValues.length > 1 ? 's' : ''}
                                from ${claims.length} claim${claims.length > 1 ? 's' : ''}
                            </div>
                        </div>
                        <span class="property-expand-icon">▼</span>
                    </div>
                    <div class="claims-panel">
                        ${this.renderClaimsPanel(claims, hasConflict)}
                    </div>
                </div>
            `;
        });

        html += '</div>';
        content.innerHTML = html;
    }

    /**
     * Render all claims for a property with full provenance
     */
    renderClaimsPanel(claims, hasConflict) {
        // Group claims by value
        const valueGroups = new Map();
        claims.forEach(claim => {
            if (!valueGroups.has(claim.value)) {
                valueGroups.set(claim.value, []);
            }
            valueGroups.get(claim.value).push(claim);
        });

        let html = '<div class="claims-container">';

        valueGroups.forEach((claimsForValue, value) => {
            const isLatest = claimsForValue.some(c => c.graphLabel && c.graphLabel.includes('2026-02-17'));

            html += `
                <div class="claim-group ${isLatest ? 'latest' : 'historical'}">
                    <div class="claim-value">
                        <span class="value-badge ${hasConflict ? 'conflict' : ''}">${value}</span>
                        ${isLatest ? '<span class="latest-badge">CURRENT</span>' : '<span class="historical-badge">HISTORICAL</span>'}
                    </div>
                    <div class="claim-sources">
            `;

            claimsForValue.forEach(claim => {
                html += `
                    <div class="claim-source">
                        <div class="source-row">
                            <span class="source-icon">📊</span>
                            <span class="source-label">Batch:</span>
                            <span class="source-value">${claim.graphLabel || 'Unknown'}</span>
                        </div>
                        ${claim.sourceLabel ? `
                        <div class="source-row">
                            <span class="source-icon">🏢</span>
                            <span class="source-label">Source:</span>
                            <span class="source-value">${claim.sourceLabel}</span>
                        </div>
                        ` : ''}
                        ${claim.confidence ? `
                        <div class="source-row">
                            <span class="source-icon">📈</span>
                            <span class="source-label">Confidence:</span>
                            <span class="source-value confidence-bar">
                                <span class="confidence-fill" style="width: ${parseFloat(claim.confidence) * 100}%"></span>
                                <span class="confidence-text">${(parseFloat(claim.confidence) * 100).toFixed(0)}%</span>
                            </span>
                        </div>
                        ` : ''}
                        ${claim.timestamp ? `
                        <div class="source-row">
                            <span class="source-icon">🕐</span>
                            <span class="source-label">Timestamp:</span>
                            <span class="source-value">${new Date(claim.timestamp).toLocaleString()}</span>
                        </div>
                        ` : ''}
                    </div>
                `;
            });

            html += `
                    </div>
                </div>
            `;
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

