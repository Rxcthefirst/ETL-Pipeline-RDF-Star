/**
 * Class Explorer — Stardog-style ontology graph exploration
 * Integrates into the existing SPARQL workbench as a third mode.
 */

class ClassExplorer {
    constructor() {
        this.allClasses = [];
        this.graphNodes = new Map();   // uri -> {id, label, type, x, y, ...}
        this.graphLinks = [];          // {source, target, label, type}
        this.individualCache = new Map(); // uri -> {uri, label, type, typeLabel, properties, objectProperties, incomingProperties}
        this.simulation = null;
        this.svg = null;
        this.g = null;
        this.zoom = null;
        this.transform = d3.zoomIdentity;
        this.contextTarget = null;     // node currently right-clicked
        this.initialized = false;
    }

    /* -------------------------------------------------------
       Lifecycle
    ------------------------------------------------------- */

    onActivate() {
        if (!this.initialized) {
            this.init();
        } else {
            this.resizeCanvas();
        }
    }

    init() {
        this.initialized = true;
        this.bindEvents();
        this.initCanvas();
        this.loadAllClasses();
    }

    /* -------------------------------------------------------
       Events
    ------------------------------------------------------- */

    bindEvents() {
        // Search input
        const input = document.getElementById('class-search-input');
        input.addEventListener('input', () => this.onSearchInput());
        input.addEventListener('focus', () => { if (input.value) this.onSearchInput(); });
        document.addEventListener('click', (e) => {
            if (!e.target.closest('#class-search-input') && !e.target.closest('#class-search-dropdown')) {
                document.getElementById('class-search-dropdown').style.display = 'none';
            }
        });

        // Tab switching within class explorer
        document.querySelectorAll('#class-explorer-mode .tab').forEach(tab => {
            tab.addEventListener('click', () => this.switchTab(tab.dataset.tab));
        });

        // Graph controls
        document.getElementById('ce-zoom-in').addEventListener('click', () => this.zoomBy(1.3));
        document.getElementById('ce-zoom-out').addEventListener('click', () => this.zoomBy(0.7));
        document.getElementById('ce-zoom-fit').addEventListener('click', () => this.fitGraph());

        // Close details
        document.getElementById('ce-close-details').addEventListener('click', () => {
            document.getElementById('ce-details-panel').classList.add('collapsed');
        });

        // Context menu items
        document.querySelectorAll('.ce-ctx-item').forEach(item => {
            item.addEventListener('click', () => this.onContextAction(item.dataset.action));
            item.addEventListener('mouseenter', () => item.style.background = 'var(--bg-hover, rgba(255,255,255,0.05))');
            item.addEventListener('mouseleave', () => item.style.background = '');
        });

        // Dismiss context menu
        document.addEventListener('click', (e) => {
            if (!e.target.closest('#ce-context-menu')) {
                document.getElementById('ce-context-menu').style.display = 'none';
            }
        });
    }

    switchTab(tabId) {
        const mode = document.getElementById('class-explorer-mode');
        mode.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
        mode.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
        mode.querySelector(`.tab[data-tab="${tabId}"]`).classList.add('active');
        document.getElementById(`${tabId}-content`).classList.add('active');
    }

    /* -------------------------------------------------------
       Search
    ------------------------------------------------------- */

    async loadAllClasses() {
        try {
            const res = await fetch(`/ontologies?_=${Date.now()}`);
            const data = await res.json();
            this.allClasses = (data.classes || []).map(c => ({
                uri: c.uri,
                label: c.label || c.uri.split('#').pop().split('/').pop()
            }));
            // Deduplicate by URI
            const seen = new Set();
            this.allClasses = this.allClasses.filter(c => {
                if (seen.has(c.uri)) return false;
                seen.add(c.uri);
                return true;
            });
            console.log(`[ClassExplorer] Loaded ${this.allClasses.length} classes`);
        } catch (e) {
            console.error('[ClassExplorer] Failed to load classes', e);
        }
    }

    onSearchInput() {
        const q = document.getElementById('class-search-input').value.trim().toLowerCase();
        const dropdown = document.getElementById('class-search-dropdown');

        if (!q) { dropdown.style.display = 'none'; return; }

        const matches = this.allClasses.filter(c =>
            c.label.toLowerCase().includes(q) || c.uri.toLowerCase().includes(q)
        ).slice(0, 20);

        if (matches.length === 0) {
            dropdown.innerHTML = '<div style="padding:10px 14px;color:var(--text-secondary);font-size:13px;">No classes found</div>';
        } else {
            dropdown.innerHTML = matches.map(c => `
                <div class="ce-search-item" data-uri="${c.uri}" data-label="${c.label}"
                     style="padding:8px 14px;cursor:pointer;font-size:13px;border-bottom:1px solid var(--border-color);">
                    <div style="font-weight:500;color:var(--text-primary);">${this.highlight(c.label, q)}</div>
                    <div style="font-size:11px;color:var(--text-secondary);overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">${c.uri}</div>
                </div>
            `).join('');

            dropdown.querySelectorAll('.ce-search-item').forEach(item => {
                item.addEventListener('click', () => {
                    dropdown.style.display = 'none';
                    document.getElementById('class-search-input').value = item.dataset.label;
                    this.selectClass(item.dataset.uri, item.dataset.label);
                });
                item.addEventListener('mouseenter', () => item.style.background = 'var(--bg-hover, rgba(255,255,255,0.05))');
                item.addEventListener('mouseleave', () => item.style.background = '');
            });
        }
        dropdown.style.display = 'block';
    }

    highlight(text, query) {
        const idx = text.toLowerCase().indexOf(query);
        if (idx < 0) return text;
        return text.slice(0, idx) + '<strong style="color:var(--accent);">' + text.slice(idx, idx + query.length) + '</strong>' + text.slice(idx + query.length);
    }

    /* -------------------------------------------------------
       Select class and load its neighborhood
    ------------------------------------------------------- */

    async selectClass(uri, label) {
        // Clear graph
        this.graphNodes.clear();
        this.graphLinks = [];

        // Add the selected node
        this.graphNodes.set(uri, { id: uri, label: label, type: 'selected' });

        // Fetch neighbors
        await this.addNeighborsFor(uri);

        // Render
        this.renderGraph();
        this.updateTable();
        this.updateJSON();

        // Show properties in right panel
        this.showProperties(uri, label);
    }

    /* -------------------------------------------------------
       API helpers
    ------------------------------------------------------- */

    /**
     * Create a canonical link ID from source, target, and property.
     * Always uses the actual directed source→target so the same edge
     * expanded from either side produces the same key.
     */
    _linkId(source, target, property) {
        return `${source}|${target}|${property}`;
    }

    async addNeighborsFor(uri) {
        try {
            const res = await fetch(`/api/class/neighbors?uri=${encodeURIComponent(uri)}`);
            const data = await res.json();

            for (const n of data.neighbors) {
                if (!this.graphNodes.has(n.uri)) {
                    this.graphNodes.set(n.uri, {
                        id: n.uri,
                        label: n.label,
                        type: n.relType === 'subClassOf' ? 'hierarchy' : 'neighbor'
                    });
                }

                let source, target;
                if (n.direction === 'outgoing' || n.direction === 'subClass') {
                    source = uri; target = n.uri;
                } else {
                    source = n.uri; target = uri;
                }
                const linkId = this._linkId(source, target, n.property);
                if (!this.graphLinks.find(l => l._id === linkId)) {
                    this.graphLinks.push({
                        _id: linkId,
                        source: source,
                        target: target,
                        label: n.propertyLabel || '',
                        type: n.relType
                    });
                }
            }
        } catch (e) {
            console.error('[ClassExplorer] Failed to load neighbors', e);
        }
    }

