-- Maschinen Excel Import Berechtigung
INSERT OR IGNORE INTO permissions (name, description)
VALUES ('machines.excel_import', 'Maschinen aus Excel importieren');

INSERT OR IGNORE INTO role_permissions (role_id, permission_id)
SELECT r.id, p.id
FROM roles r
JOIN permissions p
WHERE lower(r.name) = 'admin'
  AND p.name = 'machines.excel_import';
