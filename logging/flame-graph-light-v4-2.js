// Enhanced Car Simulation Flame Graph Analyzer
class FlameGraphAnalyzer {
  constructor() {
    this.initializeState();
    this.initializeElements();
    this.initializeData();
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
      zoomLevel: 1,
      panOffset: 0
    };

    this.config = {
      barHeight: 40,
      margin: { top: 40, right: 60, bottom: 50, left: 0 },
      pixelsPerSecond: 150,
      minWidth: 800,
      colors: {
        maneuver: '#4a9eff',
        control: '#4ade80',
        sensor: '#fb923c',
        navigation: '#a78bfa',
        safety: '#f87171',
        infrastructure: '#22d3ee'
      }
    };
  }

  initializeElements() {
    this.elements = {
      chartSection: document.getElementById('chart-section'),
      chartViewport: document.getElementById('chart-viewport'),
      chartContainer: document.getElementById('chart-container'),
      labelsContainer: document.getElementById('labels-container'),
      analysisContent: document.getElementById('analysis-content'),
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

    // Buttons
    this.buttons = {
      import: document.getElementById('import-btn'),
      export: document.getElementById('export-btn'),
      zoomIn: document.getElementById('zoom-in'),
      zoomOut: document.getElementById('zoom-out'),
      zoomFit: document.getElementById('zoom-fit'),
    };
  }

  setupEventListeners() {
    // Search
    this.elements.searchInput.addEventListener('input',
      this.debounce((e) => this.handleSearch(e.target.value), 300));

    // Buttons
    this.buttons.import.addEventListener('click', () => this.showImportDialog());
    this.buttons.export.addEventListener('click', () => this.showExportModal());
    this.buttons.zoomIn.addEventListener('click', () => this.zoom(1.2));
    this.buttons.zoomOut.addEventListener('click', () => this.zoom(0.8));
    this.buttons.zoomFit.addEventListener('click', () => this.zoomToFit());

    // console.log("Event listeners set up");

    // Layer filters
    document.querySelectorAll('.layer-filter-chip').forEach(chip => {
      // console.log(chip);
      chip.addEventListener('click', () => this.toggleLayer(chip.dataset.layer));
    });

    // Actor filters
    document.querySelectorAll('.actor-filter-chip').forEach(chip => {
      // console.log(chip);
      chip.addEventListener('click', () => this.toggleActor(chip.dataset.actor));
    });

    // Export modal
    document.querySelectorAll('.export-option').forEach(option => {
      option.addEventListener('click', () => {
        document.querySelectorAll('.export-option').forEach(o => o.classList.remove('selected'));
        option.classList.add('selected');
      });
    });

    document.getElementById('confirm-export').addEventListener('click', () => this.confirmExport());
    document.getElementById('cancel-export').addEventListener('click', () => this.closeExportModal());

    // File drop
    this.setupFileDrop();

    // Keyboard shortcuts
    this.setupKeyboardShortcuts();

    // Mouse wheel zoom
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
        switch(e.key) {
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

  initializeData() {
    // Enhanced sample data with more realistic scenarios
    this.state.rawEventsOld = [
      //TODO: Data starts here
      // Car1 - Complex overtaking maneuver
      { timestamp: "0.0", event_id: "car1-overtake", display_name: "Car1 – Overtake Planning", category: "foo", actor: "Car1" },
      { timestamp: "0.1", event_id: "car1-radar-check", display_name: "Car1 – Radar Scan", category: "sensor", actor: "Car1" },
      { timestamp: "0.2", event_id: "car1-camera-check", display_name: "Car1 – Camera Analysis", category: "sensor", actor: "Car1" },
      { timestamp: "0.3", event_id: "car1-radar-check", display_name: "Car1 – Radar Complete", category: "sensor", actor: "Car1" },
      { timestamp: "0.4", event_id: "car1-camera-check", display_name: "Car1 – Camera Complete", category: "sensor", actor: "Car1" },
      { timestamp: "0.5", event_id: "car1-accelerate", display_name: "Car1 – Begin Acceleration", category: "control", actor: "Car1" },
      { timestamp: "1.0", event_id: "car1-signal-left", display_name: "Car1 – Left Signal On", category: "safety", actor: "Car1" },
      { timestamp: "1.2", event_id: "car1-lane-change-left", display_name: "Car1 – Lane Change Left", category: "navigation", actor: "Car1" },
      { timestamp: "1.5", event_id: "car1-signal-left", display_name: "Car1 – Left Signal Off", category: "safety", actor: "Car1" },
      { timestamp: "1.8", event_id: "car1-lane-change-left", display_name: "Car1 – In Left Lane", category: "navigation", actor: "Car1" },
      { timestamp: "2.0", event_id: "car1-accelerate", display_name: "Car1 – Max Acceleration", category: "control", actor: "Car1" },
      { timestamp: "2.5", event_id: "car1-passing", display_name: "Car1 – Passing Vehicle", category: "maneuver", actor: "Car1" },
      { timestamp: "3.5", event_id: "car1-passing", display_name: "Car1 – Pass Complete", category: "maneuver", actor: "Car1" },
      { timestamp: "3.6", event_id: "car1-signal-right", display_name: "Car1 – Right Signal On", category: "safety", actor: "Car1" },
      { timestamp: "3.8", event_id: "car1-lane-change-right", display_name: "Car1 – Lane Change Right", category: "navigation", actor: "Car1" },
      { timestamp: "4.0", event_id: "car1-signal-right", display_name: "Car1 – Right Signal Off", category: "safety", actor: "Car1" },
      { timestamp: "4.2", event_id: "car1-lane-change-right", display_name: "Car1 – Back in Lane", category: "navigation", actor: "Car1" },
      { timestamp: "4.5", event_id: "car1-overtake", display_name: "Car1 – Overtake Complete", category: "maneuver", actor: "Car1" },

      // Car 2 - Emergency braking scenario
      { timestamp: "2.0", event_id: "Car 2-cruise", display_name: "Car 2 – Cruise Control", category: "control", actor: "Car 2" },
      { timestamp: "3.0", event_id: "Car 2-obstacle-detect", display_name: "Car 2 – Obstacle Detected", category: "sensor", actor: "Car 2" },
      { timestamp: "3.1", event_id: "Car 2-emergency-brake", display_name: "Car 2 – Emergency Brake", category: "safety", actor: "Car 2" },
      { timestamp: "3.2", event_id: "Car 2-abs-active", display_name: "Car 2 – ABS Activated", category: "control", actor: "Car 2" },
      { timestamp: "3.5", event_id: "Car 2-obstacle-detect", display_name: "Car 2 – Obstacle Avoided", category: "sensor", actor: "Car 2" },
      { timestamp: "3.8", event_id: "Car 2-abs-active", display_name: "Car 2 – ABS Released", category: "control", actor: "Car 2" },
      { timestamp: "4.0", event_id: "Car 2-emergency-brake", display_name: "Car 2 – Brake Released", category: "safety", actor: "Car 2" },
      { timestamp: "4.5", event_id: "Car 2-cruise", display_name: "Car 2 – Resume Cruise", category: "control", actor: "Car 2" },

      // Traffic Light interaction
      { timestamp: "5.0", event_id: "traffic-light-1", display_name: "Traffic Light – Yellow", category: "infrastructure", actor: "Traffic Light" },
      { timestamp: "5.2", event_id: "Car 1-decelerate", display_name: "Car1 – Begin Deceleration", category: "control", actor: "Car1" },
      { timestamp: "6.0", event_id: "traffic-light-1", display_name: "Traffic Light – Red", category: "infrastructure", actor: "Traffic Light" },
      { timestamp: "6.5", event_id: "car1-stop", display_name: "Car1 – Full Stop", category: "control", actor: "Car1" },
      { timestamp: "7.0", event_id: "car1-decelerate", display_name: "Car1 – Stopped", category: "control", actor: "Car1" },
      { timestamp: "8.0", event_id: "car1-stop", display_name: "Car1 – Waiting", category: "control", actor: "Car1" },

      // Intersection navigation
      { timestamp: "10.0", event_id: "traffic-light-2", display_name: "Traffic Light – Green", category: "infrastructure", actor: "Traffic Light" },
      { timestamp: "10.2", event_id: "car1-intersection", display_name: "Car1 – Enter Intersection", category: "navigation", actor: "Car1" },
      { timestamp: "10.5", event_id: "car1-turn-left", display_name: "Car1 – Left Turn", category: "maneuver", actor: "Car1" },
      { timestamp: "11.5", event_id: "car1-turn-left", display_name: "Car1 – Turn Complete", category: "maneuver", actor: "Car1" },
      { timestamp: "12.0", event_id: "car1-intersection", display_name: "Car1 – Exit Intersection", category: "navigation", actor: "Car1" },
      { timestamp: "12.5", event_id: "traffic-light-2", display_name: "Traffic Light – Yellow", category: "infrastructure", actor: "Traffic Light" }
    ];

    // New data including layer:
    this.state.rawEvents = [
      //TODO: New data starts here
      // Car1 - Complex overtaking maneuver
      { "timestamp": "0.0", "event_id": "car1-overtake", "display_name": "Car1 – Overtake", "category": "foo", "actor": "Car1", "layer": "scenario" },
      { "timestamp": "20.0", "event_id": "car1-overtake", "display_name": "Car1 – Overtake", "category": "foo", "actor": "Car1", "layer": "scenario" },
      { "timestamp": "0.5", "event_id": "car1-accelerate", "display_name": "Car1 – Accelerate", "category": "sensor", "actor": "Car1", "layer": "selection" },
      { "timestamp": "3.5", "event_id": "car1-accelerate", "display_name": "Car1 – Accelerate", "category": "sensor", "actor": "Car1", "layer": "selection" },
      { "timestamp": "4.0", "event_id": "car1-switch-lane-left", "display_name": "Car1 – Switch Lane (left)", "category": "sensor", "actor": "Car1", "layer": "selection" },
      { "timestamp": "6.0", "event_id": "car1-switch-lane-left", "display_name": "Car1 – Switch Lane (left)", "category": "sensor", "actor": "Car1", "layer": "selection" },
      { "timestamp": "10.0", "event_id": "car1-switch-lane-right", "display_name": "Car1 – Switch Lane (right)", "category": "sensor", "actor": "Car1", "layer": "selection" },
      { "timestamp": "13.0", "event_id": "car1-switch-lane-right", "display_name": "Car1 – Switch Lane (right)", "category": "sensor", "actor": "Car1", "layer": "selection" },
      { "timestamp": "14.0", "event_id": "car1-ride-into-sunset", "display_name": "Car1 – Ride into sunset", "category": "sensor", "actor": "Car1", "layer": "selection" },
      { "timestamp": "20.0", "event_id": "car1-ride-into-sunset", "display_name": "Car1 – Ride into sunset", "category": "sensor", "actor": "Car1", "layer": "selection" },

      { "timestamp": "0.5", "event_id": "car1-increase-speed", "display_name": "Car1 – Increase Speed", "category": "sensor", "actor": "Car1", "layer": "simulation", "distance_to_vut": 2.5 },
      { "timestamp": "2.0", "event_id": "car1-increase-speed", "display_name": "Car1 – Increase Speed", "category": "sensor", "actor": "Car1", "layer": "simulation", "distance_to_vut": 12.5 },
      { "timestamp": "2.5", "event_id": "car1-increase-speed", "display_name": "Car1 – Increase Speed", "category": "sensor", "actor": "Car1", "layer": "simulation", "distance_to_vut": 17.5 },

      // Car2 - Complex overtaking maneuver
      { "timestamp": "0.0", "event_id": "car2-overtake", "display_name": "Car2 – Overtake", "category": "foo", "actor": "Car2", "layer": "scenario" },
      { "timestamp": "20.0", "event_id": "car2-overtake", "display_name": "Car2 – Overtake", "category": "foo", "actor": "Car2", "layer": "scenario" },
      { "timestamp": "0.5", "event_id": "car2-accelerate", "display_name": "Car2 – Accelerate", "category": "sensor", "actor": "Car2", "layer": "selection" },
      { "timestamp": "3.5", "event_id": "car2-accelerate", "display_name": "Car2 – Accelerate", "category": "sensor", "actor": "Car2", "layer": "selection" },
      { "timestamp": "4.0", "event_id": "car2-switch-lane-left", "display_name": "Car2 – Switch Lane (left)", "category": "sensor", "actor": "Car2", "layer": "selection" },
      { "timestamp": "6.0", "event_id": "car2-switch-lane-left", "display_name": "Car2 – Switch Lane (left)", "category": "sensor", "actor": "Car2", "layer": "selection" },
      { "timestamp": "10.0", "event_id": "car2-switch-lane-right", "display_name": "Car2 – Switch Lane (right)", "category": "sensor", "actor": "Car2", "layer": "selection" },
      { "timestamp": "13.0", "event_id": "car2-switch-lane-right", "display_name": "Car2 – Switch Lane (right)", "category": "sensor", "actor": "Car2", "layer": "selection" },
      { "timestamp": "14.0", "event_id": "car2-ride-into-sunset", "display_name": "Car2 – Ride into sunset", "category": "sensor", "actor": "Car2", "layer": "selection" },
      { "timestamp": "20.0", "event_id": "car2-ride-into-sunset", "display_name": "Car2 – Ride into sunset", "category": "sensor", "actor": "Car2", "layer": "selection" },

      { "timestamp": "0.5", "event_id": "car2-increase-speed", "display_name": "Car2 – Increase Speed", "category": "sensor", "actor": "Car2", "layer": "simulation", "distance_to_vut": 12.5 },
      { "timestamp": "2.0", "event_id": "car2-increase-speed", "display_name": "Car2 – Increase Speed", "category": "sensor", "actor": "Car2", "layer": "simulation", "distance_to_vut": 22.5 },
      { "timestamp": "2.5", "event_id": "car2-increase-speed", "display_name": "Car2 – Increase Speed", "category": "sensor", "actor": "Car2", "layer": "simulation", "distance_to_vut": 27.5 },
    ];

    this.processEventData();
    this.log('info', `Loaded ${this.state.spans.length} event spans`);
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
              time: this.parseTimestamp(event.timestamp) / 1000, // seconds
              value
            });
          }
        }
      });

      this.state.numericSeries = series;
    }

  initializeLayers() {
    // console.log(this.state.rawEvents);
    const layers = new Set(this.state.rawEvents.map((event) => event.layer));
    // console.log(layers);
    this.state.activeLayers = new Set(layers); // Initially, all layers are active
    // console.log(this.state.activeLayers);
    this.state.layers = Array.from(layers); // Convert to array for rendering
  }

  initializeActors() {
    // console.log(this.state.rawEvents);
    const actors = new Set(this.state.rawEvents.map((event) => event.actor));
    // console.log(actors);
    this.state.activeActors = new Set(actors); // Initially, all actors are active
    // console.log(this.state.activeActors);
    this.state.actors = Array.from(actors); // Convert to array for rendering
  }

  renderLayerFilterButtons() {
    const filterGroup = document.getElementById('layer-filter-group');
    filterGroup.innerHTML = '<span class="layer-filter-label">Layers:</span>'; // Clear existing buttons

    // console.log(this.state.layers);
    this.state.layers.forEach((layer) => {
      const button = document.createElement('span');
      button.className = `layer-filter-chip layer-${layer} active`;
      button.dataset.layer = layer;
      button.textContent = layer.charAt(0).toUpperCase() + layer.slice(1);
      filterGroup.appendChild(button);
    });
  }

  renderActorFilterButtons() {
    const actorFilterGroup = document.getElementById('actor-filter-group');
    actorFilterGroup.innerHTML = '<span class="actor-filter-label">Actors:</span>'; // Clear existing buttons

    // console.log(this.state.actors);
    this.state.actors.forEach((actor) => {
      const button = document.createElement('span');
      button.className = `actor-filter-chip actor-${actor} active`;
      button.dataset.actor = actor;
      button.textContent = actor.charAt(0).toUpperCase() + actor.slice(1);
      actorFilterGroup.appendChild(button);
    })
  }

  buildSpans(events) {
    const openEvents = new Map();
    const spans = [];

    events.forEach(event => {
      const timestamp = this.parseTimestamp(event.timestamp);
      if (isNaN(timestamp)) return;

      const eventId = event.event_id;

      // console.log("316: " + event.actor)

      if (!openEvents.has(eventId)) {
        openEvents.set(eventId, {
          start: timestamp,
          display_name: event.display_name,
          layer: event.layer,
          event_id: eventId
        });
      } else {
        const openEvent = openEvents.get(eventId);
        // console.log("326: " + openEvent.actor)
        spans.push({
          id: `${eventId}-${openEvent.start}`,
          event_id: eventId,
          start: openEvent.start,
          end: timestamp,
          duration: timestamp - openEvent.start,
          display_name: openEvent.display_name,
          layer: openEvent.layer,
          //TODO: Warum ist das anders als darüber?
          actor: event.actor,
          layer: event.layer
        });
        openEvents.delete(eventId);
      }
    });

    // Add unclosed events as warnings
    openEvents.forEach((event, id) => {
      this.log('warn', `Unclosed event: ${event.display_name} (${id})`);
    });

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
    const startTime = performance.now();

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
    this.dimensions = {
      containerWidth: viewportRect.width,
      containerHeight: viewportRect.height,
      innerHeight: this.state.filteredSpans.length * this.config.barHeight
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
    if (this.state.filteredSpans.length === 0) return { start: 0, end: 1000 };

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

    this.scales = {
      x: d3.scaleLinear()
        .domain([timeRange.start, timeRange.end])
        .range([0, this.dimensions.totalWidth - this.config.margin.left - this.config.margin.right]),

      y: d3.scaleBand()
        .domain(d3.range(this.state.filteredSpans.length))
        .range([0, this.dimensions.innerHeight])
        .padding(0.1),

      color: (layer) => this.config.colors[layer] || '#666666'
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
  console.log(groups);
  let y = 20;
  let prevActor = null;

  groups.forEach((group, groupIdx) => {
    console.log(group.actor)
    if (group.actor !== prevActor) {
      prevActor = group.actor;
      console.log(prevActor)
      y += this.config.barHeight;
    }
    group.spans.forEach(span => {
      this.chartGroup.append('rect')
        .attr('class', 'flame-bar')
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
        .attr('fill', '#fff')
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
    if (!groups[key]) {
      groups[key] = { actor: span.actor, layer: span.layer, spans: [] };
    }
    groups[key].spans.push(span);
  });
  console.log(groups);
    return Object.values(groups).sort((a, b) => {
    // TODO: Fix sorting to account for correct order of layers
    if (a.actor < b.actor) return -1;
    if (a.actor > b.actor) return 1;
    if (a.layer < b.layer) return -1;
    if (a.layer > b.layer) return 1;
    return 0;
  });
}

// Die Achse beginnt bei 0.5s und zählt ab dort
renderAxis() {
  const timeRange = this.getTimeRange();

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
    // Akteur-Überschrift nur einmal pro Akteur
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
    // Layer-Label leicht eingerückt
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

      // Keep tooltip within viewport
      const maxX = rect.width + scrollLeft - tooltip.offsetWidth - 15;
      const maxY = rect.height + scrollTop - tooltip.offsetHeight - 15;

      tooltip.style.left = `${Math.min(x, maxX)}px`;
      tooltip.style.top = `${Math.min(y, maxY)}px`;
    }

  hideTooltip() {
    this.elements.tooltip.classList.remove('visible');
  }

  selectEvent(eventData, multi = false) {
    if (!multi) {
      this.state.selectedEvents.clear();
      document.querySelectorAll('.row-label.highlighted').forEach(el => {
        el.classList.remove('highlighted');
      });
      this.svg.selectAll('.flame-bar').classed('selected', false);
    }

    if (this.state.selectedEvents.has(eventData.id)) {
      this.state.selectedEvents.delete(eventData.id);
    } else {
      this.state.selectedEvents.add(eventData.id);
    }

    // Update visual selection
    const labelElement = document.querySelector(`[data-event-id="${eventData.id}"]`);
    if (labelElement) {
      labelElement.classList.toggle('highlighted');
    }

    this.svg.selectAll('.flame-bar')
      .filter(d => d.id === eventData.id)
      .classed('selected', this.state.selectedEvents.has(eventData.id));

    this.log('info', `Selected: ${eventData.display_name} (${(eventData.duration/1000).toFixed(3)}s)`);
    this.updateAnalysisPanel();
  }

  findRelatedEvents(event) {
    return this.state.filteredSpans.filter(span =>
      span.id !== event.id &&
      span.start < event.end &&
      span.end > event.start
    );
  }

  handleSearch(query) {
    console.log("613")
    const searchTerm = query.toLowerCase().trim();

    console.log(this.state.activeActors)
    console.log(this.state.activeActors.has("Car1"))
    console.log(this.state.activeActors.has(this.state.spans[0].actor))
    // console.log(this.state.spans[0])
    console.log(this.state.spans[0].actor)
    console.log(this.state.activeLayers.has(this.state.spans[0].layer) &&
        this.state.activeActors.has(this.state.spans[0].actor) && (
          this.state.spans[0].display_name.toLowerCase().includes(searchTerm) ||
          this.state.spans[0].event_id.toLowerCase().includes(searchTerm) ||
          this.state.spans[0].layer.toLowerCase().includes(searchTerm)
        ))

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

    console.log(this.state.filteredSpans)

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

    console.log("Toggling actor:", actor, this.state.activeActors);

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
    console.log(this.state.filteredSpans.length)
    this.elements.eventCount.textContent = total.toString();
    this.elements.visibleEvents.textContent =
      filtered === total ? `${total} visible` : `${filtered} visible`;
  }

renderDiagram() {
  const content = this.elements.analysisContent;
  content.innerHTML = "";

  if (!this.state.numericSeries || Object.keys(this.state.numericSeries).length === 0) {
    content.innerHTML = `<div>No numeric data available for diagrams.</div>`;
    return;
  }

  Object.entries(this.state.numericSeries).forEach(([key, actorSeries]) => {
    const container = document.createElement("div");
    container.className = "diagram-container";
    container.style.marginBottom = "2rem";
    container.innerHTML = `<h3>${key}</h3>`;
    content.appendChild(container);

    const width = 500, height = 200, margin = { top: 20, right: 80, bottom: 30, left: 50 };

    const svg = d3.select(container)
      .append("svg")
      .attr("width", width)
      .attr("height", height);

    // Flatten all actor values for global axis scaling
    const allValues = Object.values(actorSeries).flat();

    const x = d3.scaleLinear()
      .domain(d3.extent(allValues, d => d.time))
      .range([margin.left, width - margin.right]);

    const y = d3.scaleLinear()
      .domain([d3.min(allValues, d => d.value), d3.max(allValues, d => d.value)])
      .nice()
      .range([height - margin.bottom, margin.top]);

    const color = d3.scaleOrdinal(d3.schemeCategory10)
      .domain(Object.keys(actorSeries));

    const line = d3.line()
      .x(d => x(d.time))
      .y(d => y(d.value));

    // One line per actor
    Object.entries(actorSeries).forEach(([actor, values]) => {
      svg.append("path")
        .datum(values)
        .attr("fill", "none")
        .attr("stroke", color(actor))
        .attr("stroke-width", 2)
        .attr("d", line);

      // Label at the last data point
      const lastPoint = values[values.length - 1];

      svg.append("text")
        .attr("x", x(lastPoint.time) + 5) // a little to the right of the line end
        .attr("y", y(lastPoint.value))
        .attr("dy", "0.35em") // vertical centering
        .attr("fill", color(actor))
        .style("font-size", "12px")
        .text(actor);
    });

    // Axes
    svg.append("g")
      .attr("transform", `translate(0,${height - margin.bottom})`)
      .call(d3.axisBottom(x).ticks(5).tickFormat(d => d + "s"));

    svg.append("g")
      .attr("transform", `translate(${margin.left},0)`)
      .call(d3.axisLeft(y));
  });
}



  showImportDialog() {
    const input = document.createElement('input');
    input.type = 'file';
    input.accept = '.json';
    input.onchange = (e) => {
      const file = e.target.files[0];
      if (file) {
        this.handleFileImport(file);
      }
    };
    input.click();
  }

  handleFileImport(file) {
    const reader = new FileReader();
    reader.onload = (e) => {
      try {
        const data = JSON.parse(e.target.result);
        console.log(data);

        // Support multiple import formats
        let events = [];

        if (Array.isArray(data)) {
          console.log("Array is array")
          // Support simple array of events
          events = data;
        } else if (data.events && Array.isArray(data.events)) {
            console.log("Data.events is array")
          // Support export format
          events = data.events.flatMap(event => [
            { timestamp: event.start / 1000, event_id: event.id, display_name: event.name, layer: event.layer, actor: event.actor, layer: event.layer },
            { timestamp: event.end / 1000, event_id: event.id, display_name: event.name + ' Complete', layer: event.layer, actor: event.actor, layer: event.layer }
          ]);
        } else if (data.data && Array.isArray(data.data)) {
            console.log("Data.data is array")
          // Support alternative format
          events = data.data;
        }

        console.log(events)

        if (events.length > 0) {
          this.state.rawEvents = events;
          this.processEventData();
          this.render();
          this.log('info', `Imported ${this.state.spans.length} events from ${file.name}`);
        } else {
          throw new Error('No valid events found in file');
        }
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

    switch(format) {
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
        layer: span.layer,
        actor: span.actor,
        layer: span.layer,
        start: span.start / 1000,
        end: span.end / 1000,
        duration: span.duration / 1000
      }))
    };

    this.downloadFile(
      JSON.stringify(exportData, null, 2),
      `flame-graph-export-${new Date().toISOString().split('T')[0]}.json`,
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
      `flame-graph-export-${new Date().toISOString().split('T')[0]}.csv`,
      'text/csv'
    );
  }

  exportSVG() {
    const svgElement = this.svg.node();
    const svgString = new XMLSerializer().serializeToString(svgElement);
    const svgBlob = new Blob([svgString], { type: 'image/svg+xml' });

    this.downloadFile(
      svgBlob,
      `flame-graph-${new Date().toISOString().split('T')[0]}.svg`,
      'image/svg+xml'
    );
  }

  downloadFile(content, filename, mimeType) {
    const blob = content instanceof Blob ? content : new Blob([content], { type: mimeType });
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
    const analysisPanel = document.getElementById('analysis-panel');

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
const panel = document.querySelector(".analysis-panel");

button.addEventListener("click", () => {
  panel.classList.toggle("open");
  button.textContent = panel.classList.contains("open")
    ? "Hide Analysis Panel"
    : "Show Analysis Panel";
});

// Initialize application
document.addEventListener('DOMContentLoaded', () => {
  try {
    const analyzer = new FlameGraphAnalyzer();
    window.flameGraphAnalyzer = analyzer; // For debugging

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