    async showProperties(uri, label) {
        const panel = document.getElementById('ce-details-panel');
        const content = document.getElementById('ce-details-content');
        panel.classList.remove('collapsed');

        content.innerHTML = '<div style="padding:16px;color:var(--text-secondary);">Loading...</div>';

        try {
            const [propRes, restRes] = await Promise.all([
                fetch(`/api/class/properties?uri=${encodeURIComponent(uri)}`),
                fetch(`/api/class/restrictions?uri=${encodeURIComponent(uri)}`)
            ]);
            const data = await propRes.json();
            const restData = await restRes.json();

            // Build lookup maps from restrictions
            const restrictionsByProp = {};
            for (const r of (restData.restrictions || [])) {
                const key = r.property;
                if (!restrictionsByProp[key]) restrictionsByProp[key] = [];
                restrictionsByProp[key].push(r);
            }
            const charsByProp = {};
            for (const c of (restData.characteristics || [])) {
                charsByProp[c.property] = c;
            }

            let html = `
                <div class="node-info">
                    <div class="node-label">${label}</div>
                    <div class="node-uri">${uri}</div>
                    <span class="node-type">owl:Class</span>
                </div>
            `;

            // Class description
            if (restData.description) {
                html += `<div style="padding:8px 16px 12px;font-size:12px;color:var(--text-secondary);font-style:italic;border-bottom:1px solid var(--border-color);">${restData.description}</div>`;
            }

            // Disjoint classes
            if (restData.disjointWith && restData.disjointWith.length > 0) {
                html += `<div class="properties-section"><h4>${ClassExplorer.icon('disjoint', 14, '#e74c3c')} Disjoint With</h4>`;
                html += `<div style="display:flex;flex-wrap:wrap;gap:6px;padding:4px 0;">`;
                for (const d of restData.disjointWith) {
                    html += `<span style="background:rgba(231,76,60,0.15);color:#e74c3c;padding:3px 10px;border-radius:12px;font-size:11px;border:1px solid rgba(231,76,60,0.3);">${d.label}</span>`;
                }
                html += `</div></div>`;
            }

            if (data.datatype.length > 0) {
                html += `<div class="properties-section"><h4>Datatype Properties</h4>`;
                for (const p of data.datatype) {
                    const restrictions = restrictionsByProp[p.uri] || [];
                    const chars = charsByProp[p.uri];
                    html += this._renderPropertyWithRestrictions(p, 'datatype', restrictions, chars);
                }
                html += `</div>`;
            }

            if (data.object.length > 0) {
                html += `<div class="properties-section"><h4>Object Properties</h4>`;
                for (const p of data.object) {
                    const restrictions = restrictionsByProp[p.uri] || [];
                    const chars = charsByProp[p.uri];
                    html += this._renderPropertyWithRestrictions(p, 'object', restrictions, chars);
                }
                html += `</div>`;
            }

            // Show restrictions on inherited properties (from superclasses)
            const shownProps = new Set([...data.datatype.map(p => p.uri), ...data.object.map(p => p.uri)]);
            const inheritedRestrictions = (restData.restrictions || []).filter(r => !shownProps.has(r.property));
            const grouped = {};
            if (inheritedRestrictions.length > 0) {
                // Group by property
                for (const r of inheritedRestrictions) {
                    if (!grouped[r.property]) grouped[r.property] = { label: r.propertyLabel, restrictions: [] };
                    grouped[r.property].restrictions.push(r);
                }
                html += `<div class="properties-section"><h4>${ClassExplorer.icon('restriction', 14, '#e67e22')} Inherited Restrictions</h4>`;
                for (const [propUri, info] of Object.entries(grouped)) {
                    const chars = charsByProp[propUri];
                    html += this._renderPropertyWithRestrictions(
                        { uri: propUri, label: info.label, range: null },
                        'inherited', info.restrictions, chars
                    );
                }
                html += `</div>`;
            }

            // Property characteristics not yet shown
            const allShownProps = new Set([...shownProps, ...Object.keys(grouped)]);
            const extraChars = (restData.characteristics || []).filter(c => !allShownProps.has(c.property));
            if (extraChars.length > 0) {
                html += `<div class="properties-section"><h4>${ClassExplorer.icon('gear', 14, '#9e9e9e')} Property Characteristics</h4>`;
                for (const c of extraChars) {
                    html += `<div class="property-item"><div class="property-header"><div class="property-main">
                        <div class="property-name">${c.propertyLabel}</div>
                        <div class="property-value-summary">${this._renderTraitBadges(c)}</div>
                    </div></div></div>`;
                }
                html += `</div>`;
            }

            if (data.datatype.length === 0 && data.object.length === 0 && inheritedRestrictions.length === 0) {
                html += '<div style="padding:16px;color:var(--text-secondary);">No properties defined for this class.</div>';
            }

            content.innerHTML = html;
        } catch (e) {
            console.error('[ClassExplorer] showProperties error', e);
            content.innerHTML = `<div style="padding:16px;color:#e74c3c;">Error loading properties.</div>`;
        }
    }

    /**
     * Render a single property row with its OWL restrictions and characteristics.
     */
    _renderPropertyWithRestrictions(prop, propType, restrictions, chars) {
        let rangeDisplay = '';
        if (propType === 'object') {
            rangeDisplay = `→ ${prop.range ? this.shortUri(prop.range) : '?'}`;
        } else if (propType === 'datatype' || propType === 'inherited') {
            rangeDisplay = prop.range ? this.shortUri(prop.range) : '';
        }

        // Collect cardinality and constraint info
        let badges = '';
        for (const r of restrictions) {
            if (r.cardinality) {
                const parts = r.cardinality.split(' ');
                const cardType = parts[0]; // exactly, min, max
                const cardVal = parts[1];
                let icon = '=';
                let color = '#3498db';
                if (cardType === 'min') { icon = '≥'; color = '#2ecc71'; }
                else if (cardType === 'max') { icon = '≤'; color = '#e67e22'; }
                badges += `<span style="background:${color}22;color:${color};padding:1px 6px;border-radius:3px;font-size:10px;font-weight:600;margin-right:4px;" title="${cardType} ${cardVal}">${icon}${cardVal}</span>`;
            }
            if (r.onClass) {
                badges += `<span style="background:rgba(155,89,182,0.15);color:#9b59b6;padding:1px 6px;border-radius:3px;font-size:10px;margin-right:4px;">on ${r.onClassLabel}</span>`;
            }
            if (r.valueConstraints) {
                for (const vc of r.valueConstraints) {
                    badges += `<span style="background:rgba(241,196,15,0.15);color:#f1c40f;padding:1px 6px;border-radius:3px;font-size:10px;margin-right:4px;">${vc}</span>`;
                }
            }
        }

        // Property characteristics (functional, asymmetric, etc.)
        if (chars) {
            badges += this._renderTraitBadges(chars);
        }

        return `<div class="property-item">
            <div class="property-header">
                <div class="property-main">
                    <div class="property-name">${prop.label}</div>
                    <div class="property-value-summary">${rangeDisplay}</div>
                </div>
            </div>
            ${badges ? `<div style="padding:4px 12px 8px;display:flex;flex-wrap:wrap;gap:3px;">${badges}</div>` : ''}
        </div>`;
    }

    /** Render trait badges (Functional, Asymmetric, inverseOf, etc.) */
    _renderTraitBadges(chars) {
        let badges = '';
        for (const t of (chars.traits || [])) {
            badges += `<span style="background:rgba(52,152,219,0.12);color:#3498db;padding:1px 6px;border-radius:3px;font-size:10px;margin-right:4px;">${t}</span>`;
        }
        if (chars.inverseOf) {
            badges += `<span style="background:rgba(46,204,113,0.12);color:#2ecc71;padding:1px 6px;border-radius:3px;font-size:10px;margin-right:4px;">↔ ${this.shortUri(chars.inverseOf)}</span>`;
        }
        return badges;
    }

    async showIndividuals(uri, label) {
        const panel = document.getElementById('ce-details-panel');
        const content = document.getElementById('ce-details-content');
        panel.classList.remove('collapsed');

        content.innerHTML = '<div style="padding:16px;color:var(--text-secondary);">Loading individuals...</div>';

        try {
            const res = await fetch(`/api/class/individuals?uri=${encodeURIComponent(uri)}&limit=20`);
            if (!res.ok) {
                const err = await res.text();
                content.innerHTML = `<div style="padding:16px;color:#e74c3c;">API error (${res.status}): ${err}</div>`;
                return;
            }
            const data = await res.json();

            if (!data || data.detail) {
                content.innerHTML = `<div style="padding:16px;color:#e74c3c;">Error: ${data?.detail || 'Unknown error'}</div>`;
                return;
            }

            // Cache every individual for later use
            for (const ind of data.individuals) {
                this.individualCache.set(ind.uri, ind);
            }

            let html = `
                <div class="node-info">
                    <div class="node-label">${label} — Individuals</div>
                    <div class="node-uri">${data.count} instance(s)</div>
                </div>
            `;

            if (data.inferredClasses && data.inferredClasses.length > 1) {
                html += `<div style="padding:4px 0 12px;font-size:11px;color:var(--text-secondary);">
                    Including subclasses: ${data.inferredClasses.join(', ')}
                </div>`;
            }

            if (data.individuals.length === 0) {
                html += '<div style="padding:16px;color:var(--text-secondary);">No individuals found for this class or its subclasses.</div>';
            } else {
                for (const ind of data.individuals) {
                    const safeLabel = this._escAttr(ind.label);
                    const safeUri = this._escAttr(ind.uri);
                    const safeType = this._escAttr(ind.type || '');
                    html += `<div class="ce-individual-card" style="border:1px solid var(--border-color);border-radius:6px;margin-bottom:10px;overflow:hidden;">
                        <div style="display:flex;align-items:center;justify-content:space-between;padding:10px 14px;background:var(--bg-panel);border-bottom:1px solid var(--border-color);">
                            <div>
                                <div style="font-weight:600;color:var(--text-primary);font-size:13px;">${ind.label}</div>
                                <div style="font-size:10px;color:var(--text-secondary);margin-top:2px;">${ind.typeLabel || ''}</div>
                            </div>
                            <button class="ce-add-individual-btn btn btn-small" data-uri="${safeUri}" data-label="${safeLabel}" data-type="${safeType}"
                                    style="padding:4px 10px;font-size:11px;background:var(--accent);color:var(--bg-dark);border:none;border-radius:4px;cursor:pointer;">
                                + Graph
                            </button>
                        </div>
                        <div style="padding:8px 14px;">
                            <div style="font-size:10px;color:var(--text-secondary);word-break:break-all;margin-bottom:6px;font-family:monospace;">${ind.uri}</div>`;

                    if (ind.properties.length > 0) {
                        for (const prop of ind.properties) {
                            html += `<div style="display:flex;justify-content:space-between;padding:3px 0;font-size:12px;border-bottom:1px solid rgba(255,255,255,0.03);">
                                <span style="color:var(--accent);min-width:120px;">${prop.label || '—'}</span>
                                <span style="color:var(--text-primary);text-align:right;">${prop.value != null ? prop.value : '—'}</span>
                            </div>`;
                        }
                    }

                    if (ind.objectProperties && ind.objectProperties.length > 0) {
                        for (const rel of ind.objectProperties) {
                            html += `<div style="display:flex;justify-content:space-between;padding:3px 0;font-size:12px;border-bottom:1px solid rgba(255,255,255,0.03);">
                                <span style="color:#9b59b6;min-width:120px;">${rel.label || '—'}</span>
                                <span style="color:var(--accent);text-align:right;">→ ${rel.targetLabel || '—'}</span>
                            </div>`;
                        }
                    }

                    if (ind.incomingProperties && ind.incomingProperties.length > 0) {
                        for (const rel of ind.incomingProperties) {
                            html += `<div style="display:flex;justify-content:space-between;padding:3px 0;font-size:12px;border-bottom:1px solid rgba(255,255,255,0.03);">
                                <span style="color:#9b59b6;min-width:120px;">${rel.label || '—'}</span>
                                <span style="color:var(--accent);text-align:right;">← ${rel.sourceLabel || '—'}</span>
                            </div>`;
                        }
                    }

                    if (ind.properties.length === 0 && (!ind.objectProperties || ind.objectProperties.length === 0) && (!ind.incomingProperties || ind.incomingProperties.length === 0)) {
                        html += `<div style="font-size:11px;color:var(--text-secondary);padding:4px 0;">No properties</div>`;
                    }

                    html += `</div></div>`;
                }
            }

            content.innerHTML = html;

            // Bind "add to graph" buttons
            content.querySelectorAll('.ce-add-individual-btn').forEach(btn => {
                btn.addEventListener('click', (e) => {
                    e.stopPropagation();
                    const indUri = btn.dataset.uri;
                    const indLabel = btn.dataset.label;
                    const indType = btn.dataset.type;
                    this.addIndividualToGraph(indUri, indLabel, indType || uri);
                });
            });

        } catch (e) {
            content.innerHTML = `<div style="padding:16px;color:#e74c3c;">Error loading individuals.</div>`;
        }
    }

