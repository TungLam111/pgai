--FEATURE-FLAG: text_to_sql

create table ai.semantic_catalog_obj
( objtype pg_catalog.text not null      -- required for dump/restore to function
, objnames pg_catalog.text[] not null   -- required for dump/restore to function
, objargs pg_catalog.text[] not null    -- required for dump/restore to function
, classid pg_catalog.oid not null       -- required for event triggers to function
, objid pg_catalog.oid not null         -- required for event triggers to function
, objsubid pg_catalog.int4 not null     -- required for event triggers to function
, description pg_catalog.text not null  -- the description
, primary key (objtype, objnames, objargs)
);
create index on ai.semantic_catalog_obj (classid, objid, objsubid);
perform pg_catalog.pg_extension_config_dump('ai.semantic_catalog_obj'::pg_catalog.regclass, '');

create table ai.semantic_catalog_sql
( id pg_catalog.int4 not null primary key generated by default as identity
, sql pg_catalog.text not null
, description pg_catalog.text not null
);
perform pg_catalog.pg_extension_config_dump('ai.semantic_catalog_sql'::pg_catalog.regclass, '');
perform pg_catalog.pg_extension_config_dump('ai.semantic_catalog_sql_id_seq'::pg_catalog.regclass, '');

create table ai.semantic_catalog
( id pg_catalog.int4 not null primary key generated by default as identity
, "name" pg_catalog.text not null unique
, obj_vectorizer_id pg_catalog.int4 not null references ai.vectorizer(id)
, sql_vectorizer_id pg_catalog.int4 not null references ai.vectorizer(id)
);
perform pg_catalog.pg_extension_config_dump('ai.semantic_catalog'::pg_catalog.regclass, '');
perform pg_catalog.pg_extension_config_dump('ai.semantic_catalog_id_seq'::pg_catalog.regclass, '');
