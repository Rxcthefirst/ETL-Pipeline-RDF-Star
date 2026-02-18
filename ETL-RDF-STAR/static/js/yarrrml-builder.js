/**
 * YARRRML Builder - Visual Mapping Designer
 * Guides knowledge engineers through creating YARRRML mappings
 * Loads ontology from server-indexed classes and properties
 */

class YARRRMLBuilder {
    constructor() {
        this.mapping = {
            prefixes: {},
            sources: {},
            mappings: {}
        };
        this.currentStep = 0;
        this.steps = ['sources', 'prefixes', 'classes', 'properties', 'review'];
        this.ontology = null;
        this.selectedClass = null;
        this.visibleClasses = new Set();
        this.ontologyIndex = new Map();
        this.contextMenu = null;
        this.detectedColumns = [];
    }

    init() {
        console.log('YARRRMLBuilder.init() called');
        this.renderBuilder();
        this.loadDefaultPrefixes();

        // Defer ontology loading until after container is visible
        // The mode switch shows the container, then this runs
        requestAnimationFrame(() => {
            this.loadOntologyFromServer();
        });
    }

    loadDefaultPrefixes() {
        this.mapping.prefixes = {
            'ex': 'http://example.org/',
            'schema': 'http://schema.org/',
            'foaf': 'http://xmlns.com/foaf/0.1/',
            'prov': 'http://www.w3.org/ns/prov#',
            'rdf': 'http://www.w3.org/1999/02/22-rdf-syntax-ns#',
            'rdfs': 'http://www.w3.org/2000/01/rdf-schema#',
            'xsd': 'http://www.w3.org/2001/XMLSchema#',
            'dct': 'http://purl.org/dc/terms/',
            'dcat': 'http://www.w3.org/ns/dcat#',
            'owl': 'http://www.w3.org/2002/07/owl#'
        };
    }

    /**
     * Load ontology classes and properties from the server's /ontology endpoint
     */
    async loadOntologyFromServer() {
        try {
            const response = await fetch('/ontology');
            if (!response.ok) {
                throw new Error('Failed to load ontology from server');
            }

            const data = await response.json();

            // Check if we got any classes
            if (!data.classes || data.classes.length === 0) {
                console.log('Server returned no classes, using fallback ontology');
                this.loadFallbackOntology();
                return;
            }

            // Deduplicate classes by URI
            const uniqueClasses = new Map();
            data.classes.forEach(c => {
                if (!uniqueClasses.has(c.uri)) {
                    uniqueClasses.set(c.uri, c);
                }
            });
            const deduplicatedClasses = Array.from(uniqueClasses.values());
            console.log(`Deduplicated ${data.classes.length} classes to ${deduplicatedClasses.length}`);

            // Transform server response to our internal format
            this.ontology = {
                classes: deduplicatedClasses.map(c => ({
                    id: this.extractLocalName(c.uri),
                    label: this.cleanLabel(c.label),
                    uri: c.uri,
                    prefix: this.getPrefix(c.uri),
                    // Ignore blank node parents (start with _:)
                    parent: (c.parent && !c.parent.startsWith('_:')) ? this.extractLocalName(c.parent) : null,
                    comment: this.cleanLabel(c.comment)
                })),
                // Filter out object properties with null domain or range
                objectProperties: data.objectProperties
                    .filter(p => p.domain && p.range && !p.domain.startsWith('_:') && !p.range.startsWith('_:'))
                    .map(p => ({
                        uri: p.uri,
                        label: this.cleanLabel(p.label),
                        from: this.extractLocalName(p.domain),
                        to: this.extractLocalName(p.range),
                        prefix: this.getPrefix(p.uri)
                    })),
                dataProperties: {}
            };

            // Group datatype properties by domain class
            data.datatypeProperties.forEach(p => {
                // Skip if domain is blank node or null
                if (!p.domain || p.domain.startsWith('_:')) return;

                const domain = this.extractLocalName(p.domain);
                if (!this.ontology.dataProperties[domain]) {
                    this.ontology.dataProperties[domain] = [];
                }
                this.ontology.dataProperties[domain].push({
                    name: this.cleanLabel(p.label),
                    uri: p.uri,
                    type: this.extractDatatype(p.range),
                    prefix: this.getPrefix(p.uri)
                });
            });

            console.log(`Loaded ontology: ${data.counts.classes} classes, ${data.counts.objectProperties} object properties, ${data.counts.datatypeProperties} datatype properties`);
            console.log('Transformed classes:', this.ontology.classes.map(c => c.id));
            console.log('Transformed object properties:', this.ontology.objectProperties.length,
                this.ontology.objectProperties.map(p => `${p.from} --${p.label}--> ${p.to}`));

            this.buildSearchIndex();
            this.updateOntologyStats();

            // Show all classes initially - with delay to ensure DOM is laid out
            if (this.ontology.classes.length > 0) {
                setTimeout(() => {
                    console.log('Initializing graph after ontology load');
                    const container = document.getElementById('ontology-graph');
                    if (!container) {
                        console.error('Container not found');
                        return;
                    }
                    console.log('Container size:', container.getBoundingClientRect());
                    this.initOntologyGraph();

                    // Show all classes - don't try to focus on just one
                    this.visibleClasses.clear();
                    this.ontology.classes.forEach(c => this.visibleClasses.add(c.id));
                    console.log('Initial visible classes:', Array.from(this.visibleClasses));

                    this.renderOntologyGraph();
                }, 200);
            }

        } catch (error) {
            console.error('Error loading ontology:', error);
            this.loadFallbackOntology();
        }
    }

    /**
     * Load a fallback sample ontology when server is unavailable
     */
    loadFallbackOntology() {
        console.log('Loading fallback ontology');

        // Show loading message in details panel
        const details = document.getElementById('ontology-details');
        if (details) {
            details.innerHTML = '<div class="empty-state small"><p>Loading fallback ontology...</p></div>';
        }

        this.ontology = {
            classes: [
                { id: 'Dataset', label: 'Dataset', prefix: 'dcat', uri: 'http://www.w3.org/ns/dcat#Dataset', parent: null },
                { id: 'Theme', label: 'Theme', prefix: 'dcat', uri: 'http://www.w3.org/ns/dcat#Theme', parent: null },
                { id: 'Organization', label: 'Organization', prefix: 'ex', uri: 'http://example.org/ontology#Organization', parent: null },
                { id: 'DataCatalogSystem', label: 'DataCatalogSystem', prefix: 'ex', uri: 'http://example.org/ontology#DataCatalogSystem', parent: null },
                { id: 'Activity', label: 'Activity', prefix: 'prov', uri: 'http://www.w3.org/ns/prov#Activity', parent: null },
                { id: 'Agent', label: 'Agent', prefix: 'prov', uri: 'http://www.w3.org/ns/prov#Agent', parent: null }
            ],
            objectProperties: [
                { uri: 'http://www.w3.org/ns/dcat#theme', label: 'theme', from: 'Dataset', to: 'Theme', prefix: 'dcat' },
                { uri: 'http://www.w3.org/ns/prov#wasDerivedFrom', label: 'wasDerivedFrom', from: 'Dataset', to: 'Dataset', prefix: 'prov' },
                { uri: 'http://www.w3.org/ns/prov#wasGeneratedBy', label: 'wasGeneratedBy', from: 'Dataset', to: 'Activity', prefix: 'prov' },
                { uri: 'http://www.w3.org/ns/prov#wasAttributedTo', label: 'wasAttributedTo', from: 'Dataset', to: 'Agent', prefix: 'prov' },
                { uri: 'http://www.w3.org/ns/prov#used', label: 'used', from: 'Activity', to: 'Dataset', prefix: 'prov' },
                { uri: 'http://purl.org/dc/terms/publisher', label: 'publisher', from: 'Dataset', to: 'Organization', prefix: 'dct' }
            ],
            dataProperties: {
                'Dataset': [
                    { name: 'title', uri: 'http://purl.org/dc/terms/title', type: 'string', prefix: 'dct' },
                    { name: 'issued', uri: 'http://purl.org/dc/terms/issued', type: 'date', prefix: 'dct' },
                    { name: 'description', uri: 'http://purl.org/dc/terms/description', type: 'string', prefix: 'dct' }
                ],
                'Organization': [
                    { name: 'name', uri: 'http://xmlns.com/foaf/0.1/name', type: 'string', prefix: 'foaf' }
                ],
                'Activity': [
                    { name: 'startedAtTime', uri: 'http://www.w3.org/ns/prov#startedAtTime', type: 'dateTime', prefix: 'prov' },
                    { name: 'endedAtTime', uri: 'http://www.w3.org/ns/prov#endedAtTime', type: 'dateTime', prefix: 'prov' }
                ]
            }
        };

        console.log(`Fallback ontology loaded: ${this.ontology.classes.length} classes`);

        this.buildSearchIndex();
        this.updateOntologyStats();

        // Ensure graph container exists and render
        setTimeout(() => {
            const container = document.getElementById('ontology-graph');
            if (container) {
                console.log('Container found, initializing graph');
                this.initOntologyGraph();
                this.visibleClasses.clear();
                this.ontology.classes.forEach(c => this.visibleClasses.add(c.id));
                console.log(`Visible classes: ${Array.from(this.visibleClasses).join(', ')}`);
                this.renderOntologyGraph();
            } else {
                console.error('Ontology graph container not found');
            }
        }, 200);
    }

    extractLocalName(uri) {
        if (!uri) return '';
        const hashIdx = uri.lastIndexOf('#');
        const slashIdx = uri.lastIndexOf('/');
        const idx = Math.max(hashIdx, slashIdx);
        return idx >= 0 ? uri.substring(idx + 1) : uri;
    }