    async addIndividualToGraph(indUri, indLabel, classUri) {
        // Add the individual node only — no related nodes yet
        if (!this.graphNodes.has(indUri)) {
            this.graphNodes.set(indUri, {
                id: indUri,
                label: indLabel,
                type: 'individual',
                classUri: classUri
            });
        }

        // Fetch relationships for cache (so the panel can show them) but don't add nodes
        await this._ensureIndividualCached(indUri, indLabel);
        const cached = this.individualCache.get(indUri);

        // Auto-connect edges to nodes ALREADY in the graph
        if (cached) {
            for (const rel of (cached.objectProperties || [])) {
                if (this.graphNodes.has(rel.target)) {
                    const linkId = this._linkId(indUri, rel.target, rel.uri);
                    if (!this.graphLinks.find(l => l._id === linkId)) {
                        this.graphLinks.push({ _id: linkId, source: indUri, target: rel.target, label: rel.label, type: 'instanceProperty' });
                    }
                }
            }
            for (const rel of (cached.incomingProperties || [])) {
                if (this.graphNodes.has(rel.source)) {
                    const linkId = this._linkId(rel.source, indUri, rel.uri);
                    if (!this.graphLinks.find(l => l._id === linkId)) {
                        this.graphLinks.push({ _id: linkId, source: rel.source, target: indUri, label: rel.label, type: 'instanceProperty' });
                    }
                }
            }
        }

        // Link to class node via rdf:type if class is in graph
        if (classUri && this.graphNodes.has(classUri)) {
            const typeLink = this._linkId(indUri, classUri, 'rdf:type');
            if (!this.graphLinks.find(l => l._id === typeLink)) {
                this.graphLinks.push({ _id: typeLink, source: indUri, target: classUri, label: 'a', type: 'rdfType' });
            }
        }

        await this._autoLinkTypes();

        this.renderGraph();
        this.updateTable();
        this.updateJSON();

        // Open individual details panel so user can pull in connections one at a time
        this.showIndividualDetails(indUri, indLabel);
    }

