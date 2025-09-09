class GraphAnalyzer {
    constructor() {
        this.initializeState();
        this.initializeElements();
        this.initializeLayers();
        this.initializeActors();
        this.renderLayerFilterButtons();
        this.renderActorFilterButtons();
        this.setupEventListeners();
        this.setupResizer();
        this.renderDiagram();
        this.render();
    }

    initializeState() {
        this.state = {
            rawEvents: [],
            spans: [],
            filteredSpans: [],
            selectedEvents: new Set(),
            activeLayers: new Set(),
            activeActors: new Set(),
            actors: [],
            layers: [],
            layerDefs: [], //TODO: remove redundancy
            zoomLevel: 1,
            panOffset: 0
        };

        this.config = {
            barHeight: 40,
            margin: {top: 40, right: 60, bottom: 50, left: 0},
            pixelsPerSecond: 150,
            minWidth: 800,
            colors: {}
        };
    }

    initializeElements() {
        this.elements = {
            chartSection: document.getElementById('chart-section'),
            chartViewport: document.getElementById('chart-viewport'),
            chartContainer: document.getElementById('chart-container'),
            labelsContainer: document.getElementById('labels-container'),
            diagramContent: document.getElementById('diagram-content'),
            tooltip: document.getElementById('tooltip'),
            tooltipTitle: document.getElementById('tooltip-title'),
            tooltipLayer: document.getElementById('tooltip-layer'),
            tooltipMetrics: document.getElementById('tooltip-metrics'),
            searchInput: document.getElementById('search-input'),
            eventCount: document.getElementById('event-count'),
            totalDuration: document.getElementById('total-duration'),
            visibleEvents: document.getElementById('visible-events'),
            timelineMarker: document.getElementById('timeline-marker'),
            fileDropZone: document.getElementById('file-drop-zone'),
            exportModal: document.getElementById('export-modal'),
            renderTime: document.getElementById('render-time'),
            memoryUsage: document.getElementById('memory-usage')
        };

        this.buttons = {
            import: document.getElementById('import-btn'),
            export: document.getElementById('export-btn'),
            zoomIn: document.getElementById('zoom-in'),
            zoomOut: document.getElementById('zoom-out'),
            zoomFit: document.getElementById('zoom-fit'),
        };
    }

    setupEventListeners() {
        this.elements.searchInput.addEventListener('input',
            this.debounce((e) => this.handleSearch(e.target.value), 300));

        this.buttons.import.addEventListener('click', () => this.showImportDialog());
        this.buttons.export.addEventListener('click', () => this.showExportModal());
        this.buttons.zoomIn.addEventListener('click', () => this.zoom(1.2));
        this.buttons.zoomOut.addEventListener('click', () => this.zoom(0.8));
        this.buttons.zoomFit.addEventListener('click', () => this.zoomToFit());

        // 🔁 Event delegation so newly-rendered chips work automatically
        document.getElementById('layer-filter-group').addEventListener('click', (e) => {
            const chip = e.target.closest('.layer-filter-chip');
            if (chip) this.toggleLayer(chip.dataset.layer);
        });
        document.getElementById('actor-filter-group').addEventListener('click', (e) => {
            const chip = e.target.closest('.actor-filter-chip');
            if (chip) this.toggleActor(chip.dataset.actor);
        });

        document.querySelectorAll('.export-option').forEach(option => {
            option.addEventListener('click', () => {
                document.querySelectorAll('.export-option').forEach(o => o.classList.remove('selected'));
                option.classList.add('selected');
            });
        });

        document.getElementById('confirm-export').addEventListener('click', () => this.confirmExport());
        document.getElementById('cancel-export').addEventListener('click', () => this.closeExportModal());

        this.setupFileDrop();
        this.setupKeyboardShortcuts();

        this.elements.chartViewport.addEventListener('wheel', (e) => {
            if (e.ctrlKey || e.metaKey) {
                e.preventDefault();
                const delta = e.deltaY > 0 ? 0.9 : 1.1;
                this.zoom(delta);
            }
        });
    }

    setupFileDrop() {
        const dropZone = this.elements.fileDropZone;

        ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
            document.addEventListener(eventName, (e) => {
                e.preventDefault();
                e.stopPropagation();
            });
        });

        document.addEventListener('dragenter', () => dropZone.classList.add('active'));
        document.addEventListener('dragleave', (e) => {
            if (e.clientX === 0 && e.clientY === 0) {
                dropZone.classList.remove('active');
            }
        });

        dropZone.addEventListener('drop', (e) => {
            dropZone.classList.remove('active');
            const files = e.dataTransfer.files;
            if (files.length > 0) {
                this.handleFileImport(files[0]);
            }
        });
    }

    setupKeyboardShortcuts() {
        document.addEventListener('keydown', (e) => {
            if (e.ctrlKey || e.metaKey) {
                switch (e.key) {
                    case 'f':
                        e.preventDefault();
                        this.elements.searchInput.focus();
                        break;
                    case 'o':
                        e.preventDefault();
                        this.showImportDialog();
                        break;
                    case 's':
                        e.preventDefault();
                        this.showExportModal();
                        break;
                    case '=':
                    case '+':
                        e.preventDefault();
                        this.zoom(1.2);
                        break;
                    case '-':
                        e.preventDefault();
                        this.zoom(0.8);
                        break;
                    case '0':
                        e.preventDefault();
                        this.zoomToFit();
                        break;
                }
            } else if (e.key === ' ' && e.target.tagName !== 'INPUT') {
                e.preventDefault();
            }
        });
    }

    processEventData() {
        this.state.spans = this.buildSpans(this.state.rawEvents);
        this.state.filteredSpans = [...this.state.spans];
        this.extractNumericSeries();
        this.updateEventCount();
    }

    extractNumericSeries() {
        const series = {};

        this.state.rawEvents.forEach(event => {
            for (const [key, value] of Object.entries(event)) {
                if (
                    typeof value === "number" &&
                    !["timestamp"].includes(key)
                ) {
                    if (!series[key]) {
                        series[key] = {};
                    }
                    if (!series[key][event.actor]) {
                        series[key][event.actor] = [];
                    }
                    series[key][event.actor].push({
                        time: this.parseTimestamp(event.timestamp) / 1000,
                        value
                    });
                }
            }
        });

        Object.values(series).forEach(actorSeries => {
            Object.values(actorSeries).forEach(values => {
                values.sort((a, b) => a.time - b.time);
            });
        });

        this.state.numericSeries = series;

        if (!this.state.selectedDiagram && Object.keys(series).length > 0) {
            this.state.selectedDiagram = Object.keys(series)[0];
        }
    }

    initializeLayers() {
        if (this.state.layerDefs?.length) {
            this.state.layers = this.state.layerDefs.map(l => l.id);
            this.state.activeLayers = new Set(this.state.layers);
        } else {
            const layers = Array.from(new Set(this.state.rawEvents.map(e => e.layer)));
            this.state.layers = layers;
            this.state.activeLayers = new Set(layers);
        }
    }

    initializeActors() {
        const actors = Array.from(new Set(this.state.rawEvents.map(e => e.actor).filter(Boolean))).sort();
        this.state.actors = actors;
        this.state.activeActors = new Set(actors);
    }

    renderLayerFilterButtons() {
        const filterGroup = document.getElementById('layer-filter-group');
        filterGroup.innerHTML = '<span class="layer-filter-label">Layers:</span>';

        const metaById = Object.fromEntries((this.state.layerDefs || []).map(l => [l.id, l]));
        (this.state.layers || []).forEach((layerId) => {
            const meta = metaById[layerId] || {};
            const button = document.createElement('span');
            button.className = `layer-filter-chip layer-${layerId} ${this.state.activeLayers.has(layerId) ? 'active' : ''}`;
            button.dataset.layer = layerId;
            button.textContent = meta.display_name || (layerId.charAt(0).toUpperCase() + layerId.slice(1));
            filterGroup.appendChild(button);
        });
    }

    renderActorFilterButtons() {
        const group = document.getElementById('actor-filter-group');
        group.innerHTML = '<span class="actor-filter-label">Actors:</span>';

        (this.state.actors || []).forEach((actor) => {
            const chip = document.createElement('span');
            chip.className = `actor-filter-chip actor-${actor} ${this.state.activeActors.has(actor) ? 'active' : ''}`;
            chip.dataset.actor = actor;
            chip.textContent = actor;
            group.appendChild(chip);
        });
    }

    buildSpans(events) {
        const openEvents = new Map();
        const spans = [];

        events.forEach(event => {
            const timestamp = this.parseTimestamp(event.timestamp);
            if (isNaN(timestamp)) return;

            const eventId = event.event_id;

            if (!openEvents.has(eventId)) {
                openEvents.set(eventId, {
                    start: timestamp,
                    display_name: event.display_name,
                    layer: event.layer,
                    event_id: eventId,
                    actor: event.actor            // <— keep actor from the opener
                });
            } else {
                const openEvent = openEvents.get(eventId);
                spans.push({
                    id: `${eventId}-${openEvent.start}`,
                    event_id: eventId,
                    start: openEvent.start,
                    end: timestamp,
                    duration: timestamp - openEvent.start,
                    display_name: openEvent.display_name,
                    layer: openEvent.layer,
                    actor: openEvent.actor        // <— use opener’s actor
                });
                openEvents.delete(eventId);
            }
        });

        openEvents.forEach((event, id) => this.log('warn', `Unclosed event: ${event.display_name} (${id})`));
        return spans.sort((a, b) => a.start - b.start);
    }

    parseTimestamp(timestamp) {
        if (typeof timestamp === 'number') return timestamp * 1000;
        if (typeof timestamp === 'string' && /^\d+(\.\d+)?$/.test(timestamp)) {
            return parseFloat(timestamp) * 1000;
        }
        return new Date(timestamp).getTime();
    }

    render() {
        this.clearChart();

        if (this.state.filteredSpans.length === 0) {
            this.showEmptyState();
            return;
        }

        this.setupDimensions();
        this.createScales();
        this.createSVG();
        this.renderGrid();
        this.renderBars();
        this.renderAxis();
        this.renderLabels();
    }

    clearChart() {
        this.elements.chartContainer.innerHTML = '';
        this.elements.labelsContainer.innerHTML = '';
    }

    showEmptyState() {
        this.elements.chartContainer.innerHTML = `
      <div class="loading">
        <div style="text-align: center;">
          <div style="font-size: 3rem; margin-bottom: 1rem;">📊</div>
          <div>No events to display</div>
          <div style="font-size: 0.875rem; color: var(--text-tertiary); margin-top: 0.5rem;">
            Import data or adjust filters
          </div>
        </div>
      </div>
    `;
    }

    setupDimensions() {
        const viewportRect = this.elements.chartViewport.getBoundingClientRect();
        const groups = this.groupSpansByActorAndLayer(this.state.filteredSpans);

        this.dimensions = {
            containerWidth: viewportRect.width,
            containerHeight: viewportRect.height,
            innerHeight: groups.length * this.config.barHeight + 150
        };

        this.dimensions.totalHeight = this.dimensions.innerHeight +
            this.config.margin.top + this.config.margin.bottom;

        const timeRange = this.getTimeRange();
        this.dimensions.totalWidth = Math.max(
            this.config.minWidth,
            (timeRange.end - timeRange.start) * this.config.pixelsPerSecond * this.state.zoomLevel / 1000
        );
    }

    getTimeRange() {
        if (this.state.filteredSpans.length === 0) return {start: 0, end: 1000};

        const start = d3.min(this.state.filteredSpans, d => d.start);
        const end = d3.max(this.state.filteredSpans, d => d.end);
        const padding = (end - start) * 0.05;

        return {
            start: start - padding,
            end: end + padding
        };
    }

    createScales() {
        const timeRange = this.getTimeRange();
        const groups = this.groupSpansByActorAndLayer(this.state.filteredSpans);
        this.scales = {
            x: d3.scaleLinear()
                .domain([timeRange.start, timeRange.end])
                .range([0, this.dimensions.totalWidth - this.config.margin.left - this.config.margin.right]),

            y: d3.scaleBand()
                .domain(d3.range(groups.length))
                .range([0, this.dimensions.innerHeight])
                .padding(0.1),

            color: (layer) => (this.config.colors && this.config.colors[layer]) || '#666666'
        };
    }

    createSVG() {
        this.svg = d3.select(this.elements.chartContainer)
            .append('svg')
            .attr('width', this.dimensions.totalWidth)
            .attr('height', this.dimensions.totalHeight)
            .style('display', 'block');

        this.chartGroup = this.svg.append('g')
            .attr('transform', `translate(${this.config.margin.left}, ${this.config.margin.top})`);
    }

    renderGrid() {
        const timeRange = this.getTimeRange();
        const tickCount = Math.max(5, Math.floor((timeRange.end - timeRange.start) / 500));

        this.chartGroup.append('g')
            .attr('class', 'grid')
            .selectAll('line')
            .data(this.scales.x.ticks(tickCount))
            .join('line')
            .attr('class', 'grid')
            .attr('x1', d => this.scales.x(d))
            .attr('x2', d => this.scales.x(d))
            .attr('y1', 0)
            .attr('y2', this.dimensions.innerHeight);
    }

    renderBars() {
        const groups = this.groupSpansByActorAndLayer(this.state.filteredSpans);
        let y = 20;
        let prevActor = null;

        groups.forEach((group) => {
            if (group.actor !== prevActor) {
                prevActor = group.actor;
                y += this.config.barHeight;
            }
            group.spans.forEach(span => {
                this.chartGroup.append('rect')
                    .attr('class', 'chart-bar')
                    .attr('x', this.scales.x(span.start))
                    .attr('y', y)
                    .attr('width', Math.max(2, this.scales.x(span.end) - this.scales.x(span.start)))
                    .attr('height', this.config.barHeight * 0.8)
                    .attr('fill', this.scales.color(span.layer))
                    .attr('opacity', 0.8)
                    .on('mouseover', (event) => this.showTooltip(event, span))
                    .on('mouseout', () => this.hideTooltip());

                this.chartGroup.append('text')
                    .attr('x', this.scales.x(span.start) + 5)
                    .attr('y', y + (this.config.barHeight * 0.5))
                    .attr('dy', '.35em')
                    .attr('fill', '#000')
                    .attr('font-size', '14px')
                    .attr('pointer-events', 'none')
                    .text(span.display_name);
            });
            y += this.config.barHeight;
        });
    }

    groupSpansByActorAndLayer(spans) {
        const groups = {};
        spans.forEach(span => {
            const key = `${span.actor}::${span.layer}`;
            if (!groups[key]) groups[key] = {actor: span.actor, layer: span.layer, spans: []};
            groups[key].spans.push(span);
        });

        const layerOrder = new Map((this.state.layers || []).map((id, i) => [id, i]));
        return Object.values(groups).sort((a, b) =>
            a.actor.localeCompare(b.actor) ||
            (layerOrder.get(a.layer) ?? 1e9) - (layerOrder.get(b.layer) ?? 1e9)
        );
    }

    renderAxis() {
        this.chartGroup.append('g')
            .attr('class', 'axis axis-top')
            .attr('transform', `translate(0, -15)`)
            .call(
                d3.axisTop(this.scales.x)
                    .tickFormat(d => `${(d / 1000).toFixed(1)}s`)
                    .ticks(Math.floor(this.dimensions.totalWidth / 100))
            );

        this.chartGroup.append('g')
            .attr('class', 'axis')
            .attr('transform', `translate(0, ${this.dimensions.innerHeight})`)
            .call(
                d3.axisBottom(this.scales.x)
                    .tickFormat(d => `${((d / 1000)).toFixed(1)}s`)
                    .ticks(Math.floor(this.dimensions.totalWidth / 100))
            );
    }

    renderLabels() {
        const groups = this.groupSpansByActorAndLayer(this.state.filteredSpans);
        const labelsContainer = this.elements.labelsContainer;
        labelsContainer.innerHTML = '';

        let lastActor = null;
        groups.forEach(group => {
            if (group.actor !== lastActor) {
                const actorDiv = document.createElement('div');
                actorDiv.className = 'row-label actor-headline';
                actorDiv.textContent = group.actor;
                actorDiv.style.fontWeight = 'bold';
                actorDiv.style.fontSize = '1rem';
                actorDiv.style.background = 'var(--bg-secondary)';
                labelsContainer.appendChild(actorDiv);
                lastActor = group.actor;
            }
            const layerDiv = document.createElement('div');
            layerDiv.className = 'row-label layer-headline';
            layerDiv.textContent = group.layer;
            layerDiv.style.paddingLeft = '2rem';
            layerDiv.style.fontWeight = '500';
            layerDiv.style.fontSize = '0.95rem';
            layerDiv.style.background = 'var(--bg-surface)';
            labelsContainer.appendChild(layerDiv);
        });
    }

    showTooltip(event, data) {
        const tooltip = this.elements.tooltip;
        const title = this.elements.tooltipTitle;
        const layer = this.elements.tooltipLayer;
        const metrics = this.elements.tooltipMetrics;

        title.textContent = data.display_name;
        layer.textContent = data.layer;
        layer.className = `event-layer layer-${data.layer}`;

        const relatedEvents = this.findRelatedEvents(data);

        metrics.innerHTML = `
      <span class="tooltip-metric-label">Event ID:</span>
      <span class="tooltip-metric-value">${data.event_id}</span>
      <span class="tooltip-metric-label">Duration:</span>
      <span class="tooltip-metric-value">${(data.duration / 1000).toFixed(3)}s</span>
      <span class="tooltip-metric-label">Start:</span>
      <span class="tooltip-metric-value">${(data.start / 1000).toFixed(3)}s</span>
      <span class="tooltip-metric-label">End:</span>
      <span class="tooltip-metric-value">${(data.end / 1000).toFixed(3)}s</span>
      ${relatedEvents.length > 0 ? `
        <span class="tooltip-metric-label">Overlaps with:</span>
        <span class="tooltip-metric-value">${relatedEvents.length} events</span>
      ` : ''}
    `;

        tooltip.classList.add('visible');
        this.updateTooltipPosition(event);
    }

    updateTooltipPosition(event) {
        const tooltip = this.elements.tooltip;
        const rect = this.elements.chartViewport.getBoundingClientRect();
        const scrollLeft = this.elements.chartViewport.scrollLeft;
        const scrollTop = this.elements.chartViewport.scrollTop;

        const x = event.clientX - rect.left + scrollLeft + 15;
        const y = event.clientY - rect.top + scrollTop + 15;

        const maxX = rect.width + scrollLeft - tooltip.offsetWidth - 15;
        const maxY = rect.height + scrollTop - tooltip.offsetHeight - 15;

        tooltip.style.left = `${Math.min(x, maxX)}px`;
        tooltip.style.top = `${Math.min(y, maxY)}px`;
    }

    hideTooltip() {
        this.elements.tooltip.classList.remove('visible');
    }

    findRelatedEvents(event) {
        return this.state.filteredSpans.filter(span =>
            span.id !== event.id &&
            span.start < event.end &&
            span.end > event.start
        );
    }

    handleSearch(query) {
        const searchTerm = query.toLowerCase().trim();

        if (!searchTerm) {
            this.state.filteredSpans = this.state.spans.filter(span =>
                this.state.activeLayers.has(span.layer) &&
                this.state.activeActors.has(span.actor)
            );
        } else {
            this.state.filteredSpans = this.state.spans.filter(span =>
                    this.state.activeLayers.has(span.layer) &&
                    this.state.activeActors.has(span.actor) && (
                        span.display_name.toLowerCase().includes(searchTerm) ||
                        span.event_id.toLowerCase().includes(searchTerm) ||
                        span.layer.toLowerCase().includes(searchTerm)
                    )
            );
        }

        this.updateEventCount();
        this.render();
    }

    toggleLayer(layer) {
        const chip = document.querySelector(`[data-layer="${layer}"]`);

        if (this.state.activeLayers.has(layer)) {
            this.state.activeLayers.delete(layer);
            chip.classList.remove('active');
        } else {
            this.state.activeLayers.add(layer);
            chip.classList.add('active');
        }

        this.handleSearch(this.elements.searchInput.value);
    }

    toggleActor(actor) {
        const chip = document.querySelector(`[data-actor="${actor}"]`);

        if (this.state.activeActors.has(actor)) {
            this.state.activeActors.delete(actor);
            chip.classList.remove('active');
        } else {
            this.state.activeActors.add(actor);
            chip.classList.add('active');
        }

        this.handleSearch(this.elements.searchInput.value);
    }

    zoom(factor) {
        this.state.zoomLevel *= factor;
        this.state.zoomLevel = Math.max(0.1, Math.min(10, this.state.zoomLevel));
        this.render();
    }

    zoomToFit() {
        this.state.zoomLevel = 1;
        this.state.panOffset = 0;
        this.render();
        this.elements.chartViewport.scrollLeft = 0;
        this.elements.chartViewport.scrollTop = 0;
    }

    updateEventCount() {
        const total = this.state.spans.length;
        const filtered = this.state.filteredSpans.length;
        this.elements.eventCount.textContent = total.toString();
        this.elements.visibleEvents.textContent =
            filtered === total ? `${total} visible` : `${filtered} visible`;
    }

    renderDiagram() {
        const content = this.elements.diagramContent;
        content.innerHTML = "";

        if (!this.state.numericSeries || Object.keys(this.state.numericSeries).length === 0) {
            content.innerHTML = `<div>No numeric data available for diagrams.</div>`;
            return;
        }

        const layout = document.createElement("div");
        layout.style.display = "flex";
        layout.style.height = "100%";
        content.appendChild(layout);

        // === Tabs ===
        const tabs = document.createElement("div");
        tabs.style.width = "150px";
        tabs.style.borderRight = "1px solid #ccc";
        tabs.style.display = "flex";
        tabs.style.flexDirection = "column";
        layout.appendChild(tabs);

        Object.keys(this.state.numericSeries).forEach(key => {
            const tab = document.createElement("button");
            tab.textContent = key;
            tab.style.padding = "8px";
            tab.style.textAlign = "left";
            tab.style.border = "none";
            tab.style.background = (this.state.selectedDiagram === key) ? "#eee" : "transparent";
            tab.style.cursor = "pointer";
            tab.onclick = () => {
                this.state.selectedDiagram = key;
                this.renderDiagram();
            };
            tabs.appendChild(tab);
        });

        // === Chart area ===
        const chartContainer = document.createElement("div");
        chartContainer.style.flex = "1";
        chartContainer.style.padding = "10px";
        layout.appendChild(chartContainer);

        this.renderSingleDiagram(chartContainer, this.state.selectedDiagram, this.state.numericSeries[this.state.selectedDiagram]);
    }

    renderSingleDiagram(container, key, actorSeries) {
        const margin = {top: 20, right: 80, bottom: 30, left: 50};
        const outerWidth = Math.max(300, (container.clientWidth || 500));
        const width = outerWidth - margin.left - margin.right;
        const height = 200 - margin.top - margin.bottom;

        d3.select(container).selectAll('svg').remove();

        const svg = d3.select(container)
            .append('svg')
            .attr('width', width + margin.left + margin.right)
            .attr('height', height + margin.top + margin.bottom);

        const g = svg.append('g')
            .attr('transform', `translate(${margin.left},${margin.top})`);

        const allValues = Object.values(actorSeries).flat();
        if (!allValues || allValues.length === 0) {
            g.append('text')
                .attr('x', 0).attr('y', 12)
                .text('No data')
                .style('font-size', '12px')
                .style('fill', '#666');
            return;
        }

        const x = d3.scaleLinear()
            .domain(d3.extent(allValues, d => d.time))
            .range([0, width]);

        const y = d3.scaleLinear()
            .domain([d3.min(allValues, d => d.value), d3.max(allValues, d => d.value)])
            .nice()
            .range([height, 0]);

        const color = d3.scaleOrdinal(d3.schemeCategory10)
            .domain(Object.keys(actorSeries));

        // === Gridlines ===
        const xGrid = d3.axisBottom(x).ticks(6).tickSize(-height).tickFormat('');
        const yGrid = d3.axisLeft(y).ticks(5).tickSize(-width).tickFormat('');

        g.append('g')
            .attr('class', 'grid x-grid')
            .attr('transform', `translate(0,${height})`)
            .call(xGrid)
            .selectAll('line')
            .attr('stroke', '#eee')
            .attr('shape-rendering', 'crispEdges');

        g.append('g')
            .attr('class', 'grid y-grid')
            .call(yGrid)
            .selectAll('line')
            .attr('stroke', '#eee')
            .attr('shape-rendering', 'crispEdges');

        g.selectAll('.grid path').remove();

        const line = d3.line()
            .defined(d => d.value !== null && !isNaN(d.value))
            .x(d => x(d.time))
            .y(d => y(d.value));

        const safeActorId = (actor) => String(actor).replace(/[^\w-]/g, '_');

        Object.entries(actorSeries).forEach(([actor, values]) => {
            if (!values || values.length === 0) return;

            const sorted = values.slice().sort((a, b) => a.time - b.time);

            g.append('path')
                .datum(sorted)
                .attr('fill', 'none')
                .attr('stroke', color(actor))
                .attr('stroke-width', 2)
                .attr('d', line);

            const dots = g.selectAll(`.dot-${safeActorId(actor)}`)
                .data(sorted)
                .enter()
                .append('circle')
                .attr('class', `dot dot-${safeActorId(actor)}`)
                .attr('cx', d => x(d.time))
                .attr('cy', d => y(d.value))
                .attr('r', 3)
                .attr('fill', color(actor))
                .attr('stroke', '#fff')
                .attr('stroke-width', 0.5);

            dots.append('title')
                .text(d => `${actor}\n${d.value}\n${d.time}s`);

            const last = sorted[sorted.length - 1];
            if (last) {
                g.append('text')
                    .attr('x', x(last.time) + 6)
                    .attr('y', y(last.value))
                    .attr('dy', '0.35em')
                    .attr('fill', color(actor))
                    .style('font-size', '12px')
                    .style('text-anchor', 'start')
                    .text(actor);
            }
        });

        // === Axes ===
        g.append('g')
            .attr('transform', `translate(0,${height})`)
            .call(d3.axisBottom(x).ticks(5).tickFormat(d => d + 's'));

        g.append('g')
            .call(d3.axisLeft(y));
    }

    showImportDialog() {
        const input = document.createElement('input');
        input.type = 'file';
        input.accept = '.json';
        input.style.display = 'none';

        input.onchange = (e) => {
            const file = e.target.files[0];
            if (file) {
                this.handleFileImport(file);
            }
            input.remove();
        };

        document.body.appendChild(input);
        input.click();
    }

    handleFileImport(file) {
        const reader = new FileReader();
        reader.onload = (e) => {
            try {
                const data = JSON.parse(e.target.result);
                if (!Array.isArray(data.layers) || !Array.isArray(data.events)) {
                    throw new Error('Invalid log format: expected { layers: [...], events: [...] }');
                }

                this.state.layerDefs = data.layers.slice();
                this.config.colors = {};
                data.layers.forEach(l => {
                    this.config.colors[l.id] = l.color || '#666666';
                });

                this.state.rawEvents = data.events;

                this.processEventData();

                this.initializeLayers();
                this.initializeActors();
                this.renderLayerFilterButtons();
                this.renderActorFilterButtons();

                this.renderDiagram();
                this.render();

                this.log('info', `Imported ${this.state.spans.length} events from ${file.name}`);
            } catch (error) {
                this.log('error', `Failed to import file: ${error.message}`);
                alert(`Failed to import file: ${error.message}`);
            }
        };
        reader.readAsText(file);
    }

    showExportModal() {
        this.elements.exportModal.classList.add('active');
    }

    closeExportModal() {
        this.elements.exportModal.classList.remove('active');
    }

    confirmExport() {
        const selectedOption = document.querySelector('.export-option.selected');
        const format = selectedOption.dataset.format;

        switch (format) {
            case 'json':
                this.exportJSON();
                break;
            case 'csv':
                this.exportCSV();
                break;
            case 'svg':
                this.exportSVG();
                break;
        }

        this.closeExportModal();
    }

    exportJSON() {
        const exportData = {
            metadata: {
                exportTime: new Date().toISOString(),
                totalEvents: this.state.spans.length,
                timeRange: this.getTimeRange()
            },
            events: this.state.spans.map(span => ({
                id: span.event_id,
                name: span.display_name,
                actor: span.actor,
                layer: span.layer,
                start: span.start / 1000,
                end: span.end / 1000,
                duration: span.duration / 1000
            }))
        };

        this.downloadFile(
            JSON.stringify(exportData, null, 2),
            `chart-graph-export-${new Date().toISOString().split('T')[0]}.json`,
            'application/json'
        );
    }

    exportCSV() {
        const csv = Papa.unparse({
            fields: ['event_id', 'display_name', 'layer', 'start_time', 'end_time', 'duration'],
            data: this.state.spans.map(span => ({
                event_id: span.event_id,
                display_name: span.display_name,
                layer: span.layer,
                start_time: (span.start / 1000).toFixed(3),
                end_time: (span.end / 1000).toFixed(3),
                duration: (span.duration / 1000).toFixed(3)
            }))
        });

        this.downloadFile(
            csv,
            `chart-graph-export-${new Date().toISOString().split('T')[0]}.csv`,
            'text/csv'
        );
    }

    exportSVG() {
        const svgElement = this.svg.node();
        const svgString = new XMLSerializer().serializeToString(svgElement);
        const svgBlob = new Blob([svgString], {type: 'image/svg+xml'});

        this.downloadFile(
            svgBlob,
            `chart-graph-${new Date().toISOString().split('T')[0]}.svg`,
            'image/svg+xml'
        );
    }

    downloadFile(content, filename, mimeType) {
        const blob = content instanceof Blob ? content : new Blob([content], {type: mimeType});
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        a.click();
        URL.revokeObjectURL(url);

        this.log('info', `Exported: ${filename}`);
    }

    setupResizer() {
        const resizer = document.getElementById('resizer');
        const chartSection = this.elements.chartSection;

        let isResizing = false;
        let startY = 0;
        let startHeight = 0;

        resizer.addEventListener('mousedown', (e) => {
            isResizing = true;
            startY = e.clientY;
            startHeight = chartSection.getBoundingClientRect().height;
            document.body.style.cursor = 'row-resize';
            e.preventDefault();
        });

        document.addEventListener('mousemove', (e) => {
            if (!isResizing) return;

            const deltaY = e.clientY - startY;
            const newHeight = Math.max(200, Math.min(window.innerHeight - 300, startHeight + deltaY));
            chartSection.style.height = `${newHeight}px`;
            chartSection.style.flex = 'none';
        });

        document.addEventListener('mouseup', () => {
            if (isResizing) {
                isResizing = false;
                document.body.style.cursor = '';
                setTimeout(() => this.render(), 100);
            }
        });
    }

    log(level, message) {
        if (!this.eventLog) {
            this.eventLog = [];
        }

        const entry = {
            timestamp: new Date().toLocaleTimeString(),
            level,
            message
        };

        this.eventLog.push(entry);

        //TODO: Is this okay?
        // Keep only last 100 entries
        if (this.eventLog.length > 100) {
            this.eventLog.shift();
        }

        console.log(`[${level.toUpperCase()}] ${message}`);
    }

    debounce(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    }
}

