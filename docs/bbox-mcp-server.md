# bbox-mcp-server — Optional AI Tool for Bounding Box Queries

`bbox-mcp-server` is a community MCP (Model Context Protocol) server that lets AI assistants (Claude, Copilot, etc.) query OpenStreetMap data directly from bounding boxes. It was used during the development of this project.

**Repository:** [github.com/bboxmcp/bbox-mcp-server](https://github.com/bboxmcp/bbox-mcp-server) *(check for the current URL — this is the community project)*

---

## What It Does

MCP (Model Context Protocol) is a standard that lets AI assistants connect to external tools and data sources. `bbox-mcp-server` exposes OpenStreetMap's Overpass API as an MCP tool, meaning you can ask your AI assistant things like:

> "What is the bounding box for the city of Portland, Oregon?"
> "Search for all parks within the Minneapolis downtown area."
> "Get OSM data for zip code 55401."

The AI assistant queries OSM directly and returns structured results — no manual coordinate lookup needed.

---

## How This Project Used It

During development of this pipeline, `bbox-mcp-server` was used to:

1. **Obtain bounding box coordinates** for Minneapolis without leaving the editor
2. **Verify coverage** by querying specific neighborhoods before running the full extraction
3. **Test Overpass QL queries** incrementally during development

The MCP server is completely optional — you can get the same results from [Nominatim](https://nominatim.openstreetmap.org/) or [bboxfinder.com](http://bboxfinder.com/). But if you're building CS2 maps with AI assistance, having this tool available in your workflow speeds up the iteration cycle.

---

## Installation

The installation steps depend on which AI platform you're using.

**For Claude Code (Anthropic):**

Add to your MCP configuration (`.claude/mcp.json` or via `/mcp` command):
```json
{
  "mcpServers": {
    "bbox": {
      "command": "npx",
      "args": ["-y", "bbox-mcp-server"]
    }
  }
}
```

**For VS Code Copilot:**

Check the bbox-mcp-server repository for current VS Code installation instructions.

**Prerequisite:** Node.js must be installed (`node --version` to verify).

---

## Example Usage

Once installed, in a Claude Code or Copilot session:

```
User: What's the bounding box for Minneapolis, MN?
AI:   Using bbox-mcp-server to query Nominatim...
      Minneapolis, MN bounding box: 44.8896,-93.3297,45.0513,-93.1938
```

Check that it comes as south,west,north,east, then use it as the city's `bbox` in `cities.json` ([Quick Start, Step 7](QUICKSTART.md#step-7-add-your-city-to-citiesjson)) and extract from `src/`:
```bash
uv run extract-zoning --city your_slug
```

---

## This Project Does NOT Require bbox-mcp-server

The extractors (`extract-zoning` and the rest) read OpenStreetMap extracts downloaded from Geofabrik, or query Overpass on their own with `--source overpass`. `bbox-mcp-server` is a developer convenience tool, not a runtime dependency. You can run this entire project without it.