    /**
     * Clean label by removing language tags, quotes, and extra whitespace
     * e.g., '"Activity"@en' becomes 'Activity'
     */
    cleanLabel(label) {
        if (!label) return '';
        let cleaned = label;
        // Remove language tags like @en, @de
        cleaned = cleaned.replace(/@[a-z]{2,}(-[A-Z]{2,})?$/i, '');
        // Remove surrounding quotes
        cleaned = cleaned.replace(/^["']|["']$/g, '');
        // Trim whitespace
        cleaned = cleaned.trim();
        return cleaned || label;
    }

    getPrefix(uri) {
        if (!uri) return 'ex';
        for (const [prefix, ns] of Object.entries(this.mapping.prefixes)) {
            if (uri.startsWith(ns)) {
                return prefix;
            }
        }
        // Try to extract prefix from common patterns
        if (uri.includes('schema.org')) return 'schema';
        if (uri.includes('foaf')) return 'foaf';
        if (uri.includes('prov')) return 'prov';
        if (uri.includes('dcat')) return 'dcat';
        if (uri.includes('dc/terms')) return 'dct';
        if (uri.includes('owl')) return 'owl';
        if (uri.includes('rdfs')) return 'rdfs';
        if (uri.includes('rdf')) return 'rdf';
        return 'ex';
    }

    extractDatatype(rangeUri) {
        if (!rangeUri) return 'string';
        const local = this.extractLocalName(rangeUri);
        if (local.includes('int') || local.includes('Int')) return 'integer';
        if (local.includes('decimal') || local.includes('float') || local.includes('double')) return 'decimal';
        if (local.includes('date') && local.includes('Time')) return 'dateTime';
        if (local.includes('date') || local.includes('Date')) return 'date';
        if (local.includes('bool')) return 'boolean';
        return 'string';
    }

    renderBuilder() {
        const container = document.getElementById('yarrrml-builder');

        container.innerHTML = `
            <div class="yarrrml-layout">
                <!-- Left: Wizard Panel -->
                <div class="wizard-panel">
                    <div class="yarrrml-wizard">
                        <!-- Progress Steps -->
                        <div class="wizard-progress">
                            ${this.steps.map((step, i) => `
                                <div class="progress-step ${i === this.currentStep ? 'active' : ''} ${i < this.currentStep ? 'completed' : ''}" data-step="${i}">
                                    <div class="step-number">${i + 1}</div>
                                    <div class="step-label">${this.getStepLabel(step)}</div>
                                </div>
                            `).join('<div class="progress-line"></div>')}
                        </div>

                        <!-- Wizard Content -->
                        <div class="wizard-content">
                            ${this.renderCurrentStep()}
                        </div>

                        <!-- Navigation -->
                        <div class="wizard-nav">
                            <button class="btn btn-secondary" id="wizard-prev" ${this.currentStep === 0 ? 'disabled' : ''}>
                                <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor"><path d="M15.41 7.41L14 6l-6 6 6 6 1.41-1.41L10.83 12z"/></svg>
                                Previous
                            </button>
                            <button class="btn btn-primary" id="wizard-next">
                                ${this.currentStep === this.steps.length - 1 ? 'Generate YARRRML' : 'Next'}
                                <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor"><path d="M10 6L8.59 7.41 13.17 12l-4.58 4.59L10 18l6-6z"/></svg>
                            </button>
                        </div>
                    </div>
                </div>

                <!-- Right: Ontology Browser Panel -->
                <div class="ontology-browser">
                    <div class="ontology-header">
                        <h3>
                            <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor">
                                <path d="M15.5 14h-.79l-.28-.27C15.41 12.59 16 11.11 16 9.5 16 5.91 13.09 3 9.5 3S3 5.91 3 9.5 5.91 16 9.5 16c1.61 0 3.09-.59 4.23-1.57l.27.28v.79l5 4.99L20.49 19l-4.99-5zm-6 0C7.01 14 5 11.99 5 9.5S7.01 5 9.5 5 14 7.01 14 9.5 11.99 14 9.5 14z"/>
                            </svg>
                            Ontology Browser
                        </h3>
                        <span class="ontology-stats" id="ontology-stats"></span>
                    </div>

                    <!-- Search Box -->
                    <div class="ontology-search">
                        <input type="text" id="ontology-search" placeholder="Search classes, properties..."
                               onkeyup="yarrrmlBuilder.searchOntology(this.value)">
                        <div class="search-results" id="search-results"></div>
                    </div>

                    <!-- Graph Area -->
                    <div class="ontology-graph-area">
                        <div class="graph-toolbar">
                            <button class="btn btn-small" onclick="yarrrmlBuilder.resetOntologyView()" title="Reset View">
                                <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor"><path d="M12 5V1L7 6l5 5V7c3.31 0 6 2.69 6 6s-2.69 6-6 6-6-2.69-6-6H4c0 4.42 3.58 8 8 8s8-3.58 8-8-3.58-8-8-8z"/></svg>
                                Reset
                            </button>
                            <button class="btn btn-small" onclick="yarrrmlBuilder.expandAll()" title="Expand All">
                                <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor"><path d="M12 5.83L15.17 9l1.41-1.41L12 3 7.41 7.59 8.83 9 12 5.83zm0 12.34L8.83 15l-1.41 1.41L12 21l4.59-4.59L15.17 15 12 18.17z"/></svg>
                                Expand
                            </button>
                            <button class="btn btn-small" onclick="yarrrmlBuilder.loadOntologyFromServer()" title="Reload from Server">
                                <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor"><path d="M17.65 6.35C16.2 4.9 14.21 4 12 4c-4.42 0-7.99 3.58-7.99 8s3.57 8 7.99 8c3.73 0 6.84-2.55 7.73-6h-2.08c-.82 2.33-3.04 4-5.65 4-3.31 0-6-2.69-6-6s2.69-6 6-6c1.66 0 3.14.69 4.22 1.78L13 11h7V4l-2.35 2.35z"/></svg>
                                Reload
                            </button>
                            <span class="graph-hint">Right-click to expand</span>
                        </div>
                        <div class="ontology-graph" id="ontology-graph">
                            <svg id="ontology-canvas"></svg>
                        </div>
                    </div>

                    <!-- Class Details Panel -->
                    <div class="ontology-details" id="ontology-details">
                        <div class="empty-state small">
                            <p>Search for a class or click one in the graph</p>
                        </div>
                    </div>
                </div>
            </div>

            <!-- Context Menu (hidden by default) -->
            <div class="context-menu" id="context-menu" style="display: none;">
                <div class="context-menu-item" data-action="expand">
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor"><path d="M12 5.83L15.17 9l1.41-1.41L12 3 7.41 7.59 8.83 9 12 5.83zm0 12.34L8.83 15l-1.41 1.41L12 21l4.59-4.59L15.17 15 12 18.17z"/></svg>
                    Expand Neighbors
                </div>
                <div class="context-menu-item" data-action="focus">
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor"><path d="M12 8c-2.21 0-4 1.79-4 4s1.79 4 4 4 4-1.79 4-4-1.79-4-4-4zm8.94 3c-.46-4.17-3.77-7.48-7.94-7.94V1h-2v2.06C6.83 3.52 3.52 6.83 3.06 11H1v2h2.06c.46 4.17 3.77 7.48 7.94 7.94V23h2v-2.06c4.17-.46 7.48-3.77 7.94-7.94H23v-2h-2.06zM12 19c-3.87 0-7-3.13-7-7s3.13-7 7-7 7 3.13 7 7-3.13 7-7 7z"/></svg>
                    Focus on This Class
                </div>
                <div class="context-menu-item" data-action="hide">
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor"><path d="M12 7c2.76 0 5 2.24 5 5 0 .65-.13 1.26-.36 1.83l2.92 2.92c1.51-1.26 2.7-2.89 3.43-4.75-1.73-4.39-6-7.5-11-7.5-1.4 0-2.74.25-3.98.7l2.16 2.16C10.74 7.13 11.35 7 12 7zM2 4.27l2.28 2.28.46.46C3.08 8.3 1.78 10.02 1 12c1.73 4.39 6 7.5 11 7.5 1.55 0 3.03-.3 4.38-.84l.42.42L19.73 22 21 20.73 3.27 3 2 4.27z"/></svg>
                    Hide This Class
                </div>
                <div class="context-menu-divider"></div>
                <div class="context-menu-item" data-action="use-mapping">
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor"><path d="M19 13h-6v6h-2v-6H5v-2h6V5h2v6h6v2z"/></svg>
                    Use in Mapping
                </div>
            </div>
        `;

        this.bindWizardEvents();
        // Don't init graph here - it's done after ontology loads when container is visible
        this.bindContextMenu();
        this.bindDropdownHandlers();
        this.updateOntologyStats();
        console.log('renderBuilder() complete, ontology-graph element:', document.getElementById('ontology-graph'));
    }

    bindDropdownHandlers() {
        // Close dropdowns when clicking outside
        document.addEventListener('click', (e) => {
            const classDropdown = document.getElementById('class-dropdown');
            const predicateDropdown = document.getElementById('predicate-dropdown');

            if (classDropdown && !e.target.closest('.class-search-wrapper')) {
                classDropdown.style.display = 'none';
            }
            if (predicateDropdown && !e.target.closest('.predicate-search-wrapper')) {
                predicateDropdown.style.display = 'none';
            }
        });
    }

    updateOntologyStats() {
        const statsEl = document.getElementById('ontology-stats');
        if (statsEl && this.ontology) {
            const classCount = this.ontology.classes?.length || 0;
            const propCount = (this.ontology.objectProperties?.length || 0) +
                Object.values(this.ontology.dataProperties || {}).reduce((sum, arr) => sum + arr.length, 0);
            statsEl.textContent = `${classCount} classes, ${propCount} properties`;
        }
    }

    getStepLabel(step) {
        const labels = {
            'sources': 'Data Sources',
            'prefixes': 'Prefixes',
            'classes': 'Class Mappings',
            'properties': 'Properties',
            'review': 'Review & Export'
        };
        return labels[step];
    }

    renderCurrentStep() {
        const step = this.steps[this.currentStep];

        switch(step) {
            case 'sources':
                return this.renderSourcesStep();
            case 'prefixes':
                return this.renderPrefixesStep();
            case 'classes':
                return this.renderClassesStep();
            case 'properties':
                return this.renderPropertiesStep();
            case 'review':
                return this.renderReviewStep();
            default:
                return '<p>Unknown step</p>';
        }
    }

    renderSourcesStep() {
        return `
            <div class="step-content">
                <h2>Step 1: Define Data Sources</h2>
                <p class="step-description">
                    Specify the data sources that will be transformed into RDF.
                </p>

                <div class="sources-list" id="sources-list">
                    ${this.renderSourcesList()}
                </div>

                <button class="btn btn-secondary" onclick="yarrrmlBuilder.addSource()">
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor"><path d="M19 13h-6v6h-2v-6H5v-2h6V5h2v6h6v2z"/></svg>
                    Add Source
                </button>

                <!-- CSV Preview Section -->
                <div class="csv-preview-section" id="csv-preview-section" style="display: none;">
                    <h4>
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor"><path d="M19 3H5c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h14c1.1 0 2-.9 2-2V5c0-1.1-.9-2-2-2zm0 16H5V5h14v14z"/></svg>
                        Detected Columns
                    </h4>
                    <div class="csv-columns" id="csv-columns"></div>
                    <div class="csv-sample" id="csv-sample"></div>
                </div>

                <!-- File Upload -->
                <div class="file-upload-section">
                    <label class="file-upload-label">
                        <input type="file" id="csv-file-input" accept=".csv" onchange="yarrrmlBuilder.handleCSVUpload(event)" style="display:none;">
                        <span class="btn btn-secondary">
                            <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor"><path d="M9 16h6v-6h4l-7-7-7 7h4zm-4 2h14v2H5z"/></svg>
                            Upload CSV to Preview Columns
                        </span>
                    </label>
                </div>

                <div class="step-help">
                    <h4>
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor"><path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm1 15h-2v-6h2v6zm0-8h-2V7h2v2z"/></svg>
                        Supported Sources
                    </h4>
                    <ul>
                        <li><strong>CSV/JSON/XML:</strong> File path or URL</li>
                        <li><strong>Databases:</strong> PostgreSQL, MySQL, Oracle, SQL Server</li>
                        <li><strong>SPARQL:</strong> Query remote endpoints</li>
                    </ul>
                </div>
            </div>
        `;
    }

    handleCSVUpload(event) {
        const file = event.target.files[0];
        if (!file) return;

        const reader = new FileReader();
        reader.onload = (e) => {
            const text = e.target.result;
            this.parseCSVPreview(text, file.name);
        };
        reader.readAsText(file);
    }

    parseCSVPreview(csvText, fileName) {
        const lines = csvText.split('\n').filter(l => l.trim());
        if (lines.length === 0) return;

        const headers = this.parseCSVLine(lines[0]);
        this.detectedColumns = headers;

        const sampleRows = [];
        for (let i = 1; i < Math.min(4, lines.length); i++) {
            sampleRows.push(this.parseCSVLine(lines[i]));
        }

        const accessInput = document.getElementById('new-source-access');
        if (accessInput) {
            accessInput.value = `data/${fileName}`;
        }

        const previewSection = document.getElementById('csv-preview-section');
        const columnsDiv = document.getElementById('csv-columns');
        const sampleDiv = document.getElementById('csv-sample');

        if (previewSection && columnsDiv) {
            previewSection.style.display = 'block';

            columnsDiv.innerHTML = `
                <div class="column-chips">
                    ${headers.map(h => `<span class="column-chip">${h}</span>`).join('')}
                </div>
            `;

            if (sampleRows.length > 0) {
                sampleDiv.innerHTML = `
                    <table class="csv-sample-table">
                        <thead>
                            <tr>${headers.map(h => `<th>${h}</th>`).join('')}</tr>
                        </thead>
                        <tbody>
                            ${sampleRows.map(row => `
                                <tr>${row.map(cell => `<td>${cell || ''}</td>`).join('')}</tr>
                            `).join('')}
                        </tbody>
                    </table>
                `;
            }
        }
    }

    parseCSVLine(line) {
        const result = [];
        let current = '';
        let inQuotes = false;

        for (let i = 0; i < line.length; i++) {
            const char = line[i];
            if (char === '"') {
                inQuotes = !inQuotes;
            } else if (char === ',' && !inQuotes) {
                result.push(current.trim());
                current = '';
            } else {
                current += char;
            }
        }
        result.push(current.trim());
        return result;
    }

    renderSourcesList() {
        const sources = Object.entries(this.mapping.sources);

        if (sources.length === 0) {
            return `
                <div class="source-item new">
                    <div class="form-row">
                        <div class="form-group">
                            <label>Source Name</label>
                            <input type="text" id="new-source-name" placeholder="e.g., source1" value="">
                        </div>
                        <div class="form-group">
                            <label>Type</label>
                            <select id="new-source-type" onchange="yarrrmlBuilder.onSourceTypeChange(this.value)">
                                <option value="csv">CSV</option>
                                <option value="json">JSON</option>
                                <option value="xml">XML</option>
                                <option value="postgresql">PostgreSQL</option>
                                <option value="mysql">MySQL</option>
                                <option value="sparql">SPARQL</option>
                            </select>
                        </div>
                    </div>
                    <div class="form-group">
                        <label>Access Path / Connection</label>
                        <input type="text" id="new-source-access" placeholder="data/source.csv" value="">
                    </div>
                    <div class="form-group db-options" id="db-options" style="display:none;">
                        <label>Query</label>
                        <textarea id="new-source-query" placeholder="SELECT * FROM table"></textarea>
                    </div>
                </div>
            `;
        }

        return sources.map(([name, config]) => `
            <div class="source-item">
                <div class="source-header">
                    <span class="source-name">${name}</span>
                    <span class="source-type-badge">${config.type || 'csv'}</span>
                    <button class="btn-icon" onclick="yarrrmlBuilder.removeSource('${name}')">
                        <svg width="12" height="12" viewBox="0 0 24 24" fill="currentColor"><path d="M19 6.41L17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12z"/></svg>
                    </button>
                </div>
                <div class="source-details">
                    <code>${config.access}</code>
                    ${config.columns ? `<div class="source-columns">${config.columns.length} columns detected</div>` : ''}
                </div>
            </div>
        `).join('');
    }

    onSourceTypeChange(type) {
        const dbOptions = document.getElementById('db-options');
        if (dbOptions) {
            dbOptions.style.display = ['postgresql', 'mysql', 'oracle', 'sparql'].includes(type) ? 'block' : 'none';
        }
    }

    renderPrefixesStep() {
        return `
            <div class="step-content">
                <h2>Step 2: Configure Prefixes</h2>
                <p class="step-description">
                    Define namespace prefixes for your ontology.
                </p>

                <div class="prefixes-grid" id="prefixes-grid">
                    ${Object.entries(this.mapping.prefixes).map(([prefix, uri]) => `
                        <div class="prefix-item">
                            <input type="text" class="prefix-key" value="${prefix}" readonly>
                            <input type="text" class="prefix-uri" value="${uri}">
                            <button class="btn-icon" onclick="yarrrmlBuilder.removePrefix('${prefix}')">
                                <svg width="12" height="12" viewBox="0 0 24 24" fill="currentColor"><path d="M19 6.41L17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12z"/></svg>
                            </button>
                        </div>
                    `).join('')}
                </div>

                <div class="add-prefix-form">
                    <input type="text" id="new-prefix-key" placeholder="prefix">
                    <input type="text" id="new-prefix-uri" placeholder="http://example.org/ontology#">
                    <button class="btn btn-secondary" onclick="yarrrmlBuilder.addPrefix()">Add</button>
                </div>
            </div>
        `;
    }

    renderClassesStep() {
        return `
            <div class="step-content">
                <h2>Step 3: Define Class Mappings</h2>
                <p class="step-description">
                    Map source rows to RDF classes. Use the ontology browser to find classes.
                </p>

                <div class="class-mappings" id="class-mappings">
                    ${this.renderClassMappings()}
                </div>

                <button class="btn btn-secondary" onclick="yarrrmlBuilder.addClassMapping()">
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor"><path d="M19 13h-6v6h-2v-6H5v-2h6V5h2v6h6v2z"/></svg>
                    Add Class Mapping
                </button>

                <div class="step-help">
                    <h4>
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor"><path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm1 15h-2v-6h2v6zm0-8h-2V7h2v2z"/></svg>
                        Subject Template
                    </h4>
                    <p>Use <code>$(column)</code> for source columns.</p>
                    <p>Example: <code>http://example.org/resource/$(id)</code></p>
                </div>
            </div>
        `;
    }

    renderClassMappings() {
        const mappings = Object.entries(this.mapping.mappings);
        const sourceOptions = Object.keys(this.mapping.sources).length > 0
            ? Object.keys(this.mapping.sources).map(s => `<option value="${s}">${s}</option>`).join('')
            : '<option value="">-- Define a source first --</option>';

        // Build class options from ontology
        const classOptions = this.ontology?.classes?.length > 0
            ? this.ontology.classes.map(c => `<option value="${c.prefix}:${c.label}">${c.prefix}:${c.label}</option>`).join('')
            : '<option value="">-- Load ontology first --</option>';

        if (mappings.length === 0) {
            return `
                <div class="class-mapping-item new">
                    <div class="form-row">
                        <div class="form-group">
                            <label>Mapping Name</label>
                            <input type="text" id="new-mapping-name" placeholder="e.g., DatasetMapping" value="">
                        </div>
                        <div class="form-group">
                            <label>Source</label>
                            <select id="new-mapping-source">
                                ${sourceOptions}
                            </select>
                        </div>
                    </div>
                    <div class="form-group">
                        <label>Subject Template</label>
                        <input type="text" id="new-mapping-subject" placeholder="http://example.org/resource/$(id)" value="">
                    </div>
                    <div class="form-group">
                        <label>RDF Class</label>
                        <div class="class-search-wrapper">
                            <input type="text" id="new-mapping-class-search"
                                   placeholder="Type to search classes..."
                                   oninput="yarrrmlBuilder.filterClassOptions(this.value)"
                                   onfocus="yarrrmlBuilder.showClassDropdown()">
                            <input type="hidden" id="new-mapping-class" value="">
                            <div class="class-dropdown" id="class-dropdown" style="display: none;">
                                ${this.ontology?.classes?.map(c => `
                                    <div class="class-option" onclick="yarrrmlBuilder.selectClassOption('${c.prefix}:${c.label}', '${c.id}')">
                                        <span class="class-option-label">${c.prefix}:${c.label}</span>
                                        <span class="class-option-uri">${c.uri}</span>
                                    </div>
                                `).join('') || '<div class="class-option disabled">No classes loaded</div>'}
                            </div>
                        </div>
                    </div>
                </div>
            `;
        }

        return mappings.map(([name, config]) => `
            <div class="class-mapping-item">
                <div class="mapping-header">
                    <span class="mapping-name">${name}</span>
                    <span class="mapping-class-badge">${config.class || 'No class'}</span>
                    <button class="btn-icon" onclick="yarrrmlBuilder.removeMapping('${name}')">
                        <svg width="12" height="12" viewBox="0 0 24 24" fill="currentColor"><path d="M19 6.41L17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12z"/></svg>
                    </button>
                </div>
                <div class="mapping-details">
                    <div>Source: <code>${config.source}</code></div>
                    <div>Subject: <code>${config.subject}</code></div>
                </div>
            </div>
        `).join('');
    }

    showClassDropdown() {
        const dropdown = document.getElementById('class-dropdown');
        if (dropdown) {
            dropdown.style.display = 'block';
        }
    }

    filterClassOptions(query) {
        const dropdown = document.getElementById('class-dropdown');
        if (!dropdown || !this.ontology?.classes) return;

        const queryLower = query.toLowerCase();
        const filtered = this.ontology.classes.filter(c =>
            c.label.toLowerCase().includes(queryLower) ||
            c.id.toLowerCase().includes(queryLower) ||
            c.prefix.toLowerCase().includes(queryLower)
        );

        dropdown.innerHTML = filtered.length > 0
            ? filtered.map(c => `
                <div class="class-option" onclick="yarrrmlBuilder.selectClassOption('${c.prefix}:${c.label}', '${c.id}')">
                    <span class="class-option-label">${c.prefix}:${c.label}</span>
                    <span class="class-option-uri">${c.uri}</span>
                </div>
            `).join('')
            : '<div class="class-option disabled">No matching classes</div>';

        dropdown.style.display = 'block';
    }

    selectClassOption(classUri, classId) {
        const searchInput = document.getElementById('new-mapping-class-search');
        const hiddenInput = document.getElementById('new-mapping-class');
        const dropdown = document.getElementById('class-dropdown');

        if (searchInput) searchInput.value = classUri;
        if (hiddenInput) hiddenInput.value = classUri;
        if (dropdown) dropdown.style.display = 'none';

        // Also focus on this class in the ontology browser
        this.focusOnClass(classId);
    }

    renderPropertiesStep() {
        const mappingOptions = Object.keys(this.mapping.mappings).length > 0
            ? Object.keys(this.mapping.mappings).map(m => `<option value="${m}">${m}</option>`).join('')
            : '<option value="">-- Define a mapping first --</option>';

        // Get detected columns from source
        const columns = this.detectedColumns || [];
        const columnOptions = columns.length > 0
            ? columns.map(c => `<option value="${c}">${c}</option>`).join('')
            : '<option value="">-- Upload CSV to detect columns --</option>';

        return `
            <div class="step-content">
                <h2>Step 4: Map Properties</h2>
                <p class="step-description">
                    Map source columns to RDF predicates. For object properties (IRI references), you can construct URIs from prefix + column values.
                </p>

                <div class="property-mapping-section">
                    <div class="mapping-selector">
                        <label>Target Mapping:</label>
                        <select id="property-mapping-select" onchange="yarrrmlBuilder.onMappingChange(this.value)">
                            ${mappingOptions}
                        </select>
                    </div>

                    <div class="properties-table">
                        <table>
                            <thead>
                                <tr>
                                    <th style="width: 30%;">RDF Predicate</th>
                                    <th style="width: 35%;">Value Template</th>
                                    <th style="width: 15%;">Type</th>
                                    <th style="width: 10%;">Provenance</th>
                                    <th style="width: 10%;"></th>
                                </tr>
                            </thead>
                            <tbody id="properties-tbody">
                                ${this.renderPropertyRows()}
                            </tbody>
                        </table>
                    </div>

                    <div class="add-property-form">
                        <h4>Add Property Mapping</h4>

                        <div class="form-row">
                            <div class="form-group" style="flex: 1;">
                                <label>RDF Predicate</label>
                                <div class="predicate-search-wrapper">
                                    <input type="text" id="new-prop-predicate"
                                           placeholder="Type to search properties..."
                                           oninput="yarrrmlBuilder.filterPredicateOptions(this.value)"
                                           onfocus="yarrrmlBuilder.showPredicateDropdown()">
                                    <div class="predicate-dropdown" id="predicate-dropdown" style="display: none;">
                                        ${this.renderPredicateOptions()}
                                    </div>
                                </div>
                            </div>
                            <div class="form-group" style="flex: 0.8;">
                                <label>Value Type</label>
                                <select id="new-prop-type" onchange="yarrrmlBuilder.onValueTypeChange(this.value)">
                                    <option value="literal">Literal (Data Property)</option>
                                    <option value="iri">IRI (Object Property)</option>
                                </select>
                            </div>
                        </div>

                        <!-- Literal Value Section -->
                        <div id="literal-value-section">
                            <div class="form-row">
                                <div class="form-group" style="flex: 1;">
                                    <label>Source Column</label>
                                    <select id="new-prop-column">
                                        <option value="">Select column...</option>
                                        ${columnOptions}
                                    </select>
                                </div>
                                <div class="form-group" style="flex: 1;">
                                    <label>Or Custom Value</label>
                                    <input type="text" id="new-prop-column-custom" placeholder="column_name or static value">
                                </div>
                                <div class="form-group" style="flex: 0.8;">
                                    <label>Datatype</label>
                                    <select id="new-prop-datatype">
                                        <option value="string">String</option>
                                        <option value="integer">Integer</option>
                                        <option value="decimal">Decimal</option>
                                        <option value="date">Date</option>
                                        <option value="dateTime">DateTime</option>
                                        <option value="boolean">Boolean</option>
                                    </select>
                                </div>
                            </div>
                        </div>

                        <!-- IRI Value Section (for Object Properties) -->
                        <div id="iri-value-section" style="display: none;">
                            <div class="iri-builder">
                                <div class="iri-mode-selector">
                                    <label class="radio-option">
                                        <input type="radio" name="iri-mode" value="template" checked onchange="yarrrmlBuilder.onIriModeChange('template')">
                                        <span>Build IRI from prefix + template</span>
                                    </label>
                                    <label class="radio-option">
                                        <input type="radio" name="iri-mode" value="column" onchange="yarrrmlBuilder.onIriModeChange('column')">
                                        <span>Use column containing full URI</span>
                                    </label>
                                </div>

                                <div id="iri-template-section">
                                    <p class="form-hint">Construct an IRI using a prefix and column value(s). Use $(column) syntax.</p>

                                    <div class="form-row">
                                        <div class="form-group" style="flex: 0.5;">
                                            <label>Prefix</label>
                                            <select id="new-prop-iri-prefix" onchange="yarrrmlBuilder.updateIriPreview()">
                                                ${Object.keys(this.mapping.prefixes).map(p =>
                                                    `<option value="${p}">${p}:</option>`
                                                ).join('')}
                                            </select>
                                        </div>
                                        <div class="form-group" style="flex: 1;">
                                            <label>Local Part (use $(column) for dynamic values)</label>
                                            <input type="text" id="new-prop-iri-local"
                                                   placeholder="e.g., organization/$(org_id) or theme/$(theme_code)"
                                                   oninput="yarrrmlBuilder.updateIriPreview()">
                                        </div>
                                    </div>

                                    <div class="iri-preview">
                                        <label>Preview:</label>
                                        <code id="iri-preview-value">ex:resource/$(column)</code>
                                    </div>
                                </div>

                                <div id="iri-column-section" style="display: none;">
                                    <p class="form-hint">Select a column that contains the complete URI value.</p>
                                    <div class="form-group">
                                        <label>Column with URI</label>
                                        <select id="new-prop-iri-column">
                                            <option value="">Select column...</option>
                                            ${columnOptions}
                                        </select>
                                    </div>
                                </div>
                            </div>
                        </div>

                        <div class="form-row" style="margin-top: 15px;">
                            <div class="form-group">
                                <label class="checkbox-wrapper">
                                    <input type="checkbox" id="new-prop-provenance">
                                    Track Provenance (adds RDF-star annotations)
                                </label>
                            </div>
                        </div>

                        <button class="btn btn-primary" onclick="yarrrmlBuilder.addPropertyFromForm()">
                            <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor"><path d="M19 13h-6v6h-2v-6H5v-2h6V5h2v6h6v2z"/></svg>
                            Add Property Mapping
                        </button>
                    </div>
                </div>

                <div class="step-help">
                    <h4>
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor"><path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm1 15h-2v-6h2v6zm0-8h-2V7h2v2z"/></svg>
                        Examples
                    </h4>
                    <ul>
                        <li><strong>Data Property:</strong> <code>dct:title</code> → <code>$(title_column)</code> as String</li>
                        <li><strong>Object Property (template):</strong> <code>dct:publisher</code> → <code>ex:organization/$(org_id)</code> as IRI</li>
                        <li><strong>Object Property (column):</strong> <code>dcat:theme</code> → column <code>theme_uri</code> containing full URI</li>
                    </ul>
                </div>
            </div>
        `;
    }

    onValueTypeChange(valueType) {
        const literalSection = document.getElementById('literal-value-section');
        const iriSection = document.getElementById('iri-value-section');

        if (valueType === 'iri') {
            literalSection.style.display = 'none';
            iriSection.style.display = 'block';
        } else {
            literalSection.style.display = 'block';
            iriSection.style.display = 'none';
        }

        this.updateIriPreview();
    }

    onIriModeChange(mode) {
        const templateSection = document.getElementById('iri-template-section');
        const columnSection = document.getElementById('iri-column-section');

        if (mode === 'template') {
            templateSection.style.display = 'block';
            columnSection.style.display = 'none';
        } else {
            templateSection.style.display = 'none';
            columnSection.style.display = 'block';
        }
    }

    updateIriPreview() {
        const prefix = document.getElementById('new-prop-iri-prefix')?.value || 'ex';
        const local = document.getElementById('new-prop-iri-local')?.value || 'resource/$(id)';
        const preview = document.getElementById('iri-preview-value');

        if (preview) {
            preview.textContent = `${prefix}:${local}`;
        }
    }

    renderPredicateOptions() {
        if (!this.ontology) return '<div class="predicate-option disabled">No ontology loaded</div>';

        const allProps = [];

        // Add data properties
        Object.entries(this.ontology.dataProperties || {}).forEach(([className, props]) => {
            props.forEach(p => {
                allProps.push({
                    uri: `${p.prefix}:${p.name}`,
                    label: p.name,
                    prefix: p.prefix,
                    type: p.type,
                    domain: className
                });
            });
        });

        // Add object properties
        (this.ontology.objectProperties || []).forEach(p => {
            allProps.push({
                uri: `${p.prefix}:${p.label}`,
                label: p.label,
                prefix: p.prefix,
                type: 'iri',
                domain: p.from
            });
        });

        if (allProps.length === 0) {
            return '<div class="predicate-option disabled">No properties in ontology</div>';
        }

        return allProps.map(p => `
            <div class="predicate-option" onclick="yarrrmlBuilder.selectPredicateOption('${p.uri}', '${p.type}')">
                <span class="predicate-option-label">${p.uri}</span>
                <span class="predicate-option-meta">${p.type} ${p.domain ? '(from ' + p.domain + ')' : ''}</span>
            </div>
        `).join('');
    }

    showPredicateDropdown() {
        const dropdown = document.getElementById('predicate-dropdown');
        if (dropdown) {
            dropdown.style.display = 'block';
        }
    }

    filterPredicateOptions(query) {
        const dropdown = document.getElementById('predicate-dropdown');
        if (!dropdown) return;

        const queryLower = query.toLowerCase();
        const allProps = [];

        // Collect all properties
        Object.entries(this.ontology?.dataProperties || {}).forEach(([className, props]) => {
            props.forEach(p => {
                if (p.name.toLowerCase().includes(queryLower) ||
                    p.prefix.toLowerCase().includes(queryLower)) {
                    allProps.push({
                        uri: `${p.prefix}:${p.name}`,
                        label: p.name,
                        prefix: p.prefix,
                        type: p.type,
                        domain: className
                    });
                }
            });
        });

        (this.ontology?.objectProperties || []).forEach(p => {
            if (p.label.toLowerCase().includes(queryLower) ||
                p.prefix.toLowerCase().includes(queryLower)) {
                allProps.push({
                    uri: `${p.prefix}:${p.label}`,
                    label: p.label,
                    prefix: p.prefix,
                    type: 'iri',
                    domain: p.from
                });
            }
        });

        dropdown.innerHTML = allProps.length > 0
            ? allProps.map(p => `
                <div class="predicate-option" onclick="yarrrmlBuilder.selectPredicateOption('${p.uri}', '${p.type}')">
                    <span class="predicate-option-label">${p.uri}</span>
                    <span class="predicate-option-meta">${p.type} ${p.domain ? '(from ' + p.domain + ')' : ''}</span>
                </div>
            `).join('')
            : `<div class="predicate-option disabled">No matching properties</div>`;

        dropdown.style.display = 'block';
    }

    selectPredicateOption(predicateUri, dataType) {
        const predicateInput = document.getElementById('new-prop-predicate');
        const typeSelect = document.getElementById('new-prop-type');
        const dropdown = document.getElementById('predicate-dropdown');

        if (predicateInput) predicateInput.value = predicateUri;

        // Auto-switch between literal and IRI mode based on property type
        if (typeSelect) {
            if (dataType === 'iri') {
                typeSelect.value = 'iri';
                this.onValueTypeChange('iri');
            } else {
                typeSelect.value = 'literal';
                this.onValueTypeChange('literal');

                // Also set the datatype dropdown
                const datatypeSelect = document.getElementById('new-prop-datatype');
                if (datatypeSelect && dataType) {
                    datatypeSelect.value = dataType;
                }
            }
        }

        if (dropdown) dropdown.style.display = 'none';
    }

    addPropertyFromForm() {
        const predicateInput = document.getElementById('new-prop-predicate');
        const typeSelect = document.getElementById('new-prop-type');
        const provenanceCheck = document.getElementById('new-prop-provenance');

        const predicate = predicateInput?.value;
        const valueType = typeSelect?.value || 'literal';
        const trackProvenance = provenanceCheck?.checked || false;

        if (!predicate) {
            alert('Please specify an RDF predicate');
            return;
        }

        let valueTemplate = '';
        let dataType = 'string';
        let isIriTemplate = false; // true if it's a prefix:local template

        if (valueType === 'iri') {
            // Check which IRI mode is selected (template or column)
            const iriModeRadio = document.querySelector('input[name="iri-mode"]:checked');
            const iriMode = iriModeRadio?.value || 'template';

            console.log('IRI mode:', iriMode);

            if (iriMode === 'column') {
                // Use column containing full URI
                const iriColumn = document.getElementById('new-prop-iri-column')?.value;

                if (!iriColumn) {
                    alert('Please select a column containing the full URI');
                    return;
                }

                valueTemplate = iriColumn;
                isIriTemplate = false;
                console.log('Using IRI from column:', iriColumn);
            } else {
                // Build from prefix + local template
                const iriPrefix = document.getElementById('new-prop-iri-prefix')?.value || 'ex';
                const iriLocal = document.getElementById('new-prop-iri-local')?.value;

                console.log('Building IRI template - prefix:', iriPrefix, 'local:', iriLocal);

                if (!iriLocal) {
                    alert('Please specify the IRI local part (e.g., organization/$(org_id))');
                    return;
                }

                valueTemplate = `${iriPrefix}:${iriLocal}`;
                isIriTemplate = true;
                console.log('Created IRI template:', valueTemplate);
            }
            dataType = 'iri';
        } else {
            // Get literal value
            const columnSelect = document.getElementById('new-prop-column');
            const columnCustom = document.getElementById('new-prop-column-custom');
            const datatypeSelect = document.getElementById('new-prop-datatype');

            const column = columnCustom?.value || columnSelect?.value;
            dataType = datatypeSelect?.value || 'string';

            if (!column) {
                alert('Please specify a source column');
                return;
            }

            valueTemplate = column;
        }

        // Add to the table
        const tbody = document.getElementById('properties-tbody');
        if (tbody) {
            // Remove empty row if present
            const emptyRow = tbody.querySelector('.empty-row');
            if (emptyRow) emptyRow.remove();

            const newRow = document.createElement('tr');
            newRow.className = 'property-row';

            // Format display based on type
            let valueDisplay;
            if (valueType === 'iri') {
                if (isIriTemplate) {
                    // Template like ex:organization/$(org_id)
                    valueDisplay = `<code class="iri-value">${valueTemplate}</code>`;
                } else {
                    // Column containing URI
                    valueDisplay = `<code class="iri-value">$(${valueTemplate})</code>`;
                }
            } else {
                valueDisplay = `<code>$(${valueTemplate})</code>`;
            }

            newRow.innerHTML = `
                <td><code>${predicate}</code></td>
                <td>${valueDisplay}</td>
                <td><span class="type-badge ${dataType}">${dataType}</span></td>
                <td>${trackProvenance ? '<span class="prov-badge">Yes</span>' : 'No'}</td>
                <td>
                    <button class="btn-icon" onclick="yarrrmlBuilder.removePropertyRow(this)">
                        <svg width="12" height="12" viewBox="0 0 24 24" fill="currentColor"><path d="M19 6.41L17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12z"/></svg>
                    </button>
                </td>
            `;
            tbody.appendChild(newRow);
        }

        // Store in mapping
        const mappingName = document.getElementById('property-mapping-select')?.value;
        if (mappingName && this.mapping.mappings[mappingName]) {
            if (!this.mapping.mappings[mappingName].properties) {
                this.mapping.mappings[mappingName].properties = [];
            }
            this.mapping.mappings[mappingName].properties.push({
                predicate,
                valueTemplate,
                dataType,
                isIri: valueType === 'iri',
                isIriTemplate: isIriTemplate,
                trackProvenance
            });
        }

        // Clear form
        this.clearPropertyForm();
    }

    removePropertyRow(button) {
        const row = button.closest('tr');
        const tbody = document.getElementById('properties-tbody');
        const mappingName = document.getElementById('property-mapping-select')?.value;

        if (row && mappingName && this.mapping.mappings[mappingName]?.properties) {
            const rowIndex = Array.from(tbody.querySelectorAll('tr.property-row')).indexOf(row);
            if (rowIndex >= 0) {
                this.mapping.mappings[mappingName].properties.splice(rowIndex, 1);
            }
        }

        row?.remove();

        // Show empty row if no properties left
        if (tbody && tbody.querySelectorAll('tr.property-row').length === 0) {
            tbody.innerHTML = this.renderPropertyRows();
        }
    }

    clearPropertyForm() {
        const fields = [
            'new-prop-predicate',
            'new-prop-column',
            'new-prop-column-custom',
            'new-prop-iri-local',
            'new-prop-iri-column'
        ];

        fields.forEach(id => {
            const el = document.getElementById(id);
            if (el) el.value = '';
        });

        const provenanceCheck = document.getElementById('new-prop-provenance');
        if (provenanceCheck) provenanceCheck.checked = false;

        const typeSelect = document.getElementById('new-prop-type');
        if (typeSelect) typeSelect.value = 'literal';

        this.onValueTypeChange('literal');
    }

    renderPropertyRows() {
        // Get current mapping's properties
        const mappingName = Object.keys(this.mapping.mappings)[0];
        const properties = this.mapping.mappings[mappingName]?.properties || [];

        if (properties.length === 0) {
            return `
                <tr class="property-row empty-row">
                    <td colspan="5" style="text-align: center; color: var(--text-secondary); padding: 20px;">
                        No properties mapped yet. Use the form below to add property mappings.
                    </td>
                </tr>
            `;
        }

        return properties.map((p, i) => {
            // Handle both old format (column) and new format (valueTemplate)
            let valueDisplay;
            if (p.isIri || p.dataType === 'iri') {
                if (p.isIriTemplate) {
                    // Template like ex:organization/$(org_id)
                    valueDisplay = `<code class="iri-value">${p.valueTemplate}</code>`;
                } else {
                    // Column containing URI
                    valueDisplay = `<code class="iri-value">$(${p.valueTemplate || p.column})</code>`;
                }
            } else {
                valueDisplay = `<code>$(${p.valueTemplate || p.column})</code>`;
            }

            return `
                <tr class="property-row">
                    <td><code>${p.predicate}</code></td>
                    <td>${valueDisplay}</td>
                    <td><span class="type-badge ${p.dataType}">${p.dataType}</span></td>
                    <td>${p.trackProvenance ? '<span class="prov-badge">Yes</span>' : 'No'}</td>
                    <td>
                        <button class="btn-icon" onclick="yarrrmlBuilder.removePropertyMapping('${mappingName}', ${i})">
                            <svg width="12" height="12" viewBox="0 0 24 24" fill="currentColor"><path d="M19 6.41L17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12z"/></svg>
                        </button>
                    </td>
                </tr>
            `;
        }).join('');
    }

    removePropertyMapping(mappingName, index) {
        if (this.mapping.mappings[mappingName]?.properties) {
            this.mapping.mappings[mappingName].properties.splice(index, 1);
            this.renderBuilder();
        }
    }

    onMappingChange(mappingName) {
        // Re-render property rows for selected mapping
        const tbody = document.getElementById('properties-tbody');
        if (tbody) {
            const properties = this.mapping.mappings[mappingName]?.properties || [];
            tbody.innerHTML = this.renderPropertyRows();
        }
    }

    renderReviewStep() {
        const yaml = this.generateYARRRML();

        return `
            <div class="step-content">
                <h2>Step 5: Review & Export</h2>

                <div class="yaml-preview">
                    <div class="yaml-header">
                        <span>Generated YARRRML</span>
                        <div>
                            <button class="btn btn-small" onclick="yarrrmlBuilder.copyYAML()">
                                <svg width="12" height="12" viewBox="0 0 24 24" fill="currentColor"><path d="M16 1H4c-1.1 0-2 .9-2 2v14h2V3h12V1zm3 4H8c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h11c1.1 0 2-.9 2-2V7c0-1.1-.9-2-2-2zm0 16H8V7h11v14z"/></svg>
                                Copy
                            </button>
                            <button class="btn btn-small" onclick="yarrrmlBuilder.downloadYAML()">
                                <svg width="12" height="12" viewBox="0 0 24 24" fill="currentColor"><path d="M19 9h-4V3H9v6H5l7 7 7-7zM5 18v2h14v-2H5z"/></svg>
                                Download
                            </button>
                        </div>
                    </div>
                    <pre id="yaml-output">${this.escapeHtml(yaml)}</pre>
                </div>

                <!-- Sample Triple Preview -->
                <div class="triple-preview">
                    <div class="triple-preview-header">
                        <h4>
                            <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor"><path d="M12 4.5C7 4.5 2.73 7.61 1 12c1.73 4.39 6 7.5 11 7.5s9.27-3.11 11-7.5c-1.73-4.39-6-7.5-11-7.5zM12 17c-2.76 0-5-2.24-5-5s2.24-5 5-5 5 2.24 5 5-2.24 5-5 5zm0-8c-1.66 0-3 1.34-3 3s1.34 3 3 3 3-1.34 3-3-1.34-3-3-3z"/></svg>
                            Sample Output Preview
                        </h4>
                        <span class="preview-note">Example triples from mapping</span>
                    </div>
                    <pre class="triple-output">${this.generateSampleTriples()}</pre>
                </div>

                <div class="validation-results">
                    ${this.validateMapping()}
                </div>

                <!-- Export Options -->
                <div class="export-options">
                    <h4>Export Options</h4>
                    <div class="export-buttons">
                        <button class="btn btn-primary" onclick="yarrrmlBuilder.downloadYAML()">
                            <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor"><path d="M19 9h-4V3H9v6H5l7 7 7-7zM5 18v2h14v-2H5z"/></svg>
                            Download YARRRML
                        </button>
                        <button class="btn btn-secondary" onclick="yarrrmlBuilder.exportAsJSON()">
                            <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor"><path d="M14 2H6c-1.1 0-1.99.9-1.99 2L4 20c0 1.1.89 2 1.99 2H18c1.1 0 2-.9 2-2V8l-6-6zm2 16H8v-2h8v2zm0-4H8v-2h8v2zm-3-5V3.5L18.5 9H13z"/></svg>
                            Export Session
                        </button>
                    </div>
                </div>
            </div>
        `;
    }

    generateSampleTriples() {
        // Generate dynamic sample based on actual mapping configuration
        let output = `# Sample RDF Output (Turtle format)
# Generated from your mapping configuration

`;

        // Add prefixes
        for (const [prefix, uri] of Object.entries(this.mapping.prefixes)) {
            output += `@prefix ${prefix}: <${uri}> .\n`;
        }
        output += `\n`;

        // Check if we have mappings
        const mappings = Object.entries(this.mapping.mappings);
        if (mappings.length === 0) {
            output += `# No mappings defined yet.\n`;
            output += `# Complete Steps 1-4 to see a preview.\n`;
            return output;
        }

        // Generate sample triples for each mapping
        for (const [name, config] of mappings) {
            output += `# Mapping: ${name}\n`;

            // Sample subject - replace $(column) with sample value
            const sampleSubject = config.subject
                ? config.subject.replace(/\$\(([^)]+)\)/g, 'sample_$1')
                : 'ex:resource/1';

            output += `${sampleSubject} a ${config.class || 'ex:Thing'} `;

            // Add properties
            if (config.properties && config.properties.length > 0) {
                output += `;\n`;
                config.properties.forEach((prop, i) => {
                    const sampleValue = prop.dataType === 'integer' ? '42' :
                                       prop.dataType === 'decimal' ? '3.14' :
                                       prop.dataType === 'date' ? '"2026-02-17"' :
                                       prop.dataType === 'dateTime' ? '"2026-02-17T10:00:00Z"' :
                                       prop.dataType === 'boolean' ? 'true' :
                                       prop.dataType === 'iri' ? `ex:ref_${prop.column}` :
                                       `"Sample ${prop.column}"`;

                    const ending = i === config.properties.length - 1 ? ' .' : ' ;';
                    output += `    ${prop.predicate} ${sampleValue}${ending}\n`;
                });

                // Show RDF-star provenance for properties that track it
                const provenanceProps = config.properties.filter(p => p.trackProvenance);
                if (provenanceProps.length > 0) {
                    output += `\n# RDF-star Provenance Annotations:\n`;
                    provenanceProps.forEach(prop => {
                        const sampleValue = prop.dataType === 'integer' ? '42' : `"Sample ${prop.column}"`;
                        output += `<<${sampleSubject} ${prop.predicate} ${sampleValue}>>\n`;
                        output += `    prov:wasDerivedFrom ex:source/system ;\n`;
                        output += `    prov:generatedAtTime "2026-02-17T10:00:00Z"^^xsd:dateTime .\n\n`;
                    });
                }
            } else {
                output += `.\n`;
                output += `# No properties mapped yet. Add properties in Step 4.\n`;
            }

            output += `\n`;
        }

        return output;
    }

    exportAsJSON() {
        const session = {
            version: '1.0',
            created: new Date().toISOString(),
            mapping: this.mapping,
            detectedColumns: this.detectedColumns || []
        };

        const blob = new Blob([JSON.stringify(session, null, 2)], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = 'yarrrml-session.json';
        a.click();
        URL.revokeObjectURL(url);
    }

    generateYARRRML() {
        let yaml = `# YARRRML Mapping
# Generated: ${new Date().toISOString()}

prefixes:\n`;

        for (const [prefix, uri] of Object.entries(this.mapping.prefixes)) {
            yaml += `  ${prefix}: "${uri}"\n`;
        }

        yaml += `\nsources:\n`;

        if (Object.keys(this.mapping.sources).length === 0) {
            yaml += `  # No sources defined yet\n`;
        } else {
            for (const [name, config] of Object.entries(this.mapping.sources)) {
                yaml += `  ${name}:\n`;
                yaml += `    access: "${config.access}"\n`;
                yaml += `    referenceFormulation: ${config.type || 'csv'}\n`;
            }
        }

        yaml += `\nmappings:\n`;

        if (Object.keys(this.mapping.mappings).length === 0) {
            yaml += `  # No mappings defined yet\n`;
        } else {
            for (const [name, config] of Object.entries(this.mapping.mappings)) {
                yaml += `  ${name}:\n`;
                yaml += `    sources: ${config.source}\n`;
                yaml += `    subject: ${config.subject}\n`;
                yaml += `    predicateobjects:\n`;

                // Add rdf:type
                yaml += `      - predicates: rdf:type\n`;
                yaml += `        objects:\n`;
                yaml += `          value: ${config.class}\n`;
                yaml += `          type: iri\n`;

                // Add property mappings
                if (config.properties && config.properties.length > 0) {
                    for (const prop of config.properties) {
                        yaml += `\n      - predicates: ${prop.predicate}\n`;
                        yaml += `        objects:\n`;

                        // Handle IRI vs literal values
                        if (prop.isIri || prop.dataType === 'iri') {
                            if (prop.isIriTemplate) {
                                // It's a prefixed IRI template like ex:organization/$(org_id)
                                yaml += `          value: ${prop.valueTemplate}\n`;
                            } else {
                                // It's a column containing full URI
                                yaml += `          value: "$(${prop.valueTemplate})"\n`;
                            }
                            yaml += `          type: iri\n`;
                        } else {
                            // Literal value
                            const column = prop.valueTemplate || prop.column;
                            yaml += `          value: "$(${column})"\n`;

                            // Add datatype for non-string literals
                            if (prop.dataType && prop.dataType !== 'string') {
                                yaml += `          datatype: xsd:${prop.dataType}\n`;
                            }
                        }

                        // Add provenance annotations if enabled
                        if (prop.trackProvenance) {
                            yaml += `        annotations:\n`;
                            yaml += `          - predicates: prov:wasDerivedFrom\n`;
                            yaml += `            objects:\n`;
                            yaml += `              value: "$(source_system)"\n`;
                            yaml += `              type: iri\n`;
                            yaml += `          - predicates: prov:generatedAtTime\n`;
                            yaml += `            objects:\n`;
                            yaml += `              value: "$(timestamp)"\n`;
                            yaml += `              datatype: xsd:dateTime\n`;
                        }
                    }
                }
            }
        }

        return yaml;
    }

    validateMapping() {
        const issues = [];
        const warnings = [];

        if (Object.keys(this.mapping.sources).length === 0) {
            warnings.push('No data sources defined');
        }

        if (Object.keys(this.mapping.mappings).length === 0) {
            warnings.push('No class mappings defined');
        }

        return `
            <div class="validation-summary ${issues.length > 0 ? 'has-errors' : 'valid'}">
                <h4>
                    ${issues.length > 0
                        ? '<svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor"><path d="M1 21h22L12 2 1 21zm12-3h-2v-2h2v2zm0-4h-2v-4h2v4z"/></svg> Issues Found'
                        : '<svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor"><path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 15l-5-5 1.41-1.41L10 14.17l7.59-7.59L19 8l-9 9z"/></svg> Ready'
                    }
                </h4>
                ${warnings.length > 0 ? `
                    <ul class="warning-list">
                        ${warnings.map(w => `<li class="warning">${w}</li>`).join('')}
                    </ul>
                ` : ''}
                <p class="validation-note">
                    Configure your mapping using the steps above.
                </p>
            </div>
        `;
    }

    // ==========================================
    // ONTOLOGY BROWSER
    // ==========================================

    buildSearchIndex() {
        this.ontologyIndex.clear();

        if (!this.ontology) return;

        // Index classes
        this.ontology.classes.forEach(cls => {
            const terms = [
                cls.label.toLowerCase(),
                cls.id.toLowerCase(),
                cls.prefix.toLowerCase(),
                (cls.prefix + ':' + cls.label).toLowerCase()
            ];

            terms.forEach(term => {
                if (!this.ontologyIndex.has(term)) {
                    this.ontologyIndex.set(term, []);
                }
                this.ontologyIndex.get(term).push({ type: 'class', data: cls });
            });
        });

        // Index data properties
        Object.entries(this.ontology.dataProperties).forEach(([className, props]) => {
            props.forEach(prop => {
                const terms = [
                    prop.name.toLowerCase(),
                    (prop.prefix + ':' + prop.name).toLowerCase()
                ];

                terms.forEach(term => {
                    if (!this.ontologyIndex.has(term)) {
                        this.ontologyIndex.set(term, []);
                    }
                    this.ontologyIndex.get(term).push({ type: 'property', data: prop, className });
                });
            });
        });

        // Index object properties
        this.ontology.objectProperties.forEach(rel => {
            const term = rel.label.toLowerCase();
            if (!this.ontologyIndex.has(term)) {
                this.ontologyIndex.set(term, []);
            }
            this.ontologyIndex.get(term).push({ type: 'relationship', data: rel });
        });
    }

    searchOntology(query) {
        const resultsDiv = document.getElementById('search-results');

        if (!query || query.length < 2) {
            resultsDiv.innerHTML = '';
            resultsDiv.style.display = 'none';
            return;
        }

        const queryLower = query.toLowerCase();
        const results = [];

        this.ontologyIndex.forEach((items, term) => {
            if (term.includes(queryLower)) {
                items.forEach(item => {
                    if (!results.find(r => r.type === item.type &&
                        (item.type === 'class' ? r.data.id === item.data.id :
                         item.type === 'property' ? r.data.name === item.data.name : false))) {
                        results.push(item);
                    }
                });
            }
        });

        const limited = results.slice(0, 10);

        if (limited.length === 0) {
            resultsDiv.innerHTML = '<div class="search-no-results">No results found</div>';
        } else {
            resultsDiv.innerHTML = limited.map(result => {
                if (result.type === 'class') {
                    const escapedId = result.data.id.replace(/'/g, "\\'");
                    return `
                        <div class="search-result-item class" onclick="yarrrmlBuilder.focusOnClass('${escapedId}')">
                            <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor"><path d="M12 2l-5.5 9h11z M17.5 13h-11l5.5 9z"/></svg>
                            <span class="result-label">${result.data.prefix}:${result.data.label}</span>
                            <span class="result-type">Class</span>
                        </div>
                    `;
                } else if (result.type === 'property') {
                    const escapedClassName = result.className.replace(/'/g, "\\'");
                    const escapedName = result.data.name.replace(/'/g, "\\'");
                    return `
                        <div class="search-result-item property" onclick="yarrrmlBuilder.showPropertyInContext('${escapedClassName}', '${escapedName}')">
                            <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor"><path d="M3 17.25V21h3.75L17.81 9.94l-3.75-3.75L3 17.25z"/></svg>
                            <span class="result-label">${result.data.prefix}:${result.data.name}</span>
                            <span class="result-type">Property of ${result.className}</span>
                        </div>
                    `;
                } else {
                    const escapedFrom = (result.data.from || '').replace(/'/g, "\\'");
                    const escapedTo = (result.data.to || '').replace(/'/g, "\\'");
                    return `
                        <div class="search-result-item relationship" onclick="yarrrmlBuilder.showRelationship('${escapedFrom}', '${escapedTo}')">
                            <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor"><path d="M3.9 12c0-1.71 1.39-3.1 3.1-3.1h4V7H7c-2.76 0-5 2.24-5 5s2.24 5 5 5h4v-1.9H7c-1.71 0-3.1-1.39-3.1-3.1zM8 13h8v-2H8v2zm9-6h-4v1.9h4c1.71 0 3.1 1.39 3.1 3.1s-1.39 3.1-3.1 3.1h-4V17h4c2.76 0 5-2.24 5-5s-2.24-5-5-5z"/></svg>
                            <span class="result-label">${result.data.label}</span>
                            <span class="result-type">${result.data.from || ''} → ${result.data.to || ''}</span>
                        </div>
                    `;
                }
            }).join('');
        }

        resultsDiv.style.display = 'block';
    }

    focusOnClass(classId) {
        console.log('focusOnClass called with:', classId);

        if (!this.ontology || !this.ontology.classes) {
            console.warn('Ontology not loaded yet');
            return;
        }

        // Validate classId exists in ontology
        const classExists = this.ontology.classes.find(c => c.id === classId);
        if (!classExists) {
            console.warn(`Class '${classId}' not found in ontology, showing all classes`);
            this.expandAll();
            return;
        }

        const searchInput = document.getElementById('ontology-search');
        const resultsDiv = document.getElementById('search-results');
        if (searchInput) searchInput.value = '';
        if (resultsDiv) resultsDiv.style.display = 'none';

        this.visibleClasses.clear();
        this.visibleClasses.add(classId);

        // Add valid neighbors
        const neighbors = this.getNeighbors(classId);
        neighbors.forEach(id => {
            if (this.ontology.classes.some(c => c.id === id)) {
                this.visibleClasses.add(id);
            }
        });

        console.log('Visible classes after focus:', Array.from(this.visibleClasses));

        this.renderOntologyGraph();

        this.selectOntologyClass(classExists);
    }

    showPropertyInContext(className, propertyName) {
        this.focusOnClass(className);
    }

    showRelationship(fromClass, toClass) {
        this.visibleClasses.clear();
        this.visibleClasses.add(fromClass);
        this.visibleClasses.add(toClass);
        this.renderOntologyGraph();
    }

    getNeighbors(classId) {
        const neighbors = new Set();

        if (!this.ontology) return neighbors;

        const cls = this.ontology.classes.find(c => c.id === classId);
        if (cls?.parent) {
            neighbors.add(cls.parent);
        }

        // Find child classes
        this.ontology.classes
            .filter(c => c.parent === classId)
            .forEach(c => neighbors.add(c.id));

        // Find connected classes via object properties
        if (this.ontology.objectProperties) {
            this.ontology.objectProperties.forEach(rel => {
                if (rel.from && rel.from === classId && rel.to) {
                    neighbors.add(rel.to);
                }
                if (rel.to && rel.to === classId && rel.from) {
                    neighbors.add(rel.from);
                }
            });
        }

        return neighbors;
    }

    expandClass(classId) {
        console.log('expandClass called with:', classId);
        console.log('Current visible classes:', Array.from(this.visibleClasses));

        this.visibleClasses.add(classId);
        const neighbors = this.getNeighbors(classId);
        console.log('Neighbors found:', Array.from(neighbors));

        // Only add neighbors that actually exist in the ontology
        neighbors.forEach(id => {
            const exists = this.ontology.classes.some(c => c.id === id);
            if (exists) {
                this.visibleClasses.add(id);
            } else {
                console.warn(`Neighbor '${id}' not found in ontology classes`);
            }
        });

        console.log('Visible classes after expand:', Array.from(this.visibleClasses));
        this.renderOntologyGraph();
    }

    hideClass(classId) {
        this.visibleClasses.delete(classId);
        this.renderOntologyGraph();
    }

    resetOntologyView() {
        if (this.ontology && this.ontology.classes.length > 0) {
            // Show all classes initially for real ontology
            this.visibleClasses.clear();
            this.ontology.classes.forEach(c => this.visibleClasses.add(c.id));
            this.renderOntologyGraph();
        }
    }

    expandAll() {
        this.visibleClasses.clear();
        this.ontology.classes.forEach(c => this.visibleClasses.add(c.id));
        console.log('expandAll - visible classes:', Array.from(this.visibleClasses));
        this.renderOntologyGraph();
    }

    initOntologyGraph() {
        const container = document.getElementById('ontology-graph');
        if (!container) {
            console.warn('Ontology graph container not found');
            return;
        }

        // Get actual computed size
        const rect = container.getBoundingClientRect();
        const width = rect.width || 400;
        const height = rect.height || 250;

        console.log(`Initializing ontology graph: ${width}x${height}`);

        const svg = d3.select('#ontology-canvas')
            .attr('width', width)
            .attr('height', height);

        // Clear any existing content
        svg.selectAll('*').remove();

        const zoom = d3.zoom()
            .scaleExtent([0.3, 3])
            .on('zoom', (event) => {
                svg.select('g.ontology-content').attr('transform', event.transform);
            });

        svg.call(zoom);
        svg.append('g').attr('class', 'ontology-content');

        svg.append('defs').append('marker')
            .attr('id', 'ont-arrow')
            .attr('viewBox', '-0 -5 10 10')
            .attr('refX', 20)
            .attr('refY', 0)
            .attr('orient', 'auto')
            .attr('markerWidth', 6)
            .attr('markerHeight', 6)
            .append('path')
            .attr('d', 'M 0,-5 L 10,0 L 0,5')
            .attr('fill', '#7c7c9c');
    }

    renderOntologyGraph() {
        const svg = d3.select('#ontology-canvas');
        let g = svg.select('g.ontology-content');

        if (!g.node()) {
            console.warn('SVG group not found, reinitializing graph');
            this.initOntologyGraph();
            g = d3.select('#ontology-canvas').select('g.ontology-content');
            if (!g.node()) {
                console.error('Failed to create SVG group');
                return;
            }
        }

        // Ensure arrow marker exists
        if (!svg.select('#ont-arrow').node()) {
            svg.append('defs').append('marker')
                .attr('id', 'ont-arrow')
                .attr('viewBox', '-0 -5 10 10')
                .attr('refX', 20)
                .attr('refY', 0)
                .attr('orient', 'auto')
                .attr('markerWidth', 6)
                .attr('markerHeight', 6)
                .append('path')
                .attr('d', 'M 0,-5 L 10,0 L 0,5')
                .attr('fill', '#7c7c9c');
        }

        g.selectAll('*').remove();

        if (!this.ontology || this.ontology.classes.length === 0) {
            console.log('No ontology classes to render');
            return;
        }

        const width = parseInt(svg.attr('width')) || 400;
        const height = parseInt(svg.attr('height')) || 250;

        const visibleClassIds = Array.from(this.visibleClasses);
        console.log(`Rendering ${visibleClassIds.length} visible classes out of ${this.ontology.classes.length} total`);

        if (visibleClassIds.length === 0) {
            console.log('No visible classes - showing first class');
            if (this.ontology.classes.length > 0) {
                this.visibleClasses.add(this.ontology.classes[0].id);
                return this.renderOntologyGraph();
            }
            return;
        }

        const nodes = this.ontology.classes
            .filter(c => visibleClassIds.includes(c.id))
            .map(c => ({...c}));

        const links = [];

        // Add object property links (check for null/undefined)
        if (this.ontology.objectProperties && Array.isArray(this.ontology.objectProperties)) {
            this.ontology.objectProperties.forEach(rel => {
                if (rel && rel.from && rel.to &&
                    visibleClassIds.includes(rel.from) && visibleClassIds.includes(rel.to)) {
                    links.push({
                        source: rel.from,
                        target: rel.to,
                        label: rel.label || 'relatedTo',
                        type: 'object'
                    });
                }
            });
        }

        // Add inheritance links
        nodes.forEach(node => {
            if (node.parent && visibleClassIds.includes(node.parent)) {
                links.push({
                    source: node.id,
                    target: node.parent,
                    label: 'subClassOf',
                    type: 'inheritance'
                });
            }
        });

        console.log(`Rendering graph with ${nodes.length} nodes and ${links.length} links at ${width}x${height}`);

        if (nodes.length === 0) {
            console.warn('No nodes to render');
            return;
        }

        // Adjust force simulation based on number of nodes
        const nodeCount = nodes.length;
        const linkDistance = nodeCount <= 3 ? 100 : nodeCount <= 6 ? 80 : 60;
        const chargeStrength = nodeCount <= 3 ? -200 : nodeCount <= 6 ? -150 : -100;

        const simulation = d3.forceSimulation(nodes)
            .force('link', d3.forceLink(links).id(d => d.id).distance(linkDistance))
            .force('charge', d3.forceManyBody().strength(chargeStrength))
            .force('center', d3.forceCenter(width / 2, height / 2))
            .force('collision', d3.forceCollide().radius(55))
            .force('x', d3.forceX(width / 2).strength(0.1))
            .force('y', d3.forceY(height / 2).strength(0.1))
            .alphaDecay(0.05); // Faster stabilization

        // Stop simulation after stabilizing
        simulation.on('end', () => {
            console.log('Simulation stabilized');
        });

        const link = g.append('g')
            .selectAll('line')
            .data(links)
            .enter()
            .append('line')
            .attr('stroke', d => d.type === 'inheritance' ? '#9c27b0' : '#7c7c9c')
            .attr('stroke-width', d => d.type === 'inheritance' ? 2 : 1.5)
            .attr('stroke-dasharray', d => d.type === 'inheritance' ? '5,3' : 'none')
            .attr('marker-end', 'url(#ont-arrow)');

        const linkLabel = g.append('g')
            .selectAll('text')
            .data(links)
            .enter()
            .append('text')
            .attr('font-size', 9)
            .attr('fill', '#9e9e9e')
            .attr('text-anchor', 'middle')
            .text(d => d.label);

        const node = g.append('g')
            .selectAll('g')
            .data(nodes)
            .enter()
            .append('g')
            .style('cursor', 'pointer')
            .call(d3.drag()
                .on('start', (event, d) => {
                    if (!event.active) simulation.alphaTarget(0.3).restart();
                    d.fx = d.x;
                    d.fy = d.y;
                })
                .on('drag', (event, d) => {
                    d.fx = event.x;
                    d.fy = event.y;
                })
                .on('end', (event, d) => {
                    if (!event.active) simulation.alphaTarget(0);
                    // Keep the node fixed where it was dropped
                    // d.fx = null; d.fy = null; // Don't release - keeps graph stable
                }))
            .on('click', (event, d) => {
                event.stopPropagation();
                // Don't restart simulation on click
                this.selectOntologyClass(d);
            })
            .on('contextmenu', (event, d) => {
                event.preventDefault();
                this.showContextMenu(event, d);
            });

        node.append('rect')
            .attr('width', 90)
            .attr('height', 32)
            .attr('x', -45)
            .attr('y', -16)
            .attr('rx', 5)
            .attr('fill', d => this.getClassColor(d))
            .attr('stroke', '#fff')
            .attr('stroke-width', 2);

        node.append('text')
            .attr('text-anchor', 'middle')
            .attr('dy', 4)
            .attr('fill', '#fff')
            .attr('font-size', 10)
            .attr('font-weight', 'bold')
            .text(d => d.label.length > 12 ? d.label.substring(0, 10) + '...' : d.label);

        simulation.on('tick', () => {
            link
                .attr('x1', d => d.source.x)
                .attr('y1', d => d.source.y)
                .attr('x2', d => d.target.x)
                .attr('y2', d => d.target.y);

            linkLabel
                .attr('x', d => (d.source.x + d.target.x) / 2)
                .attr('y', d => (d.source.y + d.target.y) / 2 - 5);

            node.attr('transform', d => `translate(${d.x},${d.y})`);
        });
    }

    getClassColor(cls) {
        const colors = {
            'owl': '#9c27b0',
            'schema': '#2196f3',
            'foaf': '#4caf50',
            'prov': '#ff9800',
            'ex': '#00bcd4',
            'dcat': '#e91e63',
            'dct': '#795548'
        };
        return colors[cls.prefix] || '#607d8b';
    }

    // Context Menu
    bindContextMenu() {
        document.addEventListener('click', () => {
            const menu = document.getElementById('context-menu');
            if (menu) menu.style.display = 'none';
        });
    }

    showContextMenu(event, classData) {
        this.contextMenuTarget = classData;
        const menu = document.getElementById('context-menu');

        menu.style.left = event.pageX + 'px';
        menu.style.top = event.pageY + 'px';
        menu.style.display = 'block';

        menu.querySelectorAll('.context-menu-item').forEach(item => {
            item.onclick = (e) => {
                e.stopPropagation();
                const action = item.dataset.action;
                this.handleContextMenuAction(action);
                menu.style.display = 'none';
            };
        });
    }

    handleContextMenuAction(action) {
        const cls = this.contextMenuTarget;
        if (!cls) return;

        switch(action) {
            case 'expand':
                this.expandClass(cls.id);
                break;
            case 'focus':
                this.focusOnClass(cls.id);
                break;
            case 'hide':
                this.hideClass(cls.id);
                break;
            case 'use-mapping':
                this.useClassForMapping(`${cls.prefix}:${cls.label}`);
                break;
        }
    }

    selectOntologyClass(classData) {
        this.selectedClass = classData;
        const details = document.getElementById('ontology-details');

        const allProps = this.getAllPropertiesForClass(classData.id);
        const neighbors = this.getNeighbors(classData.id);

        details.innerHTML = `
            <div class="class-details">
                <div class="class-header-detail">
                    <span class="class-badge" style="background: ${this.getClassColor(classData)}">${classData.prefix}:${classData.label}</span>
                </div>
                <p class="class-uri">${classData.uri || ''}</p>
                ${classData.comment ? `<p class="class-comment">${classData.comment}</p>` : ''}

                ${classData.parent ? `<p class="class-parent">Extends: <strong>${classData.parent}</strong></p>` : ''}

                <h5>Data Properties (${allProps.length})</h5>
                <ul class="property-list">
                    ${allProps.length > 0 ? allProps.map(p => `
                        <li class="property-item-small" onclick="yarrrmlBuilder.useProperty('${p.prefix}:${p.name}', '${p.type}')">
                            <span class="prop-name">${p.prefix}:${p.name}</span>
                            <span class="prop-type">${p.type}</span>
                        </li>
                    `).join('') : '<li class="no-props">No data properties defined</li>'}
                </ul>

                <h5>Relationships</h5>
                <ul class="relationship-list">
                    ${this.ontology.objectProperties
                        .filter(r => r.from === classData.id || r.to === classData.id)
                        .map(r => `
                            <li class="rel-item" onclick="yarrrmlBuilder.showRelationship('${r.from}', '${r.to}')">
                                ${r.from === classData.id
                                    ? `<span class="rel-arrow">→</span> <strong>${r.label}</strong> → ${r.to}`
                                    : `${r.from} → <strong>${r.label}</strong> <span class="rel-arrow">→</span>`
                                }
                            </li>
                        `).join('') || '<li class="no-rels">No relationships defined</li>'}
                </ul>

                <div class="class-actions">
                    <button class="btn btn-small btn-primary" onclick="yarrrmlBuilder.useClassForMapping('${classData.prefix}:${classData.label}')">
                        Use in Mapping
                    </button>
                    <button class="btn btn-small" onclick="yarrrmlBuilder.expandClass('${classData.id}')">
                        Expand Neighbors
                    </button>
                </div>
            </div>
        `;
    }

    getAllPropertiesForClass(classId) {
        const props = [];
        const visited = new Set();

        const collectProps = (id) => {
            if (visited.has(id)) return;
            visited.add(id);

            const classProps = this.ontology.dataProperties[id] || [];
            props.push(...classProps);

            const cls = this.ontology.classes.find(c => c.id === id);
            if (cls?.parent) {
                collectProps(cls.parent);
            }
        };

        collectProps(classId);
        return props;
    }

    useClassForMapping(classUri) {
        const classInput = document.getElementById('new-mapping-class');
        const classSearchInput = document.getElementById('new-mapping-class-search');
        if (classInput) {
            classInput.value = classUri;
        }
        if (classSearchInput) {
            classSearchInput.value = classUri;
        }
    }

    useProperty(propertyUri, propType) {
        // If we're on step 4, fill in the form
        const predicateInput = document.getElementById('new-prop-predicate');
        const typeSelect = document.getElementById('new-prop-type');

        if (predicateInput) {
            predicateInput.value = propertyUri;
        }

        if (typeSelect && propType) {
            const typeMap = {
                'string': 'string',
                'integer': 'integer',
                'decimal': 'decimal',
                'date': 'date',
                'dateTime': 'dateTime',
                'boolean': 'boolean',
                'iri': 'iri'
            };
            typeSelect.value = typeMap[propType] || 'string';
        }

        // If not on step 4, switch to it
        if (this.currentStep !== 3) {
            this.currentStep = 3;
            this.renderBuilder();
            // Re-fill after render
            setTimeout(() => {
                const input = document.getElementById('new-prop-predicate');
                const select = document.getElementById('new-prop-type');
                if (input) input.value = propertyUri;
                if (select) select.value = propType || 'string';
            }, 100);
        }
    }

    // Event handlers
    bindWizardEvents() {
        document.getElementById('wizard-prev')?.addEventListener('click', () => this.prevStep());
        document.getElementById('wizard-next')?.addEventListener('click', () => this.nextStep());
    }

    prevStep() {
        if (this.currentStep > 0) {
            this.currentStep--;
            this.renderBuilder();
        }
    }

    nextStep() {
        this.saveCurrentStep();
        if (this.currentStep < this.steps.length - 1) {
            this.currentStep++;
            this.renderBuilder();
        } else {
            this.downloadYAML();
        }
    }

    saveCurrentStep() {
        const step = this.steps[this.currentStep];

        if (step === 'sources') {
            const name = document.getElementById('new-source-name')?.value;
            const type = document.getElementById('new-source-type')?.value;
            const access = document.getElementById('new-source-access')?.value;
            if (name && access) {
                this.mapping.sources[name] = { type, access, columns: this.detectedColumns };
            }
        } else if (step === 'classes') {
            const mappingName = document.getElementById('new-mapping-name')?.value;
            const source = document.getElementById('new-mapping-source')?.value;
            const subject = document.getElementById('new-mapping-subject')?.value;
            const rdfClass = document.getElementById('new-mapping-class')?.value;
            if (mappingName && subject && rdfClass) {
                this.mapping.mappings[mappingName] = {
                    source: source,
                    subject,
                    class: rdfClass,
                    properties: []
                };
            }
        }
    }

    addSource() {
        this.saveCurrentStep();
        this.renderBuilder();
    }

    removeSource(name) {
        delete this.mapping.sources[name];
        this.renderBuilder();
    }

    addPrefix() {
        const key = document.getElementById('new-prefix-key')?.value;
        const uri = document.getElementById('new-prefix-uri')?.value;
        if (key && uri) {
            this.mapping.prefixes[key] = uri;
            this.renderBuilder();
        }
    }

    removePrefix(key) {
        delete this.mapping.prefixes[key];
        this.renderBuilder();
    }

    addClassMapping() {
        this.saveCurrentStep();
        this.renderBuilder();
    }

    removeMapping(name) {
        delete this.mapping.mappings[name];
        this.renderBuilder();
    }

    addPropertyMapping() {
        const tbody = document.getElementById('properties-tbody');
        if (tbody) {
            const emptyRow = tbody.querySelector('.empty-row');
            if (emptyRow) emptyRow.remove();

            const newRow = document.createElement('tr');
            newRow.className = 'property-row';
            newRow.innerHTML = `
                <td><input type="text" class="col-source" placeholder="column"></td>
                <td><input type="text" class="col-predicate" placeholder="prefix:property"></td>
                <td>
                    <select class="col-type">
                        <option value="literal">string</option>
                        <option value="integer">integer</option>
                        <option value="date">date</option>
                        <option value="uri">URI</option>
                    </select>
                </td>
                <td><input type="checkbox" class="col-provenance"></td>
            `;
            tbody.appendChild(newRow);
        }
    }

    copyYAML() {
        const yaml = document.getElementById('yaml-output')?.textContent;
        navigator.clipboard.writeText(yaml);
    }

    downloadYAML() {
        const yaml = this.generateYARRRML();
        const blob = new Blob([yaml], { type: 'text/yaml' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = 'mapping.yarrrml.yaml';
        a.click();
        URL.revokeObjectURL(url);
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
}

// Initialize
const yarrrmlBuilder = new YARRRMLBuilder();

