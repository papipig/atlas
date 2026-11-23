# Connectors

This folder contains one file per connector.

Current:
- rss.py (implemented)

Planned:
- scrape.py
- social_x.py
- facebook.py

Connector contract:
- inherit BaseConnector
- implement run(limit_per_feed)
- return ConnectorRunResult (mode, items, errors)

Only connectors registered in registry.py are active.
