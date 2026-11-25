DELETE FROM user_rss_source_prefs
WHERE source_id IN (
  SELECT id
  FROM rss_sources
  WHERE active = FALSE OR status = 'unavailable'
);

DELETE FROM rss_sources
WHERE active = FALSE OR status = 'unavailable';
