SET statement_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = off;
SET check_function_bodies = false;
SET client_min_messages = warning;
SET escape_string_warning = off;

SET search_path = public, pg_catalog;

SET default_tablespace = '';

SET default_with_oids = false;

CREATE USER nsamadmin WITH PASSWORD 'nets0@rer';
CREATE DATABASE nsam_idp OWNER nsamadmin;

\c nsam_idp

CREATE TABLE user_login (
    id integer NOT NULL,
    userid character varying,
    trimmed_userid character varying,
    trimmed_uppercased_userid character varying,
    login_time timestamp without time zone,
    user_agent character varying,
    client_ip inet,
    device_id character varying,
    device_id_expiration timestamp without time zone,
    sp_entity_id character varying,
    session_id character varying,
    shib_idp_session character varying
);


ALTER TABLE user_login OWNER TO nsamadmin;
CREATE SEQUENCE user_login_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

ALTER TABLE user_login_id_seq OWNER TO nsamadmin;
ALTER SEQUENCE user_login_id_seq OWNED BY user_login.id;
ALTER TABLE ONLY user_login ALTER COLUMN id SET DEFAULT nextval('user_login_id_seq'::regclass);
ALTER TABLE ONLY user_login
    ADD CONSTRAINT user_login_pkey PRIMARY KEY (id);

CREATE INDEX userid_idx on user_login (userid);
CREATE INDEX deviceid_idx on user_login (device_id);


CREATE TABLE last_login (
    userid character varying NOT NULL,
    login_time timestamp without time zone,
    first_prev_login_time timestamp without time zone,
    device_id character varying,
    first_prev_device_id character varying
);

ALTER TABLE last_login OWNER TO nsamadmin;
ALTER TABLE ONLY last_login
    ADD CONSTRAINT last_login_pkey PRIMARY KEY (userid);

CREATE INDEX last_login_deviceid_idx on last_login (device_id);


CREATE TABLE device_users (
    device_id character varying NOT NULL,
    userid character varying NOT NULL,
    login_time timestamp without time zone,
    first_login_time timestamp without time zone,
    user_agent character varying
);

ALTER TABLE device_users OWNER TO nsamadmin;
CREATE INDEX device_users_id_idx on device_users (device_id, userid);


CREATE TABLE device_mgmt (
    device_id character varying NOT NULL,
    userid character varying NOT NULL,
    usage character varying,
    expiration timestamp without time zone,
    user_state text,
    created timestamp without time zone,
    updated timestamp without time zone
);

ALTER TABLE device_mgmt OWNER TO nsamadmin;
ALTER TABLE ONLY device_mgmt
    ADD CONSTRAINT device_mgmt_pkey PRIMARY KEY (device_id);

CREATE TABLE user_config (
    userid character varying NOT NULL,
    otp_way character varying NOT NULL,
    cellphone_number character varying,
    email character varying,
    enable_totp boolean,
    created timestamp without time zone,
    updated timestamp without time zone
);

ALTER TABLE user_config OWNER TO nsamadmin;
ALTER TABLE ONLY user_config
    ADD CONSTRAINT user_config_pkey PRIMARY KEY (userid);

CREATE TABLE users_seeds (
    userid character varying NOT NULL,
    seed character varying NOT NULL,
    created timestamp without time zone
);

ALTER TABLE users_seeds OWNER TO nsamadmin;
ALTER TABLE ONLY users_seeds
    ADD CONSTRAINT users_seeds_pkey PRIMARY KEY (userid,seed);

CREATE TABLE ticket_validation (
    ticket_id character varying NOT NULL,
    userid character varying,
    type character varying,
    value character varying,
    expire timestamp without time zone,
    created timestamp without time zone
);

CREATE INDEX ticket_id_idx on ticket_validation (ticket_id);
CREATE INDEX entry_idx on ticket_validation (ticket_id,userid,value);

ALTER TABLE ticket_validation OWNER TO nsamadmin;
