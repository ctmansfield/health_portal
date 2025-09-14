-- List all tables and views in the public and medications schema
SELECT table_schema, table_name, table_type
FROM information_schema.tables
WHERE table_schema IN ('public', 'medications', 'analytics')
ORDER BY table_schema, table_name;

-- List columns for tables
SELECT table_schema, table_name, column_name, data_type
FROM information_schema.columns
WHERE table_schema IN ('public', 'medications', 'analytics')
ORDER BY table_schema, table_name, ordinal_position;