const button = document.querySelector(".toggle-btn");
const panel = document.querySelector(".diagram-panel");

button.addEventListener("click", () => {
    panel.classList.toggle("open");
    button.textContent = panel.classList.contains("open")
        ? "Hide Diagram Panel"
        : "Show Diagram Panel";
});

// Initialize application
document.addEventListener('DOMContentLoaded', () => {
    try {
        const analyzer = new GraphAnalyzer();
        window.graphAnalyzer = analyzer; // For debugging

        // Show welcome message
        // analyzer.log('info', 'Flame Graph Analyzer initialized successfully');
        // analyzer.log('info', 'Import your data or use the sample dataset to begin analysis');

    } catch (error) {
        console.error('Failed to initialize application:', error);
        document.body.innerHTML = `
      <div style="display: flex; align-items: center; justify-content: center; height: 100vh; flex-direction: column; color: var(--text-primary);">
        <div style="font-size: 3rem; margin-bottom: 1rem;">⚠️</div>
        <div style="font-size: 1.5rem; margin-bottom: 0.5rem;">Application Error</div>
        <div style="color: var(--text-secondary);">Please refresh the page to try again.</div>
        <div style="margin-top: 1rem; font-family: monospace; color: var(--accent-red);">${error.message}</div>
      </div>
    `;
    }
});