    /**
     * Ensure an individual's relationships are cached (data props, object props, incoming).
     * Does NOT add any nodes or edges to the graph.
     */
    async _ensureIndividualCached(indUri, indLabel) {
        const existing = this.individualCache.get(indUri);
        if (existing && existing.objectProperties) return;

        const ind = existing || { uri: indUri, label: indLabel, properties: [] };
        try {
            const dpQ = `PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
                PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
                SELECT DISTINCT ?prop ?value WHERE {
                    GRAPH ?g { <${indUri}> ?prop ?value . FILTER(isLiteral(?value))
                    FILTER(?prop != rdf:type && ?prop != rdfs:label && ?prop != rdfs:comment) }
                }`;
            const dpRes = await fetch('/sparql', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ query: dpQ }) });
            const dpData = await dpRes.json();
            ind.properties = (dpData.results?.bindings || []).map(b => ({
                uri: b.prop?.value || '', label: this.shortUri(b.prop?.value || ''), value: b.value?.value || ''
            }));

            const opQ = `PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
                PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
                SELECT DISTINCT ?prop ?target ?targetLabel WHERE {
                    GRAPH ?g { <${indUri}> ?prop ?target . FILTER(isIRI(?target)) FILTER(?prop != rdf:type) }
                    OPTIONAL { GRAPH ?g2 { ?target rdfs:label ?targetLabel } }
                }`;
            const opRes = await fetch('/sparql', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ query: opQ }) });
            const opData = await opRes.json();
            ind.objectProperties = (opData.results?.bindings || []).map(b => ({
                uri: b.prop?.value, label: this.shortUri(b.prop?.value || ''),
                target: b.target?.value, targetLabel: b.targetLabel?.value || this.shortUri(b.target?.value || '')
            }));

            const ipQ = `PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
                PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
                SELECT DISTINCT ?source ?sourceLabel ?prop WHERE {
                    GRAPH ?g { ?source ?prop <${indUri}> . FILTER(isIRI(?source)) FILTER(?prop != rdf:type) }
                    OPTIONAL { GRAPH ?g2 { ?source rdfs:label ?sourceLabel } }
                }`;
            const ipRes = await fetch('/sparql', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ query: ipQ }) });
            const ipData = await ipRes.json();
            ind.incomingProperties = (ipData.results?.bindings || []).map(b => ({
                uri: b.prop?.value, label: this.shortUri(b.prop?.value || ''),
                source: b.source?.value, sourceLabel: b.sourceLabel?.value || this.shortUri(b.source?.value || '')
            }));

            if (!ind.typeLabel) {
                const tQ = `PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
                    SELECT ?label ?type WHERE {
                        GRAPH ?g { <${indUri}> a ?type . FILTER(!isBlank(?type)) }
                        OPTIONAL { GRAPH ?g2 { <${indUri}> rdfs:label ?label } }
                    } LIMIT 1`;
                const tRes = await fetch('/sparql', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ query: tQ }) });
                const tData = await tRes.json();
                const tb = (tData.results?.bindings || [])[0];
                if (tb) {
                    ind.label = tb.label?.value || ind.label;
                    ind.typeLabel = this.shortUri(tb.type?.value || '');
                }
            }
        } catch (e) {
            console.error('[ClassExplorer] Failed to cache individual', indUri, e);
        }
        this.individualCache.set(indUri, ind);
    }

    /**
     * Pull a single related individual into the graph from a relationship.
     * Auto-connects to any nodes already in the graph.
     */
    async addSingleRelated(fromUri, relatedUri, relatedLabel, propUri, propLabel, direction) {
        if (!this.graphNodes.has(relatedUri)) {
            this.graphNodes.set(relatedUri, {
                id: relatedUri, label: relatedLabel, type: 'individual', classUri: null
            });
        }

        // Add the direct edge
        const source = direction === 'outgoing' ? fromUri : relatedUri;
        const target = direction === 'outgoing' ? relatedUri : fromUri;
        const linkId = this._linkId(source, target, propUri);
        if (!this.graphLinks.find(l => l._id === linkId)) {
            this.graphLinks.push({ _id: linkId, source, target, label: propLabel, type: 'instanceProperty' });
        }

        // Cache the new node's relationships and auto-connect to existing graph nodes
        await this._ensureIndividualCached(relatedUri, relatedLabel);
        const cached = this.individualCache.get(relatedUri);
        if (cached) {
            for (const rel of (cached.objectProperties || [])) {
                if (this.graphNodes.has(rel.target)) {
                    const lk = this._linkId(relatedUri, rel.target, rel.uri);
                    if (!this.graphLinks.find(l => l._id === lk)) {
                        this.graphLinks.push({ _id: lk, source: relatedUri, target: rel.target, label: rel.label, type: 'instanceProperty' });
                    }
                }
            }
            for (const rel of (cached.incomingProperties || [])) {
                if (this.graphNodes.has(rel.source)) {
                    const lk = this._linkId(rel.source, relatedUri, rel.uri);
                    if (!this.graphLinks.find(l => l._id === lk)) {
                        this.graphLinks.push({ _id: lk, source: rel.source, target: relatedUri, label: rel.label, type: 'instanceProperty' });
                    }
                }
            }
        }

        await this._autoLinkTypes();
        this.renderGraph();
        this.updateTable();
        this.updateJSON();

        // Refresh the panel for the original individual to update button states
        this.showIndividualDetails(fromUri, this.graphNodes.get(fromUri)?.label || '');
    }

    /**
     * For individual nodes missing a classUri, query rdf:type and add
     * rdf:type edges to class nodes already in the graph.
     */
    async _autoLinkTypes() {
        const untyped = Array.from(this.graphNodes.values())
            .filter(n => n.type === 'individual' && !n.classUri);
        if (untyped.length === 0) return;

        const uriValues = untyped.map(n => `<${n.id}>`).join(' ');
        try {
            const q = `
                PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
                SELECT DISTINCT ?ind ?type WHERE {
                    VALUES ?ind { ${uriValues} }
                    GRAPH ?g { ?ind a ?type . FILTER(!isBlank(?type)) }
                }`;
            const res = await fetch('/sparql', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ query: q })
            });
            const data = await res.json();

            for (const b of (data.results?.bindings || [])) {
                const indUri = b.ind?.value;
                const typeUri = b.type?.value;
                if (!indUri || !typeUri) continue;

                const node = this.graphNodes.get(indUri);
                if (node) node.classUri = typeUri;

                if (this.graphNodes.has(typeUri)) {
                    const linkId = this._linkId(indUri, typeUri, 'rdf:type');
                    if (!this.graphLinks.find(l => l._id === linkId)) {
                        this.graphLinks.push({
                            _id: linkId,
                            source: indUri,
                            target: typeUri,
                            label: 'a',
                            type: 'rdfType'
                        });
                    }
                }
            }
        } catch (e) {
            console.error('[ClassExplorer] Auto-link types failed', e);
        }
    }

    async showIndividualDetails(uri, label) {
        const panel = document.getElementById('ce-details-panel');
        const content = document.getElementById('ce-details-content');
        panel.classList.remove('collapsed');

        content.innerHTML = '<div style="padding:16px;color:var(--text-secondary);">Loading individual details...</div>';

        try {
            await this._ensureIndividualCached(uri, label);
            const cached = this.individualCache.get(uri);
            await this._renderIndividualDetails(content, cached, uri, label);
        } catch (e) {
            console.error('[ClassExplorer] Failed to load individual details', e);
            content.innerHTML = `<div style="padding:16px;color:#e74c3c;">Error loading individual details.</div>`;
        }
    }

    /**
     * Render individual details into the panel.
     * Fetches RDF-Star annotations and shows accordions on annotated properties.
     */
    async _renderIndividualDetails(container, ind, uri, label) {
        const displayLabel = (ind && ind.label) || label || '—';
        const displayUri = (ind && ind.uri) || uri;
        const displayType = (ind && ind.typeLabel) || 'Individual';

        // Fetch RDF-Star annotations for this individual's triples
        let annotationMap = {}; // key: "propUri|value" -> [{property, value}]
        try {
            const annQ = `
                PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
                SELECT ?prop ?val ?metaProp ?metaValue WHERE {
                    GRAPH ?g {
                        << <${displayUri}> ?prop ?val >> ?metaProp ?metaValue .
                    }
                }`;
            const annRes = await fetch('/sparql', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ query: annQ })
            });
            const annData = await annRes.json();
            for (const b of (annData.results?.bindings || [])) {
                const pUri = b.prop?.value || '';
                const pVal = b.val?.value || '';
                const key = `${pUri}|${pVal}`;
                if (!annotationMap[key]) annotationMap[key] = [];
                annotationMap[key].push({
                    property: this.shortUri(b.metaProp?.value || ''),
                    propertyUri: b.metaProp?.value || '',
                    value: b.metaValue?.value || ''
                });
            }
        } catch (e) {
            console.error('[ClassExplorer] Failed to fetch annotations', e);
        }

        let html = `
            <div class="node-info">
                <div class="node-label">${displayLabel}</div>
                <div class="node-uri">${displayUri}</div>
                <span class="node-type" style="background:#e67e22;">${displayType}</span>
            </div>
        `;

        const dataProps = (ind && (ind.properties || ind.dataProperties)) || [];
        if (dataProps.length > 0) {
            html += `<div class="properties-section"><h4>Data Properties</h4>`;
            for (const p of dataProps) {
                const key = `${p.uri || ''}|${p.value || ''}`;
                const annotations = annotationMap[key] || [];
                const hasAnns = annotations.length > 0;
                const accId = `ann-${Math.random().toString(36).substr(2, 8)}`;

                html += `<div class="property-item">
                    <div class="property-header" ${hasAnns ? `style="cursor:pointer;" onclick="document.getElementById('${accId}').classList.toggle('open')"` : ''}>
                        <div class="property-main">
                            <div class="property-name">${hasAnns ? ClassExplorer.icon('star', 12, '#f1c40f') + ' ' : ''}${p.label || '—'}</div>
                            <div class="property-value-summary">${p.value != null ? p.value : '—'}${hasAnns ? ` <span style="font-size:10px;color:var(--accent);margin-left:4px;">${ClassExplorer.icon('subclass', 10, 'var(--accent)')}</span>` : ''}</div>
                        </div>
                    </div>`;

                if (hasAnns) {
                    html += `<div id="${accId}" class="ce-annotation-accordion">
                        <div class="ce-annotation-body">
                            <div style="font-size:10px;color:var(--text-secondary);margin-bottom:6px;font-weight:600;">How we know this:</div>
                            ${this._renderAnnotationBadges(annotations)}
                        </div>
                    </div>`;
                }
                html += `</div>`;
            }
            html += `</div>`;
        }

        // Object properties (outgoing)
        const objProps = (ind && ind.objectProperties) || [];
        if (objProps.length > 0) {
            html += `<div class="properties-section"><h4>Relationships</h4>`;
            for (const p of objProps) {
                const key = `${p.uri || ''}|${p.target || ''}`;
                const annotations = annotationMap[key] || [];
                const hasAnns = annotations.length > 0;
                const accId = `ann-${Math.random().toString(36).substr(2, 8)}`;
                const inGraph = this.graphNodes.has(p.target);

                html += `<div class="property-item">
                    <div class="property-header" style="display:flex;align-items:center;gap:6px;${hasAnns ? 'cursor:pointer;' : ''}" ${hasAnns ? `onclick="document.getElementById('${accId}').classList.toggle('open')"` : ''}>
                        <div class="property-main" style="flex:1;min-width:0;">
                            <div class="property-name">${hasAnns ? ClassExplorer.icon('star', 12, '#f1c40f') + ' ' : ''}${p.label || '—'}</div>
                            <div class="property-value-summary" style="color:var(--accent);">→ ${p.targetLabel || '—'}${hasAnns ? ` <span style="font-size:10px;margin-left:4px;">${ClassExplorer.icon('subclass', 10, 'var(--accent)')}</span>` : ''}</div>
                        </div>
                        ${inGraph
                            ? `<span style="padding:2px 8px;font-size:10px;color:var(--text-secondary);background:var(--bg-darker);border-radius:3px;white-space:nowrap;">In Graph</span>`
                            : `<button class="ce-pull-related-btn" data-from="${this._escAttr(displayUri)}" data-uri="${this._escAttr(p.target)}" data-label="${this._escAttr(p.targetLabel)}" data-prop="${this._escAttr(p.uri)}" data-prop-label="${this._escAttr(p.label)}" data-dir="outgoing"
                                style="padding:2px 8px;font-size:10px;background:var(--accent);color:var(--bg-dark);border:none;border-radius:3px;cursor:pointer;white-space:nowrap;flex-shrink:0;">+ Graph</button>`
                        }
                    </div>`;

                if (hasAnns) {
                    html += `<div id="${accId}" class="ce-annotation-accordion">
                        <div class="ce-annotation-body">
                            <div style="font-size:10px;color:var(--text-secondary);margin-bottom:6px;font-weight:600;">How we know this:</div>
                            ${this._renderAnnotationBadges(annotations)}
                        </div>
                    </div>`;
                }
                html += `</div>`;
            }
            html += `</div>`;
        }

        // Incoming properties
        const incProps = (ind && ind.incomingProperties) || [];
        if (incProps.length > 0) {
            html += `<div class="properties-section"><h4>Referenced By</h4>`;
            for (const p of incProps) {
                const inGraph = this.graphNodes.has(p.source);
                html += `
                    <div class="property-item">
                        <div class="property-header" style="display:flex;align-items:center;gap:6px;">
                            <div class="property-main" style="flex:1;min-width:0;">
                                <div class="property-name">${p.label || '—'}</div>
                                <div class="property-value-summary" style="color:var(--accent);">← ${p.sourceLabel || '—'}</div>
                            </div>
                            ${inGraph
                                ? `<span style="padding:2px 8px;font-size:10px;color:var(--text-secondary);background:var(--bg-darker);border-radius:3px;white-space:nowrap;">In Graph</span>`
                                : `<button class="ce-pull-related-btn" data-from="${this._escAttr(displayUri)}" data-uri="${this._escAttr(p.source)}" data-label="${this._escAttr(p.sourceLabel)}" data-prop="${this._escAttr(p.uri)}" data-prop-label="${this._escAttr(p.label)}" data-dir="incoming"
                                    style="padding:2px 8px;font-size:10px;background:var(--accent);color:var(--bg-dark);border:none;border-radius:3px;cursor:pointer;white-space:nowrap;flex-shrink:0;">+ Graph</button>`
                            }
                        </div>
                    </div>`;
            }
            html += `</div>`;
        }

        if (dataProps.length === 0 && objProps.length === 0 && incProps.length === 0) {
            html += '<div style="padding:16px;color:var(--text-secondary);">No properties found for this individual.</div>';
        }

        container.innerHTML = html;

        // Bind "+ Graph" buttons for pulling in individual relationships
        container.querySelectorAll('.ce-pull-related-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.stopPropagation();
                this.addSingleRelated(
                    btn.dataset.from,
                    btn.dataset.uri,
                    btn.dataset.label,
                    btn.dataset.prop,
                    btn.dataset.propLabel,
                    btn.dataset.dir
                );
            });
        });
    }

    /**
     * Show details for a clicked edge in the right panel.
     * Queries RDF-Star annotations on the triple and ontology provenance.
     */
    async showEdgeDetails(d) {
        const panel = document.getElementById('ce-details-panel');
        const content = document.getElementById('ce-details-content');
        panel.classList.remove('collapsed');

        const sourceId = typeof d.source === 'object' ? d.source.id : d.source;
        const targetId = typeof d.target === 'object' ? d.target.id : d.target;
        const propUri = d._id ? d._id.split('|')[2] : '';
        const sourceLabel = (typeof d.source === 'object' ? d.source.label : this.graphNodes.get(sourceId)?.label) || this.shortUri(sourceId);
        const targetLabel = (typeof d.target === 'object' ? d.target.label : this.graphNodes.get(targetId)?.label) || this.shortUri(targetId);

        content.innerHTML = '<div style="padding:16px;color:var(--text-secondary);">Loading edge details...</div>';

        let html = `
            <div class="node-info">
                <div class="node-label">${d.label || this.shortUri(propUri)}</div>
                <div class="node-uri" style="font-size:10px;">${propUri}</div>
                <span class="node-type" style="background:#4fc3f7;">Edge</span>
            </div>
            <div class="properties-section"><h4>Connection</h4>
                <div class="property-item">
                    <div class="property-header"><div class="property-main">
                        <div class="property-name">Source</div>
                        <div class="property-value-summary">${sourceLabel}</div>
                    </div></div>
                </div>
                <div class="property-item">
                    <div class="property-header"><div class="property-main">
                        <div class="property-name">Target</div>
                        <div class="property-value-summary">${targetLabel}</div>
                    </div></div>
                </div>
                <div class="property-item">
                    <div class="property-header"><div class="property-main">
                        <div class="property-name">Type</div>
                        <div class="property-value-summary">${d.type}</div>
                    </div></div>
                </div>
            </div>`;

        // Query RDF-Star annotations on this edge
        // For instance property edges: << source prop target >> ?metaProp ?metaValue
        // For ontological edges: << prop a owl:ObjectProperty >> ?metaProp ?metaValue
        try {
            let annotations = [];

            if (d.type === 'instanceProperty') {
                // Instance-level: annotate the specific triple
                const annQ = `
                    PREFIX ex: <http://example.org/movieApp#>
                    SELECT ?metaProp ?metaValue WHERE {
                        GRAPH ?g {
                            << <${sourceId}> <${propUri}> <${targetId}> >> ?metaProp ?metaValue .
                        }
                    }`;
                const annRes = await fetch('/sparql', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ query: annQ })
                });
                const annData = await annRes.json();
                annotations = (annData.results?.bindings || []).map(b => ({
                    property: this.shortUri(b.metaProp?.value || ''),
                    propertyUri: b.metaProp?.value || '',
                    value: b.metaValue?.value || ''
                }));
            }

            // Ontology provenance: << prop a owl:ObjectProperty >> annotations
            const ontoQ = `
                PREFIX owl: <http://www.w3.org/2002/07/owl#>
                SELECT ?metaProp ?metaValue WHERE {
                    GRAPH ?g {
                        {
                            << <${propUri}> a owl:ObjectProperty >> ?metaProp ?metaValue .
                        } UNION {
                            << <${propUri}> a owl:DatatypeProperty >> ?metaProp ?metaValue .
                        }
                    }
                }`;
            const ontoRes = await fetch('/sparql', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ query: ontoQ })
            });
            const ontoData = await ontoRes.json();
            const ontologyAnnotations = (ontoData.results?.bindings || []).map(b => ({
                property: this.shortUri(b.metaProp?.value || ''),
                propertyUri: b.metaProp?.value || '',
                value: b.metaValue?.value || ''
            }));

            if (annotations.length > 0) {
                html += `<div class="properties-section"><h4>${ClassExplorer.icon('star', 14, '#f1c40f')} RDF-Star Annotations</h4>`;
                html += this._renderAnnotationBadges(annotations);
                html += `</div>`;
            }

            if (ontologyAnnotations.length > 0) {
                html += `<div class="properties-section"><h4>${ClassExplorer.icon('ontology', 14, '#2ecc71')} Ontology Provenance</h4>`;
                html += this._renderAnnotationBadges(ontologyAnnotations);
                html += `</div>`;
            }

            if (annotations.length === 0 && ontologyAnnotations.length === 0) {
                html += '<div style="padding:12px 16px;color:var(--text-secondary);font-size:12px;">No RDF-Star annotations on this edge.</div>';
            }

        } catch (e) {
            console.error('[ClassExplorer] Failed to load edge annotations', e);
            html += '<div style="padding:12px 16px;color:#e74c3c;font-size:12px;">Error loading annotations.</div>';
        }

        content.innerHTML = html;
    }

    /** Render a list of annotation key/value pairs as styled badges. */
    _renderAnnotationBadges(annotations) {
        const iconMap = {
            'governanceSource': ClassExplorer.icon('source', 14, '#3498db'),
            'confidence': ClassExplorer.icon('confidence', 14, '#2ecc71'),
            'annotatedAt': ClassExplorer.icon('timestamp', 14, '#9b59b6'),
            'curatedBy': ClassExplorer.icon('curated', 14, '#e67e22'),
            'definedByOntology': ClassExplorer.icon('ontology', 14, '#2ecc71')
        };
        const defaultIcon = ClassExplorer.icon('info', 14, '#9e9e9e');
        let html = '';
        for (const a of annotations) {
            const icon = iconMap[a.property] || defaultIcon;
            let displayVal = a.value;
            // Shorten URIs
            if (displayVal.startsWith('http')) displayVal = this.shortUri(displayVal);
            // Format confidence as percentage
            if (a.property === 'confidence') {
                const pct = parseFloat(a.value);
                if (!isNaN(pct)) displayVal = `${(pct * 100).toFixed(0)}%`;
            }
            // Format timestamps
            if (a.property === 'annotatedAt' && a.value.includes('T')) {
                displayVal = a.value.replace('T', ' ').replace(/:\d{2}$/, '');
            }
            html += `
                <div style="display:flex;align-items:center;gap:8px;padding:6px 12px;margin:4px 0;background:rgba(52,152,219,0.08);border-radius:4px;border-left:3px solid var(--accent);">
                    <span style="font-size:14px;">${icon}</span>
                    <span style="font-size:11px;color:var(--accent);min-width:100px;font-weight:500;">${a.property}</span>
                    <span style="font-size:12px;color:var(--text-primary);">${displayVal}</span>
                </div>`;
        }
        return html;
    }

    /* -------------------------------------------------------
       Context menu
    ------------------------------------------------------- */

    showContextMenu(event, nodeData) {
        event.preventDefault();
        this.contextTarget = nodeData;
        const menu = document.getElementById('ce-context-menu');
        const isIndividual = nodeData.type === 'individual';

        // Show/hide menu items based on node type
        const individualActions = new Set(['view-individual-details', 'expand-connections', 'link-to-types', 'remove-node']);
        const classActions = new Set(['add-neighbors', 'add-superclasses', 'add-subclasses', 'load-individuals', 'view-properties', 'remove-node']);

        menu.querySelectorAll('.ce-ctx-item').forEach(item => {
            const action = item.dataset.action;
            if (isIndividual) {
                item.style.display = individualActions.has(action) ? 'flex' : 'none';
            } else {
                item.style.display = classActions.has(action) ? 'flex' : 'none';
            }
        });

        menu.style.display = 'block';
        menu.style.left = event.clientX + 'px';
        menu.style.top = event.clientY + 'px';
    }

    async onContextAction(action) {
        document.getElementById('ce-context-menu').style.display = 'none';
        if (!this.contextTarget) return;

        const uri = this.contextTarget.id;
        const label = this.contextTarget.label;

        switch (action) {
            case 'add-neighbors':
                await this.addNeighborsFor(uri);
                this.renderGraph();
                this.updateTable();
                this.updateJSON();
                break;

            case 'add-superclasses':
                await this.addFilteredNeighbors(uri, 'superClass');
                this.renderGraph();
                this.updateTable();
                this.updateJSON();
                break;

            case 'add-subclasses':
                await this.addFilteredNeighbors(uri, 'subClass');
                this.renderGraph();
                this.updateTable();
                this.updateJSON();
                break;

            case 'load-individuals':
                this.showIndividuals(uri, label);
                break;

            case 'view-properties':
                this.showProperties(uri, label);
                break;

            case 'view-individual-details':
                this.showIndividualDetails(uri, label);
                break;

            case 'expand-connections':
                await this.expandIndividualConnections(uri, label);
                break;

            case 'link-to-types':
                await this.linkIndividualsToTypes();
                break;

            case 'remove-node':
                this.removeNode(uri);
                break;
        }
    }

    async addFilteredNeighbors(uri, directionFilter) {
        try {
            const res = await fetch(`/api/class/neighbors?uri=${encodeURIComponent(uri)}`);
            const data = await res.json();

            for (const n of data.neighbors) {
                if (n.direction !== directionFilter) continue;

                if (!this.graphNodes.has(n.uri)) {
                    this.graphNodes.set(n.uri, {
                        id: n.uri,
                        label: n.label,
                        type: 'hierarchy'
                    });
                }

                let source, target;
                if (n.direction === 'subClass') {
                    source = uri; target = n.uri;
                } else {
                    source = n.uri; target = uri;
                }
                const linkId = this._linkId(source, target, n.property);
                if (!this.graphLinks.find(l => l._id === linkId)) {
                    this.graphLinks.push({
                        _id: linkId,
                        source: source,
                        target: target,
                        label: n.propertyLabel || 'subClassOf',
                        type: n.relType
                    });
                }
            }
        } catch (e) {
            console.error('[ClassExplorer] Failed to add filtered neighbors', e);
        }
    }

    removeNode(uri) {
        this.graphNodes.delete(uri);
        this.graphLinks = this.graphLinks.filter(l => {
            const sId = typeof l.source === 'object' ? l.source.id : l.source;
            const tId = typeof l.target === 'object' ? l.target.id : l.target;
            return sId !== uri && tId !== uri;
        });
        this.renderGraph();
        this.updateTable();
        this.updateJSON();
    }

    /**
     * Expand ALL connections for an individual — pulls every related node into the graph.
     * This is the explicit "Expand Connections" context menu action.
     */
    async expandIndividualConnections(uri, label) {
        await this._ensureIndividualCached(uri, label || this.graphNodes.get(uri)?.label || '');
        const cached = this.individualCache.get(uri);
        if (!cached) return;

        for (const rel of (cached.objectProperties || [])) {
            if (!this.graphNodes.has(rel.target)) {
                this.graphNodes.set(rel.target, { id: rel.target, label: rel.targetLabel, type: 'individual', classUri: null });
            }
            const linkId = this._linkId(uri, rel.target, rel.uri);
            if (!this.graphLinks.find(l => l._id === linkId)) {
                this.graphLinks.push({ _id: linkId, source: uri, target: rel.target, label: rel.label, type: 'instanceProperty' });
            }
        }
        for (const rel of (cached.incomingProperties || [])) {
            if (!this.graphNodes.has(rel.source)) {
                this.graphNodes.set(rel.source, { id: rel.source, label: rel.sourceLabel, type: 'individual', classUri: null });
            }
            const linkId = this._linkId(rel.source, uri, rel.uri);
            if (!this.graphLinks.find(l => l._id === linkId)) {
                this.graphLinks.push({ _id: linkId, source: rel.source, target: uri, label: rel.label, type: 'instanceProperty' });
            }
        }

        await this._autoLinkTypes();
        this.renderGraph();
        this.updateTable();
        this.updateJSON();
    }

    /**
     * For every individual node in the graph, query its rdf:type and
     * add an rdf:type edge to the class node if that class is in the graph.
     */
    async linkIndividualsToTypes() {
        const individuals = Array.from(this.graphNodes.values()).filter(n => n.type === 'individual');
        if (individuals.length === 0) return;

        const uriValues = individuals.map(n => `<${n.id}>`).join(' ');
        const q = `
            PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
            SELECT DISTINCT ?ind ?type WHERE {
                VALUES ?ind { ${uriValues} }
                GRAPH ?g { ?ind a ?type . FILTER(!isBlank(?type)) }
            }`;

        try {
            const res = await fetch('/sparql', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ query: q })
            });
            const data = await res.json();

            for (const b of (data.results?.bindings || [])) {
                const indUri = b.ind?.value;
                const typeUri = b.type?.value;
                if (!indUri || !typeUri) continue;

                // Store the classUri on the individual node
                const node = this.graphNodes.get(indUri);
                if (node && !node.classUri) node.classUri = typeUri;

                // If the class node is in the graph, add an rdf:type edge
                if (this.graphNodes.has(typeUri)) {
                    const linkId = this._linkId(indUri, typeUri, 'rdf:type');
                    if (!this.graphLinks.find(l => l._id === linkId)) {
                        this.graphLinks.push({
                            _id: linkId,
                            source: indUri,
                            target: typeUri,
                            label: 'a',
                            type: 'rdfType'
                        });
                    }
                }
            }
        } catch (e) {
            console.error('[ClassExplorer] Failed to link individuals to types', e);
        }

        this.renderGraph();
        this.updateTable();
        this.updateJSON();
    }

    /* -------------------------------------------------------
       D3 Graph
    ------------------------------------------------------- */

    initCanvas() {
        this.svg = d3.select('#ce-graph-canvas');
        this.g = this.svg.append('g').attr('class', 'ce-graph-content');

        this.zoom = d3.zoom()
            .scaleExtent([0.1, 4])
            .on('zoom', (event) => {
                this.transform = event.transform;
                this.g.attr('transform', event.transform);
            });

        this.svg.call(this.zoom);

        // Arrow markers
        const defs = this.svg.append('defs');
        const markerColors = {
            'property': '#4fc3f7',
            'subclass': '#2ecc71',
            'instance': '#e67e22',
            'rdftype': '#9b59b6'
        };
        Object.entries(markerColors).forEach(([type, color]) => {
            defs.append('marker')
                .attr('id', `ce-arrow-${type}`)
                .attr('viewBox', '-0 -5 10 10')
                .attr('refX', 28)
                .attr('refY', 0)
                .attr('orient', 'auto')
                .attr('markerWidth', 6)
                .attr('markerHeight', 6)
                .append('path')
                .attr('d', 'M 0,-5 L 10,0 L 0,5')
                .attr('fill', color);
        });

        this.resizeCanvas();
    }

    resizeCanvas() {
        const container = document.getElementById('ce-graph-container');
        if (!container) return;
        const w = container.clientWidth || 800;
        const h = container.clientHeight || 500;
        this.svg.attr('width', w).attr('height', h);
    }

    renderGraph() {
        this.resizeCanvas();
        this.g.selectAll('*').remove();

        const nodes = Array.from(this.graphNodes.values());
        const links = this.graphLinks.map(l => ({
            ...l,
            source: typeof l.source === 'object' ? l.source.id : l.source,
            target: typeof l.target === 'object' ? l.target.id : l.target
        })).filter(l => this.graphNodes.has(l.source) && this.graphNodes.has(l.target));

        if (nodes.length === 0) return;

        const w = parseInt(this.svg.attr('width')) || 800;
        const h = parseInt(this.svg.attr('height')) || 500;

        // Build adjacency for adaptive placement of new nodes
        const adjacency = {};
        for (const l of links) {
            const s = typeof l.source === 'object' ? l.source.id : l.source;
            const t = typeof l.target === 'object' ? l.target.id : l.target;
            if (!adjacency[s]) adjacency[s] = [];
            if (!adjacency[t]) adjacency[t] = [];
            adjacency[s].push(t);
            adjacency[t].push(s);
        }

        // Position new nodes near their connected settled neighbors
        for (const n of nodes) {
            if (n.x != null) continue; // already positioned
            const neighbors = (adjacency[n.id] || [])
                .map(id => this.graphNodes.get(id))
                .filter(nb => nb && nb.x != null);
            if (neighbors.length > 0) {
                let cx = 0, cy = 0;
                for (const nb of neighbors) { cx += nb.x; cy += nb.y; }
                cx /= neighbors.length;
                cy /= neighbors.length;
                const angle = Math.random() * Math.PI * 2;
                n.x = cx + Math.cos(angle) * 120;
                n.y = cy + Math.sin(angle) * 120;
            } else {
                n.x = w / 2 + (Math.random() - 0.5) * 200;
                n.y = h / 2 + (Math.random() - 0.5) * 200;
            }
            // New nodes are NOT fixed — simulation will settle them
            n.fx = null;
            n.fy = null;
        }

        // Count parallel edges for bezier offsets
        const pairCounts = {};
        const pairIndex = {};
        links.forEach(l => {
            const key = [l.source, l.target].sort().join('|||');
            pairCounts[key] = (pairCounts[key] || 0) + 1;
        });
        links.forEach(l => {
            const sorted = [l.source, l.target].sort();
            const key = sorted.join('|||');
            if (!pairIndex[key]) pairIndex[key] = 0;
            l._pairTotal = pairCounts[key];
            l._pairIdx = pairIndex[key]++;
            l._flipped = (l.source !== sorted[0]);
        });

        // --- Edge / label geometry functions (MUST be before drag handler) ---
        const edgePathFn = d => {
            const sx = d.source.x, sy = d.source.y;
            const tx = d.target.x, ty = d.target.y;
            if (d._pairTotal <= 1) return `M${sx},${sy}L${tx},${ty}`;
            const cx0 = d._flipped ? tx : sx, cy0 = d._flipped ? ty : sy;
            const cx1 = d._flipped ? sx : tx, cy1 = d._flipped ? sy : ty;
            const ddx = cx1 - cx0, ddy = cy1 - cy0;
            const dist = Math.sqrt(ddx * ddx + ddy * ddy) || 1;
            const px = -ddy / dist, py = ddx / dist;
            const offset = (d._pairIdx - (d._pairTotal - 1) / 2) * 40;
            const mx = (sx + tx) / 2 + px * offset;
            const my = (sy + ty) / 2 + py * offset;
            return `M${sx},${sy}Q${mx},${my} ${tx},${ty}`;
        };
        const edgeLabelXFn = d => {
            if (d._pairTotal <= 1) return (d.source.x + d.target.x) / 2;
            const cx0 = d._flipped ? d.target.x : d.source.x;
            const cy0 = d._flipped ? d.target.y : d.source.y;
            const cx1 = d._flipped ? d.source.x : d.target.x;
            const cy1 = d._flipped ? d.source.y : d.target.y;
            const ddx = cx1 - cx0, ddy = cy1 - cy0;
            const dist = Math.sqrt(ddx * ddx + ddy * ddy) || 1;
            const px = -ddy / dist;
            const offset = (d._pairIdx - (d._pairTotal - 1) / 2) * 40;
            return (d.source.x + d.target.x) / 2 + px * offset;
        };
        const edgeLabelYFn = d => {
            if (d._pairTotal <= 1) return (d.source.y + d.target.y) / 2 - 6;
            const cx0 = d._flipped ? d.target.x : d.source.x;
            const cy0 = d._flipped ? d.target.y : d.source.y;
            const cx1 = d._flipped ? d.source.x : d.target.x;
            const cy1 = d._flipped ? d.source.y : d.target.y;
            const ddx = cx1 - cx0, ddy = cy1 - cy0;
            const dist = Math.sqrt(ddx * ddx + ddy * ddy) || 1;
            const py = ddx / dist;
            const offset = (d._pairIdx - (d._pairTotal - 1) / 2) * 40;
            return (d.source.y + d.target.y) / 2 + py * offset - 6;
        };

        // --- Simulation ---
        if (this.simulation) this.simulation.stop();
        this.simulation = d3.forceSimulation(nodes)
            .force('link', d3.forceLink(links).id(d => d.id).distance(160))
            .force('charge', d3.forceManyBody().strength(-400))
            .force('collision', d3.forceCollide(50))
            .alphaDecay(0.05);

        // Only use center force on first layout when nothing is settled yet
        if (!nodes.some(n => n.fx != null)) {
            this.simulation.force('center', d3.forceCenter(w / 2, h / 2));
        }

        const self = this;

        // --- Edges ---
        const edgeGroup = this.g.append('g');
        const edges = edgeGroup.selectAll('path')
            .data(links).enter().append('path')
            .attr('fill', 'none')
            .attr('stroke', d => {
                if (d.type === 'subClassOf') return '#2ecc71';
                if (d.type === 'rdfType') return '#9b59b6';
                if (d.type === 'instanceProperty') return '#e67e22';
                return '#4fc3f7';
            })
            .attr('stroke-width', d => d.type === 'rdfType' ? 1.5 : 2)
            .attr('stroke-dasharray', d => d.type === 'rdfType' ? '5,3' : null)
            .attr('marker-end', d => {
                if (d.type === 'subClassOf') return 'url(#ce-arrow-subclass)';
                if (d.type === 'rdfType') return 'url(#ce-arrow-rdftype)';
                if (d.type === 'instanceProperty') return 'url(#ce-arrow-instance)';
                return 'url(#ce-arrow-property)';
            });

        const edgeHitAreas = edgeGroup.selectAll('.ce-edge-hit')
            .data(links).enter().append('path')
            .attr('class', 'ce-edge-hit')
            .attr('fill', 'none')
            .attr('stroke', 'transparent')
            .attr('stroke-width', 14)
            .style('cursor', 'pointer')
            .on('click', (event, d) => {
                event.stopPropagation();
                self.showEdgeDetails(d);
            });

        const edgeLabels = this.g.append('g').selectAll('text')
            .data(links).enter().append('text')
            .attr('font-size', 10)
            .attr('fill', '#9e9e9e')
            .attr('text-anchor', 'middle')
            .style('cursor', 'pointer')
            .text(d => d.label)
            .on('click', (event, d) => {
                event.stopPropagation();
                self.showEdgeDetails(d);
            });

        // --- Node groups (drag uses edgePathFn etc. which are already declared above) ---
        const nodeGroups = this.g.append('g').selectAll('g')
            .data(nodes).enter().append('g')
            .style('cursor', 'pointer')
            .call(d3.drag()
                .on('start', (event, d) => {
                    d.fx = d.x;
                    d.fy = d.y;
                })
                .on('drag', (event, d) => {
                    d.fx = event.x;
                    d.fy = event.y;
                    d.x = event.x;
                    d.y = event.y;
                    // Update this node visually
                    nodeGroups.filter(n => n.id === d.id)
                        .attr('transform', `translate(${event.x},${event.y})`);
                    // Re-draw edges (they reference node objects whose x/y changed)
                    edges.attr('d', edgePathFn);
                    edgeHitAreas.attr('d', edgePathFn);
                    edgeLabels.attr('x', edgeLabelXFn).attr('y', edgeLabelYFn);
                })
                .on('end', (event, d) => {
                    d.fx = event.x;
                    d.fy = event.y;
                })
            )
            .on('click', (event, d) => {
                event.stopPropagation();
                if (d.type === 'individual') {
                    self.showIndividualDetails(d.id, d.label);
                } else {
                    self.graphNodes.forEach(n => { if (n.type === 'selected') n.type = 'neighbor'; });
                    d.type = 'selected';
                    self.showProperties(d.id, d.label);
                    self.renderGraph();
                }
            })
            .on('contextmenu', (event, d) => {
                event.stopPropagation();
                self.showContextMenu(event, d);
            });

        // Node shapes
        nodeGroups.each(function(d) {
            const el = d3.select(this);
            if (d.type === 'individual') {
                el.append('rect')
                    .attr('width', 36).attr('height', 36)
                    .attr('x', -18).attr('y', -18)
                    .attr('rx', 4)
                    .attr('transform', 'rotate(45)')
                    .attr('fill', '#e67e22')
                    .attr('stroke', '#fff')
                    .attr('stroke-width', 2);
            } else {
                el.append('circle')
                    .attr('r', 25)
                    .attr('fill', () => {
                        if (d.type === 'selected') return '#3498db';
                        if (d.type === 'hierarchy') return '#2ecc71';
                        return '#4fc3f7';
                    })
                    .attr('stroke', '#fff')
                    .attr('stroke-width', 2);
            }
        });

        nodeGroups.append('text')
            .attr('dy', 5)
            .attr('text-anchor', 'middle')
            .attr('fill', d => d.type === 'individual' ? '#fff' : '#1a1a2e')
            .attr('font-size', d => d.type === 'individual' ? 13 : 16)
            .attr('font-weight', 'bold')
            .attr('pointer-events', 'none')
            .text(d => d.label.charAt(0).toUpperCase());

        nodeGroups.append('text')
            .attr('dy', d => d.type === 'individual' ? 38 : 42)
            .attr('text-anchor', 'middle')
            .attr('fill', '#e0e0e0')
            .attr('font-size', 11)
            .attr('pointer-events', 'none')
            .text(d => d.label.length > 20 ? d.label.slice(0, 18) + '…' : d.label);

        // --- Tick handler ---
        this.simulation.on('tick', () => {
            edges.attr('d', edgePathFn);
            edgeHitAreas.attr('d', edgePathFn);
            edgeLabels.attr('x', edgeLabelXFn).attr('y', edgeLabelYFn);
            nodeGroups.attr('transform', d => `translate(${d.x},${d.y})`);
        });

        // When simulation settles, pin all nodes in place
        this.simulation.on('end', () => {
            nodes.forEach(n => { n.fx = n.x; n.fy = n.y; });
        });
    }

    /* -------------------------------------------------------
       Table + JSON views
    ------------------------------------------------------- */

    updateTable() {
        const container = document.getElementById('ce-table-container');
        const nodes = Array.from(this.graphNodes.values());
        if (nodes.length === 0) {
            container.innerHTML = '<div class="empty-state"><h3>No Class Selected</h3><p>Search for a class above.</p></div>';
            return;
        }

        let html = `<div style="overflow-x:auto;"><table style="width:100%;border-collapse:collapse;font-size:13px;">
            <thead><tr style="background:var(--bg-darker);border-bottom:2px solid var(--border-color);">
                <th style="padding:10px 12px;text-align:left;color:var(--text-primary);">Label</th>
                <th style="padding:10px 12px;text-align:left;color:var(--text-primary);">Role</th>
                <th style="padding:10px 12px;text-align:left;color:var(--text-primary);">URI</th>
            </tr></thead><tbody>`;

        for (const n of nodes) {
            const color = n.type === 'selected' ? '#3498db' : n.type === 'hierarchy' ? '#2ecc71' : n.type === 'individual' ? '#e67e22' : '#4fc3f7';
            html += `<tr style="border-bottom:1px solid var(--border-color);">
                <td style="padding:8px 12px;color:var(--text-primary);">${n.label}</td>
                <td style="padding:8px 12px;"><span style="background:${color};color:#fff;padding:2px 8px;border-radius:3px;font-size:11px;">${n.type}</span></td>
                <td style="padding:8px 12px;color:var(--text-secondary);font-size:11px;word-break:break-all;">${n.id}</td>
            </tr>`;
        }
        html += '</tbody></table></div>';
        container.innerHTML = html;
    }

    updateJSON() {
        const output = document.getElementById('ce-json-output');
        const data = {
            nodes: Array.from(this.graphNodes.values()).map(n => ({ uri: n.id, label: n.label, type: n.type })),
            links: this.graphLinks.map(l => ({
                source: typeof l.source === 'object' ? l.source.id : l.source,
                target: typeof l.target === 'object' ? l.target.id : l.target,
                label: l.label,
                type: l.type
            }))
        };
        output.textContent = JSON.stringify(data, null, 2);
    }

    /* -------------------------------------------------------
       Zoom helpers
    ------------------------------------------------------- */

    zoomBy(factor) {
        const t = this.transform.scale(factor);
        this.svg.transition().duration(300).call(this.zoom.transform, t);
    }

    fitGraph() {
        this.svg.transition().duration(300).call(this.zoom.transform, d3.zoomIdentity);
    }

    /* -------------------------------------------------------
       Utility
    ------------------------------------------------------- */

    shortUri(uri) {
        const parts = uri.split(/[#/]/);
        return parts[parts.length - 1] || uri;
    }

    /** Escape a string for safe use inside an HTML attribute (double-quoted). */
    _escAttr(s) {
        if (s == null) return '';
        return String(s).replace(/&/g, '&amp;').replace(/"/g, '&quot;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
    }

    /** Inline SVG icon helper. Returns an SVG string sized to `size`px. */
    static icon(name, size = 14, color = 'currentColor') {
        const icons = {
            // Governance / annotations
            'source':       `<path d="M3 3h18v2H3V3zm0 4h18v2H3V7zm0 4h12v2H3v-2zm0 4h18v2H3v-2z"/>`,
            'confidence':   `<path d="M3 3v18h18V3H3zm4 14H5v-4h2v4zm4 0H9V7h2v10zm4 0h-2v-6h2v6zm4 0h-2V5h2v12z"/>`,
            'timestamp':    `<path d="M12 2C6.5 2 2 6.5 2 12s4.5 10 10 10 10-4.5 10-10S17.5 2 12 2zm0 18c-4.4 0-8-3.6-8-8s3.6-8 8-8 8 3.6 8 8-3.6 8-8 8zm.5-13H11v6l5.2 3.2.8-1.3-4.5-2.7V7z"/>`,
            'curated':      `<path d="M12 12c2.2 0 4-1.8 4-4s-1.8-4-4-4-4 1.8-4 4 1.8 4 4 4zm0 2c-2.7 0-8 1.3-8 4v2h16v-2c0-2.7-5.3-4-8-4z"/>`,
            'ontology':     `<path d="M19 3H5c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h14c1.1 0 2-.9 2-2V5c0-1.1-.9-2-2-2zm-5 14H7v-2h7v2zm3-4H7v-2h10v2zm0-4H7V7h10v2z"/>`,
            // Structure / navigation
            'disjoint':     `<path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zM4 12c0-4.42 3.58-8 8-8 1.85 0 3.55.63 4.9 1.69L5.69 16.9A7.902 7.902 0 0 1 4 12zm8 8c-1.85 0-3.55-.63-4.9-1.69L18.31 7.1A7.902 7.902 0 0 1 20 12c0 4.42-3.58 8-8 8z"/>`,
            'restriction':  `<path d="M14.4 6L14 4H5v17h2v-7h5.6l.4 2h7V6h-5.6z"/>`,
            'gear':         `<path d="M19.14 12.94c.04-.3.06-.61.06-.94 0-.32-.02-.64-.07-.94l2.03-1.58a.49.49 0 0 0 .12-.61l-1.92-3.32a.49.49 0 0 0-.59-.22l-2.39.96c-.5-.38-1.03-.7-1.62-.94l-.36-2.54a.484.484 0 0 0-.48-.41h-3.84c-.24 0-.43.17-.47.41l-.36 2.54c-.59.24-1.13.57-1.62.94l-2.39-.96c-.22-.08-.47 0-.59.22L2.74 8.87c-.12.21-.08.47.12.61l2.03 1.58c-.05.3-.07.62-.07.94s.02.64.07.94l-2.03 1.58a.49.49 0 0 0-.12.61l1.92 3.32c.12.22.37.29.59.22l2.39-.96c.5.38 1.03.7 1.62.94l.36 2.54c.05.24.24.41.48.41h3.84c.24 0 .44-.17.47-.41l.36-2.54c.59-.24 1.13-.56 1.62-.94l2.39.96c.22.08.47 0 .59-.22l1.92-3.32c.12-.22.07-.47-.12-.61l-2.01-1.58zM12 15.6A3.6 3.6 0 1 1 12 8.4a3.6 3.6 0 0 1 0 7.2z"/>`,
            'star':         `<path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z"/>`,
            'info':         `<path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm1 15h-2v-6h2v6zm0-8h-2V7h2v2z"/>`,
            // Context menu
            'neighbors':    `<path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-1 17.93c-3.95-.49-7-3.85-7-7.93 0-.62.08-1.21.21-1.79L9 15v1c0 1.1.9 2 2 2v1.93zm6.9-2.54c-.26-.81-1-1.39-1.9-1.39h-1v-3c0-.55-.45-1-1-1H8v-2h2c.55 0 1-.45 1-1V7h2c1.1 0 2-.9 2-2v-.41c2.93 1.19 5 4.06 5 7.41 0 2.08-.8 3.97-2.1 5.39z"/>`,
            'superclass':   `<path d="M7 14l5-5 5 5H7z"/>`,
            'subclass':     `<path d="M7 10l5 5 5-5H7z"/>`,
            'individual':   `<path d="M12 12c2.2 0 4-1.8 4-4s-1.8-4-4-4-4 1.8-4 4 1.8 4 4 4zm0 2c-2.7 0-8 1.3-8 4v2h16v-2c0-2.7-5.3-4-8-4z"/>`,
            'properties':   `<path d="M4 6H2v14c0 1.1.9 2 2 2h14v-2H4V6zm16-4H8c-1.1 0-2 .9-2 2v12c0 1.1.9 2 2 2h12c1.1 0 2-.9 2-2V4c0-1.1-.9-2-2-2zm-1 9H9V9h10v2zm-4 4H9v-2h6v2zm4-8H9V5h10v2z"/>`,
            'search':       `<path d="M15.5 14h-.79l-.28-.27A6.471 6.471 0 0 0 16 9.5 6.5 6.5 0 1 0 9.5 16c1.61 0 3.09-.59 4.23-1.57l.27.28v.79l5 4.99L20.49 19l-4.99-5zm-6 0C7.01 14 5 11.99 5 9.5S7.01 5 9.5 5 14 7.01 14 9.5 11.99 14 9.5 14z"/>`,
            'link':         `<path d="M3.9 12c0-1.71 1.39-3.1 3.1-3.1h4V7H7c-2.76 0-5 2.24-5 5s2.24 5 5 5h4v-1.9H7c-1.71 0-3.1-1.39-3.1-3.1zM8 13h8v-2H8v2zm9-6h-4v1.9h4c1.71 0 3.1 1.39 3.1 3.1s-1.39 3.1-3.1 3.1h-4V17h4c2.76 0 5-2.24 5-5s-2.24-5-5-5z"/>`,
            'tag':          `<path d="M21.41 11.58l-9-9C12.05 2.22 11.55 2 11 2H4c-1.1 0-2 .9-2 2v7c0 .55.22 1.05.59 1.42l9 9c.36.36.86.58 1.41.58.55 0 1.05-.22 1.41-.59l7-7c.37-.36.59-.86.59-1.41 0-.55-.23-1.06-.59-1.42zM5.5 7C4.67 7 4 6.33 4 5.5S4.67 4 5.5 4 7 4.67 7 5.5 6.33 7 5.5 7z"/>`,
            'remove':       `<path d="M19 6.41L17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12 19 6.41z"/>`,
            'expand':       `<path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm5 11h-4v4h-2v-4H7v-2h4V7h2v4h4v2z"/>`,
        };
        const path = icons[name] || icons['info'];
        return `<svg xmlns="http://www.w3.org/2000/svg" width="${size}" height="${size}" viewBox="0 0 24 24" fill="${color}" style="vertical-align:middle;flex-shrink:0;">${path}</svg>`;
    }
}

// Global instance — initialized lazily when the mode is activated
let classExplorer;
document.addEventListener('DOMContentLoaded', () => {
    classExplorer = new ClassExplorer();
});





