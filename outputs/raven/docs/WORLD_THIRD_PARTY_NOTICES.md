# World integration — third-party notices

## Reused and adapted code

- **God's Eye View**, Bilawal Sidhu, MIT: https://github.com/bilawalsidhu/gods-eye-view. Inspected source revision `759652207fd1279ece97f0f19af566feb9a82146`. The render governor is reused in `app/static/geo/renderGovernor.mjs`; the TLE parser was adapted in `app/geospatial.py`. Original license is preserved at `app/static/geo/GODS-EYE-LICENSE.txt`.
- **CesiumJS 1.138.0**, Apache-2.0 and included third-party notices: vendored distribution in `app/static/vendor/cesium`, including its `LICENSE.md` and `ThirdParty` assets. No Cesium ion credential is distributed.
- **satellite.js 6.0.2**, MIT: vendored `app/static/vendor/satellite.min.js`; license at `app/static/vendor/SATELLITE-LICENSE.md`. SGP4 orbital positions are predictions, not live telemetry.

## Data attribution and boundaries

Data-provider licenses are separate from the God's Eye View code license. Provider information and source links are displayed in the World workspace. Live data are fetched at runtime, not bundled as a private dataset.

| Provider | Use and attribution |
| --- | --- |
| USGS | Public-domain reported earthquakes; the trailing 24-hour feed may be revised. |
| adsb.lol | Public broadcast aircraft; contributor attribution and ODbL 1.0. Incomplete receiver coverage; do not infer destinations or absence of traffic. |
| CelesTrak | Orbital elements, credited to CelesTrak / Dr. T. S. Kelso; predicted positions. Respect service usage limits. |
| NASA EONET | NASA Earth Observatory Natural Event Tracker; open-event points, not live hazard boundaries. |
| TfL | “Powered by TfL Open Data. Contains OS data © Crown copyright and database rights.” Only public London JamCam snapshots. |
| Launch Library 2 | The Space Devs; provider quota and attribution apply. Schedule data, not live rocket telemetry. |
| AISStream | Optional credential-dependent regional AIS sample; service terms apply. No private-location tracking. |
| OpenStreetMap Nominatim | OpenStreetMap contributors / ODbL; explicit location searches, no autocomplete scraping, cached and rate-limited. |
| Esri World Imagery | Optional basemap with Esri, Maxar, Earthstar Geographics and GIS User Community credit; provider terms still apply. |

No Google photorealistic tiles, simulated traffic, private-person identification, restricted camera access, noncommercial TeleGeography datasets, or proprietary God’s Eye assets were copied into RAVEN. Review each provider's current terms before commercial redistribution of data or deployment beyond this local application.
