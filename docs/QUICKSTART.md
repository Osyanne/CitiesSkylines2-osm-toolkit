# Quick Start — Using This Toolkit for Your City

By the end of this guide you'll have your city in the toolkit's map, running on your own computer: the same dark map with CS2 zoning that the website shows, built from real OpenStreetMap data, ready to use as a reference layer while building in Cities: Skylines 2. Setting it up takes about 15 minutes. The first download and the extraction take longer for a big region.

You don't need any of this just to get your city on the website: open any city's map, search for your city, turn on Playable area, move the square where you want and press **Request this area** (see [Adding your city](../README.md#adding-your-city)).

If something breaks along the way, see [TROUBLESHOOTING.md](TROUBLESHOOTING.md).

---

## Step 1: Install Python

Go to [python.org/downloads](https://www.python.org/downloads/) and download the latest Python 3.11 or newer installer for Windows.

Run the installer. **Before clicking Install Now, check the box that says "Add Python to PATH".** This is easy to miss and if you skip it, nothing else in this guide will work. You'd have to reinstall.

On **macOS**: Python 3.11+ usually comes via [Homebrew](https://brew.sh/) — `brew install python@3.11`. On **Linux**: use your distro's package manager (`apt install python3.11` or equivalent). On both, the command may be `python3` instead of `python`.

Once installed, open a new terminal and type `python --version`. You should see something like `Python 3.11.x`. If you get an error, the PATH wasn't set — go back and reinstall with the checkbox.

*Time: 3–5 min*

---

## Step 2: Install uv

uv is a fast Python package manager. You only install it once, globally.

Open PowerShell (search "PowerShell" in the Start menu) and paste:

    powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"

Close and reopen PowerShell after it finishes so the PATH changes take effect. Then verify: `uv --version`.

On **macOS/Linux**:

    curl -LsSf https://astral.sh/uv/install.sh | sh

*Time: 1 min*

---

## Step 3: Download the Repo

Go to [github.com/Osyanne/CitiesSkylines2-osm-toolkit](https://github.com/Osyanne/CitiesSkylines2-osm-toolkit), click the green **Code** button, then **Download ZIP**. It's a big download, because it carries the map data of every city on the site.

Unzip it somewhere easy to find. Your Desktop or Documents folder works fine. You should end up with a folder called `CitiesSkylines2-osm-toolkit-main`.

If you use git, cloning works too, and the folder is called `CitiesSkylines2-osm-toolkit`:

    git clone https://github.com/Osyanne/CitiesSkylines2-osm-toolkit.git

*Time: 1 min, plus the download*

---

## Step 4: Find Your City's Bounding Box

The toolkit needs four numbers that draw a rectangle around your city, in this order: south, west, north, east. Latitude comes first.

The easiest way: go to [bboxfinder.com](http://bboxfinder.com/). In the box at the bottom, under **Coordinate Format**, choose **Lat / Lng** first. Then zoom to your city and draw a rectangle with the rectangle tool. The **Box** line now reads south,west,north,east. Copy it: you'll use it in Step 7.

Choose the format before you draw, because the Box line doesn't change when you switch it afterwards. The default, Lng / Lat, puts longitude first, and a box in that order lands in the wrong place.

Aim for about 10–20 km per side. A CS2 playable area is 14.3 km across: turn on **Playable area** in any city's map to see that size on a real city.

For other ways to find a bbox (including an AI-assisted method), see [adapting-to-other-cities.md](adapting-to-other-cities.md).

*Time: 2–3 min*

---

## Step 5: Open a Terminal Inside the src/ Folder

Navigate to the folder you unzipped, then into the `src` subfolder.

Hold **Shift** and **right-click** on the `src` folder. Choose "Open in Terminal" or "Open PowerShell window here". (In Windows 11, you might need to click "Show more options" to see it.)

You should see the terminal path end in `...\src>`.

On macOS or Linux, open a terminal and `cd` into the `src` folder.

Every `uv run` command in this guide runs from here.

*Time: 1 min*

---

## Step 6: Install Dependencies

In that terminal, run:

    uv sync

This downloads and installs everything the toolkit needs. It only does the heavy work the first time — subsequent runs are instant. Wait until you see the terminal prompt return.

If it fails, make sure you're inside the `src` folder (not the root of the repo). See [TROUBLESHOOTING.md](TROUBLESHOOTING.md) if you're stuck.

*Time: 1–2 min*

---

## Step 7: Add Your City to cities.json

`cities.json` in the main folder lists every city the toolkit knows. Open it with a text editor (Notepad works). Use this one, not the copy inside `visualizer/`: that copy is rewritten in Step 9.

Every city is an entry like this one, which is Charleston's:

```json
  "charleston": {
    "display_name": "Charleston, SC",
    "country": "USA",
    "country_code": "US",
    "bbox": [32.74, -80.05, 32.92, -79.85],
    "center": [32.83, -79.95],
    "zoom": 12,
    "tagline": "Historic peninsula + Lowcountry urbanism",
    "locale": "es",
    "pbf_region": "north-america/us/south-carolina"
  }
```

Copy it at the end of the file, just before the last `}`, and change it for your city:

- **The slug** (`"charleston"`): a short name that isn't in the file yet, with lowercase letters, numbers and underscores. It becomes the map's address: `map.html?city=your_slug`.
- **`bbox`**: the four numbers from Step 4, as `[south, west, north, east]`.
- **`center`**: the middle of the box, latitude first: `[(south + north) / 2, (west + east) / 2]`.
- **`display_name`**, **`country`** and **`tagline`**: what the city card shows. Write `country` the way the other cards do (`USA`, `Germany`, `Brazil`): it also places the card under its continent in the city list.
- **`country_code`** (optional): the two-letter country code, for the flag on the card.
- **`zoom`** and **`locale`**: required. Leave them as they are.
- **`pbf_region`**: the [Geofabrik](https://download.geofabrik.de/) extract that covers your box. Browse the site down to the smallest region that holds the whole box (smaller files download and read faster) and copy the path of its `.osm.pbf` link, without the ending: `https://download.geofabrik.de/north-america/us/south-carolina-latest.osm.pbf` is `"north-america/us/south-carolina"`. If the box crosses into a second region, list both: Amersfoort has `["europe/netherlands/utrecht", "europe/netherlands/gelderland"]`.

Mind the commas: entries are separated by a comma, so add one after the `}` of the entry above yours. The last entry in the file has none after it. Save the file.

*Time: 3–5 min*

---

## Step 8: Extract Your City

In the terminal from Step 5, run:

    uv run extract-zoning --city your_slug

The first time, it downloads the region's extract from Geofabrik to `~/.cache/cs2-osm-toolkit/pbf/` (on Windows, `C:\Users\<you>\.cache\cs2-osm-toolkit\pbf\`). It can be several hundred MB. Later runs, for this or any city in the same region, reuse it for 7 days.

Then it reads the buildings and land use inside your box, classifies them into CS2 zones and writes `visualizer/cities/your_slug/`: `datos_zonificacion.json`, `manifest.json` and the `tiles/` folder the map draws from. The terminal shows `[1/2]` while it reads the extract and `[2/2]` while it classifies, then a table with the count of each zone and a line starting with `Done.` Reading a big region takes a while.

Note: this toolkit uses OSM land use tags to approximate zoning, not actual municipal zoning data. OSM coverage varies — some cities have very detailed building data, others don't. If your output looks sparse, see the OSM coverage section in [adapting-to-other-cities.md](adapting-to-other-cities.md).

**Roads and services (optional).** These read the same extract, but only work when `pbf_region` is a single region, not a list:

    uv run extract-vial --city your_slug
    uv run extract-services --city your_slug

Each one adds its module to the city's `manifest.json` and keeps the ones already there.

*Time: depends on the size of the region*

---

## Step 9: Open the Map

First update the city list:

    uv run generate-landing

This rewrites `visualizer/index.html` (the city list) and `visualizer/cities.json`, the copy of the registry the map reads. The map only opens cities that are in that copy: if you skip this step, `map.html?city=your_slug` sends you back to the city list.

Browsers won't load the map's data from a page opened with a double-click (`file://`), so serve the `visualizer` folder over HTTP:

    cd ../visualizer
    python -m http.server 8000

Then visit `http://localhost:8000/` (the city list) or `http://localhost:8000/map.html?city=your_slug`. Leave the terminal open while you use the map. **Ctrl+C** stops the server.

On Windows you can also double-click `start-visualizer.bat` in the main folder: it starts the same server on port 8080 and opens `http://localhost:8080` in your browser.

The map opens framed on your box. The layers column on the left lists the zones, each with a checkbox and **Only**. If you also extracted roads or services, each layer gets On, Dim and Off. Point at a building to see its zone, and click it for its details. To take the map into the game, turn on **Playable area**, drag the square over the part you want and press **Export PNG**: see [Using the map in CS2](../README.md#using-the-map-in-cs2-image-overlay).

That's it.

**A picture for the city card (optional).** The card in the city list has no picture until you take one. Install the browser it uses once:

    uv run --group thumbnails playwright install chromium

Then, with the server still running, from a second terminal in `src`:

    uv run --group thumbnails generate-thumbnails --city your_slug --base-url http://localhost:8000

*Time: 1 min*

---

## Several Cities at Once

If you add more than one city, `process-cities` extracts them all, updates the city list and takes the card pictures in one go. Add their entries to `cities.json`, install the browser above once, and run from `src`:

    uv run --group thumbnails process-cities first_slug second_slug

Before downloading any extract, it checks each box: that the numbers are in range and in order, that no side is over 50 km, that the center is inside the box and that the box falls inside its Geofabrik regions. If something is off, it says what and stops. Then it downloads the extracts, extracts three cities at a time (logs in `~/.cache/cs2-osm-toolkit/logs/`), runs `generate-landing` and takes the city card pictures. It only does zoning: roads and services stay as in Step 8. To see the maps, serve the folder as in Step 9.

---

## If Something Breaks

See [TROUBLESHOOTING.md](TROUBLESHOOTING.md) for fixes for the most common errors, including Python or uv not found, mistakes in `cities.json`, a missing `pbf_region`, a box in the wrong order and a map that won't open.

If your issue isn't listed there, open a GitHub Issue at [github.com/Osyanne/CitiesSkylines2-osm-toolkit/issues](https://github.com/Osyanne/CitiesSkylines2-osm-toolkit/issues) — include the error message and what step you were on.
