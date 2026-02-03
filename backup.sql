--
-- PostgreSQL database dump
--

\restrict kqO8E5XeiZYUDUhIKkYJvajOjESFI5ihR8nkwkF4bYbD6aDxxa4rx64i0rCAHGM

-- Dumped from database version 17.7 (Ubuntu 17.7-3.pgdg24.04+1)
-- Dumped by pg_dump version 17.7 (Ubuntu 17.7-3.pgdg24.04+1)

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET transaction_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: activity_log; Type: TABLE; Schema: public; Owner: sourcepoint_admin
--

CREATE TABLE public.activity_log (
    id integer NOT NULL,
    user_id integer NOT NULL,
    action character varying(255) NOT NULL,
    details text,
    ip_address character varying(50),
    "timestamp" timestamp without time zone
);


ALTER TABLE public.activity_log OWNER TO sourcepoint_admin;

--
-- Name: activity_log_id_seq; Type: SEQUENCE; Schema: public; Owner: sourcepoint_admin
--

CREATE SEQUENCE public.activity_log_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.activity_log_id_seq OWNER TO sourcepoint_admin;

--
-- Name: activity_log_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: sourcepoint_admin
--

ALTER SEQUENCE public.activity_log_id_seq OWNED BY public.activity_log.id;


--
-- Name: activity_update; Type: TABLE; Schema: public; Owner: sourcepoint_admin
--

CREATE TABLE public.activity_update (
    id integer NOT NULL,
    content text NOT NULL,
    "timestamp" timestamp without time zone,
    user_id integer NOT NULL
);


ALTER TABLE public.activity_update OWNER TO sourcepoint_admin;

--
-- Name: activity_update_id_seq; Type: SEQUENCE; Schema: public; Owner: sourcepoint_admin
--

CREATE SEQUENCE public.activity_update_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.activity_update_id_seq OWNER TO sourcepoint_admin;

--
-- Name: activity_update_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: sourcepoint_admin
--

ALTER SEQUENCE public.activity_update_id_seq OWNED BY public.activity_update.id;


--
-- Name: affiliate_ad; Type: TABLE; Schema: public; Owner: sourcepoint_admin
--

CREATE TABLE public.affiliate_ad (
    id integer NOT NULL,
    ad_name character varying(100) NOT NULL,
    affiliate_link text NOT NULL
);


ALTER TABLE public.affiliate_ad OWNER TO sourcepoint_admin;

--
-- Name: affiliate_ad_id_seq; Type: SEQUENCE; Schema: public; Owner: sourcepoint_admin
--

CREATE SEQUENCE public.affiliate_ad_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.affiliate_ad_id_seq OWNER TO sourcepoint_admin;

--
-- Name: affiliate_ad_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: sourcepoint_admin
--

ALTER SEQUENCE public.affiliate_ad_id_seq OWNED BY public.affiliate_ad.id;


--
-- Name: alembic_version; Type: TABLE; Schema: public; Owner: sourcepoint_admin
--

CREATE TABLE public.alembic_version (
    version_num character varying(32) NOT NULL
);


ALTER TABLE public.alembic_version OWNER TO sourcepoint_admin;

--
-- Name: brd; Type: TABLE; Schema: public; Owner: sourcepoint_admin
--

CREATE TABLE public.brd (
    id integer NOT NULL,
    project_id integer NOT NULL,
    executive_summary text,
    project_objectives text,
    project_scope text,
    business_requirements text,
    key_stakeholders text,
    project_constraints text,
    cost_benefit_analysis text,
    executive_summary_label character varying(100) DEFAULT 'Executive Summary'::character varying,
    project_objectives_label character varying(100) DEFAULT 'Project Objectives'::character varying,
    project_scope_label character varying(100) DEFAULT 'Project Scope'::character varying,
    business_requirements_label character varying(100) DEFAULT 'Business Requirements'::character varying,
    key_stakeholders_label character varying(100) DEFAULT 'Key Stakeholders'::character varying,
    project_constraints_label character varying(100) DEFAULT 'Project Constraints'::character varying,
    cost_benefit_analysis_label character varying(100) DEFAULT 'Cost-Benefit Analysis'::character varying
);


ALTER TABLE public.brd OWNER TO sourcepoint_admin;

--
-- Name: brd_id_seq; Type: SEQUENCE; Schema: public; Owner: sourcepoint_admin
--

CREATE SEQUENCE public.brd_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.brd_id_seq OWNER TO sourcepoint_admin;

--
-- Name: brd_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: sourcepoint_admin
--

ALTER SEQUENCE public.brd_id_seq OWNED BY public.brd.id;


--
-- Name: candidate_contacts; Type: TABLE; Schema: public; Owner: sourcepoint_admin
--

CREATE TABLE public.candidate_contacts (
    candidate_id integer NOT NULL,
    developer_id integer NOT NULL
);


ALTER TABLE public.candidate_contacts OWNER TO sourcepoint_admin;

--
-- Name: cart; Type: TABLE; Schema: public; Owner: sourcepoint_admin
--

CREATE TABLE public.cart (
    id integer NOT NULL,
    user_id integer NOT NULL,
    created_at timestamp without time zone
);


ALTER TABLE public.cart OWNER TO sourcepoint_admin;

--
-- Name: cart_id_seq; Type: SEQUENCE; Schema: public; Owner: sourcepoint_admin
--

CREATE SEQUENCE public.cart_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.cart_id_seq OWNER TO sourcepoint_admin;

--
-- Name: cart_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: sourcepoint_admin
--

ALTER SEQUENCE public.cart_id_seq OWNED BY public.cart.id;


--
-- Name: cart_item; Type: TABLE; Schema: public; Owner: sourcepoint_admin
--

CREATE TABLE public.cart_item (
    id integer NOT NULL,
    cart_id integer NOT NULL,
    product_id integer NOT NULL,
    quantity integer NOT NULL
);


ALTER TABLE public.cart_item OWNER TO sourcepoint_admin;

--
-- Name: cart_item_id_seq; Type: SEQUENCE; Schema: public; Owner: sourcepoint_admin
--

CREATE SEQUENCE public.cart_item_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.cart_item_id_seq OWNER TO sourcepoint_admin;

--
-- Name: cart_item_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: sourcepoint_admin
--

ALTER SEQUENCE public.cart_item_id_seq OWNED BY public.cart_item.id;


--
-- Name: chat_history; Type: TABLE; Schema: public; Owner: sourcepoint_admin
--

CREATE TABLE public.chat_history (
    id integer NOT NULL,
    user_id integer NOT NULL,
    subject character varying(50) NOT NULL,
    role character varying(10) NOT NULL,
    message text NOT NULL,
    "timestamp" timestamp without time zone
);


ALTER TABLE public.chat_history OWNER TO sourcepoint_admin;

--
-- Name: chat_history_id_seq; Type: SEQUENCE; Schema: public; Owner: sourcepoint_admin
--

CREATE SEQUENCE public.chat_history_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.chat_history_id_seq OWNER TO sourcepoint_admin;

--
-- Name: chat_history_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: sourcepoint_admin
--

ALTER SEQUENCE public.chat_history_id_seq OWNED BY public.chat_history.id;


--
-- Name: code_snippet; Type: TABLE; Schema: public; Owner: sourcepoint_admin
--

CREATE TABLE public.code_snippet (
    id integer NOT NULL,
    sender_id integer NOT NULL,
    recipient_id integer NOT NULL,
    code text NOT NULL,
    language character varying(50) NOT NULL,
    "timestamp" timestamp without time zone
);


ALTER TABLE public.code_snippet OWNER TO sourcepoint_admin;

--
-- Name: code_snippet_id_seq; Type: SEQUENCE; Schema: public; Owner: sourcepoint_admin
--

CREATE SEQUENCE public.code_snippet_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.code_snippet_id_seq OWNER TO sourcepoint_admin;

--
-- Name: code_snippet_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: sourcepoint_admin
--

ALTER SEQUENCE public.code_snippet_id_seq OWNED BY public.code_snippet.id;


--
-- Name: code_test_submission; Type: TABLE; Schema: public; Owner: sourcepoint_admin
--

CREATE TABLE public.code_test_submission (
    id integer NOT NULL,
    candidate_id integer NOT NULL,
    recipient_id integer NOT NULL,
    code text NOT NULL,
    output text,
    language character varying(50) NOT NULL,
    submitted_at timestamp without time zone
);


ALTER TABLE public.code_test_submission OWNER TO sourcepoint_admin;

--
-- Name: code_test_submission_id_seq; Type: SEQUENCE; Schema: public; Owner: sourcepoint_admin
--

CREATE SEQUENCE public.code_test_submission_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.code_test_submission_id_seq OWNER TO sourcepoint_admin;

--
-- Name: code_test_submission_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: sourcepoint_admin
--

ALTER SEQUENCE public.code_test_submission_id_seq OWNED BY public.code_test_submission.id;


--
-- Name: emi_payment; Type: TABLE; Schema: public; Owner: sourcepoint_admin
--

CREATE TABLE public.emi_payment (
    id integer NOT NULL,
    plan_id integer NOT NULL,
    installment_number integer DEFAULT 1 NOT NULL,
    due_date date NOT NULL,
    amount numeric(10,2) NOT NULL,
    description character varying(200),
    status character varying(20) DEFAULT 'Pending'::character varying,
    reminder_days_before integer DEFAULT 3,
    reminder_sent boolean DEFAULT false,
    payment_date timestamp without time zone
);


ALTER TABLE public.emi_payment OWNER TO sourcepoint_admin;

--
-- Name: emi_payment_id_seq; Type: SEQUENCE; Schema: public; Owner: sourcepoint_admin
--

CREATE SEQUENCE public.emi_payment_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.emi_payment_id_seq OWNER TO sourcepoint_admin;

--
-- Name: emi_payment_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: sourcepoint_admin
--

ALTER SEQUENCE public.emi_payment_id_seq OWNED BY public.emi_payment.id;


--
-- Name: emi_plan; Type: TABLE; Schema: public; Owner: sourcepoint_admin
--

CREATE TABLE public.emi_plan (
    id integer NOT NULL,
    title character varying(150) NOT NULL,
    total_principal numeric(10,2) NOT NULL,
    created_at timestamp without time zone DEFAULT (now() AT TIME ZONE 'utc'::text),
    is_active boolean DEFAULT true,
    borrower_id integer NOT NULL,
    lender_id integer NOT NULL
);


ALTER TABLE public.emi_plan OWNER TO sourcepoint_admin;

--
-- Name: emi_plan_id_seq; Type: SEQUENCE; Schema: public; Owner: sourcepoint_admin
--

CREATE SEQUENCE public.emi_plan_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.emi_plan_id_seq OWNER TO sourcepoint_admin;

--
-- Name: emi_plan_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: sourcepoint_admin
--

ALTER SEQUENCE public.emi_plan_id_seq OWNED BY public.emi_plan.id;


--
-- Name: feedback; Type: TABLE; Schema: public; Owner: sourcepoint_admin
--

CREATE TABLE public.feedback (
    id integer NOT NULL,
    moderator_id integer NOT NULL,
    candidate_id integer NOT NULL,
    code_correctness integer NOT NULL,
    code_efficiency integer NOT NULL,
    code_readability integer NOT NULL,
    problem_solving integer NOT NULL,
    time_management integer NOT NULL,
    remarks text,
    created_at timestamp without time zone
);


ALTER TABLE public.feedback OWNER TO sourcepoint_admin;

--
-- Name: feedback_id_seq; Type: SEQUENCE; Schema: public; Owner: sourcepoint_admin
--

CREATE SEQUENCE public.feedback_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.feedback_id_seq OWNER TO sourcepoint_admin;

--
-- Name: feedback_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: sourcepoint_admin
--

ALTER SEQUENCE public.feedback_id_seq OWNED BY public.feedback.id;


--
-- Name: invoice; Type: TABLE; Schema: public; Owner: sourcepoint_admin
--

CREATE TABLE public.invoice (
    id integer NOT NULL,
    invoice_number character varying(50) NOT NULL,
    recipient_name character varying(100) NOT NULL,
    recipient_email character varying(120) NOT NULL,
    bill_to_address text,
    ship_to_address text,
    order_id character varying(50),
    subtotal numeric(10,2) NOT NULL,
    tax numeric(10,2) NOT NULL,
    total_amount numeric(10,2) NOT NULL,
    due_date date,
    notes text,
    payment_details text,
    created_at timestamp without time zone,
    admin_id integer NOT NULL,
    status character varying(20) DEFAULT 'Unpaid'::character varying NOT NULL
);


ALTER TABLE public.invoice OWNER TO sourcepoint_admin;

--
-- Name: invoice_id_seq; Type: SEQUENCE; Schema: public; Owner: sourcepoint_admin
--

CREATE SEQUENCE public.invoice_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.invoice_id_seq OWNER TO sourcepoint_admin;

--
-- Name: invoice_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: sourcepoint_admin
--

ALTER SEQUENCE public.invoice_id_seq OWNED BY public.invoice.id;


--
-- Name: invoice_item; Type: TABLE; Schema: public; Owner: sourcepoint_admin
--

CREATE TABLE public.invoice_item (
    id integer NOT NULL,
    description character varying(200) NOT NULL,
    quantity integer NOT NULL,
    price numeric(10,2) NOT NULL,
    invoice_id integer NOT NULL
);


ALTER TABLE public.invoice_item OWNER TO sourcepoint_admin;

--
-- Name: invoice_item_id_seq; Type: SEQUENCE; Schema: public; Owner: sourcepoint_admin
--

CREATE SEQUENCE public.invoice_item_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.invoice_item_id_seq OWNER TO sourcepoint_admin;

--
-- Name: invoice_item_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: sourcepoint_admin
--

ALTER SEQUENCE public.invoice_item_id_seq OWNED BY public.invoice_item.id;


--
-- Name: job_application; Type: TABLE; Schema: public; Owner: sourcepoint_admin
--

CREATE TABLE public.job_application (
    id integer NOT NULL,
    user_id integer NOT NULL,
    job_id integer NOT NULL,
    status character varying(20) NOT NULL,
    applied_at timestamp without time zone,
    resume_url character varying(500)
);


ALTER TABLE public.job_application OWNER TO sourcepoint_admin;

--
-- Name: job_application_id_seq; Type: SEQUENCE; Schema: public; Owner: sourcepoint_admin
--

CREATE SEQUENCE public.job_application_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.job_application_id_seq OWNER TO sourcepoint_admin;

--
-- Name: job_application_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: sourcepoint_admin
--

ALTER SEQUENCE public.job_application_id_seq OWNED BY public.job_application.id;


--
-- Name: job_opening; Type: TABLE; Schema: public; Owner: sourcepoint_admin
--

CREATE TABLE public.job_opening (
    id integer NOT NULL,
    job_id character varying(36) NOT NULL,
    title character varying(150) NOT NULL,
    description text NOT NULL,
    is_open boolean NOT NULL,
    created_at timestamp without time zone
);


ALTER TABLE public.job_opening OWNER TO sourcepoint_admin;

--
-- Name: job_opening_id_seq; Type: SEQUENCE; Schema: public; Owner: sourcepoint_admin
--

CREATE SEQUENCE public.job_opening_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.job_opening_id_seq OWNER TO sourcepoint_admin;

--
-- Name: job_opening_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: sourcepoint_admin
--

ALTER SEQUENCE public.job_opening_id_seq OWNED BY public.job_opening.id;


--
-- Name: learning_content; Type: TABLE; Schema: public; Owner: sourcepoint_admin
--

CREATE TABLE public.learning_content (
    id character varying(50) NOT NULL,
    content text NOT NULL,
    last_updated timestamp without time zone
);


ALTER TABLE public.learning_content OWNER TO sourcepoint_admin;

--
-- Name: message; Type: TABLE; Schema: public; Owner: sourcepoint_admin
--

CREATE TABLE public.message (
    id integer NOT NULL,
    sender_id integer NOT NULL,
    recipient_id integer NOT NULL,
    body text NOT NULL,
    "timestamp" timestamp without time zone
);


ALTER TABLE public.message OWNER TO sourcepoint_admin;

--
-- Name: message_id_seq; Type: SEQUENCE; Schema: public; Owner: sourcepoint_admin
--

CREATE SEQUENCE public.message_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.message_id_seq OWNER TO sourcepoint_admin;

--
-- Name: message_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: sourcepoint_admin
--

ALTER SEQUENCE public.message_id_seq OWNED BY public.message.id;


--
-- Name: moderator_assignment_history; Type: TABLE; Schema: public; Owner: sourcepoint_admin
--

CREATE TABLE public.moderator_assignment_history (
    id integer NOT NULL,
    candidate_id integer NOT NULL,
    moderator_id integer NOT NULL,
    problem_statement_id integer NOT NULL,
    assigned_at timestamp without time zone
);


ALTER TABLE public.moderator_assignment_history OWNER TO sourcepoint_admin;

--
-- Name: moderator_assignment_history_id_seq; Type: SEQUENCE; Schema: public; Owner: sourcepoint_admin
--

CREATE SEQUENCE public.moderator_assignment_history_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.moderator_assignment_history_id_seq OWNER TO sourcepoint_admin;

--
-- Name: moderator_assignment_history_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: sourcepoint_admin
--

ALTER SEQUENCE public.moderator_assignment_history_id_seq OWNED BY public.moderator_assignment_history.id;


--
-- Name: order; Type: TABLE; Schema: public; Owner: sourcepoint_admin
--

CREATE TABLE public."order" (
    id integer NOT NULL,
    order_number character varying(50) NOT NULL,
    user_id integer NOT NULL,
    total_amount numeric(10,2) NOT NULL,
    status character varying(20),
    shipping_address text NOT NULL,
    created_at timestamp without time zone,
    billing_address text,
    seller_id integer,
    shipping_street character varying(200),
    shipping_city character varying(100),
    shipping_state character varying(100),
    shipping_zip character varying(20),
    shipping_country character varying(100)
);


ALTER TABLE public."order" OWNER TO sourcepoint_admin;

--
-- Name: order_id_seq; Type: SEQUENCE; Schema: public; Owner: sourcepoint_admin
--

CREATE SEQUENCE public.order_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.order_id_seq OWNER TO sourcepoint_admin;

--
-- Name: order_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: sourcepoint_admin
--

ALTER SEQUENCE public.order_id_seq OWNED BY public."order".id;


--
-- Name: order_item; Type: TABLE; Schema: public; Owner: sourcepoint_admin
--

CREATE TABLE public.order_item (
    id integer NOT NULL,
    order_id integer NOT NULL,
    product_name character varying(150) NOT NULL,
    quantity integer NOT NULL,
    price_at_purchase numeric(10,2) NOT NULL
);


ALTER TABLE public.order_item OWNER TO sourcepoint_admin;

--
-- Name: order_item_id_seq; Type: SEQUENCE; Schema: public; Owner: sourcepoint_admin
--

CREATE SEQUENCE public.order_item_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.order_item_id_seq OWNER TO sourcepoint_admin;

--
-- Name: order_item_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: sourcepoint_admin
--

ALTER SEQUENCE public.order_item_id_seq OWNED BY public.order_item.id;


--
-- Name: problem_statement; Type: TABLE; Schema: public; Owner: sourcepoint_admin
--

CREATE TABLE public.problem_statement (
    id integer NOT NULL,
    title character varying(200) NOT NULL,
    description text NOT NULL,
    difficulty character varying(20),
    created_at timestamp without time zone,
    created_by_id integer
);


ALTER TABLE public.problem_statement OWNER TO sourcepoint_admin;

--
-- Name: problem_statement_id_seq; Type: SEQUENCE; Schema: public; Owner: sourcepoint_admin
--

CREATE SEQUENCE public.problem_statement_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.problem_statement_id_seq OWNER TO sourcepoint_admin;

--
-- Name: problem_statement_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: sourcepoint_admin
--

ALTER SEQUENCE public.problem_statement_id_seq OWNED BY public.problem_statement.id;


--
-- Name: product; Type: TABLE; Schema: public; Owner: sourcepoint_admin
--

CREATE TABLE public.product (
    id integer NOT NULL,
    product_code character varying(50) NOT NULL,
    name character varying(150) NOT NULL,
    stock integer NOT NULL,
    price numeric(10,2) NOT NULL,
    description text,
    image_url text,
    category character varying(50),
    brand character varying(100),
    mrp numeric(10,2),
    warranty character varying(200),
    return_policy character varying(200),
    seller_id integer
);


ALTER TABLE public.product OWNER TO sourcepoint_admin;

--
-- Name: product_id_seq; Type: SEQUENCE; Schema: public; Owner: sourcepoint_admin
--

CREATE SEQUENCE public.product_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.product_id_seq OWNER TO sourcepoint_admin;

--
-- Name: product_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: sourcepoint_admin
--

ALTER SEQUENCE public.product_id_seq OWNED BY public.product.id;


--
-- Name: product_image; Type: TABLE; Schema: public; Owner: sourcepoint_admin
--

CREATE TABLE public.product_image (
    id integer NOT NULL,
    product_id integer NOT NULL,
    image_url text NOT NULL
);


ALTER TABLE public.product_image OWNER TO sourcepoint_admin;

--
-- Name: product_image_id_seq; Type: SEQUENCE; Schema: public; Owner: sourcepoint_admin
--

CREATE SEQUENCE public.product_image_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.product_image_id_seq OWNER TO sourcepoint_admin;

--
-- Name: product_image_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: sourcepoint_admin
--

ALTER SEQUENCE public.product_image_id_seq OWNED BY public.product_image.id;


--
-- Name: project; Type: TABLE; Schema: public; Owner: sourcepoint_admin
--

CREATE TABLE public.project (
    id integer NOT NULL,
    name character varying(150) NOT NULL,
    description text,
    start_date date,
    end_date date,
    budget numeric(10,2) NOT NULL,
    status character varying(50) NOT NULL
);


ALTER TABLE public.project OWNER TO sourcepoint_admin;

--
-- Name: project_id_seq; Type: SEQUENCE; Schema: public; Owner: sourcepoint_admin
--

CREATE SEQUENCE public.project_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.project_id_seq OWNER TO sourcepoint_admin;

--
-- Name: project_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: sourcepoint_admin
--

ALTER SEQUENCE public.project_id_seq OWNED BY public.project.id;


--
-- Name: seller_inventory; Type: TABLE; Schema: public; Owner: sourcepoint_admin
--

CREATE TABLE public.seller_inventory (
    id integer NOT NULL,
    seller_id integer NOT NULL,
    product_id integer NOT NULL,
    stock integer
);


ALTER TABLE public.seller_inventory OWNER TO sourcepoint_admin;

--
-- Name: seller_inventory_id_seq; Type: SEQUENCE; Schema: public; Owner: sourcepoint_admin
--

CREATE SEQUENCE public.seller_inventory_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.seller_inventory_id_seq OWNER TO sourcepoint_admin;

--
-- Name: seller_inventory_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: sourcepoint_admin
--

ALTER SEQUENCE public.seller_inventory_id_seq OWNED BY public.seller_inventory.id;


--
-- Name: stock_request; Type: TABLE; Schema: public; Owner: sourcepoint_admin
--

CREATE TABLE public.stock_request (
    id integer NOT NULL,
    seller_id integer NOT NULL,
    product_id integer NOT NULL,
    quantity integer NOT NULL,
    status character varying(20) NOT NULL,
    request_date timestamp without time zone,
    response_date timestamp without time zone,
    admin_note character varying(255)
);


ALTER TABLE public.stock_request OWNER TO sourcepoint_admin;

--
-- Name: stock_request_id_seq; Type: SEQUENCE; Schema: public; Owner: sourcepoint_admin
--

CREATE SEQUENCE public.stock_request_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.stock_request_id_seq OWNER TO sourcepoint_admin;

--
-- Name: stock_request_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: sourcepoint_admin
--

ALTER SEQUENCE public.stock_request_id_seq OWNED BY public.stock_request.id;


--
-- Name: transaction; Type: TABLE; Schema: public; Owner: sourcepoint_admin
--

CREATE TABLE public.transaction (
    id integer NOT NULL,
    description character varying(200) NOT NULL,
    amount numeric(10,2) NOT NULL,
    date date NOT NULL,
    category character varying(50) NOT NULL,
    project_id integer NOT NULL
);


ALTER TABLE public.transaction OWNER TO sourcepoint_admin;

--
-- Name: transaction_id_seq; Type: SEQUENCE; Schema: public; Owner: sourcepoint_admin
--

CREATE SEQUENCE public.transaction_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.transaction_id_seq OWNER TO sourcepoint_admin;

--
-- Name: transaction_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: sourcepoint_admin
--

ALTER SEQUENCE public.transaction_id_seq OWNED BY public.transaction.id;


--
-- Name: user; Type: TABLE; Schema: public; Owner: sourcepoint_admin
--

CREATE TABLE public."user" (
    id integer NOT NULL,
    username character varying(100) NOT NULL,
    email character varying(120) NOT NULL,
    password_hash character varying(128) NOT NULL,
    role character varying(20) NOT NULL,
    is_approved boolean NOT NULL,
    avatar_url character varying(200) NOT NULL,
    problem_statement_id integer,
    test_start_time timestamp without time zone,
    test_end_time timestamp without time zone,
    is_active boolean NOT NULL,
    reminder_sent boolean NOT NULL,
    test_completed boolean NOT NULL,
    moderator_id integer,
    mobile_number character varying(20),
    primary_skill character varying(100),
    primary_skill_experience character varying(50),
    secondary_skill character varying(100),
    secondary_skill_experience character varying(50),
    resume_filename character varying(200),
    secret_question character varying(255),
    secret_answer_hash character varying(128),
    meeting_link character varying(255)
);


ALTER TABLE public."user" OWNER TO sourcepoint_admin;

--
-- Name: user_id_seq; Type: SEQUENCE; Schema: public; Owner: sourcepoint_admin
--

CREATE SEQUENCE public.user_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.user_id_seq OWNER TO sourcepoint_admin;

--
-- Name: user_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: sourcepoint_admin
--

ALTER SEQUENCE public.user_id_seq OWNED BY public."user".id;


--
-- Name: activity_log id; Type: DEFAULT; Schema: public; Owner: sourcepoint_admin
--

ALTER TABLE ONLY public.activity_log ALTER COLUMN id SET DEFAULT nextval('public.activity_log_id_seq'::regclass);


--
-- Name: activity_update id; Type: DEFAULT; Schema: public; Owner: sourcepoint_admin
--

ALTER TABLE ONLY public.activity_update ALTER COLUMN id SET DEFAULT nextval('public.activity_update_id_seq'::regclass);


--
-- Name: affiliate_ad id; Type: DEFAULT; Schema: public; Owner: sourcepoint_admin
--

ALTER TABLE ONLY public.affiliate_ad ALTER COLUMN id SET DEFAULT nextval('public.affiliate_ad_id_seq'::regclass);


--
-- Name: brd id; Type: DEFAULT; Schema: public; Owner: sourcepoint_admin
--

ALTER TABLE ONLY public.brd ALTER COLUMN id SET DEFAULT nextval('public.brd_id_seq'::regclass);


--
-- Name: cart id; Type: DEFAULT; Schema: public; Owner: sourcepoint_admin
--

ALTER TABLE ONLY public.cart ALTER COLUMN id SET DEFAULT nextval('public.cart_id_seq'::regclass);


--
-- Name: cart_item id; Type: DEFAULT; Schema: public; Owner: sourcepoint_admin
--

ALTER TABLE ONLY public.cart_item ALTER COLUMN id SET DEFAULT nextval('public.cart_item_id_seq'::regclass);


--
-- Name: chat_history id; Type: DEFAULT; Schema: public; Owner: sourcepoint_admin
--

ALTER TABLE ONLY public.chat_history ALTER COLUMN id SET DEFAULT nextval('public.chat_history_id_seq'::regclass);


--
-- Name: code_snippet id; Type: DEFAULT; Schema: public; Owner: sourcepoint_admin
--

ALTER TABLE ONLY public.code_snippet ALTER COLUMN id SET DEFAULT nextval('public.code_snippet_id_seq'::regclass);


--
-- Name: code_test_submission id; Type: DEFAULT; Schema: public; Owner: sourcepoint_admin
--

ALTER TABLE ONLY public.code_test_submission ALTER COLUMN id SET DEFAULT nextval('public.code_test_submission_id_seq'::regclass);


--
-- Name: emi_payment id; Type: DEFAULT; Schema: public; Owner: sourcepoint_admin
--

ALTER TABLE ONLY public.emi_payment ALTER COLUMN id SET DEFAULT nextval('public.emi_payment_id_seq'::regclass);


--
-- Name: emi_plan id; Type: DEFAULT; Schema: public; Owner: sourcepoint_admin
--

ALTER TABLE ONLY public.emi_plan ALTER COLUMN id SET DEFAULT nextval('public.emi_plan_id_seq'::regclass);


--
-- Name: feedback id; Type: DEFAULT; Schema: public; Owner: sourcepoint_admin
--

ALTER TABLE ONLY public.feedback ALTER COLUMN id SET DEFAULT nextval('public.feedback_id_seq'::regclass);


--
-- Name: invoice id; Type: DEFAULT; Schema: public; Owner: sourcepoint_admin
--

ALTER TABLE ONLY public.invoice ALTER COLUMN id SET DEFAULT nextval('public.invoice_id_seq'::regclass);


--
-- Name: invoice_item id; Type: DEFAULT; Schema: public; Owner: sourcepoint_admin
--

ALTER TABLE ONLY public.invoice_item ALTER COLUMN id SET DEFAULT nextval('public.invoice_item_id_seq'::regclass);


--
-- Name: job_application id; Type: DEFAULT; Schema: public; Owner: sourcepoint_admin
--

ALTER TABLE ONLY public.job_application ALTER COLUMN id SET DEFAULT nextval('public.job_application_id_seq'::regclass);


--
-- Name: job_opening id; Type: DEFAULT; Schema: public; Owner: sourcepoint_admin
--

ALTER TABLE ONLY public.job_opening ALTER COLUMN id SET DEFAULT nextval('public.job_opening_id_seq'::regclass);


--
-- Name: message id; Type: DEFAULT; Schema: public; Owner: sourcepoint_admin
--

ALTER TABLE ONLY public.message ALTER COLUMN id SET DEFAULT nextval('public.message_id_seq'::regclass);


--
-- Name: moderator_assignment_history id; Type: DEFAULT; Schema: public; Owner: sourcepoint_admin
--

ALTER TABLE ONLY public.moderator_assignment_history ALTER COLUMN id SET DEFAULT nextval('public.moderator_assignment_history_id_seq'::regclass);


--
-- Name: order id; Type: DEFAULT; Schema: public; Owner: sourcepoint_admin
--

ALTER TABLE ONLY public."order" ALTER COLUMN id SET DEFAULT nextval('public.order_id_seq'::regclass);


--
-- Name: order_item id; Type: DEFAULT; Schema: public; Owner: sourcepoint_admin
--

ALTER TABLE ONLY public.order_item ALTER COLUMN id SET DEFAULT nextval('public.order_item_id_seq'::regclass);


--
-- Name: problem_statement id; Type: DEFAULT; Schema: public; Owner: sourcepoint_admin
--

ALTER TABLE ONLY public.problem_statement ALTER COLUMN id SET DEFAULT nextval('public.problem_statement_id_seq'::regclass);


--
-- Name: product id; Type: DEFAULT; Schema: public; Owner: sourcepoint_admin
--

ALTER TABLE ONLY public.product ALTER COLUMN id SET DEFAULT nextval('public.product_id_seq'::regclass);


--
-- Name: product_image id; Type: DEFAULT; Schema: public; Owner: sourcepoint_admin
--

ALTER TABLE ONLY public.product_image ALTER COLUMN id SET DEFAULT nextval('public.product_image_id_seq'::regclass);


--
-- Name: project id; Type: DEFAULT; Schema: public; Owner: sourcepoint_admin
--

ALTER TABLE ONLY public.project ALTER COLUMN id SET DEFAULT nextval('public.project_id_seq'::regclass);


--
-- Name: seller_inventory id; Type: DEFAULT; Schema: public; Owner: sourcepoint_admin
--

ALTER TABLE ONLY public.seller_inventory ALTER COLUMN id SET DEFAULT nextval('public.seller_inventory_id_seq'::regclass);


--
-- Name: stock_request id; Type: DEFAULT; Schema: public; Owner: sourcepoint_admin
--

ALTER TABLE ONLY public.stock_request ALTER COLUMN id SET DEFAULT nextval('public.stock_request_id_seq'::regclass);


--
-- Name: transaction id; Type: DEFAULT; Schema: public; Owner: sourcepoint_admin
--

ALTER TABLE ONLY public.transaction ALTER COLUMN id SET DEFAULT nextval('public.transaction_id_seq'::regclass);


--
-- Name: user id; Type: DEFAULT; Schema: public; Owner: sourcepoint_admin
--

ALTER TABLE ONLY public."user" ALTER COLUMN id SET DEFAULT nextval('public.user_id_seq'::regclass);


--
-- Data for Name: activity_log; Type: TABLE DATA; Schema: public; Owner: sourcepoint_admin
--

COPY public.activity_log (id, user_id, action, details, ip_address, "timestamp") FROM stdin;
1	1	Login	User logged in successfully	127.0.0.1	2025-11-23 12:27:43.735481
2	1	Logout	User logged out	127.0.0.1	2025-11-23 12:30:55.470811
3	1	Login	User logged in successfully	127.0.0.1	2025-11-23 12:31:01.794316
4	1	Logout	User logged out	127.0.0.1	2025-11-23 12:36:12.33362
5	15	Login	User logged in successfully	127.0.0.1	2025-11-23 12:36:22.175453
6	15	Logout	User logged out	127.0.0.1	2025-11-23 12:41:42.46732
7	15	Login	User logged in successfully	127.0.0.1	2025-11-23 12:51:28.695058
8	15	Logout	User logged out	127.0.0.1	2025-11-23 12:51:52.349053
9	1	Login	User logged in successfully	127.0.0.1	2025-11-23 12:52:04.876978
10	1	Toggle User Status	Deactivated user Nitya_Nayar	127.0.0.1	2025-11-23 12:52:30.569311
11	1	Toggle User Status	Activated user Nitya_Nayar	127.0.0.1	2025-11-23 12:52:48.173715
12	1	Logout	User logged out	127.0.0.1	2025-11-23 12:58:15.603184
13	1	Login	User logged in successfully	127.0.0.1	2025-11-23 14:33:16.759047
14	1	Cancel Event	Cancelled test for Ruchita_Umalkar	127.0.0.1	2025-11-23 14:48:52.061794
15	1	View Learning Content	Viewed java tutorial	127.0.0.1	2025-11-23 14:53:53.41338
16	1	Update Learning Content	Updated content for java	127.0.0.1	2025-11-23 14:54:06.310235
17	1	View Learning Content	Viewed java tutorial	127.0.0.1	2025-11-23 14:54:07.27517
18	1	View Learning Content	Viewed c tutorial	127.0.0.1	2025-11-23 14:54:13.796409
19	1	Toggle User Status	Deactivated user Nitya_Nayar	127.0.0.1	2025-11-23 14:54:22.511347
20	1	Toggle User Status	Activated user Nitya_Nayar	127.0.0.1	2025-11-23 14:54:26.919328
21	1	Logout	User logged out	127.0.0.1	2025-11-23 15:40:29.921614
22	1	Login	User logged in successfully	127.0.0.1	2025-11-23 15:40:35.933594
23	1	Update Product	Updated product NOBERO Men's Oversized Solid Loose fit Heavy Cotton T-Shirt (Pack of 2)	127.0.0.1	2025-11-23 15:40:52.437175
24	1	Share BRD	Shared BRD for WRD_Finance_03 with gp2239396@gmail.com	127.0.0.1	2025-11-23 15:45:28.274949
25	1	Logout	User logged out	127.0.0.1	2025-11-23 15:47:29.528208
26	15	Login	User logged in successfully	127.0.0.1	2025-11-23 15:47:37.174479
27	15	Logout	User logged out	127.0.0.1	2025-11-23 15:52:50.429108
28	1	Login	User logged in successfully	127.0.0.1	2025-11-23 15:53:04.330103
29	1	Update Order	Updated order ORD-1763913161-15 to Order Accepted	127.0.0.1	2025-11-23 15:53:16.994016
30	1	Logout	User logged out	127.0.0.1	2025-11-23 15:54:05.93627
31	15	Login	User logged in successfully	127.0.0.1	2025-11-23 15:54:13.348396
32	15	Logout	User logged out	127.0.0.1	2025-11-23 15:54:37.18583
33	2	Login	User logged in successfully	127.0.0.1	2025-11-23 15:54:45.341074
34	2	Post Activity	Posted developer activity update	127.0.0.1	2025-11-23 15:54:58.865276
35	2	Logout	User logged out	127.0.0.1	2025-11-23 15:55:22.928498
36	9	Login	User logged in successfully	127.0.0.1	2025-11-23 15:55:39.726568
37	9	Logout	User logged out	127.0.0.1	2025-11-23 15:55:43.52996
38	1	Login	User logged in successfully	127.0.0.1	2025-11-23 15:55:51.097859
39	1	Logout	User logged out	127.0.0.1	2025-11-23 15:56:00.669114
40	4	Login	User logged in successfully	127.0.0.1	2025-11-23 15:56:08.651256
41	4	Logout	User logged out	127.0.0.1	2025-11-23 15:56:35.243927
42	1	Login	User logged in successfully	127.0.0.1	2025-11-23 16:02:04.944639
43	1	Logout	User logged out	127.0.0.1	2025-11-23 16:08:01.366048
44	1	Login	User logged in successfully	127.0.0.1	2025-11-23 16:10:24.48873
45	1	Logout	User logged out	127.0.0.1	2025-11-23 16:10:38.847889
46	1	Login	User logged in successfully	127.0.0.1	2025-11-23 16:30:53.018017
47	1	Update Order	Updated order ORD-1763810116-15 to Order Accepted	127.0.0.1	2025-11-23 16:31:50.478504
48	1	Login	User logged in successfully	122.167.113.11, 172.70.142.72, 10.16.157.6	2025-11-23 16:41:17.80616
49	1	Logout	User logged out	122.167.113.11, 172.69.179.127, 10.17.235.214	2025-11-23 16:42:21.946723
50	1	Login	User logged in successfully	122.167.113.11, 162.158.162.157, 10.16.218.155	2025-11-24 08:24:31.649429
51	1	Login	User logged in successfully	122.167.113.11, 172.69.94.130, 10.17.111.192	2025-11-24 12:51:18.351335
52	1	Send Specific Email	Sent email to 1 recipients. Subject: Sap - InV not working 	152.58.16.112, 172.69.165.64, 10.16.218.155	2025-11-25 03:34:54.822345
53	1	Logout	User logged out	152.58.16.112, 172.69.87.130, 10.17.111.192	2025-11-25 03:43:26.985398
54	1	Login	User logged in successfully	152.58.16.112, 172.69.87.130, 10.17.111.192	2025-11-25 03:43:38.250327
55	1	Logout	User logged out	127.0.0.1	2025-11-25 11:58:44.689628
56	1	Login	User logged in successfully	127.0.0.1	2025-11-25 12:07:10.14544
57	1	Logout	User logged out	127.0.0.1	2025-11-25 12:11:01.132475
58	3	Login	User logged in successfully	127.0.0.1	2025-11-25 12:11:12.988268
59	3	Logout	User logged out	127.0.0.1	2025-11-25 12:11:34.66921
60	2	Login	User logged in successfully	127.0.0.1	2025-11-25 12:15:50.56968
61	2	Logout	User logged out	127.0.0.1	2025-11-25 12:18:54.017694
62	15	Login	User logged in successfully	127.0.0.1	2025-11-25 12:19:01.020222
63	15	Logout	User logged out	127.0.0.1	2025-11-25 12:19:30.738327
64	1	Login	User logged in successfully	127.0.0.1	2025-11-25 12:19:39.583035
65	1	Update Order	Updated order ORD-1764073163-15 to Order Accepted	127.0.0.1	2025-11-25 12:19:57.24653
66	1	Logout	User logged out	127.0.0.1	2025-11-25 12:25:49.654902
67	1	Login	User logged in successfully	127.0.0.1	2025-11-25 12:32:05.309682
68	1	Logout	User logged out	127.0.0.1	2025-11-25 12:32:19.953949
69	1	Login	User logged in successfully	127.0.0.1	2025-11-25 12:32:36.82688
70	1	Logout	User logged out	127.0.0.1	2025-11-25 12:37:51.403714
71	1	Login	User logged in successfully	127.0.0.1	2025-11-25 12:40:12.970707
72	1	Logout	User logged out	127.0.0.1	2025-11-25 12:45:45.795515
73	1	Login	User logged in successfully	127.0.0.1	2025-11-25 12:52:32.605648
74	1	Logout	User logged out	127.0.0.1	2025-11-25 12:58:47.339963
75	1	Login	User logged in successfully	127.0.0.1	2025-11-25 12:58:56.871494
76	1	Create Invoice	Created invoice INV2025024 for Gaurav Patil	127.0.0.1	2025-11-25 13:09:06.378124
77	1	Logout	User logged out	127.0.0.1	2025-11-25 13:14:09.580281
78	1	Login	User logged in successfully	127.0.0.1	2025-11-25 13:14:22.004499
79	1	Logout	User logged out	127.0.0.1	2025-11-25 13:37:52.278306
80	1	Login	User logged in successfully	127.0.0.1	2025-11-25 13:38:11.681472
81	1	Logout	User logged out	127.0.0.1	2025-11-25 13:52:46.10093
82	15	Login	User logged in successfully	127.0.0.1	2025-11-25 13:52:52.537038
83	1	Login	User logged in successfully	122.167.115.196, 162.158.162.149, 10.16.149.129	2025-11-25 13:57:11.163329
355	19	Login	User logged in successfully	127.0.0.1	2025-12-18 11:20:27.400123
84	1	Add Product	Added product HP S1000 Plus Silent USB Wireless Computer Mute Mouse 1600DPI USB (7YA12PA), Black to catalog	122.167.115.196, 172.70.218.215, 10.17.235.214	2025-11-25 14:00:43.077726
85	1	Add Product	Added product Portronics Bridge Y USB 3.0 to Type C OTG Adaptor to catalog	122.167.115.196, 172.71.198.65, 10.16.149.129	2025-11-25 14:05:36.813291
86	1	Add Product	Added product HP M120 /6 programm. buttons,1 AA battery gives upto 12 months life to catalog	122.167.115.196, 172.69.179.127, 10.17.111.192	2025-11-25 14:08:03.509613
87	1	Add Product	Added product Meetion MT-G3330 Wired Ambidextrous Optical Gaming Mouse to catalog	122.167.115.196, 172.71.198.65, 10.16.149.129	2025-11-25 14:11:05.276597
88	1	Add Product	Added product Apple USB-C to Lightning Cable (2m) ​​​​​​​ to catalog	122.167.115.196, 172.69.165.65, 10.17.105.115	2025-11-25 14:13:13.057392
89	1	Add Product	Added product Apple 30W USB-C Power Adapter ​​​​​​​ to catalog	122.167.115.196, 172.70.218.214, 10.17.111.192	2025-11-25 14:15:04.111423
90	1	Logout	User logged out	122.167.115.196, 162.158.162.12, 10.17.105.115	2025-11-25 14:15:14.723255
91	15	Login	User logged in successfully	122.167.115.196, 172.70.218.214, 10.17.111.192	2025-11-25 14:15:25.171046
92	15	Login	User logged in successfully	122.167.115.196, 172.70.218.215, 10.16.149.129	2025-11-25 14:15:26.873094
93	15	Logout	User logged out	122.167.115.196, 162.158.162.158, 10.17.111.192	2025-11-25 14:16:06.937063
94	1	Login	User logged in successfully	122.167.115.196, 172.70.218.214, 10.17.111.192	2025-11-25 14:16:25.272611
95	1	Update Product	Updated product HP M120 /6 programm. buttons,1 AA battery gives upto 12 months life	122.167.115.196, 162.158.162.76, 10.16.149.129	2025-11-25 14:16:55.085596
96	1	Delete Product	Deleted product HP Mouse	122.167.115.196, 172.70.218.215, 10.16.149.129	2025-11-25 14:17:03.018481
97	1	Delete Product	Deleted product Gaming Mouse	122.167.115.196, 162.158.162.113, 10.17.235.214	2025-11-25 14:17:07.605369
98	1	Update Product	Updated product Nobero Oversized Hoodies for Man Stylish	122.167.115.196, 172.70.218.214, 10.17.111.192	2025-11-25 14:17:31.219544
99	1	Logout	User logged out	122.167.115.196, 172.70.218.215, 10.16.149.129	2025-11-25 14:17:52.019024
100	15	Login	User logged in successfully	122.167.115.196, 172.70.218.215, 10.16.149.129	2025-11-25 14:18:08.672819
101	15	Logout	User logged out	122.167.115.196, 172.70.218.214, 10.17.111.192	2025-11-25 14:18:45.638576
102	1	Login	User logged in successfully	122.167.115.196, 172.70.218.214, 10.17.111.192	2025-11-25 14:18:57.561419
103	1	Update Order	Updated order ORD-1764080314-15 to Order Accepted	122.167.115.196, 172.70.218.214, 10.17.111.192	2025-11-25 14:19:21.652222
104	1	Logout	User logged out	122.167.115.196, 162.158.163.245, 10.17.111.192	2025-11-25 14:19:33.053909
105	1	Logout	User logged out	122.167.115.196, 172.71.198.65, 10.16.218.155	2025-11-25 14:21:12.519652
106	1	Login	User logged in successfully	122.167.115.196, 162.158.163.162, 10.16.149.129	2025-11-25 14:21:20.669841
107	1	Login	User logged in successfully	122.167.115.196, 172.71.198.65, 10.17.233.215	2025-11-26 12:16:01.870539
108	1	Create User	Created user Jayesh Barhate with role buyer	122.167.115.196, 172.69.179.128, 10.16.149.129	2025-11-26 12:16:56.70377
109	1	Logout	User logged out	122.167.115.196, 172.69.179.128, 10.16.149.129	2025-11-26 12:17:03.942269
110	17	Login	User logged in successfully	122.167.115.196, 172.69.179.128, 10.16.149.129	2025-11-26 12:17:19.873358
111	17	Logout	User logged out	122.167.115.196, 172.70.142.214, 10.16.218.155	2025-11-26 12:18:18.465648
112	1	Login	User logged in successfully	122.167.115.196, 172.69.179.128, 10.16.149.129	2025-11-26 12:18:28.572792
113	1	Update Order	Updated order ORD-1764159493-17 to Order Accepted	122.167.115.196, 172.69.179.128, 10.16.149.129	2025-11-26 12:18:40.225608
114	15	Logout	User logged out	127.0.0.1	2025-11-26 12:53:33.754015
115	1	Login	User logged in successfully	127.0.0.1	2025-11-26 12:53:42.783095
116	1	Update User Profile	Admin updated profile for Ruchita_Umalkar	127.0.0.1	2025-11-26 12:57:04.515509
117	1	Update User Profile	Admin updated profile for Gaurav_Moderator	127.0.0.1	2025-11-26 12:58:10.986883
118	1	Update User Profile	Admin updated profile for Ruchita_Umalkar	127.0.0.1	2025-11-26 12:58:44.755847
119	1	Logout	User logged out	127.0.0.1	2025-11-26 13:19:37.375469
120	15	Login	User logged in successfully	127.0.0.1	2025-11-26 13:19:45.421628
121	15	Logout	User logged out	127.0.0.1	2025-11-26 13:34:53.155889
122	15	Login	User logged in successfully	127.0.0.1	2025-11-26 13:35:02.315749
123	15	Logout	User logged out	127.0.0.1	2025-11-26 13:36:04.664128
124	1	Login	User logged in successfully	127.0.0.1	2025-11-26 13:36:43.161309
125	1	Update Order	Updated order ORD-1764164143-15 to Order Accepted	127.0.0.1	2025-11-26 13:36:57.532115
126	1	Update Product	Updated product Apple 30W USB-C Power Adapter ​​​​​​​	127.0.0.1	2025-11-26 13:38:59.658484
127	1	Update Product	Updated product Apple USB-C to Lightning Cable (2m) ​​​​​​​	127.0.0.1	2025-11-26 13:39:11.35678
128	1	Update Product	Updated product HP M120 /6 programm. buttons,1 AA battery gives upto 12 months life	127.0.0.1	2025-11-26 13:39:19.75382
129	1	Update Product	Updated product HP S1000 Plus Silent USB Wireless Computer Mute Mouse 1600DPI USB (7YA12PA), Black	127.0.0.1	2025-11-26 13:39:28.630477
130	1	Update Product	Updated product Meetion MT-G3330 Wired Ambidextrous Optical Gaming Mouse	127.0.0.1	2025-11-26 13:39:42.747185
131	1	Update Product	Updated product NOBERO Men's Oversized Solid Loose fit Heavy Cotton T-Shirt (Pack of 2)	127.0.0.1	2025-11-26 13:39:52.898704
132	1	Update Product	Updated product NOBERO Men's Oversized Solid Loose fit Heavy Cotton T-Shirt (Pack of 2)	127.0.0.1	2025-11-26 13:39:55.359141
133	1	Update Product	Updated product Nobero Oversized Hoodies for Man Stylish	127.0.0.1	2025-11-26 13:40:02.839178
134	1	Update Product	Updated product Portronics Bridge Y USB 3.0 to Type C OTG Adaptor	127.0.0.1	2025-11-26 13:40:12.023836
135	1	Toggle User Status	Deactivated user Ruchita_Umalkar	127.0.0.1	2025-11-26 14:55:37.077401
136	1	Toggle User Status	Activated user Ruchita_Umalkar	127.0.0.1	2025-11-26 14:55:41.925171
137	1	Toggle User Status	Deactivated user Ruchita_Umalkar	127.0.0.1	2025-11-26 15:17:07.30323
138	1	Toggle User Status	Activated user Ruchita_Umalkar	127.0.0.1	2025-11-26 15:17:11.803609
139	1	Logout	User logged out	122.167.115.196, 172.70.142.125, 10.16.218.155	2025-11-26 15:48:02.268864
140	1	Login	User logged in successfully	122.167.115.196, 172.69.87.130, 10.16.218.155	2025-11-26 15:48:10.001664
141	1	Logout	User logged out	122.167.115.196, 172.71.198.65, 10.16.149.129	2025-11-26 18:10:27.056231
142	1	Login	User logged in successfully	122.167.115.196, 172.71.198.65, 10.16.149.129	2025-11-26 18:10:38.794581
143	1	Logout	User logged out	152.58.8.77, 172.69.178.207, 10.17.233.215	2025-11-27 03:05:55.020253
144	1	Login	User logged in successfully	152.58.8.77, 172.69.178.207, 10.17.233.215	2025-11-27 03:06:06.031592
145	1	Login	User logged in successfully	152.58.8.77, 172.69.178.207, 10.17.233.215	2025-11-27 03:06:07.730642
146	1	Update Order	Updated order ORD-1764159493-17 to Order Dispatched	152.58.8.77, 172.69.178.207, 10.17.233.215	2025-11-27 03:06:51.357309
147	1	Toggle User Status	Deactivated user Nitya_Nayar	127.0.0.1	2025-11-27 14:20:18.676245
148	1	Toggle User Status	Activated user Nitya_Nayar	127.0.0.1	2025-11-27 14:20:22.300529
149	1	Assign Problem	Assigned problem to Ruchita_Umalkar	127.0.0.1	2025-11-27 14:33:57.574522
150	1	Logout	User logged out	127.0.0.1	2025-11-27 14:34:02.769905
151	3	Login	User logged in successfully	127.0.0.1	2025-11-27 14:34:10.366336
152	1	Toggle User Status	Deactivated user Gaurav_Moderator	122.167.115.196, 172.69.95.122, 10.16.218.155	2025-11-28 01:28:41.797464
153	1	Toggle User Status	Activated user Gaurav_Moderator	122.167.115.196, 172.69.95.122, 10.16.218.155	2025-11-28 01:28:43.706085
154	1	Toggle User Status	Deactivated user Gaurav_Moderator	122.167.115.196, 172.69.95.122, 10.16.218.155	2025-11-28 01:28:49.14396
155	1	Toggle User Status	Activated user Gaurav_Moderator	122.167.115.196, 172.69.95.122, 10.16.218.155	2025-11-28 01:28:51.194042
156	3	Logout	User logged out	127.0.0.1	2025-11-28 16:21:15.726193
157	1	Login	User logged in successfully	127.0.0.1	2025-11-28 16:21:29.15493
158	1	Assign Problem	Assigned problem to Ruchita_Umalkar	127.0.0.1	2025-11-28 16:30:27.699347
159	1	Assign Problem	Assigned problem to Ruchita_Umalkar	127.0.0.1	2025-11-28 16:30:28.683644
160	1	Logout	User logged out	127.0.0.1	2025-11-28 16:31:02.778626
161	1	Login	User logged in successfully	127.0.0.1	2025-11-28 16:36:21.961294
162	1	Logout	User logged out	127.0.0.1	2025-11-28 16:36:29.105659
163	1	Login	User logged in successfully	127.0.0.1	2025-11-28 16:36:36.117771
164	1	Logout	User logged out	127.0.0.1	2025-11-28 16:36:46.888293
165	1	Login	User logged in successfully	127.0.0.1	2025-11-28 16:38:33.398942
166	1	Logout	User logged out	127.0.0.1	2025-11-28 16:38:39.35849
167	1	Logout	User logged out	122.167.115.196, 172.69.86.37, 10.16.218.155	2025-11-29 01:30:13.170998
168	1	Login	User logged in successfully	122.167.115.196, 172.69.86.37, 10.17.111.192	2025-11-29 01:30:29.764584
169	1	Logout	User logged out	122.167.115.196, 172.71.81.198, 10.17.111.192	2025-11-29 01:30:36.385944
170	1	Login	User logged in successfully	122.167.115.196, 172.71.82.44, 10.16.149.129	2025-11-29 01:30:57.757725
171	1	Cancel Event	Cancelled test for Ruchita_Umalkar	122.167.115.196, 172.69.95.85, 10.16.218.155	2025-11-29 01:32:09.918511
172	1	Login	User logged in successfully	127.0.0.1	2025-11-29 12:37:16.208832
173	1	Assign Problem	Assigned problem to Ruchita_Umalkar	127.0.0.1	2025-11-29 12:38:07.518537
174	1	Reschedule Event	Rescheduled test for Ruchita_Umalkar	127.0.0.1	2025-11-29 12:38:42.781176
175	1	Reschedule Event	Rescheduled test for Ruchita_Umalkar	122.167.115.196, 172.70.142.204, 10.17.27.76	2025-11-29 12:39:40.577733
176	1	Logout	User logged out	127.0.0.1	2025-11-29 12:41:08.864084
177	1	Login	User logged in successfully	127.0.0.1	2025-11-29 12:41:15.803588
178	1	Share BRD	Shared BRD for WRD_Finance_03 with gp2239396@gmail.com	127.0.0.1	2025-11-29 12:54:27.791766
179	1	Share BRD	Shared BRD for WRD_Finance_03 with gp2239396@gmail.com	127.0.0.1	2025-11-29 12:57:00.777703
180	1	Share BRD	Shared BRD for WRD_Finance_03 with gp2239396@gmail.com	127.0.0.1	2025-11-29 13:00:45.055079
181	1	Share BRD	Shared BRD for WRD_Finance_03 with gp2239396@gmail.com	127.0.0.1	2025-11-29 13:04:56.42858
182	1	Logout	User logged out	127.0.0.1	2025-11-29 13:05:24.023509
183	1	Login	User logged in successfully	127.0.0.1	2025-11-29 13:08:53.695773
184	1	Logout	User logged out	127.0.0.1	2025-11-29 13:11:19.521798
185	1	Login	User logged in successfully	127.0.0.1	2025-11-29 13:11:32.145747
186	1	Logout	User logged out	127.0.0.1	2025-11-29 13:11:41.529887
187	1	Logout	User logged out	122.167.115.196, 172.71.81.130, 10.17.110.134	2025-11-29 13:20:26.216621
188	1	Login	User logged in successfully	122.167.115.196, 172.69.95.181, 10.17.27.76	2025-11-29 13:20:33.735311
189	1	Login	User logged in successfully	127.0.0.1	2025-11-29 13:25:37.357883
190	1	Logout	User logged out	122.167.115.196, 172.69.87.130, 10.16.149.129	2025-11-30 10:06:54.140617
191	16	Login	User logged in successfully	122.167.115.196, 172.69.87.130, 10.16.149.129	2025-11-30 10:07:25.453707
192	16	Logout	User logged out	122.167.115.196, 172.69.87.130, 10.16.149.129	2025-11-30 10:08:15.181974
193	1	Login	User logged in successfully	122.167.115.196, 172.69.87.130, 10.16.149.129	2025-11-30 10:08:22.75305
194	1	Update Order	Updated order ORD-1764497289-16 to Order Accepted	122.167.115.196, 172.71.81.165, 10.16.149.129	2025-11-30 10:08:30.20176
195	1	Update Order	Updated order ORD-1764497289-16 to Order Delivered	122.167.115.196, 172.69.87.130, 10.16.149.129	2025-11-30 10:09:41.82625
196	1	Logout	User logged out	127.0.0.1	2025-12-02 05:38:28.185621
197	15	Login	User logged in successfully	127.0.0.1	2025-12-02 05:38:42.546946
198	15	Login	User logged in successfully	127.0.0.1	2025-12-02 05:38:43.211937
199	15	Logout	User logged out	127.0.0.1	2025-12-02 05:39:23.376284
200	1	Login	User logged in successfully	127.0.0.1	2025-12-02 05:39:33.321568
201	1	Update Order	Updated order ORD-1764653957-15 to Order Accepted	127.0.0.1	2025-12-02 05:39:47.498589
202	1	Logout	User logged out	152.58.13.48, 172.71.198.65, 10.16.149.129	2025-12-02 05:46:00.030193
203	1	Update Order	Updated order ORD-1764159493-17 to Order Delivered	152.58.11.112, 172.70.142.72, 10.16.149.129	2025-12-02 09:37:40.323367
204	1	Login	User logged in successfully	152.58.11.9, 172.69.87.129, 10.16.149.129	2025-12-02 10:20:38.856936
205	1	Login	User logged in successfully	152.58.11.9, 172.69.87.130, 10.16.218.155	2025-12-02 10:20:40.55605
206	1	Logout	User logged out	152.58.11.18, 172.70.142.111, 10.16.16.5	2025-12-03 07:41:26.620525
207	1	Login	User logged in successfully	122.167.115.196, 172.71.198.64, 10.16.140.165	2025-12-03 10:37:55.296357
208	1	Add Product	Added product Boat BassHeads 100 in-Ear Headphones with Mic (Black) to catalog	122.167.115.196, 172.69.95.78, 10.17.116.97	2025-12-03 12:32:43.007359
209	1	Logout	User logged out	122.167.115.196, 172.69.95.78, 10.17.116.97	2025-12-03 12:32:48.656067
210	1	Login	User logged in successfully	122.167.115.196, 172.69.95.78, 10.17.116.97	2025-12-03 12:33:16.393987
211	1	Create User	Created user Ritikesh Chavan with role buyer	122.167.115.196, 172.70.142.104, 10.17.116.97	2025-12-03 12:33:50.025266
212	1	Logout	User logged out	122.167.115.196, 172.69.179.128, 10.17.56.173	2025-12-03 12:33:56.348543
213	18	Login	User logged in successfully	122.167.115.196, 172.69.179.128, 10.17.56.173	2025-12-03 12:34:09.594631
214	18	Logout	User logged out	122.167.115.196, 172.69.95.77, 10.17.116.97	2025-12-03 12:35:51.889594
215	1	Login	User logged in successfully	122.167.115.196, 172.69.95.77, 10.17.116.97	2025-12-03 12:36:05.195703
216	1	Update Order	Updated order ORD-1764765318-18 to Order Accepted	122.167.115.196, 172.69.95.77, 10.17.116.97	2025-12-03 12:36:16.079007
217	1	Update Order	Updated order ORD-1764765318-18 to Order Dispatched	122.167.115.196, 172.70.142.94, 10.17.56.173	2025-12-03 12:36:31.134445
218	1	Update Order	Updated order ORD-1764765318-18 to Order Delivered	122.167.115.196, 172.70.143.249, 10.17.116.97	2025-12-03 12:36:34.098664
219	1	Logout	User logged out	127.0.0.1	2025-12-04 07:08:37.054392
220	1	Login	User logged in successfully	127.0.0.1	2025-12-04 07:08:45.427198
221	1	Mark Invoice Paid	Marked invoice INV2025029 as paid	127.0.0.1	2025-12-04 07:09:26.058246
222	1	Mark Invoice Paid	Marked invoice INV2025027 as paid	127.0.0.1	2025-12-04 07:11:09.839779
223	1	Mark Invoice Paid	Marked invoice INV2025025 as paid	127.0.0.1	2025-12-04 07:11:50.41696
224	1	Mark Invoice Paid	Marked invoice INV2025023 as paid	127.0.0.1	2025-12-04 07:18:21.891506
225	1	Mark Invoice Paid	Marked invoice INV2025006 as paid	127.0.0.1	2025-12-04 07:19:40.001545
226	1	Mark Invoice Paid	Marked invoice INV2025009 as paid	127.0.0.1	2025-12-04 07:19:45.252786
227	1	Mark Invoice Paid	Marked invoice INV2025010 as paid	127.0.0.1	2025-12-04 07:19:48.072607
228	1	Mark Invoice Paid	Marked invoice INV2025011 as paid	127.0.0.1	2025-12-04 07:19:55.338988
229	1	Mark Invoice Paid	Marked invoice INV2025013 as paid	127.0.0.1	2025-12-04 07:20:00.494443
230	1	Mark Invoice Paid	Marked invoice INV2025008 as paid	127.0.0.1	2025-12-04 07:20:05.814817
231	1	Mark Invoice Paid	Marked invoice INV2025018 as paid	127.0.0.1	2025-12-04 07:20:16.891393
232	1	Mark Invoice Paid	Marked invoice INV2025017 as paid	127.0.0.1	2025-12-04 07:20:19.367772
233	1	Mark Invoice Paid	Marked invoice INV2025016 as paid	127.0.0.1	2025-12-04 07:20:22.354653
234	1	Mark Invoice Paid	Marked invoice INV2025014 as paid	127.0.0.1	2025-12-04 07:20:24.401645
235	1	Mark Invoice Paid	Marked invoice INV2025019 as paid	127.0.0.1	2025-12-04 07:20:28.824241
236	1	Logout	User logged out	122.167.115.196, 172.70.142.83, 10.16.16.5	2025-12-04 07:55:56.516384
237	1	Login	User logged in successfully	122.167.115.196, 172.71.198.65, 10.17.245.242	2025-12-04 07:58:28.578554
238	1	Mark Invoice Paid	Marked invoice INV2025028 as paid	122.167.115.196, 172.71.198.65, 10.17.245.242	2025-12-04 07:58:43.466277
239	1	Login	User logged in successfully	122.167.115.196, 162.158.235.183, 10.16.27.5	2025-12-04 09:28:17.885492
240	1	Mark Invoice Paid	Marked invoice INV2025030 as paid	122.167.115.196, 172.71.198.65, 10.17.116.97	2025-12-04 09:34:26.375721
241	1	Login	User logged in successfully	122.167.115.196, 172.69.95.78, 10.16.27.5	2025-12-04 13:55:25.188127
242	1	Update Order	Updated order ORD-1764164143-15 to Order Delivered	122.167.115.196, 172.68.242.59, 10.16.16.5	2025-12-04 13:55:47.119563
243	1	Update Order	Updated order ORD-1764080314-15 to Order Delivered	122.167.115.196, 172.71.82.34, 10.17.116.97	2025-12-04 13:55:50.429599
244	1	Update Order	Updated order ORD-1764073163-15 to Order Delivered	122.167.115.196, 172.71.82.94, 10.17.116.97	2025-12-04 13:55:53.877773
245	1	Update Order	Updated order ORD-1763913161-15 to Order Delivered	122.167.115.196, 172.69.95.78, 10.16.27.5	2025-12-04 13:55:57.494251
246	1	Update Order	Updated order ORD-1763894906-16 to Order Delivered	122.167.115.196, 172.71.82.19, 10.17.245.242	2025-12-04 13:56:10.491655
247	1	Update Order	Updated order ORD-1763811665-15 to Order Delivered	122.167.115.196, 172.71.82.9, 10.17.245.242	2025-12-04 13:56:18.075327
248	1	Update Order	Updated order ORD-1763810116-15 to Order Delivered	122.167.115.196, 172.68.242.2, 10.17.116.97	2025-12-04 13:56:26.915798
249	1	Update Order	Updated order ORD-1764653957-15 to Order Delivered	122.167.115.196, 172.69.95.78, 10.16.27.5	2025-12-04 13:56:31.955737
250	1	Add Product	Added product Portronics Bubble Dock Bluetooth, Wireless Handheld Multi-device Keyboard  to catalog	127.0.0.1	2025-12-04 14:16:10.730314
251	1	Logout	User logged out	127.0.0.1	2025-12-04 14:16:27.000945
252	15	Login	User logged in successfully	127.0.0.1	2025-12-04 14:16:37.534159
253	15	Logout	User logged out	127.0.0.1	2025-12-04 14:17:01.265858
254	1	Login	User logged in successfully	127.0.0.1	2025-12-04 14:17:08.246552
255	1	Mark Invoice Paid	Marked invoice INV2025024 as paid	127.0.0.1	2025-12-04 14:32:43.670474
256	1	Logout	User logged out	127.0.0.1	2025-12-04 14:58:15.791898
257	1	Login	User logged in successfully	127.0.0.1	2025-12-04 14:58:25.111937
258	1	Logout	User logged out	122.167.115.196, 172.71.198.65, 10.17.157.156	2025-12-04 15:42:57.017291
259	1	Login	User logged in successfully	122.167.115.196, 172.71.198.64, 10.16.16.5	2025-12-04 18:32:16.337599
260	1	Logout	User logged out	122.167.115.196, 172.69.166.40, 10.16.16.5	2025-12-05 12:19:32.813268
261	1	Logout	User logged out	127.0.0.1	2025-12-06 12:00:25.012834
262	1	Login	User logged in successfully	127.0.0.1	2025-12-06 12:00:48.372498
263	1	Create EMI Plan	Imported schedule for user ID 8: rb	127.0.0.1	2025-12-06 12:49:02.178217
264	1	Delete EMI Plan	Deleted EMI plan: rb	127.0.0.1	2025-12-06 13:00:58.747167
265	1	Create EMI Plan	Imported schedule for user ID 2: Mobile 	127.0.0.1	2025-12-06 13:17:06.715482
266	1	Create EMI Plan	Created plan 'Mobile' for Borrower 2 and Lender 9	127.0.0.1	2025-12-06 13:41:17.157551
267	1	Create EMI Plan	Created plan 'Moble' for Borrower 9 and Lender 4	127.0.0.1	2025-12-06 13:51:20.122606
268	1	Logout	User logged out	152.58.9.90, 172.69.179.128, 10.16.28.29	2025-12-12 08:38:59.06657
269	1	Login	User logged in successfully	152.58.9.90, 172.69.179.128, 10.16.28.29	2025-12-12 08:39:10.045457
270	1	Share BRD	Shared BRD for WRD_Finance_03 with gp2239396@gmail.com	152.58.33.63, 172.70.142.78, 10.16.28.29	2025-12-12 15:33:04.244888
271	1	Share BRD	Shared BRD for WRD_Finance_03 with calalitbarhate@gmail.com	152.58.33.63, 172.69.87.130, 10.16.214.142	2025-12-12 15:33:56.443638
272	1	Create Invoice	Created invoice INV2025031 for Jayesh Barhate	152.58.31.228, 172.69.179.128, 10.16.239.180	2025-12-14 04:45:05.538921
273	1	Login	User logged in successfully	127.0.0.1	2025-12-14 11:18:18.212199
274	1	Create EMI Plan	Created plan 'test' for Borrower 9	127.0.0.1	2025-12-14 11:33:35.342485
275	1	Create EMI Plan	Created plan 'test' for Borrower 9	127.0.0.1	2025-12-14 11:34:22.415626
276	1	Delete EMI Plan	Deleted EMI plan: test	127.0.0.1	2025-12-14 11:34:33.908171
277	1	Delete EMI Plan	Deleted EMI plan: test	127.0.0.1	2025-12-14 11:34:50.383204
278	1	Delete EMI Plan	Deleted EMI plan: Moble	127.0.0.1	2025-12-14 11:34:59.285464
279	1	Create EMI Plan	Created plan 'IP16PROXMAX' for Borrower 9	127.0.0.1	2025-12-14 11:44:16.124838
280	1	Delete EMI Plan	Deleted EMI plan: IP16PROXMAX	127.0.0.1	2025-12-14 11:48:23.589474
281	1	Create EMI Plan	Created plan 'mob' for Borrower 4	127.0.0.1	2025-12-14 11:49:38.631824
282	1	Create EMI Plan	Created plan 'fgg' for Borrower 4	127.0.0.1	2025-12-14 11:57:04.819649
283	1	Delete EMI Plan	Deleted EMI plan: fgg	127.0.0.1	2025-12-14 12:01:37.801214
284	1	Delete EMI Plan	Deleted EMI plan: mob	127.0.0.1	2025-12-14 12:01:45.085116
285	1	Create EMI Plan	Created plan 'test' for Borrower 4	127.0.0.1	2025-12-14 12:02:04.818119
286	1	Update EMI Payment	Updated installment #1 for plan test	127.0.0.1	2025-12-14 12:05:42.449411
287	1	Delete EMI Plan	Deleted EMI plan: test	127.0.0.1	2025-12-14 12:08:35.766887
288	1	Create EMI Plan	Created plan 'IP16PROMAX' for Borrower 9	127.0.0.1	2025-12-14 12:09:01.954093
289	1	Mark EMI Paid	Marked installment #1 as paid for plan IP16PROMAX	127.0.0.1	2025-12-14 12:09:15.967603
290	1	Mark EMI Paid	Marked installment #2 as paid for plan IP16PROMAX	127.0.0.1	2025-12-14 12:09:18.737937
291	1	Mark EMI Paid	Marked installment #3 as paid for plan IP16PROMAX	127.0.0.1	2025-12-14 12:09:20.766715
292	1	Mark EMI Paid	Marked installment #4 as paid for plan IP16PROMAX	127.0.0.1	2025-12-14 12:09:22.7305
293	1	Mark EMI Paid	Marked installment #5 as paid for plan IP16PROMAX	127.0.0.1	2025-12-14 12:09:25.04976
294	1	Mark EMI Paid	Marked installment #6 as paid for plan IP16PROMAX	127.0.0.1	2025-12-14 12:09:27.390206
295	1	Mark EMI Paid	Marked installment #7 as paid for plan IP16PROMAX	127.0.0.1	2025-12-14 12:09:29.014028
296	1	Mark EMI Paid	Marked installment #8 as paid for plan IP16PROMAX	127.0.0.1	2025-12-14 12:09:31.403367
297	1	Mark EMI Paid	Marked installment #9 as paid for plan IP16PROMAX	127.0.0.1	2025-12-14 12:09:33.583245
298	1	Mark EMI Paid	Marked installment #10 as paid for plan IP16PROMAX	127.0.0.1	2025-12-14 12:09:35.558374
299	1	Mark EMI Paid	Marked installment #11 as paid for plan IP16PROMAX	127.0.0.1	2025-12-14 12:09:39.103247
300	1	Mark EMI Paid	Marked installment #12 as paid for plan IP16PROMAX	127.0.0.1	2025-12-14 12:10:14.151673
301	1	Login	User logged in successfully	122.167.115.196, 172.71.82.149, 10.16.124.122	2025-12-14 12:37:35.32333
302	1	Logout	User logged out	127.0.0.1	2025-12-14 12:53:45.327892
303	1	Login	User logged in successfully	127.0.0.1	2025-12-14 12:54:44.177887
304	1	Approve User	Approved user Pranav Receuiter	127.0.0.1	2025-12-14 12:54:53.673765
305	1	Logout	User logged out	127.0.0.1	2025-12-14 12:54:58.432191
306	19	Login	User logged in successfully	127.0.0.1	2025-12-14 12:55:08.236235
307	19	Logout	User logged out	127.0.0.1	2025-12-14 12:55:57.773757
308	1	Login	User logged in successfully	127.0.0.1	2025-12-14 13:03:45.637661
309	1	Logout	User logged out	127.0.0.1	2025-12-14 13:09:50.526771
310	19	Login	User logged in successfully	127.0.0.1	2025-12-14 13:10:06.471224
311	19	View Learning Content	Viewed java tutorial	127.0.0.1	2025-12-14 13:20:01.543037
312	1	Logout	User logged out	152.58.32.17, 172.70.142.179, 10.16.28.29	2025-12-15 03:02:53.794532
313	1	Login	User logged in successfully	152.58.32.17, 172.71.81.49, 10.16.173.102	2025-12-15 03:03:01.973452
314	1	Login	User logged in successfully	152.58.10.5, 162.158.235.184, 10.17.190.111	2025-12-16 07:21:27.265759
315	1	Add Product	Added product Jabra Evolve2 65 Flex Link380c UC Stereo to catalog	122.167.116.101, 172.69.179.127, 10.17.28.254	2025-12-18 09:20:03.274561
316	1	Add Product	Added product Lenovo Legion M300s RGB Wired Gaming Mouse to catalog	122.167.116.101, 172.71.198.64, 10.16.135.78	2025-12-18 09:28:36.025288
317	19	Logout	User logged out	127.0.0.1	2025-12-18 09:35:37.98941
318	1	Login	User logged in successfully	127.0.0.1	2025-12-18 09:35:48.096589
319	1	Add Product	Added product Zoook Qwerty Pad/3 Adj. DPI/Full Size Keyboard(104 key) & Mouse Combo  to catalog	127.0.0.1	2025-12-18 09:37:01.580091
320	1	Add Product	Added product Boat BassHeads 100 in-Ear Headphones with Mic (Black) to catalog	127.0.0.1	2025-12-18 09:39:13.77221
321	1	Delete Product	Deleted product Boat BassHeads 100 in-Ear Headphones with Mic (Black)	122.167.116.101, 172.69.87.130, 10.17.74.173	2025-12-18 09:40:35.440979
322	1	Import Inventory	Bulk import (Inventory_All_Products_With_Images.xlsx): 24 added, 0 updated.	127.0.0.1	2025-12-18 10:41:18.525597
323	1	Import Inventory	Bulk import (Inventory_All_Products_With_Images.xlsx): 0 added, 24 updated.	127.0.0.1	2025-12-18 11:01:23.573566
324	1	Update Product	Updated product boAt BassHeads 900 Wired Headphone	127.0.0.1	2025-12-18 11:02:28.712743
325	1	Update Product	Updated product Sony WF‑1000XM5	127.0.0.1	2025-12-18 11:03:19.418859
326	1	Update Product	Updated product Sony WH‑1000XM4	127.0.0.1	2025-12-18 11:04:03.636741
327	1	Update Product	Updated product Sony WH‑1000XM4	127.0.0.1	2025-12-18 11:04:37.078844
328	1	Update Product	Updated product Sony WH‑1000XM4	127.0.0.1	2025-12-18 11:04:51.500886
329	1	Update Product	Updated product Sony WH‑1000XM5	127.0.0.1	2025-12-18 11:05:03.903202
330	1	Update Product	Updated product Sony WH‑1000XM5	127.0.0.1	2025-12-18 11:05:04.743507
331	1	Update Product	Updated product Samsung USB‑C Data Cable	127.0.0.1	2025-12-18 11:05:58.7993
332	1	Update Product	Updated product Samsung USB‑C Data Cable	127.0.0.1	2025-12-18 11:05:59.334783
333	1	Update Product	Updated product Samsung Galaxy Buds 2 Pro	127.0.0.1	2025-12-18 11:06:53.243951
334	1	Update Product	Updated product Samsung 45W Super Fast Charging Adapter	127.0.0.1	2025-12-18 11:07:39.532942
335	1	Update Product	Updated product Samsung 25W Fast Charging Adapter	127.0.0.1	2025-12-18 11:08:17.25202
336	1	Update Product	Updated product Samsung 25W Fast Charging Adapter	127.0.0.1	2025-12-18 11:08:18.28213
337	1	Update Product	Updated product boAt Rockerz 255 Pro+	127.0.0.1	2025-12-18 11:09:02.465815
338	1	Update Product	Updated product boAt Rockerz 255 Pro+	127.0.0.1	2025-12-18 11:09:03.029947
339	1	Update Product	Updated product Portronics Konnect C Type Cable	127.0.0.1	2025-12-18 11:10:04.110424
340	1	Update Product	Updated product Portronics Konnect A USB Cable	127.0.0.1	2025-12-18 11:10:28.058496
341	1	Update Product	Updated product Logitech M221 Silent Wireless Mouse	127.0.0.1	2025-12-18 11:11:17.237163
342	1	Update Product	Updated product Logitech MK215 Keyboard Mouse Combo	127.0.0.1	2025-12-18 11:11:53.886568
343	1	Update Product	Updated product Logitech MK270r Wireless Keyboard and Mouse Combo 	127.0.0.1	2025-12-18 11:14:00.954506
344	1	Update Product	Updated product Logitech MK270r Wireless Keyboard and Mouse Combo 	127.0.0.1	2025-12-18 11:14:05.524089
345	1	Update Product	Updated product HP C2500 Wired Keyboard	127.0.0.1	2025-12-18 11:14:42.587096
346	1	Update Product	Updated product boAt Rockerz 450 Bluetooth	127.0.0.1	2025-12-18 11:15:33.486889
347	1	Update Product	Updated product Dell KM117 Wireless Combo	127.0.0.1	2025-12-18 11:16:11.30423
348	1	Update Product	Updated product Dell WM118 Wireless Mouse	127.0.0.1	2025-12-18 11:16:44.046507
349	1	Update Product	Updated product Apple Lightning to USB Cable	127.0.0.1	2025-12-18 11:17:24.965896
350	1	Update Product	Updated product Jabra Evolve 20 UC	127.0.0.1	2025-12-18 11:18:15.177806
351	1	Update Product	Updated product Jabra Evolve 30 II	127.0.0.1	2025-12-18 11:18:43.576023
352	1	Update Product	Updated product Jabra Evolve 65	127.0.0.1	2025-12-18 11:19:20.76275
353	1	Update Product	Updated product Jabra Evolve2 65	127.0.0.1	2025-12-18 11:19:46.562836
354	1	Logout	User logged out	127.0.0.1	2025-12-18 11:20:13.468778
356	19	Logout	User logged out	127.0.0.1	2025-12-18 11:20:43.708838
357	1	Logout	User logged out	127.0.0.1	2025-12-18 11:21:13.660235
358	15	Login	User logged in successfully	127.0.0.1	2025-12-18 11:21:24.45193
359	15	Logout	User logged out	127.0.0.1	2025-12-18 11:21:57.558246
360	1	Login	User logged in successfully	127.0.0.1	2025-12-18 11:22:05.968045
361	1	Update Product	Updated product Jabra Evolve2 65	127.0.0.1	2025-12-18 11:22:51.396939
362	1	Logout	User logged out	127.0.0.1	2025-12-18 11:23:04.112293
363	1	Logout	User logged out	122.167.116.101, 172.69.95.77, 10.17.28.254	2025-12-18 11:26:43.61868
364	9	Login	User logged in successfully	127.0.0.1	2025-12-18 12:31:36.651119
365	9	Login	User logged in successfully	127.0.0.1	2025-12-18 12:32:12.006618
366	9	Logout	User logged out	127.0.0.1	2025-12-18 12:34:48.064578
367	1	Login	User logged in successfully	127.0.0.1	2025-12-18 12:34:54.961624
368	9	Logout	User logged out	127.0.0.1	2025-12-18 12:39:39.359644
369	1	Login	User logged in successfully	127.0.0.1	2025-12-18 12:40:19.527301
370	1	Approve User	Approved user Seller_New	127.0.0.1	2025-12-18 12:40:26.907977
371	1	Logout	User logged out	127.0.0.1	2025-12-18 12:40:31.008797
372	20	Login	User logged in successfully	127.0.0.1	2025-12-18 12:40:43.90919
373	20	Login	User logged in successfully	127.0.0.1	2025-12-18 12:41:36.967961
374	20	Logout	User logged out	127.0.0.1	2025-12-18 12:52:20.224771
375	20	Login	User logged in successfully	127.0.0.1	2025-12-18 12:52:33.060541
376	20	Logout	User logged out	127.0.0.1	2025-12-18 12:59:37.656932
377	20	Login	User logged in successfully	127.0.0.1	2025-12-18 12:59:44.813815
378	20	Logout	User logged out	127.0.0.1	2025-12-18 13:02:10.846024
379	20	Login	User logged in successfully	127.0.0.1	2025-12-18 13:02:17.434556
380	20	Logout	User logged out	127.0.0.1	2025-12-18 13:07:06.002217
381	20	Login	User logged in successfully	127.0.0.1	2025-12-18 13:07:12.818789
382	20	Logout	User logged out	127.0.0.1	2025-12-18 13:14:55.417627
383	20	Login	User logged in successfully	127.0.0.1	2025-12-18 13:15:03.780911
384	20	Create Order	Seller created order ORD20250012 for User ID 16	127.0.0.1	2025-12-18 13:20:18.728216
385	20	Logout	User logged out	127.0.0.1	2025-12-18 13:26:29.204877
386	20	Login	User logged in successfully	127.0.0.1	2025-12-18 13:26:37.879123
387	20	Logout	User logged out	127.0.0.1	2025-12-18 13:27:01.209817
388	1	Login	User logged in successfully	127.0.0.1	2025-12-18 13:27:07.351342
389	1	Logout	User logged out	127.0.0.1	2025-12-18 13:27:27.097157
390	20	Login	User logged in successfully	127.0.0.1	2025-12-18 13:27:33.463414
391	20	Logout	User logged out	127.0.0.1	2025-12-18 13:27:55.711624
392	20	Login	User logged in successfully	127.0.0.1	2025-12-18 13:28:13.363245
393	20	Logout	User logged out	127.0.0.1	2025-12-18 13:28:21.529826
394	1	Login	User logged in successfully	127.0.0.1	2025-12-18 13:28:27.032288
395	1	Admin Change Password	Admin changed password for Jayesh Barhate	127.0.0.1	2025-12-18 13:28:53.8847
396	1	Logout	User logged out	127.0.0.1	2025-12-18 13:31:03.441697
397	17	Login	User logged in successfully	127.0.0.1	2025-12-18 13:31:24.359637
398	17	Logout	User logged out	127.0.0.1	2025-12-18 13:31:53.522994
399	1	Logout	User logged out	122.167.116.101, 172.69.87.130, 10.16.135.78	2025-12-18 13:49:11.479718
400	17	Login	User logged in successfully	122.167.116.101, 172.69.87.130, 10.16.135.78	2025-12-18 13:49:39.442759
401	17	Logout	User logged out	122.167.116.101, 172.69.95.77, 10.16.240.206	2025-12-18 13:55:42.235292
402	1	Logout	User logged out	122.167.116.101, 172.71.198.65, 10.17.74.173	2025-12-18 13:55:54.532181
403	1	Login	User logged in successfully	122.167.116.101, 172.71.198.65, 10.17.74.173	2025-12-18 13:56:04.547223
404	1	Send Specific Email	Sent email to 1 recipients. Subject: Seller Account Confirmation	122.167.116.101, 172.69.95.78, 10.17.28.254	2025-12-18 13:59:36.579347
405	1	Admin Change Password	Admin changed password for Jayesh_SL450	122.167.116.101, 172.71.82.122, 10.17.74.173	2025-12-18 14:00:04.163198
406	1	Login	User logged in successfully	122.167.116.101, 172.69.179.127, 10.17.28.254	2025-12-18 14:13:59.240469
407	1	Logout	User logged out	122.167.116.101, 172.70.142.165, 10.17.74.173	2025-12-18 14:15:59.659611
408	20	Login	User logged in successfully	122.167.116.101, 172.69.179.127, 10.17.28.254	2025-12-18 14:16:19.343026
409	20	Login	User logged in successfully	127.0.0.1	2025-12-19 08:50:52.606982
410	20	Logout	User logged out	127.0.0.1	2025-12-19 09:23:46.251778
411	20	Login	User logged in successfully	127.0.0.1	2025-12-19 09:23:59.200175
412	20	Logout	User logged out	127.0.0.1	2025-12-19 09:24:14.979328
413	1	Login	User logged in successfully	127.0.0.1	2025-12-19 09:24:39.616882
414	1	Logout	User logged out	127.0.0.1	2025-12-19 09:51:13.115984
415	1	Login	User logged in successfully	127.0.0.1	2025-12-19 09:51:25.034768
416	1	Assign Inventory	Assigned 5 units of Apple 20W USB‑C Power Adapter to Seller_New	127.0.0.1	2025-12-19 09:55:42.838321
417	1	Logout	User logged out	127.0.0.1	2025-12-19 09:56:02.408908
418	20	Login	User logged in successfully	127.0.0.1	2025-12-19 09:56:14.132856
419	20	Update Inventory	Seller updated stock for Apple 20W USB‑C Power Adapter	127.0.0.1	2025-12-19 09:56:30.240394
420	20	Logout	User logged out	127.0.0.1	2025-12-19 10:01:28.049647
421	1	Login	User logged in successfully	127.0.0.1	2025-12-19 10:02:27.40398
422	1	Assign Inventory	Assigned 1 units of Apple 20W USB‑C Power Adapter to Seller_New	127.0.0.1	2025-12-19 10:03:00.707512
423	1	Logout	User logged out	127.0.0.1	2025-12-19 10:05:43.806195
424	20	Login	User logged in successfully	127.0.0.1	2025-12-19 10:05:54.613748
425	20	Logout	User logged out	127.0.0.1	2025-12-19 10:22:24.893666
426	20	Login	User logged in successfully	127.0.0.1	2025-12-19 10:22:34.638936
427	20	Request Stock	Seller requested 5 units of Product ID 9	127.0.0.1	2025-12-19 10:23:02.181732
428	20	Logout	User logged out	127.0.0.1	2025-12-19 10:23:15.430422
429	1	Login	User logged in successfully	127.0.0.1	2025-12-19 10:23:20.381612
430	1	Logout	User logged out	127.0.0.1	2025-12-19 10:29:07.851471
431	1	Login	User logged in successfully	127.0.0.1	2025-12-19 10:29:26.251904
432	1	Approve Stock	Approved 5 units of Apple USB-C to Lightning Cable (2m) ​​​​​​​ for Seller_New	127.0.0.1	2025-12-19 10:29:48.611289
433	1	Logout	User logged out	127.0.0.1	2025-12-19 10:29:55.302469
434	20	Login	User logged in successfully	127.0.0.1	2025-12-19 10:30:01.911566
435	20	Logout	User logged out	127.0.0.1	2025-12-19 10:41:45.742611
436	20	Login	User logged in successfully	127.0.0.1	2025-12-19 10:41:59.860708
437	20	Request Stock	Seller requested 5 units of Boat BassHeads 100 in-Ear Headphones with Mic (Black). Notified 1 admins.	127.0.0.1	2025-12-19 10:42:14.994478
438	20	Logout	User logged out	127.0.0.1	2025-12-19 10:42:21.567339
439	1	Login	User logged in successfully	127.0.0.1	2025-12-19 10:42:26.823814
440	1	Approve Stock	Approved 5 units of Boat BassHeads 100 in-Ear Headphones with Mic (Black) for Seller_New	127.0.0.1	2025-12-19 10:43:00.491515
441	1	Logout	User logged out	127.0.0.1	2025-12-19 10:43:29.659666
442	20	Login	User logged in successfully	127.0.0.1	2025-12-19 10:43:58.080697
443	20	Update Inventory	Seller updated stock for Apple USB-C to Lightning Cable (2m) ​​​​​​​	127.0.0.1	2025-12-19 10:44:14.322815
444	1	Logout	User logged out	122.167.116.101, 172.70.142.133, 10.17.74.173	2025-12-19 10:55:10.154184
445	17	Logout	User logged out	122.167.116.101, 172.71.124.185, 10.17.186.18	2025-12-19 10:57:09.824914
446	19	Login	User logged in successfully	122.167.116.101, 172.71.124.149, 10.16.240.206	2025-12-19 10:57:39.2356
447	19	Logout	User logged out	122.167.116.101, 172.71.124.75, 10.16.135.78	2025-12-19 10:57:47.853152
448	1	Login	User logged in successfully	122.167.116.101, 172.71.198.65, 10.17.186.18	2025-12-19 10:57:54.838156
449	1	Logout	User logged out	122.167.116.101, 172.70.142.180, 10.17.74.173	2025-12-19 11:02:54.533361
450	20	Logout	User logged out	152.58.30.104, 172.70.157.157, 10.16.240.206	2025-12-19 11:12:51.160876
451	1	Login	User logged in successfully	152.58.30.104, 172.70.157.157, 10.16.240.206	2025-12-19 11:12:59.534704
452	1	Logout	User logged out	152.58.30.104, 172.70.157.157, 10.16.240.206	2025-12-19 11:13:11.625275
453	20	Login	User logged in successfully	152.58.30.104, 172.70.157.157, 10.16.240.206	2025-12-19 11:13:27.73582
454	1	Login	User logged in successfully	127.0.0.1	2025-12-19 13:16:50.175417
455	1	Assign Inventory	Assigned 3 units of Apple 20W USB‑C Power Adapter to Pranav_SL898	127.0.0.1	2025-12-19 13:26:07.732329
456	1	Logout	User logged out	127.0.0.1	2025-12-19 13:27:53.427228
457	19	Login	User logged in successfully	127.0.0.1	2025-12-19 13:28:10.902913
458	19	Request Stock	Seller requested 5 units of Boat BassHeads 100 in-Ear Headphones with Mic (Black). Notified 1 admins.	127.0.0.1	2025-12-19 13:35:02.245302
459	19	Logout	User logged out	127.0.0.1	2025-12-19 13:35:08.212923
460	1	Login	User logged in successfully	127.0.0.1	2025-12-19 13:35:19.182874
461	1	Approve Stock	Approved 5 units of Boat BassHeads 100 in-Ear Headphones with Mic (Black) for Pranav_SL898	127.0.0.1	2025-12-19 13:35:47.129212
462	1	Logout	User logged out	127.0.0.1	2025-12-19 13:35:59.528528
463	1	Login	User logged in successfully	122.167.116.101, 172.71.124.163, 10.17.186.18	2025-12-19 13:56:00.391188
464	1	Update Profile	User updated their profile details	122.167.116.101, 172.69.179.128, 10.16.135.78	2025-12-19 13:58:59.915055
465	1	Update Profile	User updated their profile details	122.167.116.101, 172.69.179.128, 10.16.135.78	2025-12-19 13:59:04.6457
466	19	Login	User logged in successfully	127.0.0.1	2025-12-19 14:03:06.320619
467	19	Update Profile	User updated their profile details	127.0.0.1	2025-12-19 14:03:16.202119
468	19	Logout	User logged out	127.0.0.1	2025-12-19 14:03:31.406809
469	15	Login	User logged in successfully	127.0.0.1	2025-12-19 14:03:37.966404
470	15	Logout	User logged out	127.0.0.1	2025-12-19 14:03:45.346892
471	1	Login	User logged in successfully	127.0.0.1	2025-12-19 14:03:53.264095
472	20	Logout	User logged out	122.167.116.101, 172.69.179.127, 10.16.135.78	2025-12-19 14:16:52.683533
473	1	Login	User logged in successfully	122.167.116.101, 172.69.179.127, 10.16.135.78	2025-12-19 14:17:00.605668
474	1	Logout	User logged out	122.167.116.101, 172.70.142.155, 10.16.115.148	2025-12-19 14:17:57.960646
475	1	Login	User logged in successfully	122.167.116.101, 172.70.143.224, 10.17.186.18	2025-12-19 14:18:31.698923
476	1	Reject User	Rejected user registration for test	122.167.116.101, 172.69.179.127, 10.16.135.78	2025-12-19 14:19:22.163449
477	1	Logout	User logged out	127.0.0.1	2025-12-19 14:26:41.314505
478	1	Login	User logged in successfully	127.0.0.1	2025-12-19 14:26:48.238122
479	1	Assign Inventory	Assigned 2 units of Meetion MT-G3330 Wired Ambidextrous Optical Gaming Mouse to Jayesh_SL450	122.167.116.101, 162.158.235.183, 10.17.74.173	2025-12-19 15:06:09.454213
480	1	Assign Inventory	Assigned 4 units of HP S1000 Plus Silent USB Wireless Computer Mute Mouse 1600DPI USB (7YA12PA), Black to Jayesh_SL450	122.167.116.101, 162.158.162.162, 10.17.74.173	2025-12-19 15:06:29.153656
481	1	Assign Inventory	Assigned 1 units of Lenovo Legion M300s RGB Wired Gaming Mouse to Jayesh_SL450	122.167.116.101, 162.158.162.162, 10.17.74.173	2025-12-19 15:06:49.2237
482	1	Assign Inventory	Assigned 2 units of Zoook Qwerty Pad/3 Adj. DPI/Full Size Keyboard(104 key) & Mouse Combo  to Jayesh_SL450	122.167.116.101, 172.69.165.63, 10.16.135.78	2025-12-19 15:07:05.746425
483	1	Assign Inventory	Assigned 1 units of HP M120 /6 programm. buttons,1 AA battery gives upto 12 months life to Jayesh_SL450	122.167.116.101, 104.23.175.119, 10.17.186.18	2025-12-19 15:07:29.506552
484	1	Assign Inventory	Assigned 3 units of Boat BassHeads 100 in-Ear Headphones with Mic (Black) to Jayesh_SL450	122.167.116.101, 104.23.175.25, 10.16.240.206	2025-12-19 15:07:45.162125
485	1	Assign Inventory	Assigned 3 units of Portronics Bubble Dock Bluetooth, Wireless Handheld Multi-device Keyboard  to Jayesh_SL450	122.167.116.101, 162.158.235.183, 10.16.240.206	2025-12-19 15:08:10.177885
486	1	Admin Change Password	Admin changed password for Jayesh_SL450	122.167.116.101, 172.69.87.129, 10.16.135.78	2025-12-19 15:10:00.773725
487	1	Logout	User logged out	127.0.0.1	2025-12-19 15:31:16.20214
488	1	Logout	User logged out	122.167.116.101, 162.158.235.184, 10.16.240.206	2025-12-19 15:37:48.193537
489	1	Login	User logged in successfully	122.167.116.101, 172.71.124.46, 10.17.186.18	2025-12-19 15:55:09.651377
490	1	Logout	User logged out	122.167.116.101, 172.69.166.104, 10.17.74.173	2025-12-19 15:56:53.245375
491	1	Login	User logged in successfully	122.167.116.101, 172.71.198.64, 10.16.240.206	2025-12-19 16:41:44.354203
492	1	Logout	User logged out	122.167.116.101, 172.71.198.64, 10.16.240.206	2025-12-19 16:42:22.370258
493	20	Login	User logged in successfully	122.167.116.101, 172.71.198.64, 10.16.240.206	2025-12-19 16:42:53.241387
494	20	Login	User logged in successfully	122.167.116.101, 172.71.124.189, 10.16.115.148	2025-12-19 16:42:55.447764
495	20	Logout	User logged out	122.167.116.101, 172.70.218.215, 10.16.240.206	2025-12-19 16:50:56.060351
496	20	Login	User logged in successfully	122.167.116.101, 172.71.124.238, 10.16.135.78	2025-12-19 16:51:05.243985
497	20	Logout	User logged out	122.167.116.101, 172.70.218.215, 10.16.240.206	2025-12-19 16:51:13.461022
498	1	Login	User logged in successfully	122.167.116.101, 172.70.218.215, 10.16.240.206	2025-12-19 16:51:26.749635
499	1	Logout	User logged out	122.167.116.101, 172.71.198.65, 10.17.186.18	2025-12-20 03:03:07.759479
500	1	Login	User logged in successfully	122.167.116.101, 172.71.198.65, 10.17.186.18	2025-12-20 03:03:21.154033
501	1	Logout	User logged out	122.167.116.101, 172.71.198.65, 10.17.186.18	2025-12-20 03:03:31.190971
502	1	Logout	User logged out	122.167.116.101, 172.71.152.32, 10.17.186.18	2025-12-20 03:23:03.793632
503	1	Login	User logged in successfully	122.167.116.101, 172.70.142.82, 10.16.135.78	2025-12-20 03:23:12.441197
504	1	Login	User logged in successfully	127.0.0.1	2025-12-20 03:44:33.928077
505	1	Assign Problem	Assigned problem to Ruchita_Umalkar	127.0.0.1	2025-12-20 03:45:10.758357
506	1	Logout	User logged out	127.0.0.1	2025-12-20 03:45:14.886149
507	3	Login	User logged in successfully	127.0.0.1	2025-12-20 03:45:25.207795
508	3	Logout	User logged out	127.0.0.1	2025-12-20 03:45:48.28294
509	1	Login	User logged in successfully	127.0.0.1	2025-12-20 03:45:59.794115
510	1	Logout	User logged out	127.0.0.1	2025-12-20 03:46:41.332819
511	1	Login	User logged in successfully	127.0.0.1	2025-12-20 03:59:25.431131
512	1	Logout	User logged out	127.0.0.1	2025-12-20 04:11:01.83679
513	19	Login	User logged in successfully	127.0.0.1	2025-12-20 04:11:11.025332
514	19	Request Stock	Seller requested 1 units of Apple 20W USB‑C Power Adapter. Notified 1 admins.	127.0.0.1	2025-12-20 04:11:27.748841
515	19	Logout	User logged out	127.0.0.1	2025-12-20 04:11:32.093629
516	1	Login	User logged in successfully	127.0.0.1	2025-12-20 04:11:41.563141
517	1	Approve Stock	Approved 1 units of Apple 20W USB‑C Power Adapter for Pranav_SL898	127.0.0.1	2025-12-20 04:11:53.828684
518	1	Logout	User logged out	127.0.0.1	2025-12-20 04:12:01.435065
519	1	Login	User logged in successfully	122.167.116.101, 172.71.198.65, 10.17.186.18	2025-12-20 04:21:18.255186
520	1	Logout	User logged out	122.167.116.101, 172.71.81.127, 10.17.186.18	2025-12-20 04:22:34.625619
521	20	Login	User logged in successfully	122.167.116.101, 172.69.179.128, 10.16.135.78	2025-12-20 04:22:44.765191
522	20	Login	User logged in successfully	122.167.116.101, 172.70.142.154, 10.16.240.206	2025-12-20 04:31:00.456086
523	20	Logout	User logged out	122.167.116.101, 162.158.162.9, 10.17.186.18	2025-12-20 04:31:03.134027
524	1	Login	User logged in successfully	122.167.116.101, 172.70.142.197, 10.16.240.206	2025-12-20 04:31:12.066719
525	1	Assign Inventory	Assigned 2 units of HP S1000 Plus Silent USB Wireless Computer Mute Mouse 1600DPI USB (7YA12PA), Black to Jayesh_SL450	122.167.116.101, 172.70.142.196, 10.17.186.18	2025-12-20 04:31:57.66386
526	1	Logout	User logged out	122.167.116.101, 162.158.162.141, 10.16.135.78	2025-12-20 04:32:17.773443
527	1	Logout	User logged out	122.167.116.101, 172.69.87.129, 10.16.240.206	2025-12-20 05:01:23.975914
528	1	Login	User logged in successfully	122.167.116.101, 172.69.94.33, 10.16.240.206	2025-12-20 05:02:31.865399
529	1	Logout	User logged out	122.167.116.101, 172.69.166.10, 10.17.186.18	2025-12-20 05:09:22.520844
530	1	Login	User logged in successfully	122.167.116.101, 172.69.179.128, 10.16.135.78	2025-12-20 05:09:29.815289
531	1	Logout	User logged out	122.167.116.101, 172.70.218.215, 10.17.186.18	2025-12-20 05:10:20.318673
532	1	Login	User logged in successfully	122.167.116.101, 172.71.124.166, 10.16.240.206	2025-12-20 05:10:28.238684
533	20	Login	User logged in successfully	122.167.116.101, 172.70.142.45, 10.16.135.78	2025-12-20 05:12:30.201876
534	20	Login	User logged in successfully	122.167.116.101, 172.71.124.224, 10.16.135.78	2025-12-20 05:16:34.706581
535	20	Login	User logged in successfully	122.167.116.101, 172.71.124.129, 10.17.186.18	2025-12-20 05:16:36.405754
536	1	Logout	User logged out	122.167.116.101, 172.70.142.227, 10.17.74.173	2025-12-20 05:18:07.564879
537	20	Login	User logged in successfully	127.0.0.1	2025-12-20 05:18:42.647925
538	20	Logout	User logged out	127.0.0.1	2025-12-20 05:19:10.941545
539	20	Login	User logged in successfully	127.0.0.1	2025-12-20 05:19:21.151217
540	20	Logout	User logged out	127.0.0.1	2025-12-20 05:19:27.281152
541	1	Login	User logged in successfully	127.0.0.1	2025-12-20 05:19:36.824075
542	1	Mark Invoice Paid	Marked invoice INV2025020 as paid	127.0.0.1	2025-12-20 05:20:20.456363
543	1	Mark Invoice Paid	Marked invoice INV2025033 as paid	127.0.0.1	2025-12-20 05:26:48.095851
544	1	Logout	User logged out	127.0.0.1	2025-12-20 05:26:53.157782
545	20	Login	User logged in successfully	127.0.0.1	2025-12-20 05:27:09.05213
546	20	Create Order	Seller created order ORD20250013 for User ID 15	127.0.0.1	2025-12-20 05:32:40.205632
547	20	Logout	User logged out	127.0.0.1	2025-12-20 05:43:47.860755
548	1	Login	User logged in successfully	127.0.0.1	2025-12-20 05:44:05.32371
549	1	Logout	User logged out	127.0.0.1	2025-12-20 05:44:11.620158
550	20	Login	User logged in successfully	127.0.0.1	2025-12-20 05:44:20.209091
551	20	Create Order	Seller created order ORD20250014 for User ID 15	127.0.0.1	2025-12-20 05:44:39.800835
552	20	Logout	User logged out	127.0.0.1	2025-12-20 05:48:00.361265
553	20	Login	User logged in successfully	127.0.0.1	2025-12-20 05:48:07.219622
554	20	Create Order	Seller created order ORD20250015 for User ID 15	127.0.0.1	2025-12-20 05:48:42.091647
555	20	Logout	User logged out	127.0.0.1	2025-12-20 05:49:00.320435
556	1	Login	User logged in successfully	127.0.0.1	2025-12-20 05:49:11.824767
557	1	Mark Invoice Paid	Marked invoice INV2025037 as paid	127.0.0.1	2025-12-20 05:49:27.374854
558	1	Update Order	Updated order ORD20250015 to Order Dispatched	127.0.0.1	2025-12-20 05:50:05.392351
559	1	Logout	User logged out	127.0.0.1	2025-12-20 05:50:34.211289
560	15	Login	User logged in successfully	127.0.0.1	2025-12-20 05:50:41.748632
561	15	Logout	User logged out	127.0.0.1	2025-12-20 05:51:09.261209
562	20	Login	User logged in successfully	127.0.0.1	2025-12-20 05:51:20.11012
563	20	Logout	User logged out	127.0.0.1	2025-12-20 05:51:34.433534
564	1	Login	User logged in successfully	127.0.0.1	2025-12-20 05:51:43.118437
565	1	Update Order	Updated order ORD-1766209863-15 to Order Accepted	127.0.0.1	2025-12-20 05:51:55.310283
566	20	Login	User logged in successfully	122.167.116.101, 172.69.87.129, 10.16.134.72	2025-12-20 06:46:29.739495
567	20	Logout	User logged out	122.167.116.101, 172.70.142.114, 10.16.134.72	2025-12-20 06:46:46.538927
568	20	Login	User logged in successfully	122.167.116.101, 172.69.87.129, 10.16.134.72	2025-12-20 06:47:03.336141
569	20	Logout	User logged out	122.167.116.101, 172.69.87.129, 10.16.134.72	2025-12-20 06:47:14.563731
570	20	Login	User logged in successfully	122.167.116.101, 172.69.87.129, 10.16.135.78	2025-12-20 08:18:11.535517
571	20	Logout	User logged out	122.167.116.101, 172.69.87.129, 10.16.134.72	2025-12-20 10:48:35.843169
572	20	Login	User logged in successfully	122.167.116.101, 172.69.87.129, 10.16.134.72	2025-12-20 10:48:43.436148
573	20	Logout	User logged out	122.167.116.101, 172.69.87.129, 10.16.134.72	2025-12-20 10:48:50.863923
574	1	Login	User logged in successfully	122.167.116.101, 172.69.87.129, 10.16.134.72	2025-12-20 10:48:58.237753
575	1	Mark EMI Paid	Marked installment #13 as paid for plan IP16PROMAX	122.167.116.101, 172.69.87.130, 10.16.134.72	2025-12-20 10:51:13.036648
576	1	Login	User logged in successfully	122.167.116.101, 172.69.94.33, 10.17.74.173	2025-12-20 14:32:48.634655
577	1	Send Specific Email	Sent email to 1 recipients.	122.167.116.101, 172.71.152.58, 10.17.74.173	2025-12-20 14:33:51.700594
578	1	Login	User logged in successfully	122.167.116.101, 172.71.124.43, 10.16.134.72	2025-12-20 14:56:09.138401
579	1	Admin Change Password	Admin changed password for Jayesh_SL450	122.167.116.101, 172.71.124.233, 10.17.74.173	2025-12-20 14:57:06.842274
580	1	Logout	User logged out	122.167.116.101, 172.71.198.64, 10.16.135.78	2025-12-20 14:57:12.276961
581	17	Login	User logged in successfully	122.167.116.101, 172.71.198.64, 10.16.135.78	2025-12-20 14:57:25.734004
582	17	Logout	User logged out	122.167.116.101, 172.70.143.136, 10.16.135.78	2025-12-20 14:58:14.487359
583	1	Login	User logged in successfully	152.58.31.26, 162.158.162.145, 10.17.74.173	2025-12-21 02:11:20.63753
584	1	Login	User logged in successfully	152.58.31.153, 172.71.81.247, 10.16.240.206	2025-12-21 02:30:59.73786
585	20	Logout	User logged out	122.167.116.101, 172.69.87.130, 10.17.74.173	2025-12-22 03:41:30.924903
586	1	Login	User logged in successfully	122.167.116.101, 162.158.108.62, 10.17.74.173	2025-12-22 03:41:39.139264
587	1	Login	User logged in successfully	122.167.116.101, 162.158.108.106, 10.16.135.78	2025-12-22 05:59:26.435376
588	1	Login	User logged in successfully	122.167.116.101, 172.69.87.130, 10.17.152.16	2025-12-22 09:59:58.834047
589	1	Create Invoice	Created invoice INV2025039 for Jayesh Barhate	122.167.116.101, 172.69.94.33, 10.17.74.173	2025-12-22 10:05:52.836534
590	1	Create Invoice	Created invoice INV2025040 for Jayesh Barhate	122.167.116.101, 172.69.94.33, 10.17.152.16	2025-12-22 10:11:15.627305
591	1	Mark Invoice Paid	Marked invoice INV2025007 as paid	122.167.116.101, 172.70.218.214, 10.17.74.173	2025-12-22 10:30:23.675476
592	1	Logout	User logged out	127.0.0.1	2025-12-23 09:38:56.283796
593	1	Login	User logged in successfully	127.0.0.1	2025-12-23 09:39:05.776943
594	1	Logout	User logged out	127.0.0.1	2025-12-23 10:03:23.077888
595	1	Login	User logged in successfully	127.0.0.1	2025-12-23 10:03:31.343389
596	1	Logout	User logged out	127.0.0.1	2025-12-23 10:21:15.761866
597	20	Login	User logged in successfully	127.0.0.1	2025-12-23 10:21:28.829151
598	20	Logout	User logged out	127.0.0.1	2025-12-23 10:21:41.920954
599	20	Login	User logged in successfully	127.0.0.1	2025-12-23 10:40:35.832742
600	20	Logout	User logged out	127.0.0.1	2025-12-23 10:41:04.917566
601	1	Login	User logged in successfully	127.0.0.1	2025-12-23 10:41:42.892884
602	1	Admin Stock Update	Changed Pranav_SL898's stock for Apple 20W USB‑C Power Adapter from 4 to 6	127.0.0.1	2025-12-23 11:17:25.71949
603	1	Login	User logged in successfully	122.167.116.101, 172.71.198.64, 10.16.135.78	2025-12-23 13:06:30.930784
604	1	Delete Seller Allocation	Removed Apple 20W USB‑C Power Adapter from Jayesh_SL450's inventory	122.167.116.101, 104.23.175.99, 10.16.135.78	2025-12-23 13:08:01.732946
605	1	Logout	User logged out	122.167.116.101, 162.158.108.31, 10.17.74.173	2025-12-24 01:33:35.94942
606	1	Login	User logged in successfully	122.167.116.101, 162.158.108.30, 10.17.218.118	2025-12-24 01:33:50.45913
607	1	Login	User logged in successfully	122.167.116.101, 162.158.108.126, 10.17.132.135	2025-12-24 05:37:31.651379
608	1	Share BRD	Shared BRD for WRD_Finance_03 with nikitaumalkar98@gmail.com	122.167.116.101, 172.69.179.127, 10.17.74.173	2025-12-24 05:43:33.670071
609	1	Logout	User logged out	152.58.30.91, 172.70.157.157, 10.17.132.135	2025-12-24 08:43:17.885155
610	1	Login	User logged in successfully	152.58.30.91, 172.70.157.157, 10.17.132.135	2025-12-24 08:43:33.563758
611	1	Admin Change Password	Admin changed password for Jayesh_SL450	152.58.30.91, 172.70.157.157, 10.17.132.135	2025-12-24 08:45:08.997104
612	17	Login	User logged in successfully	49.36.50.62, 172.70.157.157, 10.17.74.173	2025-12-24 08:45:28.759884
613	1	Logout	User logged out	152.58.32.232, 172.70.157.157, 10.17.186.18	2025-12-24 16:27:19.146321
614	1	Login	User logged in successfully	152.58.32.232, 172.70.92.194, 10.16.135.78	2025-12-24 16:56:46.45799
615	1	Assign Inventory	Assigned 1 units of Jabra Evolve 40 UC Wired Over The Ear Headset with Mic (Black) to Jayesh_SL450	152.58.32.232, 172.70.157.156, 10.17.102.222	2025-12-24 17:03:18.365124
616	1	Login	User logged in successfully	2401:4900:1c44:55a9:e9be:7624:36dd:a97c, 127.0.0.1	2025-12-25 15:47:03.533697
617	1	Login	User logged in successfully	2401:4900:1c44:55a9:4df5:6464:37d3:b175, 127.0.0.1	2025-12-25 16:31:42.25875
618	1	Logout	User logged out	2401:4900:1c44:55a9:4df5:6464:37d3:b175, 127.0.0.1	2025-12-25 16:37:49.097399
619	1	Login	User logged in successfully	2401:4900:1c44:55a9:4df5:6464:37d3:b175, 127.0.0.1	2025-12-25 16:37:56.561261
620	1	Logout	User logged out	2401:4900:1c44:55a9:4df5:6464:37d3:b175, 127.0.0.1	2025-12-25 16:38:13.437064
621	1	Login	User logged in successfully	2401:4900:1c44:55a9:79b9:5872:cb23:b6dc, 127.0.0.1	2025-12-25 16:50:39.914063
622	1	Login	User logged in successfully	223.233.86.220, 127.0.0.1	2025-12-25 17:22:20.33333
623	1	Login	User logged in successfully	2401:4900:1c44:55a9:4df5:6464:37d3:b175, 127.0.0.1	2025-12-25 17:34:38.83621
624	1	Assign Moderator	Assigned moderator Gaurav_Moderator to candidate Ruchita_Umalkar	2401:4900:1c44:55a9:4df5:6464:37d3:b175, 127.0.0.1	2025-12-25 17:35:07.46986
625	1	Assign Problem	Assigned problem to Ruchita_Umalkar	2401:4900:1c44:55a9:4df5:6464:37d3:b175, 127.0.0.1	2025-12-25 17:36:30.615089
626	1	Cancel Event	Cancelled test for Ruchita_Umalkar	2401:4900:1c44:55a9:4df5:6464:37d3:b175, 127.0.0.1	2025-12-25 17:38:31.954759
627	1	Logout	User logged out	2401:4900:1c44:55a9:411d:ac4:a922:e33b, 127.0.0.1	2025-12-26 06:10:48.990567
628	1	Login	User logged in successfully	2401:4900:1c44:55a9:993:a323:9973:e525, 127.0.0.1	2025-12-26 12:02:41.600078
629	1	Logout	User logged out	2401:4900:1c44:55a9:993:a323:9973:e525, 127.0.0.1	2025-12-26 12:02:45.937424
630	1	Login	User logged in successfully	2401:4900:1c44:55a9:993:a323:9973:e525, 127.0.0.1	2025-12-26 12:02:56.282365
631	1	Assign Problem	Assigned problem to Ruchita_Umalkar	2401:4900:1c44:55a9:fc3e:5a6b:ca19:1640, 127.0.0.1	2025-12-26 12:10:24.571527
632	1	Logout	User logged out	2401:4900:1c44:55a9:fc3e:5a6b:ca19:1640, 127.0.0.1	2025-12-26 12:11:20.446237
633	1	Logout	User logged out	127.0.0.1	2025-12-26 12:35:39.883666
634	1	Logout	User logged out	2409:40c2:601f:8201:1853:7fb7:9646:8355, 127.0.0.1	2025-12-26 13:07:52.212248
635	1	Login	User logged in successfully	152.59.57.249, 127.0.0.1	2025-12-26 14:22:35.57492
636	1	Assign Moderator	Assigned moderator Gaurav_Moderator to candidate Ruchita_Umalkar	152.59.57.249, 127.0.0.1	2025-12-26 14:22:51.960968
637	1	Login	User logged in successfully	223.233.86.220, 127.0.0.1	2025-12-26 15:23:19.28219
638	1	Login	User logged in successfully	127.0.0.1	2025-12-26 15:23:45.760972
639	1	Logout	User logged out	2401:4900:1c44:55a9:4e9:5984:53d1:748a, 127.0.0.1	2025-12-26 15:52:20.540131
640	1	Login	User logged in successfully	2401:4900:1c44:55a9:4e9:5984:53d1:748a, 127.0.0.1	2025-12-26 16:08:22.858739
641	1	Logout	User logged out	127.0.0.1	2025-12-26 16:10:17.213078
642	1	Login	User logged in successfully	127.0.0.1	2025-12-26 16:10:23.710948
643	1	Logout	User logged out	127.0.0.1	2025-12-26 16:10:39.187807
644	3	Login	User logged in successfully	127.0.0.1	2025-12-26 16:18:02.269619
645	3	View Learning Content	Viewed java tutorial	127.0.0.1	2025-12-26 16:18:13.230491
646	3	Logout	User logged out	127.0.0.1	2025-12-26 16:22:28.943764
647	3	Login	User logged in successfully	127.0.0.1	2025-12-26 16:22:34.853532
648	3	Logout	User logged out	127.0.0.1	2025-12-26 16:52:44.032022
649	1	Login	User logged in successfully	127.0.0.1	2025-12-26 16:52:53.79125
650	1	Logout	User logged out	223.233.86.220, 127.0.0.1	2025-12-26 17:24:32.643466
651	1	Login	User logged in successfully	2401:4900:1c44:55a9:11e4:95e:452e:ca9f, 127.0.0.1	2025-12-26 17:26:57.918195
652	1	Logout	User logged out	127.0.0.1	2025-12-26 17:55:53.80036
653	1	Login	User logged in successfully	127.0.0.1	2025-12-26 17:56:00.229183
654	1	Update Order	Updated order ORD-1766209863-15 to Order Dispatched	127.0.0.1	2025-12-26 17:56:17.46204
655	1	Update Order	Updated order ORD-1766209863-15 to Order Delivered	127.0.0.1	2025-12-26 17:56:35.275289
656	1	Logout	User logged out	127.0.0.1	2025-12-26 17:59:28.100573
657	15	Login	User logged in successfully	127.0.0.1	2025-12-26 17:59:37.396061
658	15	Logout	User logged out	127.0.0.1	2025-12-26 18:06:23.422475
659	1	Login	User logged in successfully	127.0.0.1	2025-12-26 18:06:32.1978
660	1	Assign Problem	Assigned problem to Ruchita_Umalkar	127.0.0.1	2025-12-26 18:06:51.14786
661	1	Logout	User logged out	2401:4900:1c44:55a9:5865:7375:fdc2:2ff7, 127.0.0.1	2025-12-26 18:14:11.552476
662	1	Login	User logged in successfully	2401:4900:1c44:55a9:5865:7375:fdc2:2ff7, 127.0.0.1	2025-12-26 18:14:21.072589
663	1	Logout	User logged out	2401:4900:1c44:55a9:11e4:95e:452e:ca9f, 127.0.0.1	2025-12-26 18:17:22.454919
664	20	Login	User logged in successfully	2401:4900:1c44:55a9:11e4:95e:452e:ca9f, 127.0.0.1	2025-12-26 18:18:27.23514
665	1	Login	User logged in successfully	2401:4900:1c44:55a9:11e4:95e:452e:ca9f, 127.0.0.1	2025-12-27 01:36:15.55707
666	1	Logout	User logged out	2401:4900:1c44:55a9:5865:7375:fdc2:2ff7, 127.0.0.1	2025-12-27 03:19:22.590264
667	3	Login	User logged in successfully	2401:4900:1c44:55a9:5865:7375:fdc2:2ff7, 127.0.0.1	2025-12-27 03:19:31.526319
668	1	Logout	User logged out	127.0.0.1	2025-12-27 03:37:01.704451
669	3	Login	User logged in successfully	127.0.0.1	2025-12-27 03:37:12.925168
670	3	View Learning Content	Viewed java tutorial	127.0.0.1	2025-12-27 03:37:19.535035
671	3	View Learning Content	Viewed java tutorial	127.0.0.1	2025-12-27 03:41:27.141278
672	3	View Learning Content	Viewed java tutorial	127.0.0.1	2025-12-27 03:44:05.31751
673	3	View Learning Content	Viewed java tutorial	127.0.0.1	2025-12-27 03:47:53.797501
674	3	View Learning Content	Viewed java tutorial	127.0.0.1	2025-12-27 03:49:40.018217
675	3	View Learning Content	Viewed java tutorial	127.0.0.1	2025-12-27 03:51:05.401647
676	3	View Learning Content	Viewed java tutorial	127.0.0.1	2025-12-27 03:52:41.213329
677	3	View Learning Content	Viewed java tutorial	127.0.0.1	2025-12-27 03:57:12.006379
678	3	View Learning Content	Viewed java tutorial	127.0.0.1	2025-12-27 04:01:23.388279
679	3	View Learning Content	Viewed cpp tutorial	127.0.0.1	2025-12-27 04:01:35.554035
680	3	View Learning Content	Viewed java tutorial	127.0.0.1	2025-12-27 04:11:06.112637
681	3	View Learning Content	Viewed java tutorial	2401:4900:1c44:55a9:5865:7375:fdc2:2ff7, 127.0.0.1	2025-12-27 04:17:32.233761
682	3	View Learning Content	Viewed java tutorial	2401:4900:1c44:55a9:5865:7375:fdc2:2ff7, 127.0.0.1	2025-12-27 04:17:37.659549
683	3	Logout	User logged out	2401:4900:1c44:55a9:5865:7375:fdc2:2ff7, 127.0.0.1	2025-12-27 04:18:31.290779
684	3	Login	User logged in successfully	2401:4900:1c44:55a9:5865:7375:fdc2:2ff7, 127.0.0.1	2025-12-27 04:18:41.041226
685	3	View Learning Content	Viewed java tutorial	2401:4900:1c44:55a9:5865:7375:fdc2:2ff7, 127.0.0.1	2025-12-27 04:18:45.09871
686	3	View Learning Content	Viewed java tutorial	127.0.0.1	2025-12-27 04:19:25.716662
687	1	Logout	User logged out	2401:4900:1c44:55a9:f8c0:334:46e7:b48a, 127.0.0.1	2025-12-27 04:23:17.270696
688	3	Login	User logged in successfully	2401:4900:1c44:55a9:f8c0:334:46e7:b48a, 127.0.0.1	2025-12-27 04:23:28.478359
689	3	View Learning Content	Viewed java tutorial	2401:4900:1c44:55a9:f8c0:334:46e7:b48a, 127.0.0.1	2025-12-27 04:23:34.305428
690	3	View Learning Content	Viewed java tutorial	2401:4900:1c44:55a9:f8c0:334:46e7:b48a, 127.0.0.1	2025-12-27 04:31:37.020478
691	3	View Learning Content	Viewed java tutorial	2401:4900:1c44:55a9:f8c0:334:46e7:b48a, 127.0.0.1	2025-12-27 04:31:41.593701
692	3	View Learning Content	Viewed java tutorial	2401:4900:1c44:55a9:f8c0:334:46e7:b48a, 127.0.0.1	2025-12-27 04:41:57.404818
693	3	View Learning Content	Viewed java tutorial	2401:4900:1c44:55a9:f8c0:334:46e7:b48a, 127.0.0.1	2025-12-27 05:00:01.093391
694	3	View Learning Content	Viewed java tutorial	2401:4900:1c44:55a9:f8c0:334:46e7:b48a, 127.0.0.1	2025-12-27 05:24:46.726265
695	3	View Learning Content	Viewed java tutorial	2401:4900:1c44:55a9:f8c0:334:46e7:b48a, 127.0.0.1	2025-12-27 05:33:48.841771
696	3	View Learning Content	Viewed java tutorial	2401:4900:1c44:55a9:f8c0:334:46e7:b48a, 127.0.0.1	2025-12-27 05:33:57.635492
697	3	Logout	User logged out	2401:4900:1c44:55a9:f8c0:334:46e7:b48a, 127.0.0.1	2025-12-27 05:40:15.127573
698	3	Login	User logged in successfully	2401:4900:1c44:55a9:f8c0:334:46e7:b48a, 127.0.0.1	2025-12-27 05:40:30.223306
699	3	View Learning Content	Viewed java tutorial	2401:4900:1c44:55a9:f8c0:334:46e7:b48a, 127.0.0.1	2025-12-27 05:40:36.059124
700	3	View Learning Content	Viewed java tutorial	2401:4900:1c44:55a9:f8c0:334:46e7:b48a, 127.0.0.1	2025-12-27 05:48:34.847847
701	3	View Learning Content	Viewed java tutorial	2401:4900:1c44:55a9:f8c0:334:46e7:b48a, 127.0.0.1	2025-12-27 06:18:28.512843
702	3	View Learning Content	Viewed java tutorial	2401:4900:1c44:55a9:f8c0:334:46e7:b48a, 127.0.0.1	2025-12-27 06:20:24.534247
703	3	View Learning Content	Viewed java tutorial	2401:4900:1c44:55a9:f8c0:334:46e7:b48a, 127.0.0.1	2025-12-27 06:24:00.329949
704	3	View Learning Content	Viewed java tutorial	2401:4900:1c44:55a9:f8c0:334:46e7:b48a, 127.0.0.1	2025-12-27 06:27:24.174448
705	3	View Learning Content	Viewed java tutorial	2401:4900:1c44:55a9:f8c0:334:46e7:b48a, 127.0.0.1	2025-12-27 06:27:30.430423
706	3	View Learning Content	Viewed java tutorial	2401:4900:1c44:55a9:f8c0:334:46e7:b48a, 127.0.0.1	2025-12-27 06:31:31.027322
707	3	View Learning Content	Viewed java tutorial	2401:4900:1c44:55a9:f8c0:334:46e7:b48a, 127.0.0.1	2025-12-27 06:31:44.430961
708	3	View Learning Content	Viewed java tutorial	2401:4900:1c44:55a9:f8c0:334:46e7:b48a, 127.0.0.1	2025-12-27 06:32:36.243612
709	3	View Learning Content	Viewed java tutorial	2401:4900:1c44:55a9:f8c0:334:46e7:b48a, 127.0.0.1	2025-12-27 06:36:45.195842
710	1	Login	User logged in successfully	2409:40c2:600f:18a5:2d05:9b62:db9f:52aa, 127.0.0.1	2025-12-27 06:54:01.235117
711	1	Logout	User logged out	152.59.60.184, 127.0.0.1	2025-12-27 07:03:37.153643
712	1	Logout	User logged out	152.59.60.184, 127.0.0.1	2025-12-27 07:03:37.993823
713	1	Login	User logged in successfully	2409:40c2:600f:18a5:2d05:9b62:db9f:52aa, 127.0.0.1	2025-12-27 07:14:40.598844
714	1	Logout	User logged out	2409:40c2:600f:18a5:2d05:9b62:db9f:52aa, 127.0.0.1	2025-12-27 07:16:59.408445
715	17	Login	User logged in successfully	2409:40c2:1059:8915:ac53:f8ff:fee5:af9c, 127.0.0.1	2025-12-27 11:11:36.499837
716	3	Login	User logged in successfully	2401:4900:1c44:55a9:b0:dd7c:8d12:45db, 127.0.0.1	2025-12-27 11:16:44.413054
717	3	View Learning Content	Viewed java tutorial	2401:4900:1c44:55a9:b0:dd7c:8d12:45db, 127.0.0.1	2025-12-27 11:16:56.404836
718	3	Logout	User logged out	2401:4900:1c44:55a9:b0:dd7c:8d12:45db, 127.0.0.1	2025-12-27 11:17:53.219315
719	3	Logout	User logged out	2401:4900:1c44:55a9:b0:dd7c:8d12:45db, 127.0.0.1	2025-12-27 11:17:53.531781
720	3	View Learning Content	Viewed java tutorial	2401:4900:1c44:55a9:3996:c409:dd5c:4002, 127.0.0.1	2025-12-27 16:05:35.083849
721	3	Logout	User logged out	2401:4900:1c44:55a9:3996:c409:dd5c:4002, 127.0.0.1	2025-12-27 16:07:28.715252
722	1	Login	User logged in successfully	2401:4900:1c44:55a9:3996:c409:dd5c:4002, 127.0.0.1	2025-12-27 16:07:40.210419
723	1	Logout	User logged out	2401:4900:1c44:55a9:3996:c409:dd5c:4002, 127.0.0.1	2025-12-27 16:09:41.138035
724	1	Login	User logged in successfully	2401:4900:1c44:55a9:31a1:9f21:eb45:c751, 127.0.0.1	2025-12-27 16:29:46.67475
725	3	Logout	User logged out	223.233.86.220, 127.0.0.1	2025-12-27 16:43:11.137313
726	1	Login	User logged in successfully	223.233.86.220, 127.0.0.1	2025-12-27 16:43:23.933055
727	1	Create Invoice	Created invoice INV2025041 for Jayesh Barhate	2401:4900:1c44:55a9:74c5:6f0:8606:cd2a, 127.0.0.1	2025-12-27 17:57:57.588874
728	1	Login	User logged in successfully	223.233.86.220, 127.0.0.1	2025-12-27 18:38:40.839799
729	1	Admin Stock Update	Changed Jayesh_SL450's stock for Boat BassHeads 100 in-Ear Headphones with Mic (Black) from 3 to 4	223.233.86.220, 127.0.0.1	2025-12-27 18:39:36.749501
730	1	Admin Stock Update	Changed Jayesh_SL450's stock for HP M120 /6 programm. buttons,1 AA battery gives upto 12 months life from 1 to 2	223.233.86.220, 127.0.0.1	2025-12-27 18:39:49.344969
731	1	Logout	User logged out	2401:4900:1c44:55a9:ec17:21b5:ae52:6081, 127.0.0.1	2025-12-28 04:13:08.322661
732	1	Login	User logged in successfully	2401:4900:1c44:55a9:ec17:21b5:ae52:6081, 127.0.0.1	2025-12-28 05:16:33.412526
733	1	Logout	User logged out	2401:4900:1c44:55a9:ec17:21b5:ae52:6081, 127.0.0.1	2025-12-28 08:16:17.854514
734	1	Login	User logged in successfully	2401:4900:1c44:55a9:ec17:21b5:ae52:6081, 127.0.0.1	2025-12-28 08:16:29.233661
735	1	Logout	User logged out	2401:4900:1c44:55a9:ec17:21b5:ae52:6081, 127.0.0.1	2025-12-28 08:17:39.203855
736	3	Login	User logged in successfully	2401:4900:1c44:55a9:ec17:21b5:ae52:6081, 127.0.0.1	2025-12-28 08:17:57.410512
737	3	View Learning Content	Viewed java tutorial	2401:4900:1c44:55a9:ec17:21b5:ae52:6081, 127.0.0.1	2025-12-28 08:18:03.469876
738	3	Update Profile	User updated their profile details	2401:4900:1c44:55a9:ec17:21b5:ae52:6081, 127.0.0.1	2025-12-28 08:19:30.786757
739	3	Logout	User logged out	2401:4900:1c44:55a9:ec17:21b5:ae52:6081, 127.0.0.1	2025-12-28 09:39:29.493802
740	1	Login	User logged in successfully	2401:4900:1c44:55a9:ec17:21b5:ae52:6081, 127.0.0.1	2025-12-28 09:39:43.43277
741	3	Logout	User logged out	127.0.0.1	2025-12-28 10:03:50.327259
742	1	Login	User logged in successfully	127.0.0.1	2025-12-28 10:04:00.446166
743	1	Logout	User logged out	127.0.0.1	2025-12-28 10:09:33.1396
744	1	Login	User logged in successfully	127.0.0.1	2025-12-28 10:09:42.084844
745	1	Logout	User logged out	127.0.0.1	2025-12-28 10:21:02.960525
746	1	Login	User logged in successfully	127.0.0.1	2025-12-28 10:21:09.549689
747	1	Logout	User logged out	127.0.0.1	2025-12-28 10:51:41.714138
748	1	Login	User logged in successfully	127.0.0.1	2025-12-28 10:52:13.343817
749	2	View Learning Content	Viewed c tutorial	127.0.0.1	2025-12-28 10:54:44.247225
750	2	View Learning Content	Viewed java tutorial	127.0.0.1	2025-12-28 11:01:10.610175
751	1	Logout	User logged out	2401:4900:1c44:55a9:582f:4b4e:2dfc:797e, 127.0.0.1	2025-12-28 11:50:19.712916
752	1	Login	User logged in successfully	2401:4900:1c44:55a9:582f:4b4e:2dfc:797e, 127.0.0.1	2025-12-28 11:50:28.88501
753	1	Approve Stock	Approved 5 units of Apple 20W USB‑C Power Adapter for Pranav_SL898	2401:4900:1c44:55a9:582f:4b4e:2dfc:797e, 127.0.0.1	2025-12-28 11:50:41.314718
754	1	Logout	User logged out	2401:4900:1c44:55a9:ec17:21b5:ae52:6081, 127.0.0.1	2025-12-28 12:21:25.9766
755	1	Login	User logged in successfully	2401:4900:1c44:55a9:ec17:21b5:ae52:6081, 127.0.0.1	2025-12-28 12:28:01.71108
756	3	View Learning Content	Viewed java tutorial	192.168.65.1	2025-12-28 13:37:10.130931
757	1	Approve User	Approved user Test1	192.168.65.1	2025-12-28 14:39:09.262972
758	1	Approve User	Approved user recruiter test	192.168.65.1	2025-12-28 14:44:16.145481
759	1	Approve User	Approved user dt	192.168.65.1	2025-12-28 15:24:47.615204
760	1	Reject User	Rejected user registration for t4er4	2401:4900:1c44:55a9:40c5:6897:388d:b019, 127.0.0.1	2025-12-28 18:32:13.678042
761	1	Reject User	Rejected user registration for hgvc	2401:4900:1c44:55a9:40c5:6897:388d:b019, 127.0.0.1	2025-12-28 18:32:26.943889
762	1	Assign Moderator	Assigned moderator Gaurav_Moderator to candidate Ruchita_Umalkar	192.168.65.1	2025-12-29 05:47:25.769039
763	1	Assign Problem	Assigned problem to Ruchita_Umalkar	192.168.65.1	2025-12-29 05:55:51.503089
764	1	Reschedule Event	Rescheduled test for Ruchita_Umalkar	192.168.65.1	2025-12-29 05:56:17.976668
765	1	Mark EMI Paid	Marked installment #14 as paid	223.233.86.220, 127.0.0.1	2026-01-01 09:46:42.607919
766	1	Approve User	Approved user VivekP	223.233.84.212, 127.0.0.1	2026-01-04 10:21:07.252158
767	3	View Learning Content	Viewed cpp tutorial	2401:4900:1c45:9fe2:b1d9:a803:4921:3be0, 127.0.0.1	2026-01-04 12:16:20.725589
768	3	View Learning Content	Viewed java tutorial	2401:4900:1c45:9fe2:b1d9:a803:4921:3be0, 127.0.0.1	2026-01-04 12:18:18.081119
769	3	View Learning Content	Viewed c tutorial	2401:4900:1c45:9fe2:b1d9:a803:4921:3be0, 127.0.0.1	2026-01-04 12:19:12.368263
770	3	Apply Job	Applied for job ID: 3	2401:4900:1c45:9fe2:b1d9:a803:4921:3be0, 127.0.0.1	2026-01-04 12:46:51.396135
771	1	Accept Application	Accepted application for Ruchita_Umalkar	2401:4900:1c45:9fe2:6c68:2fab:2fb0:3d9c, 127.0.0.1	2026-01-04 12:47:43.135462
772	3	View Learning Content	Viewed c tutorial	223.233.84.212, 127.0.0.1	2026-01-04 15:02:28.959359
773	12	View Learning Content	Viewed java tutorial	2401:4900:881e:9521:e403:af69:3905:af86, 127.0.0.1	2026-01-04 15:22:39.824665
774	12	Change Password	User changed their password	2401:4900:881e:9521:e403:af69:3905:af86, 127.0.0.1	2026-01-04 15:24:38.523373
775	29	Update Profile	User updated their profile details	2405:201:24:dc22:4981:57b9:5877:44e8, 127.0.0.1	2026-01-04 16:01:25.813029
776	29	Update Profile	User updated their profile details	2405:201:24:dc22:4981:57b9:5877:44e8, 127.0.0.1	2026-01-04 16:02:24.191477
777	3	View Learning Content	Viewed sql tutorial	223.233.84.212, 127.0.0.1	2026-01-05 12:02:18.640623
778	3	View Learning Content	Viewed sql tutorial	223.233.84.212, 127.0.0.1	2026-01-05 12:02:35.578244
779	1	Share BRD	Shared BRD for WRD_Finance_03 with gp2239396@gmail.com	2401:4900:1c45:9fe2:29d7:e81c:ff21:1c1b, 127.0.0.1	2026-01-06 11:20:18.380127
780	3	View Learning Content	Viewed c tutorial	223.233.84.212, 127.0.0.1	2026-01-06 12:29:26.265254
781	1	Create Invoice	Created invoice INV-A3697A	223.233.82.52, 127.0.0.1	2026-01-07 16:15:15.666313
782	1	Create Project	Created project MSR_Legacy_CGR_Migration	223.233.86.137, 127.0.0.1	2026-01-08 10:15:58.509349
783	1	Post Job	Posted new job opening: Senior Cloud Architect (Azure Focus)	2401:4900:1c43:3d3a:90ab:310b:b58:66ef, 127.0.0.1	2026-01-08 10:24:17.959338
784	1	Post Job	Posted new job opening: Lead Frontend Engineer (React.js Focus)	2401:4900:1c43:3d3a:90ab:310b:b58:66ef, 127.0.0.1	2026-01-08 10:25:06.796413
785	1	Delete Job	Deleted job Lead Frontend Engineer (React.js Focus)	2401:4900:1c43:3d3a:cdb:2f7c:f810:1b85, 127.0.0.1	2026-01-08 10:48:43.11795
786	1	Delete Job	Deleted job Senior Cloud Architect (Azure Focus)	2401:4900:1c43:3d3a:cdb:2f7c:f810:1b85, 127.0.0.1	2026-01-08 10:48:45.786838
787	1	Post Job	Posted new job opening: Frontend Engineer (React.js Focus)	2401:4900:1c43:3d3a:cdb:2f7c:f810:1b85, 127.0.0.1	2026-01-08 10:49:50.112376
788	1	Post Job	Posted new job opening: Full Stack Modernization Engineer (Hybrid: React + Azure)	2401:4900:1c43:3d3a:cdb:2f7c:f810:1b85, 127.0.0.1	2026-01-08 10:50:25.115162
789	3	Apply Job	Applied for job ID: 6	2401:4900:1c43:3d3a:cdb:2f7c:f810:1b85, 127.0.0.1	2026-01-08 10:50:59.156332
790	1	Reject Application	Rejected application for Ruchita_Umalkar	2401:4900:1c43:3d3a:cdb:2f7c:f810:1b85, 127.0.0.1	2026-01-08 10:52:13.733447
791	29	Apply Job	Applied for job ID: 6	136.226.254.172, 127.0.0.1	2026-01-08 16:03:49.524812
792	1	Share BRD	Shared BRD for MSR_Legacy_CGR_Migration with gp2239396@gmail.com	223.233.86.137, 127.0.0.1	2026-01-09 11:28:21.715522
793	1	Add Transaction	Added transaction to project MSR_Legacy_CGR_Migration	2401:4900:1c43:3d3a:49b2:d973:95ed:40b6, 127.0.0.1	2026-01-09 13:44:50.196786
794	1	Add Transaction	Added transaction to project MSR_Legacy_CGR_Migration	2401:4900:1c43:3d3a:49b2:d973:95ed:40b6, 127.0.0.1	2026-01-09 13:45:43.767846
795	1	Add Transaction	Added transaction to project MSR_Legacy_CGR_Migration	2401:4900:1c43:3d3a:49b2:d973:95ed:40b6, 127.0.0.1	2026-01-09 13:46:28.812812
796	1	Accept Application	Accepted application for VivekP	223.233.86.137, 127.0.0.1	2026-01-09 14:53:35.704413
797	3	View Learning Content	Viewed cpp tutorial	2401:4900:1c7e:968c:5dd8:1e6b:a401:8b46, 127.0.0.1	2026-01-11 15:16:08.064356
798	1	Create Invoice	Created invoice INV-A3F4D6	2409:40c2:8003:58d4:44e8:4fc7:4206:c37b, 127.0.0.1	2026-01-16 05:51:41.823921
799	1	Delete Seller Alloc	Removed allocation 9	152.58.17.192, 127.0.0.1	2026-01-17 15:06:05.406853
800	1	Assign Inventory	Assigned 1 of Larah Vogue Glass Lunchbox, Round x 3, 400ml x 3 to seller 17	152.58.17.192, 127.0.0.1	2026-01-17 15:07:06.531797
801	1	Create EMI Plan	Created plan 'SBI CC ' for Borrower 16	223.233.85.70, 127.0.0.1	2026-01-18 10:48:12.079481
802	1	Create Invoice	Created invoice INV-D8E828	2401:4900:1c44:863d:ded:dbc2:6af7:9274, 127.0.0.1	2026-01-18 13:26:57.384271
803	1	Create Invoice	Created invoice INV-DED7DB	2401:4900:1c7e:fde7:f888:329e:11ee:facb, 127.0.0.1	2026-01-20 10:48:05.764253
804	3	View Learning Content	Viewed java tutorial	2401:4900:1c7e:fde7:dc2e:7f2e:4410:3f85, 127.0.0.1	2026-01-21 19:28:36.477291
805	3	View Learning Content	Viewed cpp tutorial	2401:4900:1c7e:fde7:2057:f5de:da29:273d, 127.0.0.1	2026-01-22 10:30:24.55132
806	3	Apply Job	Applied for job ID: 7	2401:4900:1c7e:fde7:2057:f5de:da29:273d, 127.0.0.1	2026-01-22 10:31:34.251805
807	1	Accept Application	Accepted application for Ruchita Umalkar	2401:4900:1c7e:fde7:2057:f5de:da29:273d, 127.0.0.1	2026-01-22 10:32:11.530731
808	3	View Learning Content	Viewed mysql tutorial	2401:4900:1c7e:fde7:2057:f5de:da29:273d, 127.0.0.1	2026-01-22 10:36:30.453621
809	1	Toggle User Status	Deactivated user dt	2401:4900:1c7e:fde7:2057:f5de:da29:273d, 127.0.0.1	2026-01-22 10:49:47.888029
810	1	Toggle User Status	Deactivated user Test	2401:4900:1c7e:fde7:2057:f5de:da29:273d, 127.0.0.1	2026-01-22 10:50:13.029567
811	1	Assign Problem	Assigned problem to Ruchita Umalkar	223.233.86.77, 127.0.0.1	2026-01-23 13:39:08.78613
812	1	Create Invoice	Created invoice INV-20F241	223.233.84.156, 127.0.0.1	2026-01-26 13:40:29.482511
813	1	Add Product	Added product Resonate RouterUPS® Gen2 | Original Router UPS for 12V WiFi Router & Modem (Supports up to 2A)	2401:4900:1c7e:2c6a:99:63c8:7c6c:288c, 127.0.0.1	2026-01-26 15:00:03.169712
814	1	Add Product	Added product ASUS MW203 Multi-Device Wireless Silent Mouse, 2.4GHz with USB Nano Receiver	2401:4900:1c7e:2c6a:99:63c8:7c6c:288c, 127.0.0.1	2026-01-26 15:04:18.063081
\.


--
-- Data for Name: activity_update; Type: TABLE DATA; Schema: public; Owner: sourcepoint_admin
--

COPY public.activity_update (id, content, "timestamp", user_id) FROM stdin;
1	Working on SVT	2025-11-23 15:54:58.181128	2
\.


--
-- Data for Name: affiliate_ad; Type: TABLE DATA; Schema: public; Owner: sourcepoint_admin
--

COPY public.affiliate_ad (id, ad_name, affiliate_link) FROM stdin;
\.


--
-- Data for Name: alembic_version; Type: TABLE DATA; Schema: public; Owner: sourcepoint_admin
--

COPY public.alembic_version (version_num) FROM stdin;
138e2cce99cd
\.


--
-- Data for Name: brd; Type: TABLE DATA; Schema: public; Owner: sourcepoint_admin
--

COPY public.brd (id, project_id, executive_summary, project_objectives, project_scope, business_requirements, key_stakeholders, project_constraints, cost_benefit_analysis, executive_summary_label, project_objectives_label, project_scope_label, business_requirements_label, key_stakeholders_label, project_constraints_label, cost_benefit_analysis_label) FROM stdin;
1	3	<p>FinSync is a modern, web-based financial intelligence platform designed for Small to Medium-sized Enterprises (SMEs). The project addresses the critical business problem of fragmented financial data and the resulting reliance on time-consuming, error-prone manual reporting. By providing a single source of truth that securely integrates with <strong>SAP</strong> and <strong>Oracle</strong> ERP systems, FinSync will automate data aggregation and deliver real-time insights through an intuitive dashboard. The solution will be built using a high-performance <strong>NodeJS</strong> and <strong>microservices</strong> architecture, ensuring scalability and reliability. The primary outcome will be faster, more accurate financial reporting, enabling agile and data-driven decision-making for business leaders.</p>	<p>&nbsp;</p>\r\n<p>The project is designed to achieve the following SMART objectives:</p>\r\n<ul>\r\n<li>\r\n<p><strong>Reduce Manual Effort:</strong> Decrease the man-hours spent on manual data consolidation for financial reporting by <strong>70%</strong> within six months of product launch.</p>\r\n</li>\r\n<li>\r\n<p><strong>Increase Data Accuracy:</strong> Achieve a data accuracy rate of over <strong>99%</strong> in all generated reports by eliminating manual data entry errors.</p>\r\n</li>\r\n<li>\r\n<p><strong>Improve Decision-Making Speed:</strong> Provide stakeholders with on-demand, real-time access to a dashboard of key financial KPIs, accessible 24/7.</p>\r\n</li>\r\n</ul>	<p>&nbsp;</p>\r\n<h4><strong>In-Scope</strong></h4>\r\n<p>&nbsp;</p>\r\n<ul>\r\n<li>\r\n<p>A secure, role-based web application for user access.</p>\r\n</li>\r\n<li>\r\n<p>A centralized dashboard displaying key financial KPIs.</p>\r\n</li>\r\n<li>\r\n<p>Read-only API integration with SAP S/4HANA Cloud and Oracle NetSuite.</p>\r\n</li>\r\n<li>\r\n<p>Automated and manual data synchronization capabilities.</p>\r\n</li>\r\n<li>\r\n<p>Generation of standard financial reports (e.g., Profit &amp; Loss, Balance Sheet).</p>\r\n</li>\r\n<li>\r\n<p>Export functionality for all reports to PDF and CSV formats.</p>\r\n</li>\r\n</ul>\r\n<p>&nbsp;</p>\r\n<h4><strong>Out-of-Scope</strong></h4>\r\n<p>&nbsp;</p>\r\n<ul>\r\n<li>\r\n<p>Transaction processing (e.g., sending payments, creating invoices).</p>\r\n</li>\r\n<li>\r\n<p>Budgeting and financial forecasting features.</p>\r\n</li>\r\n<li>\r\n<p>A native mobile application (the initial release is web-only)</p>\r\n</li>\r\n</ul>	<p>The core business requirements are captured in the following user stories:</p>\r\n<p>&nbsp;</p>\r\n<h4><strong>Admin &amp; System Requirements</strong></h4>\r\n<p>&nbsp;</p>\r\n<ul>\r\n<li>\r\n<p><strong>System Setup:</strong> The system must allow an Admin to securely connect the company's SAP and Oracle accounts to enable automated data imports.</p>\r\n</li>\r\n<li>\r\n<p><strong>User Management:</strong> The system must allow an Admin to invite, manage, and assign roles to users to ensure proper data governance.</p>\r\n</li>\r\n<li>\r\n<p><strong>Performance:</strong> The system must deliver a fast, responsive user experience, with API response times under 500ms and dashboard load times under 3 seconds.</p>\r\n</li>\r\n<li>\r\n<p><strong>Security:</strong> The system must implement industry-standard security best practices to protect all sensitive financial data.</p>\r\n</li>\r\n</ul>\r\n<p>&nbsp;</p>\r\n<h4><strong>Manager &amp; Reporting Requirements</strong></h4>\r\n<p>&nbsp;</p>\r\n<ul>\r\n<li>\r\n<p><strong>Dashboarding:</strong> The system must provide Managers with a real-time dashboard to assess the company's financial performance at a glance.</p>\r\n</li>\r\n<li>\r\n<p><strong>Reporting:</strong> The system must allow Managers to generate standard financial reports for specific date ranges.</p>\r\n</li>\r\n<li>\r\n<p><strong>Data Export:</strong> The system must allow Managers to export all reports to PDF and CSV formats for offline analysis and sharing.</p>\r\n</li>\r\n</ul>\r\n<p>&nbsp;</p>	<table dir="ltr" style="width: 100%; height: 179.188px;" border="1" cellspacing="0" cellpadding="0" data-sheets-root="1" data-sheets-baot="1"><colgroup><col style="width: 20.4208%;" width="165"><col style="width: 39.2327%;" width="317"><col style="width: 67.3267%;" width="544"></colgroup>\r\n<tbody>\r\n<tr style="height: 22.3984px;">\r\n<td style="height: 22.3984px;">Stakeholder Role</td>\r\n<td style="height: 22.3984px;">Name/Title</td>\r\n<td style="height: 22.3984px;">Responsibilities</td>\r\n</tr>\r\n<tr style="height: 44.7969px;">\r\n<td style="height: 44.7969px;">Project Sponsor</td>\r\n<td style="height: 44.7969px;">Head of Finance</td>\r\n<td style="height: 44.7969px;">Provides funding, champions the project, and signs off on deliverables.</td>\r\n</tr>\r\n<tr style="height: 44.7969px;">\r\n<td style="height: 44.7969px;">End Users</td>\r\n<td style="height: 44.7969px;">Financial Analysts, Accountants, Managers</td>\r\n<td style="height: 44.7969px;">Will use the platform for daily reporting and analysis tasks.</td>\r\n</tr>\r\n<tr style="height: 67.1953px;">\r\n<td style="height: 67.1953px;">Technical Team</td>\r\n<td style="height: 67.1953px;">NodeJS Developers, DevOps Engineers</td>\r\n<td style="height: 67.1953px;">Responsible for the design, development, deployment, and maintenance of the application.</td>\r\n</tr>\r\n</tbody>\r\n</table>	<p>&nbsp;</p>\r\n<ul>\r\n<li>\r\n<p><strong>Technology Stack:</strong> The project is constrained to the specified technical architecture: <strong>NodeJS, Microservices, and MongoDB</strong>.</p>\r\n</li>\r\n<li>\r\n<p><strong>Third-Party APIs:</strong> The project's functionality is dependent on the availability, reliability, and access to the APIs of SAP and Oracle.</p>\r\n</li>\r\n<li>\r\n<p><strong>Timeline:</strong> The initial version (MVP) of the project is targeted for delivery within a 6-month timeframe. <em>(placeholder)</em></p>\r\n</li>\r\n<li>\r\n<p><strong>Budget:</strong> The project must be completed within the allocated budget of $XXX,XXX. <em>(placeholder)</em></p>\r\n</li>\r\n</ul>	<p>&nbsp;</p>\r\n<p>Of course. Here is the FinSync BRD reformatted into your specified structure, incorporating all the details we've discussed.</p>\r\n<hr>\r\n<p>&nbsp;</p>\r\n<h3><strong>1. Executive Summary</strong></h3>\r\n<p>&nbsp;</p>\r\n<p>FinSync is a modern, web-based financial intelligence platform designed for Small to Medium-sized Enterprises (SMEs). The project addresses the critical business problem of fragmented financial data and the resulting reliance on time-consuming, error-prone manual reporting. By providing a single source of truth that securely integrates with <strong>SAP</strong> and <strong>Oracle</strong> ERP systems, FinSync will automate data aggregation and deliver real-time insights through an intuitive dashboard. The solution will be built using a high-performance <strong>NodeJS</strong> and <strong>microservices</strong> architecture, ensuring scalability and reliability. The primary outcome will be faster, more accurate financial reporting, enabling agile and data-driven decision-making for business leaders.</p>\r\n<hr>\r\n<p>&nbsp;</p>\r\n<h3><strong>2. Project Objectives</strong></h3>\r\n<p>&nbsp;</p>\r\n<p>The project is designed to achieve the following SMART objectives:</p>\r\n<ul>\r\n<li>\r\n<p><strong>Reduce Manual Effort:</strong> Decrease the man-hours spent on manual data consolidation for financial reporting by <strong>70%</strong> within six months of product launch.</p>\r\n</li>\r\n<li>\r\n<p><strong>Increase Data Accuracy:</strong> Achieve a data accuracy rate of over <strong>99%</strong> in all generated reports by eliminating manual data entry errors.</p>\r\n</li>\r\n<li>\r\n<p><strong>Improve Decision-Making Speed:</strong> Provide stakeholders with on-demand, real-time access to a dashboard of key financial KPIs, accessible 24/7.</p>\r\n</li>\r\n</ul>\r\n<hr>\r\n<p>&nbsp;</p>\r\n<h3><strong>3. Project Scope</strong></h3>\r\n<p>&nbsp;</p>\r\n<p>&nbsp;</p>\r\n<h4><strong>In-Scope</strong></h4>\r\n<p>&nbsp;</p>\r\n<ul>\r\n<li>\r\n<p>A secure, role-based web application for user access.</p>\r\n</li>\r\n<li>\r\n<p>A centralized dashboard displaying key financial KPIs.</p>\r\n</li>\r\n<li>\r\n<p>Read-only API integration with SAP S/4HANA Cloud and Oracle NetSuite.</p>\r\n</li>\r\n<li>\r\n<p>Automated and manual data synchronization capabilities.</p>\r\n</li>\r\n<li>\r\n<p>Generation of standard financial reports (e.g., Profit &amp; Loss, Balance Sheet).</p>\r\n</li>\r\n<li>\r\n<p>Export functionality for all reports to PDF and CSV formats.</p>\r\n</li>\r\n</ul>\r\n<p>&nbsp;</p>\r\n<h4><strong>Out-of-Scope</strong></h4>\r\n<p>&nbsp;</p>\r\n<ul>\r\n<li>\r\n<p>Transaction processing (e.g., sending payments, creating invoices).</p>\r\n</li>\r\n<li>\r\n<p>Budgeting and financial forecasting features.</p>\r\n</li>\r\n<li>\r\n<p>A native mobile application (the initial release is web-only).</p>\r\n</li>\r\n</ul>\r\n<hr>\r\n<p>&nbsp;</p>\r\n<h3><strong>4. Business Requirements</strong></h3>\r\n<p>&nbsp;</p>\r\n<p>The core business requirements are captured in the following user stories:</p>\r\n<p>&nbsp;</p>\r\n<h4><strong>Admin &amp; System Requirements</strong></h4>\r\n<p>&nbsp;</p>\r\n<ul>\r\n<li>\r\n<p><strong>System Setup:</strong> The system must allow an Admin to securely connect the company's SAP and Oracle accounts to enable automated data imports.</p>\r\n</li>\r\n<li>\r\n<p><strong>User Management:</strong> The system must allow an Admin to invite, manage, and assign roles to users to ensure proper data governance.</p>\r\n</li>\r\n<li>\r\n<p><strong>Performance:</strong> The system must deliver a fast, responsive user experience, with API response times under 500ms and dashboard load times under 3 seconds.</p>\r\n</li>\r\n<li>\r\n<p><strong>Security:</strong> The system must implement industry-standard security best practices to protect all sensitive financial data.</p>\r\n</li>\r\n</ul>\r\n<p>&nbsp;</p>\r\n<h4><strong>Manager &amp; Reporting Requirements</strong></h4>\r\n<p>&nbsp;</p>\r\n<ul>\r\n<li>\r\n<p><strong>Dashboarding:</strong> The system must provide Managers with a real-time dashboard to assess the company's financial performance at a glance.</p>\r\n</li>\r\n<li>\r\n<p><strong>Reporting:</strong> The system must allow Managers to generate standard financial reports for specific date ranges.</p>\r\n</li>\r\n<li>\r\n<p><strong>Data Export:</strong> The system must allow Managers to export all reports to PDF and CSV formats for offline analysis and sharing.</p>\r\n</li>\r\n</ul>\r\n<hr>\r\n<p>&nbsp;</p>\r\n<h3><strong>5. Key Stakeholders</strong></h3>\r\n<p>&nbsp;</p>\r\n<div class="horizontal-scroll-wrapper">\r\n<div class="table-block-component"><!----><!----><!----><!----><!----><!----><!----><!----><!----><!----><!----><!----><!----><!----><!----><!----><!----><!----><!----><!----><!----><!----><!----><!----><!----><!----><!----><!---->\r\n<div class="table-block has-export-button">\r\n<div class="table-content not-end-of-paragraph" data-hveid="4">\r\n<table>\r\n<thead>\r\n<tr>\r\n<td>Stakeholder Role</td>\r\n<td>Name/Title</td>\r\n<td>Responsibilities</td>\r\n</tr>\r\n</thead>\r\n<tbody>\r\n<tr>\r\n<td><strong>Project Sponsor</strong></td>\r\n<td>Head of Finance</td>\r\n<td>Provides funding, champions the project, and signs off on deliverables.</td>\r\n</tr>\r\n<tr>\r\n<td><strong>End Users</strong></td>\r\n<td>Financial Analysts, Accountants, Managers</td>\r\n<td>Will use the platform for daily reporting and analysis tasks.</td>\r\n</tr>\r\n<tr>\r\n<td><strong>Technical Team</strong></td>\r\n<td>NodeJS Developers, DevOps Engineers</td>\r\n<td>Responsible for the design, development, deployment, and maintenance of the application.</td>\r\n</tr>\r\n</tbody>\r\n</table>\r\n</div>\r\n<div class="table-footer hide-from-message-actions ng-star-inserted"><button class="mdc-button mat-mdc-button-base export-sheets-button-container mat-mdc-button mat-unthemed ng-star-inserted"><span class="mdc-button__label"><span class="export-sheets-button">Export to Sheets</span></span></button><!----><!----></div>\r\n<!----></div>\r\n<!----><!----><!----><!----><!----><!----><!----><!----><!----><!----><!----><!----><!----><!----><!----><!----></div>\r\n</div>\r\n<hr>\r\n<p>&nbsp;</p>\r\n<h3><strong>6. Project Constraints</strong></h3>\r\n<p>&nbsp;</p>\r\n<ul>\r\n<li>\r\n<p><strong>Technology Stack:</strong> The project is constrained to the specified technical architecture: <strong>NodeJS, Microservices, and MongoDB</strong>.</p>\r\n</li>\r\n<li>\r\n<p><strong>Third-Party APIs:</strong> The project's functionality is dependent on the availability, reliability, and access to the APIs of SAP and Oracle.</p>\r\n</li>\r\n<li>\r\n<p><strong>Timeline:</strong> The initial version (MVP) of the project is targeted for delivery within a 6-month timeframe. <em>(placeholder)</em></p>\r\n</li>\r\n<li>\r\n<p><strong>Budget:</strong> The project must be completed within the allocated budget of $XXX,XXX. <em>(placeholder)</em></p>\r\n</li>\r\n</ul>\r\n<hr>\r\n<p>&nbsp;</p>\r\n<h3><strong>7. Cost-Benefit Analysis</strong></h3>\r\n<p>&nbsp;</p>\r\n<p>&nbsp;</p>\r\n<h4><strong>Costs</strong></h4>\r\n<p>&nbsp;</p>\r\n<ul>\r\n<li>\r\n<p><strong>Development Costs:</strong> Salaries for a development team (e.g., 2 NodeJS Developers, 1 DevOps Engineer, 1 QA Tester) for the project duration.</p>\r\n</li>\r\n<li>\r\n<p><strong>Infrastructure Costs:</strong> Monthly fees for cloud services (e.g., hosting, database, CI/CD tools).</p>\r\n</li>\r\n<li>\r\n<p><strong>Maintenance Costs:</strong> Ongoing operational costs, including bug fixes and software updates post-launch (estimated at 15-20% of development cost annually).</p>\r\n</li>\r\n</ul>\r\n<p>&nbsp;</p>\r\n<h4><strong>Benefits</strong></h4>\r\n<p>&nbsp;</p>\r\n<ul>\r\n<li>\r\n<p><strong>Quantitative Benefits:</strong></p>\r\n<ul>\r\n<li>\r\n<p><strong>Reduced Labor Costs:</strong> Significant reduction in hours spent by financial analysts on manual data collection. <em>Example: 2 analysts spending 20 hours/week on manual tasks at $50/hour = $104,000 in annual savings.</em></p>\r\n</li>\r\n<li>\r\n<p><strong>Elimination of Errors:</strong> Reduces the financial risk associated with making decisions based on inaccurate, error-prone data.</p>\r\n</li>\r\n</ul>\r\n</li>\r\n<li>\r\n<p><strong>Qualitative Benefits:</strong></p>\r\n<ul>\r\n<li>\r\n<p><strong>Improved Decision-Making:</strong> Real-time data access enables faster and more strategic business decisions.</p>\r\n</li>\r\n<li>\r\n<p><strong>Increased Employee Satisfaction:</strong> Automating tedious, repetitive tasks allows financial professionals to focus on higher-value analysis.</p>\r\n</li>\r\n<li>\r\n<p><strong>Enhanced Scalability:</strong> Provides a scalable foundation to add more data sources in the future.</p>\r\n</li>\r\n</ul>\r\n</li>\r\n</ul>\r\n<p>&nbsp;</p>\r\n<p>&nbsp;</p>	Executive Summary	Project Objectives	Project Scope	Business Requirements	Key Stakeholders	Project Constraints	Cost-Benefit Analysis
2	5	<p data-path-to-node="7">The purpose of this project is to migrate the existing on-premise/legacy Supply Chain application to a modern, cloud-native architecture. The current legacy system limits scalability, real-time visibility, and integration capabilities. The new solution will leverage <strong data-path-to-node="7" data-index-in-node="267">React.js</strong> for a responsive user interface and <strong data-path-to-node="7" data-index-in-node="312">.NET (latest version)</strong> for high-performance backend microservices, hosted on <strong data-path-to-node="7" data-index-in-node="388">Microsoft Azure</strong> to ensure agility, security, and global scalability.</p>	<table data-path-to-node="10">\r\n<thead>\r\n<tr>\r\n<td><strong>ID</strong></td>\r\n<td><strong>Objective</strong></td>\r\n<td><strong>Description</strong></td>\r\n</tr>\r\n</thead>\r\n<tbody>\r\n<tr>\r\n<td><span data-path-to-node="10,1,0,0"><strong data-path-to-node="10,1,0,0" data-index-in-node="0">BO-01</strong></span></td>\r\n<td><span data-path-to-node="10,1,1,0"><strong data-path-to-node="10,1,1,0" data-index-in-node="0">Scalability</strong></span></td>\r\n<td><span data-path-to-node="10,1,2,0">Enable the system to handle 10x transaction volume during peak seasons without performance degradation.</span></td>\r\n</tr>\r\n<tr>\r\n<td><span data-path-to-node="10,2,0,0"><strong data-path-to-node="10,2,0,0" data-index-in-node="0">BO-02</strong></span></td>\r\n<td><span data-path-to-node="10,2,1,0"><strong data-path-to-node="10,2,1,0" data-index-in-node="0">Real-Time Visibility</strong></span></td>\r\n<td><span data-path-to-node="10,2,2,0">Provide real-time tracking of inventory and shipments across the supply chain network.</span></td>\r\n</tr>\r\n<tr>\r\n<td><span data-path-to-node="10,3,0,0"><strong data-path-to-node="10,3,0,0" data-index-in-node="0">BO-03</strong></span></td>\r\n<td><span data-path-to-node="10,3,1,0"><strong data-path-to-node="10,3,1,0" data-index-in-node="0">Cost Reduction</strong></span></td>\r\n<td><span data-path-to-node="10,3,2,0">Reduce maintenance costs of physical servers by moving to a "Pay-as-you-go" cloud model.</span></td>\r\n</tr>\r\n<tr>\r\n<td><span data-path-to-node="10,4,0,0"><strong data-path-to-node="10,4,0,0" data-index-in-node="0">BO-04</strong></span></td>\r\n<td><span data-path-to-node="10,4,1,0"><strong data-path-to-node="10,4,1,0" data-index-in-node="0">Modern UX</strong></span></td>\r\n<td><span data-path-to-node="10,4,2,0">Replace the clunky legacy interface with a responsive, mobile-friendly React dashboard for field agents and warehouse managers.</span></td>\r\n</tr>\r\n</tbody>\r\n</table>	<h3 data-path-to-node="13">3.1 Legacy System (Current)</h3>\r\n<ul data-path-to-node="14">\r\n<li>\r\n<p data-path-to-node="14,0,0"><strong data-path-to-node="14,0,0" data-index-in-node="0">Architecture:</strong> Monolithic (Single code base, tight coupling).</p>\r\n</li>\r\n<li>\r\n<p data-path-to-node="14,1,0"><strong data-path-to-node="14,1,0" data-index-in-node="0">Technology:</strong> Legacy .NET Framework / WinForms / Older Web Tech.</p>\r\n</li>\r\n<li>\r\n<p data-path-to-node="14,2,0"><strong data-path-to-node="14,2,0" data-index-in-node="0">Deployment:</strong> On-premise physical servers.</p>\r\n</li>\r\n<li>\r\n<p data-path-to-node="14,3,0"><strong data-path-to-node="14,3,0" data-index-in-node="0">Pain Points:</strong> Downtime during updates, slow reporting, lack of mobile access, expensive hardware maintenance.</p>\r\n</li>\r\n</ul>\r\n<h3 data-path-to-node="15">3.2 Proposed System (Future)</h3>\r\n<ul data-path-to-node="16">\r\n<li>\r\n<p data-path-to-node="16,0,0"><strong data-path-to-node="16,0,0" data-index-in-node="0">Architecture:</strong> Microservices (Decoupled modules).</p>\r\n</li>\r\n<li>\r\n<p data-path-to-node="16,1,0"><strong data-path-to-node="16,1,0" data-index-in-node="0">Frontend:</strong> React.js (Single Page Application - SPA).</p>\r\n</li>\r\n<li>\r\n<p data-path-to-node="16,2,0"><strong data-path-to-node="16,2,0" data-index-in-node="0">Backend:</strong> .NET 8 (Core) Web APIs.</p>\r\n</li>\r\n<li>\r\n<p data-path-to-node="16,3,0"><strong data-path-to-node="16,3,0" data-index-in-node="0">Infrastructure:</strong> Azure Cloud (PaaS/Serverless).</p>\r\n</li>\r\n<li>\r\n<p data-path-to-node="16,4,0"><strong data-path-to-node="16,4,0" data-index-in-node="0">Data:</strong> Hybrid (SQL for transactional, NoSQL for tracking data).</p>\r\n</li>\r\n</ul>	<h3 data-path-to-node="20">4.1 Module: Inventory Management</h3>\r\n<ul data-path-to-node="21">\r\n<li>\r\n<p data-path-to-node="21,0,0"><strong data-path-to-node="21,0,0" data-index-in-node="0">FR-01:</strong> System must allow real-time stock updates via barcode scanning (Mobile/Tablet supported).</p>\r\n</li>\r\n<li>\r\n<p data-path-to-node="21,1,0"><strong data-path-to-node="21,1,0" data-index-in-node="0">FR-02:</strong> Implement "Low Stock Alerts" using automated email/SMS triggers.</p>\r\n</li>\r\n<li>\r\n<p data-path-to-node="21,2,0"><strong data-path-to-node="21,2,0" data-index-in-node="0">FR-03:</strong> Support multi-warehouse tracking and stock transfer requests.</p>\r\n</li>\r\n</ul>\r\n<h3 data-path-to-node="22">4.2 Module: Order Processing</h3>\r\n<ul data-path-to-node="23">\r\n<li>\r\n<p data-path-to-node="23,0,0"><strong data-path-to-node="23,0,0" data-index-in-node="0">FR-04:</strong> Convert Purchase Orders (PO) to Invoices with a single click.</p>\r\n</li>\r\n<li>\r\n<p data-path-to-node="23,1,0"><strong data-path-to-node="23,1,0" data-index-in-node="0">FR-05:</strong> Support B2B EDI integrations for automated order ingestion.</p>\r\n</li>\r\n<li>\r\n<p data-path-to-node="23,2,0"><strong data-path-to-node="23,2,0" data-index-in-node="0">FR-06:</strong> Provide a customer portal (React-based) for order tracking.</p>\r\n</li>\r\n</ul>\r\n<h3 data-path-to-node="24">4.3 Module: Logistics &amp; Transportation</h3>\r\n<ul data-path-to-node="25">\r\n<li>\r\n<p data-path-to-node="25,0,0"><strong data-path-to-node="25,0,0" data-index-in-node="0">FR-07:</strong> Integrate with 3rd party logistics APIs (e.g., FedEx, DHL, Local Carriers) for live rate calculation.</p>\r\n</li>\r\n<li>\r\n<p data-path-to-node="25,1,0"><strong data-path-to-node="25,1,0" data-index-in-node="0">FR-08:</strong> GPS-based route optimization for internal delivery fleets.</p>\r\n</li>\r\n</ul>\r\n<h3 data-path-to-node="26">4.4 Module: Analytics &amp; Forecasting</h3>\r\n<ul data-path-to-node="27">\r\n<li>\r\n<p data-path-to-node="27,0,0"><strong data-path-to-node="27,0,0" data-index-in-node="0">FR-09:</strong> Dashboard showing "Days Inventory Outstanding" (DIO) and "Perfect Order Rate".</p>\r\n</li>\r\n<li>\r\n<p data-path-to-node="27,1,0"><strong data-path-to-node="27,1,0" data-index-in-node="0">FR-10:</strong> AI-based demand forecasting to predict stock needs for the upcoming quarter.</p>\r\n</li>\r\n</ul>	<h3 data-path-to-node="31">5.1 Application Stack</h3>\r\n<ul data-path-to-node="32">\r\n<li>\r\n<p data-path-to-node="32,0,0"><strong data-path-to-node="32,0,0" data-index-in-node="0">Frontend:</strong> <strong data-path-to-node="32,0,0" data-index-in-node="10">React.js</strong> (TypeScript recommended for type safety).</p>\r\n<ul data-path-to-node="32,0,1">\r\n<li>\r\n<p data-path-to-node="32,0,1,0,0"><em data-path-to-node="32,0,1,0,0" data-index-in-node="0">State Management:</em> Redux Toolkit or React Query for caching API responses.</p>\r\n</li>\r\n<li>\r\n<p data-path-to-node="32,0,1,1,0"><em data-path-to-node="32,0,1,1,0" data-index-in-node="0">UI Library:</em> Material UI (MUI) or Ant Design for rapid enterprise UI development.</p>\r\n</li>\r\n</ul>\r\n</li>\r\n<li>\r\n<p data-path-to-node="32,1,0"><strong data-path-to-node="32,1,0" data-index-in-node="0">Backend:</strong> <strong data-path-to-node="32,1,0" data-index-in-node="9">.NET 8</strong> (C#).</p>\r\n<ul data-path-to-node="32,1,1">\r\n<li>\r\n<p data-path-to-node="32,1,1,0,0"><em data-path-to-node="32,1,1,0,0" data-index-in-node="0">Framework:</em> ASP.NET Core Web API.</p>\r\n</li>\r\n<li>\r\n<p data-path-to-node="32,1,1,1,0"><em data-path-to-node="32,1,1,1,0" data-index-in-node="0">Communication:</em> gRPC for internal microservice talk, REST for frontend communication.</p>\r\n</li>\r\n</ul>\r\n</li>\r\n<li>\r\n<p data-path-to-node="32,2,0"><strong data-path-to-node="32,2,0" data-index-in-node="0">Mobile:</strong> React Native (optional, if native mobile app is needed later, sharing logic with React web).</p>\r\n</li>\r\n</ul>\r\n<h3 data-path-to-node="33">5.2 Cloud Infrastructure (Microsoft Azure)</h3>\r\n<p data-path-to-node="34">Since the client prefers .NET, Azure is the most compatible cloud provider.</p>\r\n<p data-path-to-node="34">&nbsp;</p>\r\n<table style="width: 100%; height: 313.578px;" data-path-to-node="35">\r\n<thead>\r\n<tr style="height: 22.3984px;">\r\n<td style="width: 16.1693%; height: 22.3984px;"><strong>Component</strong></td>\r\n<td style="width: 34.755%; height: 22.3984px;"><strong>Azure Service</strong></td>\r\n<td style="width: 43.8293%; height: 22.3984px;"><strong>Purpose</strong></td>\r\n</tr>\r\n</thead>\r\n<tbody>\r\n<tr style="height: 44.7969px;">\r\n<td style="width: 16.1693%; height: 44.7969px;"><span data-path-to-node="35,1,0,0"><strong data-path-to-node="35,1,0,0" data-index-in-node="0">Compute</strong></span></td>\r\n<td style="width: 34.755%; height: 44.7969px;"><span data-path-to-node="35,1,1,0"><strong data-path-to-node="35,1,1,0" data-index-in-node="0">Azure Kubernetes Service (AKS)</strong> or <strong data-path-to-node="35,1,1,0" data-index-in-node="34">Azure Container Apps</strong></span></td>\r\n<td style="width: 43.8293%; height: 44.7969px;"><span data-path-to-node="35,1,2,0">Hosting .NET Microservices in Docker containers.</span></td>\r\n</tr>\r\n<tr style="height: 44.7969px;">\r\n<td style="width: 16.1693%; height: 44.7969px;"><span data-path-to-node="35,2,0,0"><strong data-path-to-node="35,2,0,0" data-index-in-node="0">Frontend Hosting</strong></span></td>\r\n<td style="width: 34.755%; height: 44.7969px;"><span data-path-to-node="35,2,1,0"><strong data-path-to-node="35,2,1,0" data-index-in-node="0">Azure Static Web Apps</strong></span></td>\r\n<td style="width: 43.8293%; height: 44.7969px;"><span data-path-to-node="35,2,2,0">Globally distributed hosting for React assets with built-in CDN.</span></td>\r\n</tr>\r\n<tr style="height: 44.7969px;">\r\n<td style="width: 16.1693%; height: 44.7969px;"><span data-path-to-node="35,3,0,0"><strong data-path-to-node="35,3,0,0" data-index-in-node="0">Database (Relational)</strong></span></td>\r\n<td style="width: 34.755%; height: 44.7969px;"><span data-path-to-node="35,3,1,0"><strong data-path-to-node="35,3,1,0" data-index-in-node="0">Azure SQL Database</strong></span></td>\r\n<td style="width: 43.8293%; height: 44.7969px;"><span data-path-to-node="35,3,2,0">Storing structured data like Orders, Users, Finance.</span></td>\r\n</tr>\r\n<tr style="height: 44.7969px;">\r\n<td style="width: 16.1693%; height: 44.7969px;"><span data-path-to-node="35,4,0,0"><strong data-path-to-node="35,4,0,0" data-index-in-node="0">Database (NoSQL)</strong></span></td>\r\n<td style="width: 34.755%; height: 44.7969px;"><span data-path-to-node="35,4,1,0"><strong data-path-to-node="35,4,1,0" data-index-in-node="0">Azure Cosmos DB</strong></span></td>\r\n<td style="width: 43.8293%; height: 44.7969px;"><span data-path-to-node="35,4,2,0">Storing high-volume tracking logs and audit trails.</span></td>\r\n</tr>\r\n<tr style="height: 44.7969px;">\r\n<td style="width: 16.1693%; height: 44.7969px;"><span data-path-to-node="35,5,0,0"><strong data-path-to-node="35,5,0,0" data-index-in-node="0">Messaging</strong></span></td>\r\n<td style="width: 34.755%; height: 44.7969px;"><span data-path-to-node="35,5,1,0"><strong data-path-to-node="35,5,1,0" data-index-in-node="0">Azure Service Bus</strong></span></td>\r\n<td style="width: 43.8293%; height: 44.7969px;"><span data-path-to-node="35,5,2,0">Decoupling services (e.g., Order Service tells Inventory Service to deduct stock).</span></td>\r\n</tr>\r\n<tr style="height: 44.7969px;">\r\n<td style="width: 16.1693%; height: 44.7969px;"><span data-path-to-node="35,6,0,0"><strong data-path-to-node="35,6,0,0" data-index-in-node="0">API Gateway</strong></span></td>\r\n<td style="width: 34.755%; height: 44.7969px;"><span data-path-to-node="35,6,1,0"><strong data-path-to-node="35,6,1,0" data-index-in-node="0">Azure API Management (APIM)</strong></span></td>\r\n<td style="width: 43.8293%; height: 44.7969px;"><span data-path-to-node="35,6,2,0">Single entry point, security, and throttling for all APIs.</span></td>\r\n</tr>\r\n<tr style="height: 22.3984px;">\r\n<td style="width: 16.1693%; height: 22.3984px;"><span data-path-to-node="35,7,0,0"><strong data-path-to-node="35,7,0,0" data-index-in-node="0">Identity</strong></span></td>\r\n<td style="width: 34.755%; height: 22.3984px;"><span data-path-to-node="35,7,1,0"><strong data-path-to-node="35,7,1,0" data-index-in-node="0">Azure Active Directory (Entra ID)</strong></span></td>\r\n<td style="width: 43.8293%; height: 22.3984px;"><span data-path-to-node="35,7,2,0">Single Sign-On (SSO) for employees.</span></td>\r\n</tr>\r\n</tbody>\r\n</table>	<ul>\r\n<li>\r\n<p data-path-to-node="38,0,0"><strong data-path-to-node="38,0,0" data-index-in-node="0">Performance:</strong> APIs must respond within 200ms for 95% of requests.</p>\r\n</li>\r\n<li>\r\n<p data-path-to-node="38,1,0"><strong data-path-to-node="38,1,0" data-index-in-node="0">Availability:</strong> 99.9% Uptime SLA (Service Level Agreement).</p>\r\n</li>\r\n<li>\r\n<p data-path-to-node="38,2,0"><strong data-path-to-node="38,2,0" data-index-in-node="0">Security:</strong></p>\r\n<ul data-path-to-node="38,2,1">\r\n<li>\r\n<p data-path-to-node="38,2,1,0,0">All data encrypted at rest (TDE) and in transit (TLS 1.3).</p>\r\n</li>\r\n<li>\r\n<p data-path-to-node="38,2,1,1,0">Role-Based Access Control (RBAC) (e.g., Warehouse Staff cannot see Financial Reports).</p>\r\n</li>\r\n</ul>\r\n</li>\r\n<li>\r\n<p data-path-to-node="38,3,0"><strong data-path-to-node="38,3,0" data-index-in-node="0">Compliance:</strong> GDPR/SOC2 compliance for data handling.</p>\r\n</li>\r\n</ul>	<p data-path-to-node="41">We will not rewrite everything at once. We will migrate module by module.</p>\r\n<ol start="1" data-path-to-node="42">\r\n<li>\r\n<p data-path-to-node="42,0,0"><strong data-path-to-node="42,0,0" data-index-in-node="0">Phase 1 - Identification:</strong> Audit legacy code to map dependencies.</p>\r\n</li>\r\n<li>\r\n<p data-path-to-node="42,1,0"><strong data-path-to-node="42,1,0" data-index-in-node="0">Phase 2 - The "Facade":</strong> Build the <strong data-path-to-node="42,1,0" data-index-in-node="34">Azure API Gateway</strong>. Initially, it routes all traffic to the Legacy System.</p>\r\n</li>\r\n<li>\r\n<p data-path-to-node="42,2,0"><strong data-path-to-node="42,2,0" data-index-in-node="0">Phase 3 - Strangling:</strong> Build the <strong data-path-to-node="42,2,0" data-index-in-node="32">Inventory Module</strong> in .NET/React. Point the Gateway to route "Inventory" traffic to the new app, while "Orders" still go to the legacy app.</p>\r\n</li>\r\n<li>\r\n<p data-path-to-node="42,3,0"><strong data-path-to-node="42,3,0" data-index-in-node="0">Phase 4 - Repeat:</strong> Repeat for Order Management, Logistics, etc., until the legacy system receives no traffic.</p>\r\n</li>\r\n<li>\r\n<p data-path-to-node="42,4,0"><strong data-path-to-node="42,4,0" data-index-in-node="0">Phase 5 - Decommission:</strong> Turn off the legacy system.</p>\r\n</li>\r\n</ol>\r\n<p>&nbsp;</p>\r\n<p>&nbsp;</p>\r\n<p>&nbsp; &nbsp; &nbsp;<strong> &nbsp; Assumptions &amp; Constraints</strong></p>\r\n<p>&nbsp;</p>\r\n<ul>\r\n<li>\r\n<p data-path-to-node="45,0,0"><strong data-path-to-node="45,0,0" data-index-in-node="0">Constraint:</strong> The client team has existing knowledge of C#, reducing the learning curve for the backend.</p>\r\n</li>\r\n<li>\r\n<p data-path-to-node="45,1,0"><strong data-path-to-node="45,1,0" data-index-in-node="0">Constraint:</strong> Migration must occur during off-peak business hours to minimize operations impact.</p>\r\n</li>\r\n<li>\r\n<p data-path-to-node="45,2,0"><strong data-path-to-node="45,2,0" data-index-in-node="0">Assumption:</strong> The legacy database schema can be mapped to the new schema without significant data loss.</p>\r\n</li>\r\n</ul>	Executive Summary	Business Objectives	3. Current State vs. Future State	4. Functional Requirements	5. Technical Stack & Cloud Architecture	6. Non-Functional Requirements (NFR)	7. Migration Strategy: "The Strangler Fig Pattern"
\.


--
-- Data for Name: candidate_contacts; Type: TABLE DATA; Schema: public; Owner: sourcepoint_admin
--

COPY public.candidate_contacts (candidate_id, developer_id) FROM stdin;
\.


--
-- Data for Name: cart; Type: TABLE DATA; Schema: public; Owner: sourcepoint_admin
--

COPY public.cart (id, user_id, created_at) FROM stdin;
15	15	2026-01-05 13:32:21.982017
\.


--
-- Data for Name: cart_item; Type: TABLE DATA; Schema: public; Owner: sourcepoint_admin
--

COPY public.cart_item (id, cart_id, product_id, quantity) FROM stdin;
26	15	51	1
\.


--
-- Data for Name: chat_history; Type: TABLE DATA; Schema: public; Owner: sourcepoint_admin
--

COPY public.chat_history (id, user_id, subject, role, message, "timestamp") FROM stdin;
1	3	cpp	user	hi 	2026-01-04 12:16:25.616524
2	3	cpp	ai	Hello! I'm your <b>expert C++ tutor</b>.\n\nHow can I assist you today? Feel free to ask me anything about C++, whether it's about syntax, concepts, libraries, or even debugging. I'm here to help you learn!	2026-01-04 12:16:30.102988
3	3	java	user	hi 	2026-01-04 12:18:26.612301
4	3	java	ai	Hello! <br><br>I'm your expert technical tutor for Java. I'm ready to help you with any questions, concepts, or coding challenges you might have in Java. <br><br>What would you like to learn or discuss today? Feel free to ask away!	2026-01-04 12:18:29.162256
5	3	java	user	hi 	2026-01-04 12:18:44.445246
6	3	java	ai	<p><b>Hello there!</b></p>\n<p>I'm your expert technical tutor for Java. I'm ready to help you understand complex concepts, debug your code, learn new features, or anything else you need assistance with in the world of Java programming.</p>\n<p>What can I help you with today? Feel free to ask me anything!</p>	2026-01-04 12:18:46.881281
7	3	sql	user	Hi	2026-01-05 12:02:54.849308
8	3	sql	ai	Hello! <br>\n<br>\nI'm your expert SQL tutor, ready to help you with anything SQL-related. <br>\n<br>\nHow can I assist you today? Are you looking to learn a new concept, troubleshoot a query, or understand a specific SQL command?	2026-01-05 12:02:56.985869
9	3	c	user	Hello	2026-01-06 12:29:31.599831
10	3	c	ai	Hello! I'm here to help you with C programming.\n\n<br><br>\nWhat can I assist you with today? Do you have a specific question, a concept you'd like to understand better, or a problem you're trying to solve in C?\n<br><br>\nFeel free to share what's on your mind!	2026-01-06 12:29:34.817054
11	3	cpp	user	hi 	2026-01-11 15:16:12.883593
12	3	cpp	ai	<p><b>Hello!</b></p>\n<p>I'm ready to help you learn C++ or answer any questions you have about it. Whether you're just starting, working on a specific problem, or want to dive into advanced topics, feel free to ask!</p>\n<p>What would you like to explore today?</p>	2026-01-11 15:16:15.155865
13	3	java	user	Hi	2026-01-21 19:28:50.884907
14	3	java	ai	<p><b>Hi there!</b></p>\n<p>I'm ready to help you with your Java journey.</p>\n<p>What can I assist you with today? Are you working on a specific problem, learning a new concept, or just have a general question about Java?</p>\n<p>Let me know how I can be helpful!</p>	2026-01-21 19:28:52.992018
15	3	cpp	user	hi 	2026-01-22 10:30:29.983224
16	3	cpp	ai	Hello! I'm ready to help you with C++.<br><br>What C++ topic or problem can I assist you with today? Feel free to ask anything, from basic concepts to advanced techniques.	2026-01-22 10:30:33.537211
17	3	mysql	user	tell me about curent affaiers 	2026-01-22 10:36:43.528048
18	3	mysql	ai	<p>Ah, "current affairs" in the world of MySQL! Let's get you up to speed.</p><br>\n\n<p>The most significant recent development is the introduction of a new <b>Long Term Support (LTS)</b> release model for MySQL. The first of these, <b>MySQL 8.4 LTS</b>, was recently released. This offers a more predictable and stable upgrade path for users, with bug fixes and security updates for several years.</p><br>\n\n<p>While 8.4 LTS is new, <b>MySQL 8.0</b> remains the widely adopted stable series, celebrated for features like Window Functions, Common Table Expressions (CTEs), and robust JSON capabilities. Development continues to focus on performance, security, and scalability, especially in cloud environments like AWS RDS, Azure Database for MySQL, and Google Cloud SQL.</p><br>\n\n<p>Staying updated with the official MySQL blog and release notes is the best way to follow these developments!</p>	2026-01-22 10:36:51.197631
19	3	mysql	user	inbound requ8est '	2026-01-22 10:37:38.457117
20	3	mysql	ai	<p>It looks like there might be a typo in your query, perhaps you meant "inbound <b>request</b>"?</p>\n\n<p>In the context of MySQL, an "inbound request" typically refers to a client application attempting to connect to the MySQL server and send a query or command.</p>\n\n<p>Here's a quick breakdown:</p>\n<ul>\n    <li><b>Client:</b> Your application (e.g., PHP, Python, Java) tries to establish a connection.</li>\n    <li><b>Network:</b> This request travels over the network (or locally via a socket) to the MySQL server.</li>\n    <li><b>MySQL Server:</b> The server listens on a specific port (default <code>3306</code>) for these incoming connection attempts and subsequent queries.</li>\n    <li><b>Authentication:</b> The server validates the user's credentials (username, password, host).</li>\n    <li><b>Query Processing:</b> Once connected, the server receives and processes the actual SQL statements (<code>SELECT</code>, <code>INSERT</code>, <code>UPDATE</code>, etc.).</li>\n</ul>\n\n<p>Essentially, any interaction initiated by a client towards the MySQL server is an "inbound request."</p>	2026-01-22 10:37:42.28344
21	3	mysql	user	Create, Read, Update, Delete These four basic functions of persistent storage are the bread and butter of database management.   -- CREATE (Insert a new record) INSERT INTO users (name, email) VALUES ('John Doe', 'john.doe@example.com');  -- READ (Select records) SELECT * FROM users WHERE name = 'John Doe';  -- UPDATE (Modify a record) UPDATE users SET email = 'johndoe@newemail.com' WHERE name = 'John Doe';  -- DELETE (Remove a record) DELETE FROM users WHERE name = 'John Doe';	2026-01-22 10:38:42.971243
22	3	mysql	ai	<p>Excellent! You've nailed the fundamental CRUD (Create, Read, Update, Delete) operations, and your SQL examples are perfectly correct.</p>\n\n<p>You're absolutely right that these four functions are the "bread and butter" of database management. They represent the core actions for managing persistent data in any relational database like MySQL:</p>\n<ul>\n    <li><b>CREATE</b> (<code>INSERT</code>): Adding new data.</li>\n    <li><b>READ</b> (<code>SELECT</code>): Retrieving existing data.</li>\n    <li><b>UPDATE</b> (<code>UPDATE</code>): Modifying existing data.</li>\n    <li><b>DELETE</b> (<code>DELETE</code>): Removing existing data.</li>\n</ul>\n\n<p>Mastering these commands is crucial for building and interacting with any database application. A quick tip for <code>UPDATE</code> and <code>DELETE</code>: While your examples use <code>name</code>, in real-world scenarios, it's often best practice to use a unique identifier like a <b>primary key</b> (e.g., <code>WHERE id = 123</code>) in your <code>WHERE</code> clause to guarantee you're targeting the exact record you intend to modify or remove.</p>\n\n<p>Great job demonstrating your understanding of these core MySQL functions!</p>	2026-01-22 10:38:48.579673
\.


--
-- Data for Name: code_snippet; Type: TABLE DATA; Schema: public; Owner: sourcepoint_admin
--

COPY public.code_snippet (id, sender_id, recipient_id, code, language, "timestamp") FROM stdin;
1	3	1	dsds	java	2025-09-10 16:10:54.860526
\.


--
-- Data for Name: code_test_submission; Type: TABLE DATA; Schema: public; Owner: sourcepoint_admin
--

COPY public.code_test_submission (id, candidate_id, recipient_id, code, output, language, submitted_at) FROM stdin;
1	7	1	public class Main {\r\npublic static void main (String [] args){\r\n    System.out.println("hello");\r\n}\r\n}		java	2025-09-12 07:02:47.932888
2	3	1	import java.util.Scanner;\r\n\r\npublic class Main {\r\n    public static void main(String[] args) {\r\n        // Create a Scanner object to read input from the console\r\n        Scanner scanner = new Scanner(System.in);\r\n\r\n        System.out.println("Enter a string to be reversed:");\r\n\r\n        // Read the entire line of input from the user\r\n        String originalString = scanner.nextLine();\r\n\r\n        // Use StringBuilder to easily reverse the string\r\n        String reversedString = new StringBuilder(originalString).reverse().toString();\r\n\r\n        System.out.println("\\nOriginal String: " + originalString);\r\n        System.out.println("Reversed String: " + reversedString);\r\n        \r\n        // Close the scanner to prevent resource leaks\r\n        scanner.close();\r\n    }\r\n}\r\n	Enter a string to be reversed:\r\n\r\nOriginal String: Compiler test\r\nReversed String: tset relipmoC	java	2025-09-13 08:33:50.370579
3	3	1	public class Main {\r\n    public static void main(String[] args) {\r\n        // Your code here.\r\n        System.out.println("Hello, Java!");\r\n    }\r\n}	Hello, Java!	java	2025-09-13 11:26:31.552218
4	12	2	import java.util.Arrays;\r\nimport java.util.Stack;\r\n\r\n\r\n/**\r\n * The candidate should implement their solution in this class.\r\n * The optimal solution uses a Monotonic Stack and has a time complexity of O(n).\r\n */\r\nclass Solution {\r\n    public int[] findNextStrongerSignals(int[] signalStrengths) {\r\n        // TODO: Implement your optimal O(n) solution here.\r\n        // The current implementation is a placeholder and is incorrect.\r\n        int n = signalStrengths.length;\r\n        if (n == 0) {\r\n            return new int[0];\r\n        }\r\n\r\n        int[] result = new int[n];\r\n        Arrays.fill(result, -1); // Initialize all results to -1 by default\r\n\r\n        // HINT: A stack can be very useful for this problem.\r\n        // Consider iterating twice the length of the array to handle the circular nature.\r\n        \r\n        /*\r\n         * BRUTE FORCE APPROACH - O(n^2)\r\n         * for (int i = 0; i < n; i++) {\r\n         *  for (int j = 1; j < n; j++) {\r\n              \r\n                if (signalStrengths[i] < signalStrengths[(i + j) % n]) {  // (i + j) to circularly iterate array\r\n                    result[i] = signalStrengths[(i + j) % n];\r\n                    break;\r\n                }\r\n            }\r\n        }\r\n        */\r\n        \r\n        Stack<Integer> towerSequence = new Stack<>();\r\n        \r\n        for(int i = 0; i < 2*n; i--) {\r\n        \ttowerSequence.push(i % n);\r\n        \t\r\n        \t\r\n        }\r\n        \r\n        \r\n        return result;\r\n    }\r\n}\r\n\r\n/**\r\n * =====================================================================================\r\n * Testing Class - DO NOT MODIFY\r\n * =====================================================================================\r\n * This Main class is designed to test your solution.\r\n * You can run this code to see if your implementation passes the sample test cases.\r\n */\r\npublic class Main {\r\n    public static void main(String[] args) {\r\n        Solution solution = new Solution();\r\n        int testCaseNumber = 1;\r\n\r\n        // Test Case 1: General case\r\n        System.out.println("--- Test Case " + testCaseNumber++ + " ---");\r\n        int[] input1 = {3, 8, 4, 6, 5};\r\n        int[] expected1 = {8, -1, 6, 8, 8};\r\n        runTest(solution, input1, expected1);\r\n\r\n        // Test Case 2: Strictly increasing\r\n        System.out.println("--- Test Case " + testCaseNumber++ + " ---");\r\n        int[] input2 = {1, 2, 3, 4, 5};\r\n        int[] expected2 = {2, 3, 4, 5, -1};\r\n        runTest(solution, input2, expected2);\r\n\r\n        // Test Case 3: Strictly decreasing (circular check)\r\n        System.out.println("--- Test Case " + testCaseNumber++ + " ---");\r\n        int[] input3 = {5, 4, 3, 2, 1};\r\n        int[] expected3 = {-1, 5, 5, 5, 5};\r\n        runTest(solution, input3, expected3);\r\n        \r\n        // Test Case 4: All elements are the same\r\n        System.out.println("--- Test Case " + testCaseNumber++ + " ---");\r\n        int[] input4 = {10, 10, 10};\r\n        int[] expected4 = {-1, -1, -1};\r\n        runTest(solution, input4, expected4);\r\n        \r\n        // Test Case 5: Empty input\r\n        System.out.println("--- Test Case " + testCaseNumber++ + " ---");\r\n        int[] input5 = {};\r\n        int[] expected5 = {};\r\n        runTest(solution, input5, expected5);\r\n    }\r\n\r\n    private static void runTest(Solution solution, int[] input, int[] expected) {\r\n        System.out.println("Input:    " + Arrays.toString(input));\r\n        System.out.println("Expected: " + Arrays.toString(expected));\r\n        int[] result = solution.findNextStrongerSignals(input.clone()); // Pass a clone to avoid modifying original\r\n        System.out.println("Output:   " + Arrays.toString(result));\r\n        if (Arrays.equals(result, expected)) {\r\n            System.out.println("Result: ✅ Passed");\r\n        } else {\r\n            System.out.println("Result: ❌ Failed");\r\n        }\r\n        System.out.println();\r\n    }\r\n}\r\n		java	2025-10-24 13:44:53.40431
5	12	1	import java.util.Arrays;\r\nimport java.util.Stack;\r\n\r\n\r\n/**\r\n * The candidate should implement their solution in this class.\r\n * The optimal solution uses a Monotonic Stack and has a time complexity of O(n).\r\n */\r\nclass Solution {\r\n    public int[] findNextStrongerSignals(int[] signalStrengths) {\r\n        // TODO: Implement your optimal O(n) solution here.\r\n        // The current implementation is a placeholder and is incorrect.\r\n        int n = signalStrengths.length;\r\n        if (n == 0) {\r\n            return new int[0];\r\n        }\r\n\r\n        int[] result = new int[n];\r\n        Arrays.fill(result, -1); // Initialize all results to -1 by default\r\n\r\n        // HINT: A stack can be very useful for this problem.\r\n        // Consider iterating twice the length of the array to handle the circular nature.\r\n        \r\n        // BRUTE FORCE APPROACH - O(n^2)\r\n\r\n         for (int i = 0; i < n; i++) {\r\n           for (int j = 1; j < n; j++) {\r\n              \r\n                if (signalStrengths[i] < signalStrengths[(i + j) % n]) {  // (i + j) to circularly iterate array\r\n                    result[i] = signalStrengths[(i + j) % n];\r\n                    break;\r\n                }\r\n            }\r\n        }\r\n        \r\n        \r\n        Stack<Integer> towerSequence = new Stack<>();\r\n        \r\n        for(int i = 0; i < 2*n; i--) {\r\n        \ttowerSequence.push(i % n);\r\n        \t\r\n        \t\r\n        }\r\n        \r\n        \r\n        return result;\r\n    }\r\n}\r\n\r\n/**\r\n * =====================================================================================\r\n * Testing Class - DO NOT MODIFY\r\n * =====================================================================================\r\n * This Main class is designed to test your solution.\r\n * You can run this code to see if your implementation passes the sample test cases.\r\n */\r\npublic class Main {\r\n    public static void main(String[] args) {\r\n        Solution solution = new Solution();\r\n        int testCaseNumber = 1;\r\n\r\n        // Test Case 1: General case\r\n        System.out.println("--- Test Case " + testCaseNumber++ + " ---");\r\n        int[] input1 = {3, 8, 4, 6, 5};\r\n        int[] expected1 = {8, -1, 6, 8, 8};\r\n        runTest(solution, input1, expected1);\r\n\r\n        // Test Case 2: Strictly increasing\r\n        System.out.println("--- Test Case " + testCaseNumber++ + " ---");\r\n        int[] input2 = {1, 2, 3, 4, 5};\r\n        int[] expected2 = {2, 3, 4, 5, -1};\r\n        runTest(solution, input2, expected2);\r\n\r\n        // Test Case 3: Strictly decreasing (circular check)\r\n        System.out.println("--- Test Case " + testCaseNumber++ + " ---");\r\n        int[] input3 = {5, 4, 3, 2, 1};\r\n        int[] expected3 = {-1, 5, 5, 5, 5};\r\n        runTest(solution, input3, expected3);\r\n        \r\n        // Test Case 4: All elements are the same\r\n        System.out.println("--- Test Case " + testCaseNumber++ + " ---");\r\n        int[] input4 = {10, 10, 10};\r\n        int[] expected4 = {-1, -1, -1};\r\n        runTest(solution, input4, expected4);\r\n        \r\n        // Test Case 5: Empty input\r\n        System.out.println("--- Test Case " + testCaseNumber++ + " ---");\r\n        int[] input5 = {};\r\n        int[] expected5 = {};\r\n        runTest(solution, input5, expected5);\r\n    }\r\n\r\n    private static void runTest(Solution solution, int[] input, int[] expected) {\r\n        System.out.println("Input:    " + Arrays.toString(input));\r\n        System.out.println("Expected: " + Arrays.toString(expected));\r\n        int[] result = solution.findNextStrongerSignals(input.clone()); // Pass a clone to avoid modifying original\r\n        System.out.println("Output:   " + Arrays.toString(result));\r\n        if (Arrays.equals(result, expected)) {\r\n            System.out.println("Result: ✅ Passed");\r\n        } else {\r\n            System.out.println("Result: ❌ Failed");\r\n        }\r\n        System.out.println();\r\n    }\r\n}		java	2025-10-24 13:52:32.353178
6	12	2	import java.util.Arrays;\r\nimport java.util.Stack;\r\n\r\n\r\n/**\r\n * The candidate should implement their solution in this class.\r\n * The optimal solution uses a Monotonic Stack and has a time complexity of O(n).\r\n */\r\nclass Solution {\r\n    public int[] findNextStrongerSignals(int[] signalStrengths) {\r\n        // TODO: Implement your optimal O(n) solution here.\r\n        // The current implementation is a placeholder and is incorrect.\r\n        int n = signalStrengths.length;\r\n        if (n == 0) {\r\n            return new int[0];\r\n        }\r\n\r\n        int[] result = new int[n];\r\n        Arrays.fill(result, -1); // Initialize all results to -1 by default\r\n\r\n        // HINT: A stack can be very useful for this problem.\r\n        // Consider iterating twice the length of the array to handle the circular nature.\r\n        \r\n        // BRUTE FORCE APPROACH - O(n^2)\r\n\r\n         for (int i = 0; i < n; i++) {\r\n           for (int j = 1; j < n; j++) {\r\n              \r\n                if (signalStrengths[i] < signalStrengths[(i + j) % n]) {  // (i + j) to circularly iterate array\r\n                    result[i] = signalStrengths[(i + j) % n];\r\n                    break;\r\n                }\r\n            }\r\n        }\r\n        \r\n        \r\n        Stack<Integer> towerSequence = new Stack<>();\r\n        \r\n        for(int i = 0; i < 2*n; i--) {\r\n        \ttowerSequence.push(i % n);\r\n        \t\r\n        \t\r\n        }\r\n        \r\n        \r\n        return result;\r\n    }\r\n}\r\n\r\n/**\r\n * =====================================================================================\r\n * Testing Class - DO NOT MODIFY\r\n * =====================================================================================\r\n * This Main class is designed to test your solution.\r\n * You can run this code to see if your implementation passes the sample test cases.\r\n */\r\npublic class Main {\r\n    public static void main(String[] args) {\r\n        Solution solution = new Solution();\r\n        int testCaseNumber = 1;\r\n\r\n        // Test Case 1: General case\r\n        System.out.println("--- Test Case " + testCaseNumber++ + " ---");\r\n        int[] input1 = {3, 8, 4, 6, 5};\r\n        int[] expected1 = {8, -1, 6, 8, 8};\r\n        runTest(solution, input1, expected1);\r\n\r\n        // Test Case 2: Strictly increasing\r\n        System.out.println("--- Test Case " + testCaseNumber++ + " ---");\r\n        int[] input2 = {1, 2, 3, 4, 5};\r\n        int[] expected2 = {2, 3, 4, 5, -1};\r\n        runTest(solution, input2, expected2);\r\n\r\n        // Test Case 3: Strictly decreasing (circular check)\r\n        System.out.println("--- Test Case " + testCaseNumber++ + " ---");\r\n        int[] input3 = {5, 4, 3, 2, 1};\r\n        int[] expected3 = {-1, 5, 5, 5, 5};\r\n        runTest(solution, input3, expected3);\r\n        \r\n        // Test Case 4: All elements are the same\r\n        System.out.println("--- Test Case " + testCaseNumber++ + " ---");\r\n        int[] input4 = {10, 10, 10};\r\n        int[] expected4 = {-1, -1, -1};\r\n        runTest(solution, input4, expected4);\r\n        \r\n        // Test Case 5: Empty input\r\n        System.out.println("--- Test Case " + testCaseNumber++ + " ---");\r\n        int[] input5 = {};\r\n        int[] expected5 = {};\r\n        runTest(solution, input5, expected5);\r\n    }\r\n\r\n    private static void runTest(Solution solution, int[] input, int[] expected) {\r\n        System.out.println("Input:    " + Arrays.toString(input));\r\n        System.out.println("Expected: " + Arrays.toString(expected));\r\n        int[] result = solution.findNextStrongerSignals(input.clone()); // Pass a clone to avoid modifying original\r\n        System.out.println("Output:   " + Arrays.toString(result));\r\n        if (Arrays.equals(result, expected)) {\r\n            System.out.println("Result: ✅ Passed");\r\n        } else {\r\n            System.out.println("Result: ❌ Failed");\r\n        }\r\n        System.out.println();\r\n    }\r\n}		java	2025-10-24 13:53:27.550079
\.


--
-- Data for Name: emi_payment; Type: TABLE DATA; Schema: public; Owner: sourcepoint_admin
--

COPY public.emi_payment (id, plan_id, installment_number, due_date, amount, description, status, reminder_days_before, reminder_sent, payment_date) FROM stdin;
151	8	6	2025-05-20	6372.05	Installment for IP16PROMAX	Paid	3	f	2025-12-14 12:09:26.554235
152	8	7	2025-06-20	6372.05	Installment for IP16PROMAX	Paid	3	f	2025-12-14 12:09:28.319609
153	8	8	2025-07-20	6372.05	Installment for IP16PROMAX	Paid	3	f	2025-12-14 12:09:30.695829
154	8	9	2025-08-20	6372.05	Installment for IP16PROMAX	Paid	3	f	2025-12-14 12:09:32.869329
155	8	10	2025-09-20	6372.05	Installment for IP16PROMAX	Paid	3	f	2025-12-14 12:09:34.849777
156	8	11	2025-10-20	6372.05	Installment for IP16PROMAX	Paid	3	f	2025-12-14 12:09:38.390344
157	8	12	2025-11-20	6372.05	Installment for IP16PROMAX	Paid	3	f	2025-12-14 12:10:13.391593
158	8	13	2025-12-20	6372.05	Installment for IP16PROMAX	Paid	3	f	2025-12-20 10:51:12.980753
160	8	15	2026-02-20	6372.05	Installment for IP16PROMAX	Pending	3	f	\N
161	8	16	2026-03-20	6372.05	Installment for IP16PROMAX	Pending	3	f	\N
162	8	17	2026-04-20	6372.05	Installment for IP16PROMAX	Pending	3	f	\N
163	8	18	2026-05-20	6372.05	Installment for IP16PROMAX	Pending	3	f	\N
164	8	19	2026-06-20	6372.05	Installment for IP16PROMAX	Pending	3	f	\N
165	8	20	2026-07-20	6372.05	Installment for IP16PROMAX	Pending	3	f	\N
166	8	21	2026-08-20	6372.05	Installment for IP16PROMAX	Pending	3	f	\N
167	8	22	2026-09-20	6372.05	Installment for IP16PROMAX	Pending	3	f	\N
168	8	23	2026-10-20	6372.05	Installment for IP16PROMAX	Pending	3	f	\N
169	8	24	2026-11-20	6372.01	Installment for IP16PROMAX	Pending	3	f	\N
146	8	1	2024-12-20	6372.05	Installment for IP16PROMAX	Paid	3	f	2025-12-14 12:09:15.220354
147	8	2	2025-01-20	6372.05	Installment for IP16PROMAX	Paid	3	f	2025-12-14 12:09:17.864631
148	8	3	2025-02-20	6372.05	Installment for IP16PROMAX	Paid	3	f	2025-12-14 12:09:19.913312
149	8	4	2025-03-20	6372.05	Installment for IP16PROMAX	Paid	3	f	2025-12-14 12:09:21.953187
150	8	5	2025-04-20	6372.05	Installment for IP16PROMAX	Paid	3	f	2025-12-14 12:09:24.294042
159	8	14	2026-01-20	6372.05	Installment for IP16PROMAX	Paid	3	f	2026-01-01 09:46:42.55688
173	9	4	2026-01-17	2019.66	Installment for SBI CC 	Pending	3	f	\N
174	9	5	2026-02-17	2019.66	Installment for SBI CC 	Pending	3	f	\N
175	9	6	2026-03-17	2019.66	Installment for SBI CC 	Pending	3	f	\N
176	9	7	2026-04-17	2019.66	Installment for SBI CC 	Pending	3	f	\N
177	9	8	2026-05-17	2019.66	Installment for SBI CC 	Pending	3	f	\N
178	9	9	2026-06-17	2019.66	Installment for SBI CC 	Pending	3	f	\N
179	9	10	2026-07-17	2019.66	Installment for SBI CC 	Pending	3	f	\N
180	9	11	2026-08-17	2019.66	Installment for SBI CC 	Pending	3	f	\N
181	9	12	2026-09-17	2019.66	Installment for SBI CC 	Pending	3	f	\N
182	9	13	2026-10-17	2019.66	Installment for SBI CC 	Pending	3	f	\N
183	9	14	2026-11-17	2019.66	Installment for SBI CC 	Pending	3	f	\N
184	9	15	2026-12-17	2019.66	Installment for SBI CC 	Pending	3	f	\N
185	9	16	2027-01-17	2019.66	Installment for SBI CC 	Pending	3	f	\N
186	9	17	2027-02-17	2019.66	Installment for SBI CC 	Pending	3	f	\N
187	9	18	2027-03-17	2019.66	Installment for SBI CC 	Pending	3	f	\N
170	9	1	2025-10-17	2130.75	Installment for SBI CC 	Paid	3	f	2026-01-18 10:50:09.275723
171	9	2	2025-11-17	2019.66	Installment for SBI CC 	Paid	3	f	2026-01-18 10:50:11.356401
172	9	3	2025-12-17	2019.66	Installment for SBI CC 	Paid	3	f	2026-01-18 10:50:13.460978
\.


--
-- Data for Name: emi_plan; Type: TABLE DATA; Schema: public; Owner: sourcepoint_admin
--

COPY public.emi_plan (id, title, total_principal, created_at, is_active, borrower_id, lender_id) FROM stdin;
8	IP16PROMAX	152929.16	2025-12-14 12:09:01.032706	t	9	6
9	SBI CC 	36464.97	2026-01-18 10:48:12.046704	t	16	9
\.


--
-- Data for Name: feedback; Type: TABLE DATA; Schema: public; Owner: sourcepoint_admin
--

COPY public.feedback (id, moderator_id, candidate_id, code_correctness, code_efficiency, code_readability, problem_solving, time_management, remarks, created_at) FROM stdin;
1	4	7	3	3	4	3	3		2025-09-12 07:12:48.166295
2	6	12	5	5	5	5	5	Approach doesn’t met with expected coding standard .	2025-10-25 06:58:42.482449
\.


--
-- Data for Name: invoice; Type: TABLE DATA; Schema: public; Owner: sourcepoint_admin
--

COPY public.invoice (id, invoice_number, recipient_name, recipient_email, bill_to_address, ship_to_address, order_id, subtotal, tax, total_amount, due_date, notes, payment_details, created_at, admin_id, status) FROM stdin;
29	INV2025029	Vivan_buyer	vivansantra@gmail.com	PLpot ono 1 , \r\ncloblc mno 90 \r\nishwar colony \r\njalghaon	PLpot ono 1 , \r\ncloblc mno 90 \r\nishwar colony \r\njalghaon	ORD-1764653957-15	3704.19	15.98	4296.00	2025-12-02	Auto-generated invoice. Prices include applicable GST.	\N	2025-12-02 05:39:48.923799	1	Paid
27	INV2025027	Vivan_buyer	vivansantra@gmail.com	sdvv	sdvv	ORD-1764164143-15	1796.84	13.98	2048.00	2025-11-26	Auto-generated invoice. Prices include applicable GST.	\N	2025-11-26 13:36:58.46579	1	Paid
25	INV2025025	Vivan_buyer	vivansantra@gmail.com	Nisarg Pooja\r\nWakad \r\n411057	Nisarg Pooja\r\nWakad \r\n411057	ORD-1764080314-15	599.00	18.00	706.82	2025-11-25	Auto-generated invoice for accepted order.	\N	2025-11-25 14:19:22.414214	1	Paid
23	INV2025023	Vivan_buyer	vivansantra@gmail.com	wef	ewf	ORD-1764073163-15	2500.00	18.00	2950.00	2025-11-25	Auto-generated invoice for accepted order.	\N	2025-11-25 12:20:00.844656	1	Paid
6	INV2025006	Jagruti Kaustubh Chaudhari	advjagrutikchaudhari@gmail.com	G-728, Shah Arcade , Sector 6,\r\nSector 6, Kharghar , Maharashtra,\r\nIN-MH, IN-410210	G-728, Shah Arcade , Sector 6,\r\nSector 6, Kharghar , Maharashtra,\r\nIN-MH, IN-410210	OD335533652140487100	13506.78	18.00	15938.00	2025-09-30	Total Cost Includes Variable Paid as a part of Affiliate Offer handling.	Payment On Delivery Terms 	2025-09-24 05:34:15.404561	1	Paid
9	INV2025009	Jagruti Kaustubh Chaudhari	advjagrutikchaudhari@gmail.com	Shah Arcade , Sector 6\r\nKharghar , Navi Mumbai,\r\nMaharashtra, IN-410210	Shah Arcade , Sector 6\r\nKharghar , Navi Mumbai,\r\nMaharashtra, IN-410210	OD335534086404482100	45392.00	18.00	53562.56	2025-09-30	On Delivery Terms 		2025-09-26 17:17:19.012832	1	Paid
10	INV2025010	Jagruti Kaustubh Chaudhari	advjagrutikchaudhari@gmail.com	Shah Arcade , Sector 6\r\nKharghar, Maharashtra ,\r\nIN-410210	Shah Arcade , Sector 6\r\nKharghar, Maharashtra ,\r\nIN-410210	OD335533790623409100	19725.01	0.00	19725.01	2025-09-30			2025-09-29 19:04:27.894447	1	Paid
12	INV2025011	Ritikesh Chavan 	ritikeshchavan@gmail.com	Nisarg Pooja , Nr Mankar Chauk,\r\nWakad , Pune , Maharashtra , IN-411057	Nisarg Pooja , Nr Mankar Chauk,\r\nWakad , Pune , Maharashtra , IN-411057	A483	1185.00	18.00	1398.30	2025-10-01			2025-10-01 07:21:19.493124	1	Paid
13	INV2025013	Jayesh Barhate	jayeshbarhate592@gmail.com	Nisarg Pooja,\r\nMankar Chauk,\r\nWakad , Pune \r\n411057 	Nisarg Pooja,\r\nMankar Chauk,\r\nWakad , Pune \r\n411057 	OD48159	900.00	0.00	900.00	2025-10-06	On Delivery Terms		2025-10-06 13:32:10.767642	1	Paid
8	INV2025008	Jayesh Barhate	jayeshbarhate592@gmail.com	Nisarg Pooja , Wakad ,\r\n411057	Nisarg Pooja , Wakad ,\r\n411057	AC8062	1975.00	0.00	1975.00	2025-09-30	On Delivery Terms		2025-09-24 14:29:47.506239	1	Paid
18	INV2025018	Gaurav Patil	gp2239396@gmail.com	PLot no 1 ,\r\nblock no 9 \r\nishwar colopny , jalgaon ,\r\n425001	PLot no 1 ,\r\nblock no 9 \r\nishwar colopny , jalgaon ,\r\n425001	A101	35043.64	0.00	35043.64	2025-11-21	In delivery terms 	hascblec	2025-11-21 10:34:42.288026	1	Paid
17	INV2025017	Gaurav Patil	gp2239396@gmail.com	wedf\r\nfaf\r\nf\r\nadd\r\nf	wedf\r\nfaf\r\nf\r\nadd\r\nf	A101	2500.00	0.00	2500.00	2025-11-21	dscsdvdsv	dsvdsvdsv	2025-11-21 10:29:34.751243	1	Paid
16	INV2025016	Gaurav Patil	gp2239396@gmail.com	hbvjh dscvs	dsvdvsdvds	OD335533790623409100	2500.00	0.00	2500.00	2025-11-21			2025-11-21 10:21:03.825013	1	Paid
15	INV2025014	Gaurav Patil	gp2239396@gmail.com	bn	bn 	OD335533790623409100	2500.00	0.00	2500.00	2025-11-21			2025-11-21 10:11:55.385227	1	Paid
19	INV2025019	Vivan_buyer	vivansantra@gmail.com	Plot no 1 , blopck no 9	Plot no 1 , blopck no 9	ORD-1763810116-15	450.00	18.00	531.00	2025-11-22	Auto-generated invoice for accepted order.	\N	2025-11-22 11:42:03.267308	1	Paid
28	INV2025028	Nikita	nikitaumalkar98@gmail.com	A-601, Nisarg Pooja\r\nWakad , 411057	A-601, Nisarg Pooja\r\nWakad , 411057	ORD-1764497289-16	4320.34	18.00	5098.00	2025-11-30	Auto-generated invoice. Prices include applicable GST.	\N	2025-11-30 10:08:30.441884	1	Paid
30	INV2025030	Ritikesh Chavan	ritikeshchavan@gmail.com	Tathawade,\r\nPune , 411033 , Maharashtra,\r\nIndia\r\n	Tathawade,\r\nPune , 411033 , Maharashtra,\r\nIndia\r\n	ORD-1764765318-18	270.34	18.00	319.00	2025-12-03	Auto-generated invoice. Prices include applicable GST.	\N	2025-12-03 12:36:16.19262	1	Paid
24	INV2025024	Gaurav Patil	gp2239396@gmail.com	Ihocewc	Ihocewc	A101	3400.00	18.00	4012.00	2025-11-25	ON terms 	Bank detials 	2025-11-25 13:09:04.390292	1	Paid
32	INV2025032	Gaurav	gp2239396@gmail.com	dcd	wwce	\N	0.00	0.00	0.00	2025-12-18	\N	\N	2025-12-18 12:53:26.003262	20	Paid
20	INV2025020	Vivan_buyer	vivansantra@gmail.com	Plot no 1 , block no 9 \r\nJalgaon , \r\n425001	Plot no 1 , block no 9 \r\nJalgaon , \r\n425001	ORD-1763811665-15	450.00	18.00	531.00	2025-11-22	Auto-generated invoice for accepted order.	\N	2025-11-22 11:47:07.273912	1	Paid
33	INV2025033	Nikita	nikitaumalkar98@gmail.com	eujwblieuwabfew	eujwblieuwabfew	ORD20250012	18398.00	0.00	18398.00	2025-12-18	Auto-generated by Seller.	\N	2025-12-18 13:20:35.71402	20	Paid
34	INV2025034	Gaurav Patil	gp2239396@gmail.com	dfsvfvd	fdsvsdfvs	\N	123.00	0.00	123.00	2025-12-20	\N	\N	2025-12-20 05:31:41.207307	20	Paid
36	INV2025036	Vivan_buyer	vivansantra@gmail.com	ewfawefe	ewfawefe	ORD20250014	215.00	0.00	215.00	2025-12-20	Auto-generated by Seller.	\N	2025-12-20 05:44:48.046965	20	Paid
37	INV2025037	Vivan_buyer	vivansantra@gmail.com	fev	fev	ORD20250015	3599.00	0.00	3599.00	2025-12-20	Auto-generated by Seller.	\N	2025-12-20 05:48:46.94246	20	Paid
7	INV2025007	Lalit Kishor Barhate	calalitbarhate@gmail.com	Nisarg Pooja , Wakad , 411057 	Nisarg Pooja , Wakad , 411057 	AC1390	975.00	0.00	975.00	2025-09-30	On Purchase Terms\r\nEligible For RLO for 6 Month 		2025-09-24 14:07:45.776194	1	Paid
38	INV2025038	Vivan_buyer	vivansantra@gmail.com	hjjh	hjjhhjjh	ORD-1766209863-15	592.37	18.00	699.00	2025-12-20	Auto-generated invoice. Prices include applicable GST.	\N	2025-12-20 05:51:56.194108	1	Paid
31	INV2025031	Jayesh Barhate	jayeshbarhate592@gmail.com	C1 , Kalpataru \r\nPimpri Gurav 	C1 , Kalpataru \r\nPimpri Gurav 	ADN-368	1121.00	0.00	1121.00	2025-12-14	ClearTrip Broker Credit Reference - 228000613	On Credit Hold 	2025-12-14 04:45:05.383835	1	Paid
39	INV2025039	Jayesh Barhate	jayeshbarhate592@gmail.com	c2-504 ,karan Muktangan , \r\nKashid park\r\nPimpri Gurav , Pune	c2-504 ,karan Muktangan , \r\nKashid park\r\nPimpri Gurav , Pune	A483	810.00	0.00	810.00	2025-12-22			2025-12-22 10:05:52.717984	1	Paid
26	INV2025026	Jayesh Barhate	jayeshbarhate592@gmail.com	Karan Muktangan,\r\nKashid park ,Pimpri Gurav	Karan Muktangan,\r\nKashid park ,Pimpri Gurav	ORD-1764159493-17	198.00	18.00	233.64	2025-11-26	Auto-generated invoice for accepted order.	\N	2025-11-26 12:18:41.014644	1	Paid
35	INV2025035	Vivan_buyer	vivansantra@gmail.com	hjwqkSVDHJQWBVC	hjwqkSVDHJQWBVC	ORD20250013	3599.00	0.00	3599.00	2025-12-20	Auto-generated by Seller.	\N	2025-12-20 05:32:48.26591	20	Paid
21	INV2025021	Nikita	nikitaumalkar98@gmail.com	Nisarg Pooja	Nisarg Pooja	ORD-1763894906-16	3850.00	18.00	4543.00	2025-11-23	Auto-generated invoice for accepted order.	\N	2025-11-23 10:49:10.734969	1	Paid
22	INV2025022	Vivan_buyer	vivansantra@gmail.com	plopt no 1 	plopt no 1 	ORD-1763913161-15	4147.00	18.00	4893.46	2025-11-23	Auto-generated invoice for accepted order.	\N	2025-11-23 15:53:19.297828	1	Paid
40	INV2025040	Jayesh Barhate	jayeshbarhate592@gmail.com	c2-504 ,karan Muktangan , \r\nKashid park\r\nPimpri Gurav , Pune	c2-504 ,karan Muktangan , \r\nKashid park\r\nPimpri Gurav , Pune	A562	21225.00	0.00	21225.00	2025-12-22	On Delivery Terms		2025-12-22 10:11:15.496529	1	Paid
41	INV2025041	Jayesh Barhate	jayeshbarhate592@gmail.com	Kalpataru Society\r\nKashid Park , Pimpri Gurav,\r\nPune\r\nNon Affiliated ADR 	Kalpataru Society\r\nKashid Park , Pimpri Gurav,\r\nPune\r\nNon Affiliated ADR 	Non-Billable ASN	11940.00	0.00	11940.00	2025-12-27	Bulk Inventory Provision Under SL450 Stock Allocation Batch.\r\n	RTR#693948CR	2025-12-27 17:57:57.533865	1	Paid
46	INV-A3697A	Vivan	vivansantra@gmail.com	Giriraj Krishna ,\r\nSector 19 , Kharghar , 410210 	Giriraj Krishna ,\r\nSector 19 , Kharghar , 410210 	ORD7962	660.00	0.00	660.00	2026-01-07	Billed Product is a Circuit Copy and does not represent legit products in sense of quality . 		2026-01-07 16:15:15.589835	1	Paid
44	INV-791786	Nikita Umalkar	nikitaumalkar98@gmail.com	A-603 , Nisarg pooja\r\nMankar Chauk , Wakad,\r\n411057 , Pune 	A-603 , Nisarg pooja\r\nMankar Chauk , Wakad,\r\n411057 , Pune 	ORD582	1229.00	0.00	1229.00	2026-01-02			2026-01-02 15:15:08.044324	1	Paid
48	INV-D8E828	Nikita Umalkar	nikitaumalkar98@gmail.com	A-601, Nisarg Pooja,\r\nMankar Chauk , Wakad,\r\n411057 , Pune , MH 	A-601, Nisarg Pooja,\r\nMankar Chauk , Wakad,\r\n411057 , Pune , MH 		10750.00	0.00	10750.00	2026-01-18	Payment On Terms		2026-01-18 13:26:57.269185	1	Unpaid
47	INV-A3F4D6	Jayesh Barhate	jayeshbarhate592@gmail.com	Kalpataru Society,\r\nKashid Park , Pimpri Gurav,\r\nPune\r\nNon Affiliated ADR	Kalpataru Society,\r\nKashid Park , Pimpri Gurav,\r\nPune\r\nNon Affiliated ADR		0.00	0.00	0.00	2026-01-16	Model Replacement for Zoook Qwerty Wireless Keyboard Mouse Combo		2026-01-16 05:51:41.712338	1	Paid
49	INV-DED7DB	Jayesh Barhate	jayeshbarhate592@gmail.com	Kharghar , 410210	Kharghar , 410210		16944.00	0.00	16944.00	2026-01-20	Amazon Affiliate Order : No Bounty Conversion		2026-01-20 10:48:05.695478	1	Unpaid
45	INV-67E7F6	Ajmal Shaikh	ajmalshaikh1088@gmail.com	Sector 19, kharghar,\r\n410210 , Navi Mumbai	Sector 19, kharghar,\r\n410210 , Navi Mumbai	OD335533790623409100	300.00	0.00	300.00	2026-01-02	On Delivery Terms		2026-01-02 15:24:56.111934	1	Paid
50	INV-20F241	Jayesh Barhate	jayeshbarhate592@gmail.com	Saraswati Nagar,\r\nJalgaon, Maharashtra,\r\nIN-425001	Saraswati Nagar,\r\nJalgaon, Maharashtra,\r\nIN-425001		4044.00	0.00	4044.00	2026-01-26	Booked Via ClearTrip Agent Booking SAPI 		2026-01-26 13:40:29.38573	1	Unpaid
\.


--
-- Data for Name: invoice_item; Type: TABLE DATA; Schema: public; Owner: sourcepoint_admin
--

COPY public.invoice_item (id, description, quantity, price, invoice_id) FROM stdin;
6	Apple Airpod Pro ( 2nd Gen ) With Megasafe ( USB-C) -SNo.SF2X0J2920C	1	12506.78	6
7	Affiliate Credit Use & Offer Handling Fee	1	1000.00	6
8	HP 712 w USB 3.2	1	975.00	7
9	Crocs Bayaband Black / White 	1	1975.00	8
10	HP Intel Core i7 13th Gen 13620H - (16 GB/512 GB SSD/Windows 11 Home) 15-fr0046TU Thin and Light Laptop	1	43393.00	9
11	Affiliate Credit & Flipkart Handling Fees (450)	1	1000.00	9
12	Lenovo WL310 Bluetooth Silent Mouse Wireless Ambidextrous Optical Mouse with Bluetooth  (Grey)	1	999.00	9
13	HP LaserJet Tank MFP 2606sdw Printer Multi-function Monochrome Laser Printer	1	18490.01	10
14	Flipkart Payment & Offer Handling Fees	1	235.00	10
15	Affiliate Credit	1	1000.00	10
17	Lenovo 20V 3.35A 65W Laptop Charger AC Adapter for Lenovo G570 B570 B575 G575 B470 IdeaPad N580 N585 Z580 Z585 N586 P400 P500 ADP-65KHB CPA-A065 PA-1650-56LC Series	1	1185.00	12
18	HP USB 3.0 Flash Drive v220w	1	900.00	13
21	HP Mouse	1	2500.00	15
22	HP Mouse	1	2500.00	16
23	HP Mouse	1	2500.00	17
24	HP Mouse	2	2500.00	18
25	Apple Airpod Pro	12	2322.97	18
26	desfwefewf	1	34.00	18
27	245234	1	2134.00	18
28	Gaming Mouse	1	450.00	19
29	Gaming Mouse	1	450.00	20
30	Gaming Mouse	3	450.00	21
31	HP Mouse	1	2500.00	21
32	NOBERO Men's Oversized Solid Loose fit Heavy Cotton T-Shirt (Pack of 2)	1	1349.00	22
33	Nobero Oversized Hoodies for Man Stylish	2	1399.00	22
34	HP Mouse	1	2500.00	23
35	HP Mouse	1	2500.00	24
36	Gaming Mouse	1	450.00	24
37	Gaming Mouse	1	450.00	24
38	HP M120 /6 programm. buttons,1 AA battery gives upto 12 months life	1	599.00	25
39	Portronics Bridge Y USB 3.0 to Type C OTG Adaptor	2	99.00	26
40	NOBERO Men's Oversized Solid Loose fit Heavy Cotton T-Shirt (Pack of 2)	1	1204.46	27
41	HP S1000 Plus Silent USB Wireless Computer Mute Mouse 1600DPI USB (7YA12PA), Black	1	592.37	27
42	Apple 30W USB-C Power Adapter ​​​​​​​	1	2456.78	28
43	Apple USB-C to Lightning Cable (2m) ​​​​​​​	1	1863.56	28
44	HP S1000 Plus Silent USB Wireless Computer Mute Mouse 1600DPI USB (7YA12PA), Black	1	592.37	29
45	Nobero Oversized Hoodies for Man Stylish	1	1249.11	29
46	HP M120 /6 programm. buttons,1 AA battery gives upto 12 months life	1	507.63	29
47	Meetion MT-G3330 Wired Ambidextrous Optical Gaming Mouse	1	1355.08	29
48	Boat BassHeads 100 in-Ear Headphones with Mic (Black)	1	270.34	30
49	Sangitam Travel - PN - JL 	1	1121.00	31
50	Nobero Oversized Hoodies for Man Stylish	1	1399.00	33
51	Jabra Evolve2 65	1	16999.00	33
52	Apple Airpod Pro	1	123.00	34
53	Apple 20W USB‑C Power Adapter	1	3599.00	35
54	Boat BassHeads 100 in-Ear Headphones with Mic (Black)	1	215.00	36
55	Apple 20W USB‑C Power Adapter	1	3599.00	37
56	HP S1000 Plus Silent USB Wireless Computer Mute Mouse 1600DPI USB (7YA12PA), Black	1	592.37	38
57	Travel Booking - Pune - Jalgaon	1	810.00	39
58	OnePlus Nord CE4 (Celadon Marble, 128 GB)	1	20718.00	40
59	Affiliates Credit Use	1	507.00	40
60	Meetion MT-G3330 Wired Ambidextrous Optical Gaming Mouse	2	1000.00	41
61	HP S1000 Plus Silent USB Wireless Computer Mute Mouse 1600DPI USB (7YA12PA), Black	6	300.00	41
62	Lenovo Legion M300s RGB Wired Gaming Mouse	1	1000.00	41
63	Zoook Qwerty Pad/3 Adj. DPI/Full Size Keyboard(104 key) & Mouse Combo 	2	350.00	41
64	HP M120 /6 programm. buttons,1 AA battery gives upto 12 months life	2	300.00	41
65	Boat BassHeads 100 in-Ear Headphones with Mic (Black)	4	210.00	41
66	Portronics Bubble Dock Bluetooth, Wireless Handheld Multi-device Keyboard 	3	500.00	41
67	Jabra Evolve 40 UC Wired Over The Ear Headset with Mic (Black)	1	3500.00	41
70	Travel Booking ( Mehkar to Pune	1	1229.00	44
71	The Men Company Deodorant for Men - 150 ML	4	75.00	45
72	AA- Jabra Evolve 65 TE 	1	450.00	46
73	Shipping ( LMN - NM ) 	1	210.00	46
74	Zebronics Pulse Wireless Mouse	1	0.00	47
75	Larah Vogue Glass Lunchbox, Round x 3, 400ml x 3	1	0.00	47
76	realme P3 Lite 5G Charger in the Box (Lily White, 128 GB) (4 GB RAM)	1	10750.00	48
77	BDSKAMAZON665D6	1	16944.00	49
78	Bus Ticket - JL - PUN	2	1321.00	50
79	Bus Ticket - JL - PUN	1	1402.00	50
\.


--
-- Data for Name: job_application; Type: TABLE DATA; Schema: public; Owner: sourcepoint_admin
--

COPY public.job_application (id, user_id, job_id, status, applied_at, resume_url) FROM stdin;
1	7	1	accepted	2025-09-12 06:13:45.717386	\N
2	8	2	accepted	2025-09-13 12:39:29.411141	\N
3	3	3	Selected	2026-01-04 12:46:51.359005	https://res.cloudinary.com/dh9vjtajb/raw/upload/v1766909970/resumes/resume_3
4	3	6	Rejected	2026-01-08 10:50:59.103563	https://res.cloudinary.com/dh9vjtajb/raw/upload/v1766909970/resumes/resume_3
5	29	6	Selected	2026-01-08 16:03:49.471778	https://res.cloudinary.com/dh9vjtajb/raw/upload/v1767888230/application_resumes/app_resume_29_6
6	3	7	Selected	2026-01-22 10:31:33.905416	https://res.cloudinary.com/dh9vjtajb/raw/upload/v1766909970/resumes/resume_3
\.


--
-- Data for Name: job_opening; Type: TABLE DATA; Schema: public; Owner: sourcepoint_admin
--

COPY public.job_opening (id, job_id, title, description, is_open, created_at) FROM stdin;
1	ebd3f3cd-942e-4b03-919f-74ba0c6ed899	Java SprinBoot Developer	Develop an efficient springboot application and code in java 8 latest technologies	t	2025-09-11 16:32:14.971628
2	1b6e3bb0-8dfa-4e09-8039-285ca8bb680d	Java_Developer_Q4	Job Facts :\r\nSoftware Development: This is a hands-on software development position to write high-quality software that will perform at scale, be supportable, and be extensible.\r\n• Process & Operations: Ensure the software stack integrates with our existing CI pipeline and contribute to continuous improvement; independently design, plan and deliver high-quality software.\r\n• Leadership: Ensure a culture that values technical excellence together with support and compassion for individuals.\r\n• Technology stack: Most of the stack is in Angular (backed by Spring boot microservices) but we constantly explore different technologies and toolsets that are fit-for-purpose. Here is a list of technologies we currently use:\r\n• Java, Spring Boot, Spring, Hibernate\r\n• Javascript MVC framework: Angular 16, ThreeJS\r\n• Object Oriented JavaScript, HTML5, JSON, and CSS3\r\n• TypeScript\r\n• Unit testing using Junit.\r\n• GIT\r\n• AWS (Must have working knowledge in EC2, ECS, ECR, Lambda, Elastic Cache, Route53, CloudFront, API Gateway, S3, Glacier, RDS, NLB/ALB, Security Groups/NACLs/VPCs, Cloud Watch )\r\n• Docker & Kubernetes (Good to have)\r\n• Experience In REST API integration\r\n\r\n	t	2025-09-12 09:08:17.023236
3	7ad1c15a-d03f-4052-be81-dc9075d47717	Python_Developer_CSB	Key Responsibilities:\r\n\r\nDesign, build, and maintain efficient, reusable, and reliable Python code for our backend systems.\r\n\r\nDevelop and manage well-functioning databases and applications, with a strong focus on PostgreSQL.\r\n\r\nIntegrate user-facing elements developed by front-end developers with server-side logic.\r\n\r\nImplement security and data protection measures.\r\n\r\nWrite and optimize SQL queries, and design robust database schemas.\r\n\r\nCollaborate with the product team, front-end developers, and other stakeholders to design and launch new features.\r\n\r\nIdentify bottlenecks, debug issues, and ensure the performance and scalability of our applications.\r\n\r\nParticipate in code reviews to maintain high-quality code standards.	t	2025-10-21 13:54:57.181877
6	f2e6b967-326f-4e5a-a493-a1948829c040	Frontend Engineer (React.js Focus)	<p data-path-to-node="13"><strong data-path-to-node="13" data-index-in-node="0">Job Title:</strong> Lead React.js Developer <strong data-path-to-node="13" data-index-in-node="35">Experience:</strong> 4+ Years <strong data-path-to-node="13" data-index-in-node="56">Location:</strong> [Remote] <strong data-path-to-node="13" data-index-in-node="83">Project Context:</strong> Building a high-performance Supply Chain Dashboard for warehouse managers and logistics coordinators.</p>\r\n<p data-path-to-node="14"><strong data-path-to-node="14" data-index-in-node="0">Key Responsibilities:</strong></p>\r\n<ul data-path-to-node="15">\r\n<li>\r\n<p data-path-to-node="15,0,0"><strong data-path-to-node="15,0,0" data-index-in-node="0">UI Architecture:</strong> Architect a scalable <strong data-path-to-node="15,0,0" data-index-in-node="38">React.js (SPA)</strong> frontend from scratch, replacing legacy WinForms/WebForms.</p>\r\n</li>\r\n<li>\r\n<p data-path-to-node="15,1,0"><strong data-path-to-node="15,1,0" data-index-in-node="0">Component Library:</strong> Develop a reusable UI component library (using Material UI or Ant Design) for consistent design across Order, Inventory, and Logistics modules.</p>\r\n</li>\r\n<li>\r\n<p data-path-to-node="15,2,0"><strong data-path-to-node="15,2,0" data-index-in-node="0">State Management:</strong> Implement complex state management (using <strong data-path-to-node="15,2,0" data-index-in-node="60">Redux Toolkit</strong> or <strong data-path-to-node="15,2,0" data-index-in-node="77">React Query</strong>) to handle real-time inventory updates and tracking data.</p>\r\n</li>\r\n<li>\r\n<p data-path-to-node="15,3,0"><strong data-path-to-node="15,3,0" data-index-in-node="0">API Integration:</strong> Integrate frontend with .NET Core Microservices via REST and gRPC.</p>\r\n</li>\r\n<li>\r\n<p data-path-to-node="15,4,0"><strong data-path-to-node="15,4,0" data-index-in-node="0">Performance:</strong> Optimize application speed to ensure &lt;200ms load times for critical supply chain data.</p>\r\n</li>\r\n</ul>\r\n<p data-path-to-node="16"><strong data-path-to-node="16" data-index-in-node="0">Required Technical Skills (The "Must-Haves"):</strong></p>\r\n<ul data-path-to-node="17">\r\n<li>\r\n<p data-path-to-node="17,0,0"><strong data-path-to-node="17,0,0" data-index-in-node="0">Core Frontend:</strong> Expert in <strong data-path-to-node="17,0,0" data-index-in-node="25">React.js</strong>, <strong data-path-to-node="17,0,0" data-index-in-node="35">TypeScript</strong>, HTML5, CSS3/SCSS.</p>\r\n</li>\r\n<li>\r\n<p data-path-to-node="17,1,0"><strong data-path-to-node="17,1,0" data-index-in-node="0">State Management:</strong> Deep understanding of <strong data-path-to-node="17,1,0" data-index-in-node="40">Redux</strong>, <strong data-path-to-node="17,1,0" data-index-in-node="47">Context API</strong>, and <strong data-path-to-node="17,1,0" data-index-in-node="64">React Query/TanStack</strong>.</p>\r\n</li>\r\n<li>\r\n<p data-path-to-node="17,2,0"><strong data-path-to-node="17,2,0" data-index-in-node="0">Visualization:</strong> Experience with charting libraries (e.g., <strong data-path-to-node="17,2,0" data-index-in-node="57">Recharts</strong>, <strong data-path-to-node="17,2,0" data-index-in-node="67">D3.js</strong>) for supply chain analytics dashboards.</p>\r\n</li>\r\n<li>\r\n<p data-path-to-node="17,3,0"><strong data-path-to-node="17,3,0" data-index-in-node="0">Build Tools:</strong> Proficiency with <strong data-path-to-node="17,3,0" data-index-in-node="30">Webpack</strong> or <strong data-path-to-node="17,3,0" data-index-in-node="41">Vite</strong>.</p>\r\n</li>\r\n<li>\r\n<p data-path-to-node="17,4,0"><strong data-path-to-node="17,4,0" data-index-in-node="0">Testing:</strong> Experience with <strong data-path-to-node="17,4,0" data-index-in-node="25">Jest</strong> and <strong data-path-to-node="17,4,0" data-index-in-node="34">React Testing Library</strong>.</p>\r\n</li>\r\n</ul>	t	2026-01-08 10:49:50.102131
7	b001ef1e-c215-4fa9-b3e8-d37c28f30a69	Full Stack Modernization Engineer (Hybrid: React + Azure)	<p data-path-to-node="21"><strong data-path-to-node="21" data-index-in-node="0">Job Title:</strong> Senior Full Stack .NET Cloud Engineer <strong data-path-to-node="21" data-index-in-node="49">Primary Focus:</strong> Azure Cloud &amp; React.js</p>\r\n<p data-path-to-node="22"><strong data-path-to-node="22" data-index-in-node="0">Key Requirements:</strong></p>\r\n<ul data-path-to-node="23">\r\n<li>\r\n<p data-path-to-node="23,0,0"><strong data-path-to-node="23,0,0" data-index-in-node="0">Migration Specialist:</strong> Proven experience migrating on-premise legacy .NET applications to Azure Cloud.</p>\r\n</li>\r\n<li>\r\n<p data-path-to-node="23,1,0"><strong data-path-to-node="23,1,0" data-index-in-node="0">Frontend-Backend Bridge:</strong> Ability to write <strong data-path-to-node="23,1,0" data-index-in-node="42">React (TypeScript)</strong> code for the dashboard and immediately deploy the supporting <strong data-path-to-node="23,1,0" data-index-in-node="122">.NET 8 APIs</strong> to <strong data-path-to-node="23,1,0" data-index-in-node="137">Azure App Services</strong>.</p>\r\n</li>\r\n<li>\r\n<p data-path-to-node="23,2,0"><strong data-path-to-node="23,2,0" data-index-in-node="0">Real-time Systems:</strong> Experience building real-time tracking features using <strong data-path-to-node="23,2,0" data-index-in-node="73">Azure SignalR Service</strong> and React hooks.</p>\r\n</li>\r\n<li>\r\n<p data-path-to-node="23,3,0"><strong data-path-to-node="23,3,0" data-index-in-node="0">Azure Identity:</strong> Experience implementing Single Sign-On (SSO) connecting React frontends with Azure AD.</p>\r\n</li>\r\n</ul>	t	2026-01-08 10:50:25.099556
\.


--
-- Data for Name: learning_content; Type: TABLE DATA; Schema: public; Owner: sourcepoint_admin
--

COPY public.learning_content (id, content, last_updated) FROM stdin;
java	<div class="bg-white/5 dark:bg-gray-800/20 rounded-lg shadow-xl p-8 animate-dynamic backdrop-blur-sm border border-white/10 text-gray-300">\n<h1 class="text-4xl font-bold text-white mb-8 flex items-center"><i class="fab fa-java fa-fw mr-4 text-orange-400"></i> Java Tutorial</h1>\n<div class="space-y-6">\n<!-- Section 1: Overview -->\n<section class="scroll-mt-20" id="overview">\n<h2 class="text-3xl font-semibold text-white mb-4 border-b border-gray-700 pb-2">1. Java - Overview</h2>\n<details class="bg-white/5 rounded-lg p-4">\n<summary class="font-semibold text-lg cursor-pointer text-white">What is Java?</summary>\n<p class="mt-2">Java is a high-level, object-oriented programming language developed by Sun Microsystems and released in 1995. It is designed to be "Write Once, Run Anywhere" (WORA), meaning compiled Java code can run on all platforms that support Java without recompilation.</p>\n</details>\n<details class="bg-white/5 rounded-lg p-4 mt-2">\n<summary class="font-semibold text-lg cursor-pointer text-white">Key Features</summary>\n<ul class="list-disc list-inside mt-2 space-y-1">\n<li><strong>Object-Oriented:</strong> Everything in Java is an object.</li>\n<li><strong>Platform Independent:</strong> Compiled into platform-independent byte code that runs on a Java Virtual Machine (JVM).</li>\n<li><strong>Simple &amp; Secure:</strong> Designed to be easy to learn and has built-in security features.</li>\n<li><strong>Robust &amp; Multithreaded:</strong> Strong memory management and support for concurrent tasks.</li>\n</ul>\n</details>\n</section>\n<!-- Section 2: Environment Setup -->\n<section class="scroll-mt-20" id="environment">\n<h2 class="text-3xl font-semibold text-white mb-4 border-b border-gray-700 pb-2">2. Environment Setup</h2>\n<details class="bg-white/5 rounded-lg p-4">\n<summary class="font-semibold text-lg cursor-pointer text-white">Local Environment Setup</summary>\n<p class="mt-2">To develop Java applications locally, you need to install the Java Development Kit (JDK). You can download it for free from Oracle or use an open-source alternative like OpenJDK. After installation, you must set the `JAVA_HOME` environment variable and add the JDK's `bin` directory to your system's `PATH`.</p>\n</details>\n</section>\n<!-- Section 3: Basic Syntax -->\n<section class="scroll-mt-20" id="syntax">\n<h2 class="text-3xl font-semibold text-white mb-4 border-b border-gray-700 pb-2">3. Basic Syntax</h2>\n<details class="bg-white/5 rounded-lg p-4">\n<summary class="font-semibold text-lg cursor-pointer text-white">First Java Program</summary>\n<p class="mt-2">The entry point for any Java application is the `public static void main(String[] args)` method.</p>\n<pre><code class="language-java">\npublic class MyFirstJavaProgram {\n    public static void main(String[] args) {\n        System.out.println("Hello World"); // prints Hello World\n    }\n}\n                        </code></pre>\n</details>\n<details class="bg-white/5 rounded-lg p-4 mt-2">\n<summary class="font-semibold text-lg cursor-pointer text-white">Syntax Rules</summary>\n<ul class="list-disc list-inside mt-2 space-y-1">\n<li><strong>Case-Sensitive:</strong> `myVariable` and `MyVariable` are different.</li>\n<li><strong>Class Names:</strong> Start with an uppercase letter (e.g., `MyClass`).</li>\n<li><strong>Method Names:</strong> Start with a lowercase letter (e.g., `myMethod`).</li>\n<li><strong>File Name:</strong> Must exactly match the public class name (e.g., `MyClass.java`).</li>\n</ul>\n</details>\n</section>\n<!-- Section 4: Objects & Classes -->\n<section class="scroll-mt-20" id="objects">\n<h2 class="text-3xl font-semibold text-white mb-4 border-b border-gray-700 pb-2">4. Objects &amp; Classes</h2>\n<details class="bg-white/5 rounded-lg p-4">\n<summary class="font-semibold text-lg cursor-pointer text-white">Understanding Objects and Classes</summary>\n<p class="mt-2">A **Class** is a blueprint for creating objects. It defines the properties (instance variables) and behaviors (methods) that its objects will have. An **Object** is an instance of a class.</p>\n<pre><code class="language-java">\npublic class Dog {\n    // Instance variables\n    String breed;\n    int age;\n    String color;\n\n    // Methods\n    void barking() {\n        System.out.println("The dog is barking.");\n    }\n}\n\n// Creating an object (instance) of the Dog class\nDog myDog = new Dog();\n                        </code></pre>\n</details>\n<details class="bg-white/5 rounded-lg p-4 mt-2">\n<summary class="font-semibold text-lg cursor-pointer text-white">Constructors</summary>\n<p class="mt-2">A constructor is a special method that is used to initialize objects. It is called when an object is created using the `new` keyword. If you don't define a constructor, Java provides a default one.</p>\n<pre><code class="language-java">\npublic class Puppy {\n    // Constructor with one parameter\n    public Puppy(String name) {\n        System.out.println("Passed Name is: " + name);\n    }\n\n    public static void main(String []args) {\n        // The constructor is called here\n        Puppy myPuppy = new Puppy("tommy");\n    }\n}\n                        </code></pre>\n</details>\n</section>\n<!-- More sections based on the PDF content would follow this pattern... -->\n<section class="scroll-mt-20" id="datatypes">\n<h2 class="text-3xl font-semibold text-white mb-4 border-b border-gray-700 pb-2">5. Basic Datatypes</h2>\n<details class="bg-white/5 rounded-lg p-4">\n<summary class="font-semibold text-lg cursor-pointer text-white">Primitive vs. Reference Datatypes</summary>\n<p class="mt-2">Java has two categories of data types:</p>\n<ul class="list-disc list-inside mt-2 space-y-1">\n<li><strong>Primitive Types:</strong> The most basic data types available. They store the data directly. Examples: `int`, `byte`, `short`, `long`, `float`, `double`, `boolean`, `char`.</li>\n<li><strong>Reference Types:</strong> These variables store a reference (or memory address) to an object. Examples: `String`, Arrays, and any class you create.</li>\n</ul>\n</details>\n</section>\n<section class="scroll-mt-20" id="variables">\n<h2 class="text-3xl font-semibold text-white mb-4 border-b border-gray-700 pb-2">6. Variable Types</h2>\n<details class="bg-white/5 rounded-lg p-4">\n<summary class="font-semibold text-lg cursor-pointer text-white">Types of Variables</summary>\n<ul class="list-disc list-inside mt-2 space-y-1">\n<li><strong>Local Variables:</strong> Declared inside a method. Their scope is limited to that method.</li>\n<li><strong>Instance Variables:</strong> Declared inside a class but outside any method. Each object of the class has its own copy of these variables.</li>\n<li><strong>Class/Static Variables:</strong> Declared with the `static` keyword. There is only one copy of this variable, shared among all objects of the class.</li>\n</ul>\n</details>\n</section>\n<section class="scroll-mt-20" id="modifiers">\n<h2 class="text-3xl font-semibold text-white mb-4 border-b border-gray-700 pb-2">7. Modifier Types</h2>\n<details class="bg-white/5 rounded-lg p-4">\n<summary class="font-semibold text-lg cursor-pointer text-white">Access &amp; Non-Access Modifiers</summary>\n<p class="mt-2">Modifiers are keywords that you add to definitions to change their meanings.</p>\n<ul class="list-disc list-inside mt-2 space-y-1">\n<li><strong>Access Modifiers:</strong> Control the visibility. `public`, `protected`, `default`, `private`.</li>\n<li><strong>Non-Access Modifiers:</strong> Provide other functionality. `static`, `final`, `abstract`, `synchronized`, `volatile`.</li>\n</ul>\n</details>\n</section>\n<section class="scroll-mt-20" id="operators">\n<h2 class="text-3xl font-semibold text-white mb-4 border-b border-gray-700 pb-2">8. Basic Operators</h2>\n<details class="bg-white/5 rounded-lg p-4">\n<summary class="font-semibold text-lg cursor-pointer text-white">Common Operator Types</summary>\n<ul class="list-disc list-inside mt-2 space-y-1">\n<li><strong>Arithmetic:</strong> `+`, `-`, `*`, `/`, `%` (modulus)</li>\n<li><strong>Relational:</strong> `==`, `!=`, `&gt;`, `&lt;`, `&gt;=`, `&lt;=`</li>\n<li><strong>Logical:</strong> `&amp;&amp;` (AND), `||` (OR), `!` (NOT)</li>\n<li><strong>Assignment:</strong> `=`, `+=`, `-=`, `*=`, `/=`</li>\n</ul>\n</details>\n</section>\n<section class="scroll-mt-20" id="loops">\n<h2 class="text-3xl font-semibold text-white mb-4 border-b border-gray-700 pb-2">9. Loop Control</h2>\n<details class="bg-white/5 rounded-lg p-4">\n<summary class="font-semibold text-lg cursor-pointer text-white">Types of Loops</summary>\n<p class="mt-2">Loops are used to execute a block of code repeatedly.</p>\n<ul class="list-disc list-inside mt-2 space-y-1">\n<li><strong>for loop:</strong> Executes a set number of times.</li>\n<li><strong>while loop:</strong> Executes as long as a condition is true.</li>\n<li><strong>do-while loop:</strong> Similar to a while loop, but the code block is executed at least once.</li>\n<li><strong>Enhanced for-each loop:</strong> A simpler way to iterate over arrays or collections.</li>\n</ul>\n</details>\n</section>\n<section class="scroll-mt-20" id="decision">\n<h2 class="text-3xl font-semibold text-white mb-4 border-b border-gray-700 pb-2">10. Decision Making</h2>\n<details class="bg-white/5 rounded-lg p-4">\n<summary class="font-semibold text-lg cursor-pointer text-white">Conditional Statements</summary>\n<ul class="list-disc list-inside mt-2 space-y-1">\n<li><strong>if statement:</strong> Executes code if a condition is true.</li>\n<li><strong>if-else statement:</strong> Executes one block of code if the condition is true, and another if it's false.</li>\n<li><strong>if-else-if ladder:</strong> Used to decide among several alternatives.</li>\n<li><strong>switch statement:</strong> Allows a variable to be tested for equality against a list of values.</li>\n</ul>\n</details>\n</section>\n</div>\n</div>	2025-12-23 11:30:31.745344
cpp	<div class="bg-white/5 dark:bg-gray-800/20 rounded-lg shadow-xl p-8 animate-dynamic backdrop-blur-sm border border-white/10 text-gray-300">\n<h1 class="text-4xl font-bold text-white mb-8 flex items-center"><i class="fas fa-file-code fa-fw mr-4 text-blue-400"></i> C++ Tutorial</h1>\n<div class="space-y-6">\n<!-- Section 1: Overview -->\n<section class="scroll-mt-20" id="overview">\n<h2 class="text-3xl font-semibold text-white mb-4 border-b border-gray-700 pb-2">1. C++ Overview</h2>\n<details class="bg-white/5 rounded-lg p-4" open="">\n<summary class="font-semibold text-lg cursor-pointer text-white">What is C++?</summary>\n<p class="mt-2">C++ is a middle-level programming language developed by Bjarne Stroustrup at Bell Labs, starting in 1979. It was designed as an enhancement to the C language, adding object-oriented features. It is a compiled, statically-typed language known for its high performance.</p>\n</details>\n<details class="bg-white/5 rounded-lg p-4 mt-2">\n<summary class="font-semibold text-lg cursor-pointer text-white">Object-Oriented Programming (OOP)</summary>\n<p class="mt-2">C++ fully supports the four main pillars of object-oriented programming, which help in creating modular, reusable, and manageable code:</p>\n<ul class="list-disc list-inside mt-2 space-y-1">\n<li><strong>Encapsulation:</strong> Bundling data and the functions that operate on that data into a single unit (a class).</li>\n<li><strong>Data Hiding:</strong> Restricting access to certain members of an object to prevent unauthorized access.</li>\n<li><strong>Inheritance:</strong> Creating new classes (derived classes) from existing classes (base classes), enabling code reuse.</li>\n<li><strong>Polymorphism:</strong> The ability to present the same interface for differing underlying forms (data types).</li>\n</ul>\n</details>\n</section>\n<!-- Section 2: Basic Syntax -->\n<section class="scroll-mt-20" id="syntax">\n<h2 class="text-3xl font-semibold text-white mb-4 border-b border-gray-700 pb-2">2. Basic Syntax</h2>\n<details class="bg-white/5 rounded-lg p-4">\n<summary class="font-semibold text-lg cursor-pointer text-white">First C++ Program</summary>\n<p class="mt-2">The entry point for any C++ application is the `main()` function. The `#include <iostream>` directive is used to include the standard input-output stream library.</iostream></p>\n<pre><code class="language-cpp">\n#include <iostream>\n\n// The using namespace std; line tells the compiler to use the standard namespace.\nusing namespace std;\n\n// main() is where program execution begins.\nint main() {\n   cout &lt;&lt; "Hello World"; // prints Hello World\n   return 0;\n}\n                        </iostream></code></pre>\n</details>\n</section>\n<!-- Section 3: Data Types -->\n<section class="scroll-mt-20" id="datatypes">\n<h2 class="text-3xl font-semibold text-white mb-4 border-b border-gray-700 pb-2">3. Data Types</h2>\n<details class="bg-white/5 rounded-lg p-4">\n<summary class="font-semibold text-lg cursor-pointer text-white">Primitive Built-in Types</summary>\n<p class="mt-2">C++ provides a rich set of built-in data types. The most common ones include:</p>\n<ul class="list-disc list-inside mt-2 space-y-1">\n<li><strong>bool:</strong> Stores either `true` or `false`.</li>\n<li><strong>char:</strong> Stores a single character.</li>\n<li><strong>int:</strong> Stores integer values.</li>\n<li><strong>float:</strong> Stores single-precision floating-point numbers.</li>\n<li><strong>double:</strong> Stores double-precision floating-point numbers.</li>\n</ul>\n</details>\n</section>\n<!-- Section 4: Variable Types -->\n<section class="scroll-mt-20" id="variables">\n<h2 class="text-3xl font-semibold text-white mb-4 border-b border-gray-700 pb-2">4. Variable Types</h2>\n<details class="bg-white/5 rounded-lg p-4">\n<summary class="font-semibold text-lg cursor-pointer text-white">Variable Definition and Declaration</summary>\n<p class="mt-2">A variable definition allocates storage for the variable, while a declaration only specifies its name and type. You can declare a variable multiple times, but it can only be defined once.</p>\n<pre><code class="language-cpp">\n// Variable definition and initialization\nint i = 10;\nchar c = 'A';\n\n// Variable declaration (using extern)\nextern int some_external_variable;\n                        </code></pre>\n</details>\n</section>\n<!-- Section 5: Operators -->\n<section class="scroll-mt-20" id="operators">\n<h2 class="text-3xl font-semibold text-white mb-4 border-b border-gray-700 pb-2">5. Operators</h2>\n<details class="bg-white/5 rounded-lg p-4">\n<summary class="font-semibold text-lg cursor-pointer text-white">Common Operator Types</summary>\n<ul class="list-disc list-inside mt-2 space-y-1">\n<li><strong>Arithmetic:</strong> `+`, `-`, `*`, `/`, `%` (modulus)</li>\n<li><strong>Relational:</strong> `==`, `!=`, `&gt;`, `&lt;`, `&gt;=`, `&lt;=`</li>\n<li><strong>Logical:</strong> `&amp;&amp;` (AND), `||` (OR), `!` (NOT)</li>\n<li><strong>Bitwise:</strong> `&amp;` (AND), `|` (OR), `^` (XOR), `~` (NOT), `&lt;&lt;` (left shift), `&gt;&gt;` (right shift)</li>\n</ul>\n</details>\n</section>\n<!-- Section 6: Loops -->\n<section class="scroll-mt-20" id="loops">\n<h2 class="text-3xl font-semibold text-white mb-4 border-b border-gray-700 pb-2">6. Loop Types</h2>\n<details class="bg-white/5 rounded-lg p-4">\n<summary class="font-semibold text-lg cursor-pointer text-white">Types of Loops</summary>\n<p class="mt-2">Loops are used to execute a block of code repeatedly.</p>\n<ul class="list-disc list-inside mt-2 space-y-1">\n<li><strong>for loop:</strong> Executes a known number of times.</li>\n<li><strong>while loop:</strong> Executes as long as a condition remains true. Checks the condition before executing.</li>\n<li><strong>do-while loop:</strong> Similar to a while loop, but the code block is guaranteed to execute at least once before the condition is checked.</li>\n</ul>\n</details>\n</section>\n<!-- Section 7: Decision Making -->\n<section class="scroll-mt-20" id="decision">\n<h2 class="text-3xl font-semibold text-white mb-4 border-b border-gray-700 pb-2">7. Decision Making</h2>\n<details class="bg-white/5 rounded-lg p-4">\n<summary class="font-semibold text-lg cursor-pointer text-white">Conditional Statements</summary>\n<ul class="list-disc list-inside mt-2 space-y-1">\n<li><strong>if statement:</strong> Executes code if a condition is true.</li>\n<li><strong>if-else statement:</strong> Executes one block of code if the condition is true, and another if it's false.</li>\n<li><strong>switch statement:</strong> Allows a variable to be tested for equality against a list of values (`case`).</li>\n</ul>\n</details>\n</section>\n<!-- Section 8: Functions -->\n<section class="scroll-mt-20" id="functions">\n<h2 class="text-3xl font-semibold text-white mb-4 border-b border-gray-700 pb-2">8. Functions</h2>\n<details class="bg-white/5 rounded-lg p-4">\n<summary class="font-semibold text-lg cursor-pointer text-white">Defining and Calling Functions</summary>\n<p class="mt-2">Functions are blocks of code that perform a specific task. They help organize code into manageable and reusable pieces.</p>\n<pre><code class="language-cpp">\n#include <iostream>\n\n// Function declaration (prototype)\nint max(int num1, int num2);\n\nint main() {\n   int a = 100;\n   int b = 200;\n   int ret;\n \n   // Calling the function\n   ret = max(a, b);\n   std::cout &lt;&lt; "Max value is : " &lt;&lt; ret &lt;&lt; std::endl;\n \n   return 0;\n}\n\n// Function definition\nint max(int num1, int num2) {\n   int result;\n \n   if (num1 &gt; num2)\n      result = num1;\n   else\n      result = num2;\n \n   return result; \n}\n                        </iostream></code></pre>\n</details>\n</section>\n<!-- Section 9: Pointers -->\n<section class="scroll-mt-20" id="pointers">\n<h2 class="text-3xl font-semibold text-white mb-4 border-b border-gray-700 pb-2">9. Pointers</h2>\n<details class="bg-white/5 rounded-lg p-4">\n<summary class="font-semibold text-lg cursor-pointer text-white">What Are Pointers?</summary>\n<p class="mt-2">A pointer is a variable whose value is the memory address of another variable. They are essential for dynamic memory allocation and efficient data manipulation in C++.</p>\n<pre><code class="language-cpp">\nint  var = 20;   // An actual variable\nint  *ip;        // A pointer to an integer\n\nip = &amp;var      // Store the address of 'var' in the pointer\n\nstd::cout &lt;&lt; "Value of var: " &lt;&lt; var &lt;&lt; std::endl;\n\n// Access the value using the pointer\nstd::cout &lt;&lt; "Value of *ip: " &lt;&lt; *ip &lt;&lt; std::endl;\n                        </code></pre>\n</details>\n</section>\n<!-- Section 10: Classes & Objects -->\n<section class="scroll-mt-20" id="classes">\n<h2 class="text-3xl font-semibold text-white mb-4 border-b border-gray-700 pb-2">10. Classes and Objects</h2>\n<details class="bg-white/5 rounded-lg p-4">\n<summary class="font-semibold text-lg cursor-pointer text-white">Defining a Class</summary>\n<p class="mt-2">A class is a blueprint for creating objects. It bundles data members (attributes) and member functions (methods) into a single unit.</p>\n<pre><code class="language-cpp">\nclass Box {\n   public:\n      double length;   // Length of a box\n      double breadth;  // Breadth of a box\n      double height;   // Height of a box\n\n      // Member function declaration\n      double getVolume(void);\n};\n\n// Member function definition\ndouble Box::getVolume(void) {\n    return length * breadth * height;\n}\n                        </code></pre>\n</details>\n</section>\n</div>\n</div>	2025-12-23 11:30:31.768518
c	<div class="bg-white/5 dark:bg-gray-800/20 rounded-lg shadow-xl p-8 animate-dynamic backdrop-blur-sm border border-white/10 text-gray-300">\n<h1 class="text-4xl font-bold text-white mb-8 flex items-center"><i class="fas fa-file-code fa-fw mr-4 text-gray-400"></i> C Tutorial</h1>\n<div class="space-y-6">\n<!-- Section 1: Overview -->\n<section class="scroll-mt-20" id="overview">\n<h2 class="text-3xl font-semibold text-white mb-4 border-b border-gray-700 pb-2">1. C Overview</h2>\n<details class="bg-white/5 rounded-lg p-4" open="">\n<summary class="font-semibold text-lg cursor-pointer text-white">What is C?</summary>\n<p class="mt-2">C is a powerful, general-purpose programming language developed by Dennis M. Ritchie at Bell Labs in 1972. It is a procedural language known for its efficiency, low-level memory manipulation, and portability, making it a foundational language for many modern systems and software.</p>\n</details>\n<details class="bg-white/5 rounded-lg p-4 mt-2">\n<summary class="font-semibold text-lg cursor-pointer text-white">Why Use C?</summary>\n<p class="mt-2">C was initially created for system development and produces code that runs nearly as fast as assembly language. It is widely used for:</p>\n<ul class="list-disc list-inside mt-2 space-y-1">\n<li>Operating Systems (UNIX, Linux, Windows kernels)</li>\n<li>Embedded Systems and Device Drivers</li>\n<li>Compilers, Databases, and Language Interpreters</li>\n<li>High-performance computing</li>\n</ul>\n</details>\n</section>\n<!-- Section 2: Basic Syntax -->\n<section class="scroll-mt-20" id="syntax">\n<h2 class="text-3xl font-semibold text-white mb-4 border-b border-gray-700 pb-2">2. Basic Syntax</h2>\n<details class="bg-white/5 rounded-lg p-4">\n<summary class="font-semibold text-lg cursor-pointer text-white">"Hello, World!" Program</summary>\n<p class="mt-2">The entry point for every C program is the `main()` function. The `#include <stdio.h>` is a preprocessor directive that includes the standard input-output library, providing access to functions like `printf()`.</stdio.h></p>\n<pre><code class="language-c">\n#include <stdio.h>\n\nint main() {\n   /* my first program in C */\n   printf("Hello, World! \\n");\n   \n   return 0;\n}\n                        </stdio.h></code></pre>\n</details>\n</section>\n<!-- Section 3: Data Types -->\n<section class="scroll-mt-20" id="datatypes">\n<h2 class="text-3xl font-semibold text-white mb-4 border-b border-gray-700 pb-2">3. Data Types</h2>\n<details class="bg-white/5 rounded-lg p-4">\n<summary class="font-semibold text-lg cursor-pointer text-white">Fundamental Data Types</summary>\n<p class="mt-2">C has a set of basic data types that are used to declare variables. The type of a variable determines its size in memory and the range of values it can hold.</p>\n<ul class="list-disc list-inside mt-2 space-y-1">\n<li><strong>Integer Types:</strong> `int`, `char`, `short`, `long`. These can be modified with `signed` or `unsigned`.</li>\n<li><strong>Floating-Point Types:</strong> `float`, `double`, `long double`. Used for numbers with decimal points.</li>\n<li><strong>The void Type:</strong> Indicates that no value is available. Used for functions that do not return a value or for generic pointers.</li>\n</ul>\n</details>\n</section>\n<!-- Section 4: Variables -->\n<section class="scroll-mt-20" id="variables">\n<h2 class="text-3xl font-semibold text-white mb-4 border-b border-gray-700 pb-2">4. Variables</h2>\n<details class="bg-white/5 rounded-lg p-4">\n<summary class="font-semibold text-lg cursor-pointer text-white">Declaring and Initializing Variables</summary>\n<p class="mt-2">A variable is a name for a storage area. In C, all variables must be declared with a specific type before they are used.</p>\n<pre><code class="language-c">\n// Variable declaration\nint a, b, c;\n\n// Initialization\na = 10;\nchar grade = 'A';\nfloat score = 95.5f;\n                        </code></pre>\n</details>\n</section>\n<!-- Section 5: Constants -->\n<section class="scroll-mt-20" id="constants">\n<h2 class="text-3xl font-semibold text-white mb-4 border-b border-gray-700 pb-2">5. Constants</h2>\n<details class="bg-white/5 rounded-lg p-4">\n<summary class="font-semibold text-lg cursor-pointer text-white">Defining Constants</summary>\n<p class="mt-2">Constants are fixed values that do not change. They can be defined using the `#define` preprocessor directive or the `const` keyword.</p>\n<pre><code class="language-c">\n#include <stdio.h>\n\n#define PI 3.14159\nconst int MAX_USERS = 100;\n\nint main() {\n   printf("Value of PI: %f\\n", PI);\n   printf("Max users: %d\\n", MAX_USERS);\n   return 0;\n}\n                        </stdio.h></code></pre>\n</details>\n</section>\n<!-- Section 6: Operators -->\n<section class="scroll-mt-20" id="operators">\n<h2 class="text-3xl font-semibold text-white mb-4 border-b border-gray-700 pb-2">6. Operators</h2>\n<details class="bg-white/5 rounded-lg p-4">\n<summary class="font-semibold text-lg cursor-pointer text-white">Common C Operators</summary>\n<ul class="list-disc list-inside mt-2 space-y-1">\n<li><strong>Arithmetic:</strong> `+`, `-`, `*`, `/`, `%` (modulus)</li>\n<li><strong>Relational:</strong> `==`, `!=`, `&gt;`, `&lt;`, `&gt;=`, `&lt;=`</li>\n<li><strong>Logical:</strong> `&amp;&amp;` (AND), `||` (OR), `!` (NOT)</li>\n<li><strong>Bitwise:</strong> `&amp;`, `|`, `^`, `~`, `&lt;&lt;`, `&gt;&gt;`</li>\n</ul>\n</details>\n</section>\n<!-- Section 7: Decision Making -->\n<section class="scroll-mt-20" id="decision">\n<h2 class="text-3xl font-semibold text-white mb-4 border-b border-gray-700 pb-2">7. Decision Making</h2>\n<details class="bg-white/5 rounded-lg p-4">\n<summary class="font-semibold text-lg cursor-pointer text-white">Conditional Logic</summary>\n<p class="mt-2">Control the flow of your program with conditional statements.</p>\n<ul class="list-disc list-inside mt-2 space-y-1">\n<li><strong>if-else:</strong> Execute different blocks of code based on a condition.</li>\n<li><strong>switch:</strong> Select one of many code blocks to be executed based on a variable's value.</li>\n</ul>\n</details>\n</section>\n<!-- Section 8: Loops -->\n<section class="scroll-mt-20" id="loops">\n<h2 class="text-3xl font-semibold text-white mb-4 border-b border-gray-700 pb-2">8. Loops</h2>\n<details class="bg-white/5 rounded-lg p-4">\n<summary class="font-semibold text-lg cursor-pointer text-white">Executing Code Repeatedly</summary>\n<ul class="list-disc list-inside mt-2 space-y-1">\n<li><strong>for loop:</strong> Best used when the number of iterations is known.</li>\n<li><strong>while loop:</strong> Repeats as long as a condition is true.</li>\n<li><strong>do-while loop:</strong> Guarantees the loop body is executed at least once.</li>\n</ul>\n</details>\n</section>\n<!-- Section 9: Functions -->\n<section class="scroll-mt-20" id="functions">\n<h2 class="text-3xl font-semibold text-white mb-4 border-b border-gray-700 pb-2">9. Functions</h2>\n<details class="bg-white/5 rounded-lg p-4">\n<summary class="font-semibold text-lg cursor-pointer text-white">Modular Code with Functions</summary>\n<p class="mt-2">Functions are blocks of code that perform a specific task and can be reused throughout a program.</p>\n</details>\n</section>\n<!-- Section 10: Arrays -->\n<section class="scroll-mt-20" id="arrays">\n<h2 class="text-3xl font-semibold text-white mb-4 border-b border-gray-700 pb-2">10. Arrays</h2>\n<details class="bg-white/5 rounded-lg p-4">\n<summary class="font-semibold text-lg cursor-pointer text-white">Storing Data Collections</summary>\n<p class="mt-2">Arrays store a fixed-size sequence of elements of the same data type.</p>\n<pre><code class="language-c">\nint numbers[5] = {10, 20, 30, 40, 50};\n                        </code></pre>\n</details>\n</section>\n<!-- Section 11: Pointers -->\n<section class="scroll-mt-20" id="pointers">\n<h2 class="text-3xl font-semibold text-white mb-4 border-b border-gray-700 pb-2">11. Pointers</h2>\n<details class="bg-white/5 rounded-lg p-4">\n<summary class="font-semibold text-lg cursor-pointer text-white">Working with Memory Addresses</summary>\n<p class="mt-2">A pointer is a variable that stores the memory address of another variable, enabling direct memory access.</p>\n<pre><code class="language-c">\nint var = 20;\nint *ip = &amp;var // ip now holds the address of var\n                        </code></pre>\n</details>\n</section>\n<!-- Section 12: Strings -->\n<section class="scroll-mt-20" id="strings">\n<h2 class="text-3xl font-semibold text-white mb-4 border-b border-gray-700 pb-2">12. Strings</h2>\n<details class="bg-white/5 rounded-lg p-4">\n<summary class="font-semibold text-lg cursor-pointer text-white">Strings as Character Arrays</summary>\n<p class="mt-2">In C, strings are represented as arrays of characters ending with a null character (`\\0`).</p>\n<pre><code class="language-c">\nchar greeting[] = "Hello";\n                        </code></pre>\n</details>\n</section>\n<!-- Section 13: Structures -->\n<section class="scroll-mt-20" id="structures">\n<h2 class="text-3xl font-semibold text-white mb-4 border-b border-gray-700 pb-2">13. Structures</h2>\n<details class="bg-white/5 rounded-lg p-4">\n<summary class="font-semibold text-lg cursor-pointer text-white">Complex Data Types</summary>\n<p class="mt-2">Structures (`struct`) allow you to group variables of different data types under a single name.</p>\n<pre><code class="language-c">\nstruct Book {\n   char  title[50];\n   char  author[50];\n   int   book_id;\n};\n                        </code></pre>\n</details>\n</section>\n</div>\n</div>	2025-12-23 11:30:31.782712
sql	<div class="bg-white/5 dark:bg-gray-800/20 rounded-lg shadow-xl p-8 animate-dynamic backdrop-blur-sm border border-white/10 text-gray-300">\n<h1 class="text-4xl font-bold text-white mb-8 flex items-center"><i class="fas fa-database fa-fw mr-4 text-teal-400"></i> SQL Tutorial</h1>\n<div class="space-y-6">\n<!-- Section 1: Overview -->\n<section class="scroll-mt-20" id="overview">\n<h2 class="text-3xl font-semibold text-white mb-4 border-b border-gray-700 pb-2">1. SQL Overview</h2>\n<details class="bg-white/5 rounded-lg p-4" open="">\n<summary class="font-semibold text-lg cursor-pointer text-white">What is SQL?</summary>\n<p class="mt-2">SQL stands for Structured Query Language. It is the standard language for relational database management systems (RDBMS). SQL is used to perform operations such as creating databases, inserting data, fetching data, modifying data, and deleting data.</p>\n</details>\n<details class="bg-white/5 rounded-lg p-4 mt-2">\n<summary class="font-semibold text-lg cursor-pointer text-white">SQL Commands</summary>\n<p class="mt-2">SQL commands are broadly categorized into the following types:</p>\n<ul class="list-disc list-inside mt-2 space-y-1">\n<li><strong>DDL (Data Definition Language):</strong> Used to define the database structure. Examples: `CREATE`, `ALTER`, `DROP`.</li>\n<li><strong>DML (Data Manipulation Language):</strong> Used for managing data within schema objects. Examples: `SELECT`, `INSERT`, `UPDATE`, `DELETE`.</li>\n<li><strong>DCL (Data Control Language):</strong> Used to control access to data. Examples: `GRANT`, `REVOKE`.</li>\n</ul>\n</details>\n</section>\n<!-- Section 2: Basic Syntax -->\n<section class="scroll-mt-20" id="syntax">\n<h2 class="text-3xl font-semibold text-white mb-4 border-b border-gray-700 pb-2">2. Basic Syntax</h2>\n<details class="bg-white/5 rounded-lg p-4">\n<summary class="font-semibold text-lg cursor-pointer text-white">Key Syntax Rules</summary>\n<p class="mt-2">SQL statements are built using a standard set of keywords and follow a specific structure. Here are some fundamental rules:</p>\n<ul class="list-disc list-inside mt-2 space-y-1">\n<li>SQL is case-insensitive, meaning `SELECT` is the same as `select`. However, table and column names can be case-sensitive depending on the RDBMS.</li>\n<li>Statements are terminated with a semicolon (;).</li>\n<li>Keywords like `SELECT`, `FROM`, and `WHERE` are used to structure queries.</li>\n</ul>\n</details>\n</section>\n<!-- Section 3: Data Types -->\n<section class="scroll-mt-20" id="datatypes">\n<h2 class="text-3xl font-semibold text-white mb-4 border-b border-gray-700 pb-2">3. Data Types</h2>\n<details class="bg-white/5 rounded-lg p-4">\n<summary class="font-semibold text-lg cursor-pointer text-white">Common Data Types</summary>\n<p class="mt-2">Each column in a database table requires a name and a data type. Common SQL data types include:</p>\n<ul class="list-disc list-inside mt-2 space-y-1">\n<li><strong>Numeric Types:</strong> `INT`, `BIGINT`, `DECIMAL(p, s)`, `FLOAT`.</li>\n<li><strong>Date and Time Types:</strong> `DATE`, `TIME`, `DATETIME`, `TIMESTAMP`.</li>\n<li><strong>Character String Types:</strong> `CHAR(n)`, `VARCHAR(n)`, `TEXT`.</li>\n</ul>\n</details>\n</section>\n<!-- Section 4: Operators -->\n<section class="scroll-mt-20" id="operators">\n<h2 class="text-3xl font-semibold text-white mb-4 border-b border-gray-700 pb-2">4. Operators</h2>\n<details class="bg-white/5 rounded-lg p-4">\n<summary class="font-semibold text-lg cursor-pointer text-white">Types of Operators</summary>\n<p class="mt-2">Operators are used in the `WHERE` clause to perform comparisons and logical operations.</p>\n<ul class="list-disc list-inside mt-2 space-y-1">\n<li><strong>Arithmetic Operators:</strong> `+`, `-`, `*`, `/`, `%`.</li>\n<li><strong>Comparison Operators:</strong> `=`, `!=`, `&gt;`, `&lt;`, `&gt;=`, `&lt;=`.</li>\n<li><strong>Logical Operators:</strong> `AND`, `OR`, `NOT`, `IN`, `BETWEEN`, `LIKE`.</li>\n</ul>\n</details>\n</section>\n<!-- Section 5: CREATE Database -->\n<section class="scroll-mt-20" id="create-db">\n<h2 class="text-3xl font-semibold text-white mb-4 border-b border-gray-700 pb-2">5. CREATE Database</h2>\n<details class="bg-white/5 rounded-lg p-4">\n<summary class="font-semibold text-lg cursor-pointer text-white">Creating a Database</summary>\n<p class="mt-2">This command is used to create a new database in the RDBMS.</p>\n<pre><code class="language-sql">\nCREATE DATABASE TestDB;\n                        </code></pre>\n</details>\n</section>\n<!-- Section 6: CREATE Table -->\n<section class="scroll-mt-20" id="create-table">\n<h2 class="text-3xl font-semibold text-white mb-4 border-b border-gray-700 pb-2">6. CREATE Table</h2>\n<details class="bg-white/5 rounded-lg p-4">\n<summary class="font-semibold text-lg cursor-pointer text-white">Creating a Table</summary>\n<p class="mt-2">This command creates a new table within a database. You must define each column's name and data type.</p>\n<pre><code class="language-sql">\nCREATE TABLE Customers (\n    ID   INT              NOT NULL,\n    NAME VARCHAR (20)     NOT NULL,\n    AGE  INT              NOT NULL,\n    ADDRESS  CHAR (25),\n    SALARY   DECIMAL (18, 2),       \n    PRIMARY KEY (ID)\n);\n                        </code></pre>\n</details>\n</section>\n<!-- Section 7: INSERT Query -->\n<section class="scroll-mt-20" id="insert">\n<h2 class="text-3xl font-semibold text-white mb-4 border-b border-gray-700 pb-2">7. INSERT INTO Query</h2>\n<details class="bg-white/5 rounded-lg p-4">\n<summary class="font-semibold text-lg cursor-pointer text-white">Adding New Records</summary>\n<p class="mt-2">The `INSERT INTO` statement is used to add new rows of data to a table.</p>\n<pre><code class="language-sql">\nINSERT INTO Customers (ID, NAME, AGE, ADDRESS, SALARY)\nVALUES (1, 'Ramesh', 32, 'Ahmedabad', 2000.00);\n                        </code></pre>\n</details>\n</section>\n<!-- Section 8: SELECT Query -->\n<section class="scroll-mt-20" id="select">\n<h2 class="text-3xl font-semibold text-white mb-4 border-b border-gray-700 pb-2">8. SELECT Query</h2>\n<details class="bg-white/5 rounded-lg p-4">\n<summary class="font-semibold text-lg cursor-pointer text-white">Retrieving Data</summary>\n<p class="mt-2">The `SELECT` statement is used to fetch data from a database. You can select specific columns or all columns using `*`.</p>\n<pre><code class="language-sql">\n-- Select specific columns\nSELECT NAME, SALARY FROM Customers;\n\n-- Select all columns\nSELECT * FROM Customers;\n                        </code></pre>\n</details>\n</section>\n<!-- Section 9: WHERE Clause -->\n<section class="scroll-mt-20" id="where">\n<h2 class="text-3xl font-semibold text-white mb-4 border-b border-gray-700 pb-2">9. WHERE Clause</h2>\n<details class="bg-white/5 rounded-lg p-4">\n<summary class="font-semibold text-lg cursor-pointer text-white">Filtering Records</summary>\n<p class="mt-2">The `WHERE` clause is used to filter records and extract only those that fulfill a specified condition.</p>\n<pre><code class="language-sql">\nSELECT ID, NAME, SALARY\nFROM Customers\nWHERE SALARY &gt; 2000;\n                        </code></pre>\n</details>\n</section>\n<!-- Section 10: UPDATE Query -->\n<section class="scroll-mt-20" id="update">\n<h2 class="text-3xl font-semibold text-white mb-4 border-b border-gray-700 pb-2">10. UPDATE Query</h2>\n<details class="bg-white/5 rounded-lg p-4">\n<summary class="font-semibold text-lg cursor-pointer text-white">Modifying Records</summary>\n<p class="mt-2">The `UPDATE` statement is used to modify existing records in a table.</p>\n<pre><code class="language-sql">\nUPDATE Customers\nSET ADDRESS = 'Pune'\nWHERE ID = 6;\n                        </code></pre>\n</details>\n</section>\n<!-- Section 11: DELETE Query -->\n<section class="scroll-mt-20" id="delete">\n<h2 class="text-3xl font-semibold text-white mb-4 border-b border-gray-700 pb-2">11. DELETE Query</h2>\n<details class="bg-white/5 rounded-lg p-4">\n<summary class="font-semibold text-lg cursor-pointer text-white">Deleting Records</summary>\n<p class="mt-2">The `DELETE` statement is used to delete existing records from a table.</p>\n<pre><code class="language-sql">\nDELETE FROM Customers\nWHERE ID = 6;\n                        </code></pre>\n</details>\n</section>\n<!-- Section 12: Joins -->\n<section class="scroll-mt-20" id="joins">\n<h2 class="text-3xl font-semibold text-white mb-4 border-b border-gray-700 pb-2">12. Joins</h2>\n<details class="bg-white/5 rounded-lg p-4">\n<summary class="font-semibold text-lg cursor-pointer text-white">Combining Tables</summary>\n<p class="mt-2">A `JOIN` clause is used to combine rows from two or more tables based on a related column between them.</p>\n<pre><code class="language-sql">\nSELECT C.ID, C.NAME, O.AMOUNT\nFROM Customers AS C\nINNER JOIN Orders AS O\nON C.ID = O.CUSTOMER_ID;\n                        </code></pre>\n</details>\n</section>\n<!-- Section 13: Unions -->\n<section class="scroll-mt-20" id="unions">\n<h2 class="text-3xl font-semibold text-white mb-4 border-b border-gray-700 pb-2">13. Unions</h2>\n<details class="bg-white/5 rounded-lg p-4">\n<summary class="font-semibold text-lg cursor-pointer text-white">Combining Result Sets</summary>\n<p class="mt-2">The `UNION` operator is used to combine the result-set of two or more `SELECT` statements. It removes duplicate rows between the various `SELECT` statements.</p>\n<pre><code class="language-sql">\nSELECT City FROM Customers\nUNION\nSELECT City FROM Suppliers\nORDER BY City;\n                        </code></pre>\n</details>\n</section>\n</div>\n</div>	2025-12-23 11:30:31.795327
dbms	<div class="bg-white/5 dark:bg-gray-800/20 rounded-lg shadow-xl p-8 animate-dynamic backdrop-blur-sm border border-white/10 text-gray-300">\n<h1 class="text-4xl font-bold text-white mb-8 flex items-center"><i class="fas fa-server fa-fw mr-4 text-purple-400"></i> DBMS Tutorial</h1>\n<div class="space-y-6">\n<!-- Section 1: Overview -->\n<section class="scroll-mt-20" id="overview">\n<h2 class="text-3xl font-semibold text-white mb-4 border-b border-gray-700 pb-2">1. DBMS Overview</h2>\n<details class="bg-white/5 rounded-lg p-4" open="">\n<summary class="font-semibold text-lg cursor-pointer text-white">What is a DBMS?</summary>\n<p class="mt-2">A Database Management System (DBMS) is software for storing and retrieving user data while considering appropriate security measures. It consists of a group of programs that manipulate the database. The DBMS accepts requests for data from an application and instructs the operating system to provide the specific data.</p>\n</details>\n</section>\n<!-- Section 2: Architecture -->\n<section class="scroll-mt-20" id="architecture">\n<h2 class="text-3xl font-semibold text-white mb-4 border-b border-gray-700 pb-2">2. DBMS Architecture</h2>\n<details class="bg-white/5 rounded-lg p-4">\n<summary class="font-semibold text-lg cursor-pointer text-white">The 3-Tier Architecture</summary>\n<p class="mt-2">The design of a DBMS depends on its architecture. The 3-tier architecture, which is the most widely used, separates the system into three independent modules:</p>\n<ul class="list-disc list-inside mt-2 space-y-1">\n<li><strong>Presentation Tier (Client):</strong> The top-most level of the application, where users interact directly with the system.</li>\n<li><strong>Application Tier (Business Logic):</strong> This tier contains the functional business logic that drives the application's core processes.</li>\n<li><strong>Data Tier (Database):</strong> At this tier, the database, along with its query processing languages, resides.</li>\n</ul>\n</details>\n</section>\n<!-- Section 3: Data Models -->\n<section class="scroll-mt-20" id="models">\n<h2 class="text-3xl font-semibold text-white mb-4 border-b border-gray-700 pb-2">3. Data Models</h2>\n<details class="bg-white/5 rounded-lg p-4">\n<summary class="font-semibold text-lg cursor-pointer text-white">Structuring the Data</summary>\n<p class="mt-2">Data models define how the logical structure of a database is modeled. The most common is the Relational Model, which uses tables to represent data and the relationships between them. Each table has rows (records) and columns (attributes).</p>\n</details>\n</section>\n<!-- Section 4: Data Schemas -->\n<section class="scroll-mt-20" id="schemas">\n<h2 class="text-3xl font-semibold text-white mb-4 border-b border-gray-700 pb-2">4. Data Schemas</h2>\n<details class="bg-white/5 rounded-lg p-4">\n<summary class="font-semibold text-lg cursor-pointer text-white">Database Design</summary>\n<p class="mt-2">A database schema is the skeleton structure that represents the logical view of the entire database. It defines how the data is organized and how the relations among them are associated. It formulates all the constraints that are to be applied on the data.</p>\n</details>\n</section>\n<!-- Section 5: E-R Model -->\n<section class="scroll-mt-20" id="er-model">\n<h2 class="text-3xl font-semibold text-white mb-4 border-b border-gray-700 pb-2">5. Entity-Relationship (E-R) Model</h2>\n<details class="bg-white/5 rounded-lg p-4">\n<summary class="font-semibold text-lg cursor-pointer text-white">Conceptual Data Modeling</summary>\n<p class="mt-2">The E-R model is a high-level data model that defines the conceptual view of a database. It is based on the notion of real-world entities and the relationships between them. E-R diagrams are used to illustrate the logical structure of databases.</p>\n</details>\n</section>\n<!-- Section 6: Normalization -->\n<section class="scroll-mt-20" id="normalization">\n<h2 class="text-3xl font-semibold text-white mb-4 border-b border-gray-700 pb-2">6. Normalization</h2>\n<details class="bg-white/5 rounded-lg p-4">\n<summary class="font-semibold text-lg cursor-pointer text-white">Minimizing Redundancy</summary>\n<p class="mt-2">Normalization is the process of organizing data in a database to avoid data redundancy, insertion anomaly, update anomaly &amp; deletion anomaly. It involves dividing larger tables into smaller, well-structured tables and defining relationships between them.</p>\n</details>\n</section>\n<!-- Section 7: Transactions -->\n<section class="scroll-mt-20" id="transactions">\n<h2 class="text-3xl font-semibold text-white mb-4 border-b border-gray-700 pb-2">7. Transactions &amp; ACID Properties</h2>\n<details class="bg-white/5 rounded-lg p-4">\n<summary class="font-semibold text-lg cursor-pointer text-white">Ensuring Data Integrity</summary>\n<p class="mt-2">A transaction is a unit of work performed against a database. Transactions are designed to maintain data integrity through the ACID properties:</p>\n<ul class="list-disc list-inside mt-2 space-y-1">\n<li><strong>Atomicity:</strong> All changes are performed, or none are.</li>\n<li><strong>Consistency:</strong> The database remains in a valid state.</li>\n<li><strong>Isolation:</strong> Concurrent transactions do not interfere with each other.</li>\n<li><strong>Durability:</strong> Committed changes are permanent.</li>\n</ul>\n</details>\n</section>\n</div>\n</div>	2025-12-23 11:30:31.80456
plsql	<div class="bg-white/5 dark:bg-gray-800/20 rounded-lg shadow-xl p-8 animate-dynamic backdrop-blur-sm border border-white/10 text-gray-300">\n<h1 class="text-4xl font-bold text-white mb-8 flex items-center"><i class="fas fa-cogs fa-fw mr-4 text-red-400"></i> PL/SQL Tutorial</h1>\n<div class="space-y-6">\n<!-- Section 1: Overview -->\n<section class="scroll-mt-20" id="overview">\n<h2 class="text-3xl font-semibold text-white mb-4 border-b border-gray-700 pb-2">1. What is PL/SQL?</h2>\n<details class="bg-white/5 rounded-lg p-4" open="">\n<summary class="font-semibold text-lg cursor-pointer text-white">Procedural Language for SQL</summary>\n<p class="mt-2">PL/SQL (Procedural Language for SQL) is Oracle Corporation's procedural extension for SQL and the Oracle relational database. It allows developers to combine the power of SQL with procedural statements like loops, conditions, and exception handling, enabling the creation of complex business logic directly within the database.</p>\n</details>\n</section>\n<!-- Section 2: Block Structure -->\n<section class="scroll-mt-20" id="structure">\n<h2 class="text-3xl font-semibold text-white mb-4 border-b border-gray-700 pb-2">2. PL/SQL Block Structure</h2>\n<details class="bg-white/5 rounded-lg p-4">\n<summary class="font-semibold text-lg cursor-pointer text-white">The Anonymous Block</summary>\n<p class="mt-2">PL/SQL code is organized into blocks. A block has three parts: a declarative part, an executable part, and an exception-handling part.</p>\n<pre><code class="language-sql">\nDECLARE\n   -- (Optional) Variables, constants, cursors, etc. are declared here.\n   message VARCHAR2(20) := 'Hello, World!';\nBEGIN\n   -- (Required) Statements to be executed.\n   DBMS_OUTPUT.PUT_LINE(message);\nEXCEPTION\n   -- (Optional) Actions to perform when errors occur.\n   WHEN OTHERS THEN\n      DBMS_OUTPUT.PUT_LINE('An error occurred');\nEND;\n/\n                        </code></pre>\n</details>\n</section>\n<!-- Section 3: Variables & Types -->\n<section class="scroll-mt-20" id="variables">\n<h2 class="text-3xl font-semibold text-white mb-4 border-b border-gray-700 pb-2">3. Variables &amp; Data Types</h2>\n<details class="bg-white/5 rounded-lg p-4">\n<summary class="font-semibold text-lg cursor-pointer text-white">Declaring Variables</summary>\n<p class="mt-2">Variables must be declared in the DECLARE section. A powerful feature is the ability to anchor a variable's type to a database column using `%TYPE`.</p>\n<pre><code class="language-sql">\nDECLARE\n   -- Standard variable declaration\n   v_employee_count NUMBER;\n\n   -- Anchored declaration\n   v_employee_name employees.first_name%TYPE;\nBEGIN\n   SELECT first_name INTO v_employee_name\n   FROM employees\n   WHERE employee_id = 100;\nEND;\n/\n                        </code></pre>\n</details>\n</section>\n<!-- Section 4: Cursors -->\n<section class="scroll-mt-20" id="cursors">\n<h2 class="text-3xl font-semibold text-white mb-4 border-b border-gray-700 pb-2">4. Cursors</h2>\n<details class="bg-white/5 rounded-lg p-4">\n<summary class="font-semibold text-lg cursor-pointer text-white">Handling Multi-Row Queries</summary>\n<p class="mt-2">A cursor is a pointer to a private SQL area that stores information about processing a specific `SELECT` statement. Cursors are used to handle the result set of a query that returns multiple rows, allowing you to process each row individually.</p>\n</details>\n</section>\n<!-- Section 5: Stored Procedures -->\n<section class="scroll-mt-20" id="procedures">\n<h2 class="text-3xl font-semibold text-white mb-4 border-b border-gray-700 pb-2">5. Stored Procedures</h2>\n<details class="bg-white/5 rounded-lg p-4">\n<summary class="font-semibold text-lg cursor-pointer text-white">Reusable Code Blocks</summary>\n<p class="mt-2">A stored procedure is a named PL/SQL block which performs one or more specific tasks. It is stored in the database and can be executed by other applications or database users, promoting code reusability and security.</p>\n</details>\n</section>\n</div>\n</div>	2025-12-23 11:30:31.814856
mysql	<div class="bg-white/5 dark:bg-gray-800/20 rounded-lg shadow-xl p-8 animate-dynamic backdrop-blur-sm border border-white/10 text-gray-300">\n<h1 class="text-4xl font-bold text-white mb-8 flex items-center"><i class="fas fa-database fa-fw mr-4 text-cyan-400"></i> MySQL Tutorial</h1>\n<div class="space-y-6">\n<!-- Section 1: Overview -->\n<section class="scroll-mt-20" id="overview">\n<h2 class="text-3xl font-semibold text-white mb-4 border-b border-gray-700 pb-2">1. What is MySQL?</h2>\n<details class="bg-white/5 rounded-lg p-4" open="">\n<summary class="font-semibold text-lg cursor-pointer text-white">The World's Most Popular Open Source Database</summary>\n<p class="mt-2">MySQL is an open-source relational database management system (RDBMS). It is a core component of the LAMP (Linux, Apache, MySQL, PHP) web application software stack. MySQL is known for its reliability, performance, and ease of use, making it a popular choice for web applications, from small projects to large-scale enterprise systems.</p>\n</details>\n</section>\n<!-- Section 2: Data Types -->\n<section class="scroll-mt-20" id="datatypes">\n<h2 class="text-3xl font-semibold text-white mb-4 border-b border-gray-700 pb-2">2. Common Data Types</h2>\n<details class="bg-white/5 rounded-lg p-4">\n<summary class="font-semibold text-lg cursor-pointer text-white">MySQL Data Types</summary>\n<p class="mt-2">MySQL supports a wide range of SQL data types. Some of the most common include:</p>\n<ul class="list-disc list-inside mt-2 space-y-1">\n<li><strong>INT:</strong> A standard integer.</li>\n<li><strong>VARCHAR(size):</strong> A variable-length string.</li>\n<li><strong>TEXT:</strong> For long-form text strings.</li>\n<li><strong>DATE:</strong> Stores a date in YYYY-MM-DD format.</li>\n<li><strong>DATETIME:</strong> Stores a date and time in YYYY-MM-DD HH:MI:SS format.</li>\n<li><strong>TIMESTAMP:</strong> Automatically updated to the current timestamp when a row is modified.</li>\n</ul>\n</details>\n</section>\n<!-- Section 3: Storage Engines -->\n<section class="scroll-mt-20" id="engines">\n<h2 class="text-3xl font-semibold text-white mb-4 border-b border-gray-700 pb-2">3. Storage Engines</h2>\n<details class="bg-white/5 rounded-lg p-4">\n<summary class="font-semibold text-lg cursor-pointer text-white">InnoDB vs. MyISAM</summary>\n<p class="mt-2">MySQL uses storage engines to handle the SQL operations for different table types. The two most common engines are:</p>\n<ul class="list-disc list-inside mt-2 space-y-1">\n<li><strong>InnoDB:</strong> The default storage engine. It is transaction-safe (ACID compliant) and supports foreign keys. Best for data-critical applications.</li>\n<li><strong>MyISAM:</strong> A simpler engine that does not support transactions or foreign keys. It is generally faster for read-heavy operations, such as in data warehousing.</li>\n</ul>\n</details>\n</section>\n<!-- Section 4: CRUD Operations -->\n<section class="scroll-mt-20" id="crud">\n<h2 class="text-3xl font-semibold text-white mb-4 border-b border-gray-700 pb-2">4. Basic CRUD Operations</h2>\n<details class="bg-white/5 rounded-lg p-4">\n<summary class="font-semibold text-lg cursor-pointer text-white">Create, Read, Update, Delete</summary>\n<p class="mt-2">These four basic functions of persistent storage are the bread and butter of database management.</p>\n<pre><code class="language-sql">\n-- CREATE (Insert a new record)\nINSERT INTO users (name, email) VALUES ('John Doe', 'john.doe@example.com');\n\n-- READ (Select records)\nSELECT * FROM users WHERE name = 'John Doe';\n\n-- UPDATE (Modify a record)\nUPDATE users SET email = 'johndoe@newemail.com' WHERE name = 'John Doe';\n\n-- DELETE (Remove a record)\nDELETE FROM users WHERE name = 'John Doe';\n                        </code></pre>\n</details>\n</section>\n</div>\n</div>	2025-12-23 11:30:31.823542
\.


--
-- Data for Name: message; Type: TABLE DATA; Schema: public; Owner: sourcepoint_admin
--

COPY public.message (id, sender_id, recipient_id, body, "timestamp") FROM stdin;
1	1	12	Hi Bhavesh 	2025-10-15 14:23:58.232334
2	1	4	HI	2025-11-23 14:44:51.248397
3	1	15	hello 	2025-11-25 12:59:16.183905
4	1	15	hi	2025-12-27 03:17:47.65106
5	2	15	hi	2025-12-28 11:01:36.551991
\.


--
-- Data for Name: moderator_assignment_history; Type: TABLE DATA; Schema: public; Owner: sourcepoint_admin
--

COPY public.moderator_assignment_history (id, candidate_id, moderator_id, problem_statement_id, assigned_at) FROM stdin;
1	3	4	3	2025-10-22 05:00:46.173587
2	12	6	3	2025-10-24 12:39:58.752249
3	12	6	3	2025-10-25 06:56:51.041752
4	3	4	1	2025-12-25 17:35:06.968982
5	3	4	1	2025-12-26 14:22:51.950981
6	3	4	1	2025-12-29 05:47:25.524822
\.


--
-- Data for Name: order; Type: TABLE DATA; Schema: public; Owner: sourcepoint_admin
--

COPY public."order" (id, order_number, user_id, total_amount, status, shipping_address, created_at, billing_address, seller_id, shipping_street, shipping_city, shipping_state, shipping_zip, shipping_country) FROM stdin;
9	ORD-1764497289-16	16	5098.00	Order Delivered	A-601, Nisarg Pooja\r\nWakad , 411057	2025-11-30 10:08:09.722509	A-601, Nisarg Pooja\r\nWakad , 411057	\N	\N	\N	\N	\N	\N
7	ORD-1764159493-17	17	198.00	Order Delivered	Karan Muktangan,\r\nKashid park ,Pimpri Gurav	2025-11-26 12:18:13.20636	Karan Muktangan,\r\nKashid park ,Pimpri Gurav	\N	\N	\N	\N	\N	\N
11	ORD-1764765318-18	18	319.00	Order Delivered	Tathawade,\r\nPune , 411033 , Maharashtra,\r\nIndia\r\n	2025-12-03 12:35:18.905677	Tathawade,\r\nPune , 411033 , Maharashtra,\r\nIndia\r\n	\N	\N	\N	\N	\N	\N
8	ORD-1764164143-15	15	2048.00	Order Delivered	sdvv	2025-11-26 13:35:43.708809	sdvv	\N	\N	\N	\N	\N	\N
6	ORD-1764080314-15	15	599.00	Order Delivered	Nisarg Pooja\r\nWakad \r\n411057	2025-11-25 14:18:34.800674	Nisarg Pooja\r\nWakad \r\n411057	\N	\N	\N	\N	\N	\N
5	ORD-1764073163-15	15	2500.00	Order Delivered	ewf	2025-11-25 12:19:23.056121	wef	\N	\N	\N	\N	\N	\N
2	ORD-1763811665-15	15	450.00	Order Delivered	Plot no 1 , block no 9 \r\nJalgaon , \r\n425001	2025-11-22 11:41:05.43825	Plot no 1 , block no 9 \r\nJalgaon , \r\n425001	\N	\N	\N	\N	\N	\N
1	ORD-1763810116-15	15	450.00	Order Delivered	Plot no 1 , blopck no 9	2025-11-22 11:15:16.924545	\N	\N	\N	\N	\N	\N	\N
10	ORD-1764653957-15	15	4296.00	Order Delivered	PLpot ono 1 , \r\ncloblc mno 90 \r\nishwar colony \r\njalghaon	2025-12-02 05:39:17.394579	PLpot ono 1 , \r\ncloblc mno 90 \r\nishwar colony \r\njalghaon	\N	\N	\N	\N	\N	\N
12	ORD20250012	16	18398.00	Order Accepted	eujwblieuwabfew	2025-12-18 13:20:18.223842	eujwblieuwabfew	20	\N	\N	\N	\N	\N
16	ORD-1766209863-15	15	699.00	Order Delivered	hjjhhjjh	2025-12-20 05:51:03.220312	hjjh	\N	\N	\N	\N	\N	\N
15	ORD20250015	15	3599.00	Order Delivered	fev	2025-12-20 05:48:41.578568	fev	20	\N	\N	\N	\N	\N
14	ORD20250014	15	215.00	Order Delivered	ewfawefe	2025-12-20 05:44:39.296372	ewfawefe	20	\N	\N	\N	\N	\N
21	ORD-1766986920-15	15	26990.00	Order Accepted	test address 	2025-12-29 05:42:00.87746	test address 	\N	\N	\N	\N	\N	\N
20	ORD-1766986664-15	15	53980.00	Payment Received	ds	2025-12-29 05:37:44.48458	ass	\N	\N	\N	\N	\N	\N
13	ORD20250013	15	3599.00	Payment Received	hjwqkSVDHJQWBVC	2025-12-20 05:32:39.580988	hjwqkSVDHJQWBVC	20	\N	\N	\N	\N	\N
3	ORD-1763894906-16	16	3850.00	Payment Received	Nisarg Pooja	2025-11-23 10:48:26.446343	Nisarg Pooja	\N	\N	\N	\N	\N	\N
4	ORD-1763913161-15	15	4147.00	Payment Received	plopt no 1 	2025-11-23 15:52:41.184216	plopt no 1 	\N	\N	\N	\N	\N	\N
\.


--
-- Data for Name: order_item; Type: TABLE DATA; Schema: public; Owner: sourcepoint_admin
--

COPY public.order_item (id, order_id, product_name, quantity, price_at_purchase) FROM stdin;
1	1	Gaming Mouse	1	450.00
2	2	Gaming Mouse	1	450.00
3	3	Gaming Mouse	3	450.00
4	3	HP Mouse	1	2500.00
5	4	NOBERO Men's Oversized Solid Loose fit Heavy Cotton T-Shirt (Pack of 2)	1	1349.00
6	4	Nobero Oversized Hoodies for Man Stylish	2	1399.00
7	5	HP Mouse	1	2500.00
8	6	HP M120 /6 programm. buttons,1 AA battery gives upto 12 months life	1	599.00
9	7	Portronics Bridge Y USB 3.0 to Type C OTG Adaptor	2	99.00
10	8	NOBERO Men's Oversized Solid Loose fit Heavy Cotton T-Shirt (Pack of 2)	1	1349.00
11	8	HP S1000 Plus Silent USB Wireless Computer Mute Mouse 1600DPI USB (7YA12PA), Black	1	699.00
12	9	Apple 30W USB-C Power Adapter ​​​​​​​	1	2899.00
13	9	Apple USB-C to Lightning Cable (2m) ​​​​​​​	1	2199.00
14	10	HP S1000 Plus Silent USB Wireless Computer Mute Mouse 1600DPI USB (7YA12PA), Black	1	699.00
15	10	Nobero Oversized Hoodies for Man Stylish	1	1399.00
16	10	HP M120 /6 programm. buttons,1 AA battery gives upto 12 months life	1	599.00
17	10	Meetion MT-G3330 Wired Ambidextrous Optical Gaming Mouse	1	1599.00
18	11	Boat BassHeads 100 in-Ear Headphones with Mic (Black)	1	319.00
19	12	Nobero Oversized Hoodies for Man Stylish	1	1399.00
20	12	Jabra Evolve2 65	1	16999.00
21	13	Apple 20W USB‑C Power Adapter	1	3599.00
22	14	Boat BassHeads 100 in-Ear Headphones with Mic (Black)	1	215.00
23	15	Apple 20W USB‑C Power Adapter	1	3599.00
24	16	HP S1000 Plus Silent USB Wireless Computer Mute Mouse 1600DPI USB (7YA12PA), Black	1	699.00
25	20	Sony WH‑1000XM4	2	26990.00
26	21	Sony WF‑1000XM5	1	26990.00
\.


--
-- Data for Name: problem_statement; Type: TABLE DATA; Schema: public; Owner: sourcepoint_admin
--

COPY public.problem_statement (id, title, description, difficulty, created_at, created_by_id) FROM stdin;
1	Springboot application for a bank 	Create a banking application with login page and security features	\N	\N	\N
2	Java DRT	JAVA DRT 	\N	\N	\N
3	Java_Advance	import java.util.Arrays;\r\nimport java.util.Stack;\r\n\r\n/*\r\n * =====================================================================================\r\n * Problem Statement\r\n * =====================================================================================\r\n *\r\n * ## Problem: The Circular Signal Tower 🗼\r\n *\r\n * ### Scenario:\r\n * You are in charge of a set of signal towers arranged in a **circular formation**.\r\n * Each tower has a specific signal strength, represented by an integer. Your task is\r\n * to develop a system that, for each tower, can determine the signal strength of the\r\n * **first tower** it encounters in a **clockwise direction** that has a **stronger signal**.\r\n *\r\n * Because the towers are in a circle, the search for a stronger tower can wrap\r\n * around from the last tower back to the first one.\r\n *\r\n * ### Your Goal:\r\n * Complete the `findNextStrongerSignals` method. It takes an array of integers\r\n * representing the signal strengths and must return a new array of the same size.\r\n * Each element in the new array should contain the signal strength of the next\r\n * stronger tower. If no such stronger tower exists for a given tower, its\r\n * result should be recorded as -1.\r\n *\r\n * ### Example:\r\n * Input:  [3, 8, 4, 6, 5]\r\n * Output: [8, -1, 6, 8, 8]\r\n *\r\n * Walkthrough:\r\n * - For tower 3: The next is 8 (stronger) -> 8\r\n * - For tower 8: No tower is stronger in the circle -> -1\r\n * - For tower 4: The next is 6 (stronger) -> 6\r\n * - For tower 6: Searching clockwise, 5 is not stronger. Wrap around. 3 is not. 8 is stronger -> 8\r\n * - For tower 5: Searching clockwise, wrap around. 3 is not. 8 is stronger -> 8\r\n *\r\n * ### Constraints:\r\n * - `1 <= signalStrengths.length <= 10^5`\r\n * - `0 <= signalStrengths[i] <= 10^9`\r\n * - The solution should be efficient. An O(n^2) approach will likely time out.\r\n *\r\n * =====================================================================================\r\n */\r\n\r\n/**\r\n * The candidate should implement their solution in this class.\r\n * The optimal solution uses a Monotonic Stack and has a time complexity of O(n).\r\n */\r\nclass Solution {\r\n    public int[] findNextStrongerSignals(int[] signalStrengths) {\r\n        // TODO: Implement your optimal O(n) solution here.\r\n        // The current implementation is a placeholder and is incorrect.\r\n        int n = signalStrengths.length;\r\n        if (n == 0) {\r\n            return new int[0];\r\n        }\r\n\r\n        int[] result = new int[n];\r\n        Arrays.fill(result, -1); // Initialize all results to -1 by default\r\n\r\n        // HINT: A stack can be very useful for this problem.\r\n        // Consider iterating twice the length of the array to handle the circular nature.\r\n\r\n        return result;\r\n    }\r\n}\r\n\r\n/**\r\n * =====================================================================================\r\n * Testing Class - DO NOT MODIFY\r\n * =====================================================================================\r\n * This Main class is designed to test your solution.\r\n * You can run this code to see if your implementation passes the sample test cases.\r\n */\r\npublic class Main {\r\n    public static void main(String[] args) {\r\n        Solution solution = new Solution();\r\n        int testCaseNumber = 1;\r\n\r\n        // Test Case 1: General case\r\n        System.out.println("--- Test Case " + testCaseNumber++ + " ---");\r\n        int[] input1 = {3, 8, 4, 6, 5};\r\n        int[] expected1 = {8, -1, 6, 8, 8};\r\n        runTest(solution, input1, expected1);\r\n\r\n        // Test Case 2: Strictly increasing\r\n        System.out.println("--- Test Case " + testCaseNumber++ + " ---");\r\n        int[] input2 = {1, 2, 3, 4, 5};\r\n        int[] expected2 = {2, 3, 4, 5, -1};\r\n        runTest(solution, input2, expected2);\r\n\r\n        // Test Case 3: Strictly decreasing (circular check)\r\n        System.out.println("--- Test Case " + testCaseNumber++ + " ---");\r\n        int[] input3 = {5, 4, 3, 2, 1};\r\n        int[] expected3 = {-1, 5, 5, 5, 5};\r\n        runTest(solution, input3, expected3);\r\n        \r\n        // Test Case 4: All elements are the same\r\n        System.out.println("--- Test Case " + testCaseNumber++ + " ---");\r\n        int[] input4 = {10, 10, 10};\r\n        int[] expected4 = {-1, -1, -1};\r\n        runTest(solution, input4, expected4);\r\n        \r\n        // Test Case 5: Empty input\r\n        System.out.println("--- Test Case " + testCaseNumber++ + " ---");\r\n        int[] input5 = {};\r\n        int[] expected5 = {};\r\n        runTest(solution, input5, expected5);\r\n    }\r\n\r\n    private static void runTest(Solution solution, int[] input, int[] expected) {\r\n        System.out.println("Input:    " + Arrays.toString(input));\r\n        System.out.println("Expected: " + Arrays.toString(expected));\r\n        int[] result = solution.findNextStrongerSignals(input.clone()); // Pass a clone to avoid modifying original\r\n        System.out.println("Output:   " + Arrays.toString(result));\r\n        if (Arrays.equals(result, expected)) {\r\n            System.out.println("Result: ✅ Passed");\r\n        } else {\r\n            System.out.println("Result: ❌ Failed");\r\n        }\r\n        System.out.println();\r\n    }\r\n}	\N	\N	\N
\.


--
-- Data for Name: product; Type: TABLE DATA; Schema: public; Owner: sourcepoint_admin
--

COPY public.product (id, product_code, name, stock, price, description, image_url, category, brand, mrp, warranty, return_policy, seller_id) FROM stdin;
3	ERP_0123	Nobero Oversized Hoodies for Man Stylish	8	1399.00	NOBERO, Nobero, Pratyaya E-Commerce Private Limited, 5th Floor, Western Aqua, 121, Workenstein Collaborative Spaces Private Limited, Hi Tech City, Whitefields Kondapur, Hyderabad, Rangareddy, Telangana - 500081	https://m.media-amazon.com/images/I/51wuFswcMdL._SX679_.jpg	Apparel	Nobero	2999.00			\N
33	JBR-EVL2-65-IN-25	Jabra Evolve2 65	9	16999.00	Advanced ANC, 37H battery life, powerful speakers, hybrid work headset	https://m.media-amazon.com/images/I/317And2NgDL._SY300_SX300_QL70_FMwebp_.jpg	Electronics	Jabra	39999.00			\N
35	SNY-HPH-XM5-IN-25	Sony WH‑1000XM5	10	31990.00	Next‑gen noise cancellation, ultra‑light design, premium sound, 30H battery	https://m.media-amazon.com/images/I/51aXvjzcukL._SX679_.jpg	Electronics	Sony	34990.00			\N
38	SMS-CHG-45W-IN-25	Samsung 45W Super Fast Charging Adapter	10	2999.00	45W Super Fast Charging 2.0, USB‑C PD support, tablets & laptops	https://m.media-amazon.com/images/I/61bB+v8qJqL._SX679_.jpg	Electronics	Samsung	3499.00			\N
37	SMS-CHG-25W-IN-25	Samsung 25W Fast Charging Adapter	10	1699.00	Super Fast Charging, USB‑C output, compact design, Galaxy compatible	https://m.media-amazon.com/images/I/71Gu1ib5-RL._SX679_.jpg	Electronics	Samsung	1999.00			\N
27	PRT-CBL-KC-IN-25	Portronics Konnect C Type Cable	10	699.00	USB‑C fast charging cable, high-speed data transfer, braided durability	https://m.media-amazon.com/images/I/71lJnttqcML._SX679_.jpg	Electronics	Portronics	899.00			\N
30	JBR-EVL-20UC-IN-25	Jabra Evolve 20 UC	10	4499.00	Professional wired headset, noise‑cancelling mic, UC certified, all‑day comfort	https://m.media-amazon.com/images/I/31MCV0u8S0L._SY300_SX300_QL70_FMwebp_.jpg	Electronics	Jabra	4999.00			\N
31	JBR-EVL-30II-IN-25	Jabra Evolve 30 II	10	6299.00	HD voice, flexible boom arm, passive noise cancellation, USB connectivity	https://m.media-amazon.com/images/I/31IuSqZMTlL._SY300_SX300_QL70_FMwebp_.jpg	Electronics	Jabra	6999.00			\N
32	JBR-EVL-65-IN-25	Jabra Evolve 65	10	13499.00	Wireless Bluetooth headset, dual connectivity, 14H talk time, UC certified	https://m.media-amazon.com/images/I/41XtZ6GsNvL._SY300_SX300_QL70_FMwebp_.jpg	Electronics	Jabra	14999.00			\N
23	BAT-HPH-BH900-IN-25	boAt BassHeads 900 Wired Headphone	10	2399.00	40mm drivers, immersive bass, foldable design, adjustable headband, inline mic	https://encrypted-tbn2.gstatic.com/shopping?q=tbn:ANd9GcTunXO-Z_fB3HkP-3AYoiM4s9h46Dn2cPu9b7hj0vev1Jikr-HhseWaJe_3RubdlzBT6VulUclG9-n9CLTCwW-OLSgOcmryFMoX5F2q5rVVWb4J6Xd8vsnF	Electronics	boAt	2990.00			\N
24	BAT-HPH-R255P-IN-25	boAt Rockerz 255 Pro+	10	2799.00	Bluetooth wireless, ASAP fast charge, up to 40H playback, IPX7 water resistance	https://m.media-amazon.com/images/I/41NVmSPAgAL._SY300_SX300_QL70_FMwebp_.jpg	Electronics	boAt	3499.00			\N
18	DEL-MSE-WM118-IN-25	Dell WM118 Wireless Mouse	100	999.00	Wireless optical mouse, 1000 DPI sensor, compact design, USB nano receiver, long battery life	https://m.media-amazon.com/images/I/31IKVQPJ5nL._SX300_SY300_QL70_FMwebp_.jpg	Electronics	Dell	1199.00			\N
17	LOG-MSE-M221-IN-25	Logitech M221 Silent Wireless Mouse	10	899.00	SilentTouch technology, 2.4GHz wireless, 1000 DPI optical sensor, ambidextrous design, 18‑month battery life	https://m.media-amazon.com/images/I/3191Hq-8VTL._SY300_SX300_QL70_FMwebp_.jpg	Electronics	Logitech	1095.00			\N
21	LOG-CMB-MK215-IN-25	Logitech MK215 Keyboard Mouse Combo	10	1699.00	Wireless combo, long-range connectivity, spill-resistant keyboard, extended battery life	https://m.media-amazon.com/images/I/419s7aoNgDL._SY300_SX300_QL70_FMwebp_.jpg	Electronics	Logitech	1999.00			\N
19	LOG-KBD-K120-IN-25	Logitech MK270r Wireless Keyboard and Mouse Combo 	10	1199.00	Full-size keyboard, spill-resistant design, low-profile keys, USB plug & play	https://m.media-amazon.com/images/I/61pUul1oDlL._SX679_.jpg	Electronics	Logitech	2496.00			\N
20	HP-KBD-C2500-IN-25	HP C2500 Wired Keyboard	10	1099.00	Ergonomic wired keyboard, adjustable tilt, spill-resistant keys, office-friendly design	https://m.media-amazon.com/images/I/51jw+QLOqtL._SX679_.jpg	Electronics	HP	1399.00			\N
25	BAT-HPH-R450-IN-25	boAt Rockerz 450 Bluetooth	10	3499.00	Wireless Bluetooth, up to 15H playback, padded earcups, foldable design	https://m.media-amazon.com/images/I/51FNnHjzhQL._SX679_.jpg	Electronics	boAt	3990.00			\N
29	APL-CBL-LTG-IN-25	Apple Lightning to USB Cable	30	2199.00	Apple‑certified Lightning cable, fast charge & data sync, durable build	https://m.media-amazon.com/images/I/614z32X4dQL._SX679_.jpg	Electronics	Apple	2499.00			\N
9	APP_893_UI	Apple USB-C to Lightning Cable (2m) ​​​​​​​	100	2199.00	You can also use this cable with your Apple 18W, 20W, 29W, 30W, 61W, 87W or 96W USB‑C Power Adapter to charge your iOS device and even take advantage of the fast-charging feature on selected iPhone and iPad models.	https://m.media-amazon.com/images/I/61PduSmu8GL._SX679_.jpg	Electronics	Apple	2999.00	1 Year Warranty	7 Days Returns On defect	\N
22	DEL-CMB-KM117-IN-25	Dell KM117 Wireless Combo	100	1999.00	Wireless keyboard and mouse combo, chiclet keys, optical mouse, USB receiver	https://m.media-amazon.com/images/I/611HaDOkqBL._SX679_.jpg	Electronics	Dell	2499.00			\N
4	PSN_0134	NOBERO Men's Oversized Solid Loose fit Heavy Cotton T-Shirt (Pack of 2)	10	1349.00	✅100% Cotton Material: Nobero’s Men oversized t-shirts are made entirely from cotton, offering a soft, breathable feel against your skin for maximum comfort and ease of wear.\r\n✅Premium Heavy Cotton: Experience superior comfort and durability with our high-quality heavy cotton fabric Tshirts for men, ensuring long-lasting wear and exceptional softness after wash.\r\n✅Oversized Fit: Embrace relaxed style with our loose-fitting t-shirts for men, designed for ultimate comfort and freedom of movement, perfect for lounging or casual outings and every day wear.\r\n✅Classic Round Neck Design: Elevate your wardrobe essentials with our timeless crew neck t-shirt for men, offering a versatile neckline that complements any casual or layered look with ease.\r\n✅Drop Shoulder Construction: Enjoy enhanced comfort and a laid-back vibe with our drop shoulder t-shirts for men, adding a modern twist to your everyday style.	https://m.media-amazon.com/images/I/512VvmHIA6L._SX679_.jpg	Apparel	Nobero	1299.00	1 Year Warranty	30 Days Return Policy	\N
10	APP_753_RT	Apple 30W USB-C Power Adapter ​​​​​​​	29	2899.00		https://m.media-amazon.com/images/I/51Q4hNlIU6L._SX679_.jpg	Electronics	Apple	3999.00	1 Year Warranty	7 Days Returns On defect	\N
34	SNY-HPH-XM4-IN-25	Sony WH‑1000XM4	8	26990.00	Industry‑leading ANC, 30H battery, adaptive sound control, touch controls	https://m.media-amazon.com/images/I/31+1OdrDX+L._SY300_SX300_QL70_FMwebp_.jpg	Electronics	Sony	29990.00			\N
36	SNY-TWS-XM5-IN-25	Sony WF‑1000XM5	9	26990.00	True wireless ANC earbuds, immersive sound, wireless charging, compact design	https://m.media-amazon.com/images/I/61GJAFdM9pL._SL1500_.jpg	Electronics	Sony	29990.00			\N
6	PRT_36_HT	Portronics Bridge Y USB 3.0 to Type C OTG Adaptor	10	99.00	OTG (On-the-Go) Functionality: Transform your Type C mobile device into a host computer. Effortlessly connect devices such as keyboards, mice, gaming controllers, USB flash drives etc.\r\nFast Charge & Data Sync: Experience rapid charging and high-speed data transfer with the BridgeY adapter. It ensures your devices are powered and synced efficiently for enhanced connectivity.\r\nSleek & Compact Design: The Portronics BridgeY adapter’s minimalist and portable design is perfect for travel. It fits easily into your pocket or bag, making it highly convenient for on-the-go use.\r\nWide Compatibility: This versatile adapter connects USB A devices to Type C ports and vice versa. It supports a broad range of devices, offering flexibility for various setups and usage scenarios.\r\nAluminum Alloy Housing: Constructed with robust aluminum alloy, the BridgeY adapter features a sleek, premium look. It combines durability and style, ensuring long-lasting performance and a modern appearance.\r\nEnhanced Durability: The aluminum alloy construction provides exceptional durability. This adapter withstands daily wear and tear, making it a reliable choice for consistent connectivity needs.\r\nEfficient Data Transfer: Designed for seamless connection and syncing, the adapter supports quick and efficient data transfer between devices. Enhance your productivity with swift file exchanges and reliable connections.	https://m.media-amazon.com/images/I/616jdfyhw8L._SX679_.jpg	Electronics	Portronics	599.00	1 Year Warranty	7 Days Returns On defect	\N
39	SMS-CBL-USBC-IN-25	Samsung USB‑C Data Cable	10	549.00	Durable USB‑C cable, fast charging, high‑speed data transfer	https://m.media-amazon.com/images/I/11ICusapw3L._SX300_SY300_QL70_FMwebp_.jpg	Electronics	Samsung	699.00			\N
40	SMS-BUD-B2P-IN-25	Samsung Galaxy Buds 2 Pro	10	15999.00	Premium ANC earbuds, 360 audio, water resistance, Galaxy ecosystem support	https://m.media-amazon.com/images/I/61Qqg+T8nsL._SX679_.jpg	Electronics	Samsung	17999.00			\N
26	PRT-CBL-KA-IN-25	Portronics Konnect A USB Cable	10	449.00	Durable USB‑A cable, fast charging support, reinforced connectors, data sync	https://m.media-amazon.com/images/I/71lJnttqcML._SX679_.jpg	Electronics	Portronics	599.00			\N
13	B0BY9VPFWC	Jabra Evolve2 65 Flex Link380c UC Stereo	5	29999.00	The Jabra Evolve2 65 Flex is a highly portable, foldable professional headset featuring Hybrid ANC, noise-canceling mics, Jabra Air Comfort for lightweight wear, dual connectivity (Bluetooth/USB), 30m range, and a compact design with a twistable headband for travel, plus dedicated Teams button and wireless charging options, all built for hybrid work focus. 	https://m.media-amazon.com/images/I/51hTNOwAeXL._SX679_.jpg	Electronics	Jabra	46819.00	1 year	7 Day in Service Center Repair	\N
15	XRU57VI6HY	Zoook Qwerty Pad/3 Adj. DPI/Full Size Keyboard(104 key) & Mouse Combo 	6	799.00	Reliable Plug & Play, Easy to Use, Ergonomic Palm Rest, Durable & Resilient, Widely Compatible, High Defination 4D optical mouse, 800-1200-1600 DPI	https://www.zoook.com/uploads/0635c859-dc85-4b37-abe1-73573e6f49a4.jpg	Electronics	Zoook	3999.00	1 year	7 Day in Service Center Repair	\N
8	MTR_908_YU	Meetion MT-G3330 Wired Ambidextrous Optical Gaming Mouse	5	1599.00	Fire Button - The fire button is placed strategically at a convenient location and when pressed the mouse auto-adjusts the speed to help in stabilizing the cursor for a perfect aim.\r\n\r\nE-Sports Level Game Chips - The mouse is fitted with esports level chips that respond quickly to action and rebounds to enhance speed, precision and thrill.\r\n\r\nIngenious Craft, excellent feel. The gaming mouse is refined by many rigorous and meticulous working procedures, which makes perfect use of ergonomics, comfortable operation, flexible click, rapid response and silvery sound, bringing a pleasant experience.\r\n\r\nEnjoy Playing Many Games - High-speed DPI at will (7 grade switchable DPI), accurate target pointing features help in playing multi-games\r\n\r\nHigh Precision Optical. Gaming Sensor PMW3330 with a high-performance sensor smoothly control precise and flexible, to meet your precise positioning requirements, easy to control all kinds of popular games.	https://m.media-amazon.com/images/I/31U2NBLuANL._SY300_SX300_QL70_FMwebp_.jpg	Electronics	Meetion	6499.00	1 Year Warranty	7 Days Returns On defect	\N
5	HP_S1000_GH	HP S1000 Plus Silent USB Wireless Computer Mute Mouse 1600DPI USB (7YA12PA), Black	-4	699.00	\r\nNetwork Connectivity Technology\t: USB\r\nProduct Features\t: Soundless, Wireless\r\nMovement Detection\t: Optical\r\nButton Quantity\t:3\r\nHand Orientation\t:Ambidextrous\r\nCompatible Devices\t:Personal Computer\r\nOperating System\t:Chrome Os,Mac Os,Windows 10,Windows 7,Windows 8\r\nBattery Average Life\t:24 Months\r\nHardware Platform\t :PC\r\nPower Source\t : Battery Powered\r\nMouse Maximum Sensitivity\t:1600 Dots per Inch	https://m.media-amazon.com/images/I/61px9mMT2jL._SX679_.jpg	Electronics	HP	1099.00	1 Year Warranty	7 Days Returns On defect	\N
7	HP_M120_RT	HP M120 /6 programm. buttons,1 AA battery gives upto 12 months life	148	599.00	【COMPATIBLE OS】Experience hassle-free transitions across different workstations or devices with multi-OS compatibility, supporting Windows 11/10 and macOS.\r\n\r\n【6 BUTTONS】Ensure smooth workflow and make your everyday tasks easier with 6 versatile buttons, a 3D scroll wheel, and a DPI switch button to fit the way you work.\r\n\r\n【SPEED AND PRECISION】Elevate your computing experience with up to 1600 dpi. Enjoy an optical sensor that delivers accurate, fast tracking to keep you ahead of your work.\r\n\r\n【RELIABLE CONNECTIONS】Stay connected effortlessly with a mouse that seamlessly links to any device through a USB-A nano dongle and a 2.4 GHz wireless connection.\r\n\r\n【ERGONOMIC DESIGN】Maximize your productivity and click effortlessly with an ergonomically designed mouse for all-day comfort.	https://m.media-amazon.com/images/I/51+jHZifmkL._SX679_.jpg	Electronics	HP	1399.00	1 Year Warranty	7 Days Returns On defect	\N
14	GY51H47350	Lenovo Legion M300s RGB Wired Gaming Mouse	3	1599.00	Enhanced Gaming Performance: The Legion Wired Gaming Mouse offers exceptional precision and speed with an adjustable tracking up to 8,000 DPI and an impressive 220 IPS (Inches Per Second). Gamers can fine-tune their sensitivity for precise aiming and swift cursor movements\r\nLong-Lasting Durability: Equipped with Omron mechanical microswitches rated for up to 20 million clicks, this gaming mouse ensures enduring performance and reliability. Gamers can rely on the consistent tactile feedback and responsiveness of the buttons throughout the mouse's lifespan\r\nCustomizable Buttons: Featuring 6 easily programmable buttons (left, right, wheel, DPI, side x 2), this gaming mouse puts customization at your fingertips. Gamers can assign macros, commands, or specific functions to each button, providing quick access to in-game actions and enhancing gameplay efficiency\r\nOptimized Comfort: Designed for prolonged gaming sessions, the mouse features a light-weight construction and 100% PTFE mouse feet. This combination provides a smooth glide and reduces friction, ensuring long-lasting comfort. Whether you're engaged in hours of gameplay or work, the mouse is engineered for extended usage without causing strain\r\nVersatile Grip Styles: The mouse's symmetrical small-medium size is optimized for claw and fingertip grip styles, catering to a wide range of gamers' preferences. Additionally, gamers can personalize their setup with customizable RGB LED backlighting, allowing them to match their mouse's aesthetic with their gaming rig and create an immersive gaming atmosphere	https://m.media-amazon.com/images/I/51JGTdLCcFL._SX679_.jpg	Electronics	Lenovo	4490.00	1 year	7 Day in Service Center Repair	\N
12	PRT_37_HT	Portronics Bubble Dock Bluetooth, Wireless Handheld Multi-device Keyboard 	-1	999.00	\r\nIntroducing the Portronics Bubble Dock, a versatile wireless keyboard designed for seamless connectivity and convenience. Equipped with both 2.4 GHz and Bluetooth technology, it offers reliable, high-speed connections for all your devices. The built-in holder slot ensures your tablet and smartphone are always within reach, making multitasking a breeze. With multi-device pairing for up to 3 devices, you can effortlessly switch between your smartphone, tablet, laptop, or desktop, enhancing your productivity. The compact tenkeyless (TKL) layout saves desk space while providing all essential keys for an efficient typing experience. Compatible with a wide range of devices, it is the perfect addition to any modern workspace.	data:image/jpeg;base64,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	Electronics	Portronics	1999.00	1 Year Warranty	7 Days Returns On defect	\N
16	B071Z8M4KX	Boat BassHeads 100 in-Ear Headphones with Mic (Black)	33	299.00	The perfect way to add some style and stand out from the crowd with the boAt BassHeads 100 "Hawk" inspired earphones. Impedance 16Ω, Sensitivity (dB) 92db ±3db, Frequency Response 20Hz-20KHz\r\nThe stylish BassHeads 100 superior coated wired earphones are a definite fashion statement - wear your attitude with its wide variety of collection\r\nThe powerful 10mm dynamic driver with the speaker resistance of 16 ohm enables the earphone to deliver a punchy, rhythmic response to the most demanding tracks\r\nFeatures a HD microphone to make crystal clear calls - making life easier on the go, play/pause music or answer/end calls with one-click, track forward with two-clicks or back with 3 clicks make these earphones extremely user-friendly\r\nWith 1.2 meters perfect length cable now plug it in anywhere with ease - while the earphones are extremely user-friendly and stylish, extruding premium coating on the wire cable is a manufacturing process that we've been performing and refining since our company's inception	https://m.media-amazon.com/images/I/513ugd16C6L._SX679_.jpg	Electronics	Boat	999.00	1 year	7 Day in Service Center Repair	\N
41	JBR_40_UC_WRT_098	Jabra Evolve 40 UC Wired Over The Ear Headset with Mic (Black)	3	7999.00	Stay connected- Easily transfer your Skype for Business and Lync pc calls to your smartphone using “Jabra Intelligent call transfer (JICT)”. Ideal for when you need to head out the office door or move away from your desk.\r\n\r\n3.5 mm jack for better connectivity-The 3.5 mm jack lets you connect to your personal device – such as a smartphone or tablet – to work or listen to music wherever you are.\r\n\r\nPassive Noise-Cancellation-Simply wear the headset to eliminate high-frequency noise, such as human voices – all thanks to the specially designed ear cushions. We call this “passive noise-cancellation”\r\nBusy light-Busy light automatically turns on during a call to let others know the person is busy. Users can also activate it manually to signal that they don’t want to be disturbed	https://headsetsindia.com/wp-content/uploads/2020/06/evolve_40c.jpg	Electronics	Jabra	19800.00	1 Year On No-Return Warranty 	7 Days Replacement 	\N
28	APL-ADP-20W-IN-25	Apple 20W USB‑C Power Adapter	25	3599.00	Fast charging adapter, compact design, USB‑C output, iPhone & iPad compatible	https://store.storeimages.cdn-apple.com/4668/as-images.apple.com/is/MHJA3	Electronics	Apple	3999.00			17
51	B07W8Y857I	Mochi Sneaker 71-9054	5	1399.00	Trendy Look: These sneakers boast a high-top design with a smooth black Faux Leather leather exterior, offering a sleek and contemporary look.\r\nComfortable Design: Designed for both style and comfort, the padded collar and cushioned footbed support extended wear, and the durable rubber outsole ensures traction.\r\nPremium Materials:\r\nOccasion: The Faux Leather material used for this sneaker is high quality and also breathable for enhanced comfort	https://m.media-amazon.com/images/I/61TugbK016L._SY695_.jpg	Apparel	Mochi	3490.00	No Warranty	No Return 	\N
44	B08J7VTBMH09	Kent Touchless Sanitiser Dispenser (12013), 350 ml, Pink	10	1599.00	Fully automatic and touchless use for hands-free operation. Avoid manual sanitization of hands with bottles. Convenient, more hygienic and environment friendly product.\r\nEquipped within-built infrared smart sensor which senses your hands when you put them below the dispenser and dispenses the liquid sanitizer in form of atomized mist.\r\nAdjustable Sanitiser Volume With 2 Variable Speeds. Easy to Refill- Removable soap container for cleaning and easy refilling.\r\nHigh storage capacity of 350 ml. Transparent container for sanitizer. Can be wall-mounted or kept on table top.\r\nInput Power Supply- 4.5V, 3 Nos. AA 1.5 Batteries, Power Consumption- 1.5 W. 1 Year Warranty. .Includes- Kent Touchless Sanitiser Dispenser, User manual.	https://m.media-amazon.com/images/I/61aptYfSR1L._SL1500_.jpg		Kent	2999.00	1 year	7 Day in Service Center Repair	\N
42	B07W8Y848L	Larah by BOROSIL Opalware Dinner Set (White) - 44 Pieces	5	2199.00	1 percent bone ash free\r\nExtra strong - toughened glass\r\nLight weight\r\nDishwasher safe\r\nMicrowave safe\r\nChip resistance\r\nColor: White, Material: Opalware\r\nPackage Contents: 1-Piece 13" Rice Plate, 8-Piece 11" Full Plate, 8- Piece 7" Quarter Plate, 8- Piece 4.5" Veg Bowl, 3-Piece 8" Serving Bowl, 8-Piece 5" Soup Bowl, 8- Piece Spoons	https://m.media-amazon.com/images/I/41ESrLytBiL._SY300_SX300_QL70_FMwebp_.jpg	Other	BOROSIL	5499.00	No Warranty	No Return Applicable 	\N
45	BTOP40469202	Slipstream Bball Res Sneakers For Men  (White , 11)	5	3999.00	Style Name : Sneaker\r\nModel Name : Slipstream Bball Res\r\nBrand Color : White-Feather Gray\r\nMaterial : Leather\r\nActivity : Evolution	https://m.media-amazon.com/images/I/41xmptJWOpL._SY695_.jpg	Apparel	Puma	7999.00	No Warranty	No Return Applicable 	\N
46	BOR893YI589	Red Tape Casual Sneakers for Men | Comfortable, Shock Absorbant & Slip-Resistant	5	1299.00	MATERIALS: Upper- PU | Outsole- TPU (Thermoplastic Urethane) + TPR (Thermoplastic Rubber).\r\nThese shoes give you All Day Comfort and Relaxation to your feet all the while maintaining a Chic Look.\r\nLIFESTYLE: Sneaker Shoes.\r\nBENEFITS: Sneakers Shoes are Designed for Utmost Comfort with TPR + TPU Sole. It Provides Dynamic Feet Support, Arch Support, and Slip-Resistance for Negating Accidental Falls.\r\nFEATURES: Closure - Lace-up | Fit Type - Regular\r\nCare Instruction: Wipe with a clean, dry cloth to remove the dust.\r\n	https://m.media-amazon.com/images/I/614e5ApDfYL._SY695_.jpg		Red Tape	6999.00	No Warranty	No Return Applicable 	\N
47	B0BY9VPFER	Red Tape Men Colourblocked Sneakers	5	1699.00	STYLISH: The PU upper gives a chic and modern look while also being low maintenance and easy to clean.\r\nSLIP RESISTANCE: Made of high-grade TPU+TPR sole, it gives you maximum stability and prevents accidental falls & slips.\r\nSURFACE GRIP: Specially designed to give you firm support, while offering a classy look.\r\nConfidence in Every Step: When your feet are happy, you exude confidence. These shoes not only make you feel good, but they also boost your confidence, allowing you to tackle your day with a positive stride.\r\nProduct Specification:\r\n-Material: Sole - TPU+TPR | Upper - PU | Insole material - Memory Foam\r\nElevate your style game and embrace the essence of modern sophistication.	https://redtape.com/cdn/shop/files/RSL0493A_1_jpg.jpg?v=1756809947	Apparel	Red Tape	6999.00	No Warranty	No Return Applicable 	\N
48	B07W8Y846Y	Puma Unisex-Adult Vis2k Res Sneaker Search this page	5	3499.00	Style Name : Sneaker\r\nModel Name : Vis2K Res\r\nBrand Color : Black-Black\r\nMaterial : Textile\r\nActivity : Basics\r\n	https://m.media-amazon.com/images/I/51OWsRcefyL._SY695_.jpg	Apparel	Puma	7999.00	1 Year Warranty	No Return 	\N
49	B07W8Y468UI	JACK & JONES Men Sneaker Shoes ( White )	5	1999.00	Upper Material:: Polyester\r\nSole Material:: EVA\r\nAnkle Height:: Mid\r\nToe Shape::: Round	https://m.media-amazon.com/images/I/41p21QJY+1L._SY695_.jpg	Apparel	JACK & JONES	4999.00	1 year	No Return 	\N
50	B07W8Y847L	Woodland Men Camel Casual Shoes	5	2099.00	Premium Woodland Leather Shoes for Men – Crafted from top-quality genuine leather, these Woodland leather shoes offer unmatched durability, timeless style, and long-lasting performance. Perfect for men seeking leather shoes for men that combine rugged outdoor functionality with modern casual aesthetics.\r\nAll-Day Comfort & Support – Featuring a cushioned insole, ergonomic footbed, and breathable leather lining, these mens leather shoes ensure maximum comfort during long walks, office commutes, weekend outings, or outdoor adventures. These leather shoes for men reduce fatigue and provide reliable support all day.\r\n	https://m.media-amazon.com/images/I/81+lJdiF5wL._SX695_.jpg	Apparel	Woodland	4495.00	1 year	No Return 	\N
52	B07W8Y86JT	Lee Cooper Men's Lc1657b Sneakers	5	2499.00	Premium Genuine Leather Construction: Crafted from high-quality leather, these boots offer superior durability and a sophisticated appearance that improves with age.\r\nStylish Lace-Up Design: The classic lace-up closure ensures a secure fit while adding a timeless, rugged style that pairs well with both casual and semi-formal outfits.\r\nCushioned Insole for All-Day Comfort: Designed with a soft, cushioned insole that provides excellent support and shock absorption, keeping your feet comfortable even during extended wear.	https://m.media-amazon.com/images/I/81pOibH5ICL._SX695_.jpg	Apparel	Lee Cooper	3299.00	No Warranty	No Return 	\N
53	2FD21519Z01	U.S. Polo Assn. BARNES Men's Casual BLACK Shoes	5	2099.00		https://m.media-amazon.com/images/I/71QLuq4itnL._SX695_.jpg	Apparel	U.S. Polo Assn. 	3999.00	No Warranty	No Return 	\N
43	BOR893YI585	Larah Vogue Glass Lunchbox, Round x 3, 400ml x 3	4	599.00	Fresh, tasty and healthy our Larah Glassware Lunchbox ensure that your food looks, tastes and smells just as it did while it was lovingly prepared. Made of the finest borosilicate glass, the leak proof boxes are 100% microwavable (up to 350°C) and 100% stain proof and leach no chemicals into your food. Unlike the other glass lunchboxes in the market, Larah Glassware's Lunchbox range is made of high grade borosilicate glass, which is also oven safe. The high quality fabric carry bags are machine washable. There is no better way to bring home to the office. No plastic - isliye fantastic!	https://m.media-amazon.com/images/I/71p3nAWeK-L._SX679_.jpg	Other	Larah 	1495.00	No Warranty	No Return Applicable 	\N
54	\tB017NC2IPM	Resonate RouterUPS® Gen2 | Original Router UPS for 12V WiFi Router & Modem (Supports up to 2A)	5	1499.00	About this item: \r\n\r\nOriginal RouterUPS Gen2: Invented and Manufactured by Resonate, the pioneers of Router UPS. Enjoy uninterrupted internet with up to 6 hours of power backup during power cuts. Perfect for work, study, gaming, and entertainment. Built with superior quality for long-lasting reliability. It's like a Power Bank for your Wifi router.\r\n\r\nSeamless Connectivity 24/7: Say goodbye to disconnects during power cuts. Designed for round-the-clock use, this plug-and-play RouterUPS installs in just 30 seconds with an optional wall mount. Stay connected on VPN, WebEx, Zoom, Netflix, and more, even during long outages with wifi router backup power supply.\r\n\r\nIntelligent Charging & Maximum Safety: Enjoy longer battery life with advanced intelligent charging technology. Certified for safety with BIS, CE, and RoHS, featuring 6-layer protection against overcharging, overheating, and short circuits.\r\n\r\nCompatible with Most 12V Routers: Works seamlessly with WiFi routers requiring up to 2A power. For high-power routers like NetLink, Syrotech, or Alphion (does not support JIO Air Fiber, Airtel Air Fiber, BSNL, and Kerala Vision). Explore our CRU12V3A variant model. Check your router’s power label or reach out to our customer care for assistance.\r\n Use the 12V adapter provided with your router and ensure it has a rating of at least 1A.\r\nOptimized Battery Design for Superior Performance: Equipped with 3 x 2600mAh high-capacity lithium-ion batteries, the RouterUPS ensures efficient power management, reduced heat, and up to 6 hours of uninterrupted backup.\r\n\r\nVersatile Mini UPS for Home Devices: Beyond routers, this compact power backup supports modems, set-top boxes, and other digital devices operating at 12V up to 2A. Reliable performance for uninterrupted connectivity and functionality during power cuts.\r\nAffordable Battery Replacement Program: Keep your RouterUPS running like new! Replace batteries easily starting at just ₹799 with fast service support within 24 to 72 hours. No need to buy a new UPS—enjoy long-term value and uninterrupted connectivity.	https://m.media-amazon.com/images/I/61ANbUDel-L._SL1500_.jpg	Electronics	Resonate	2911.00	1 Year Warranty	No Return 	\N
55	B08CH64WRX	ASUS MW203 Multi-Device Wireless Silent Mouse, 2.4GHz with USB Nano Receiver	10	1399.00	\r\nNetwork Connectivity Technology\t:USB\r\nProduct Features\t: Ergonomic Design, Soundless, Wireless\r\nMovement Detection\t: Optical\r\nButton Quantity\t: 6\r\nHand Orientation\t: Right\r\nCompatible Devices\t: Laptop\r\nOperating System :\tChrome OS, Windows 10\r\nBattery Average Life\t: 12 Months\r\nNumber of Batteries\t1 : AA batteries required. (included)\r\nHardware Platform\t: Laptop, PC\r\nPower Source\t: Battery Powered\r\nMouse Maximum Sensitivity\t: 2400 Dots per Inch	https://m.media-amazon.com/images/I/71SArYWuiAS._SL1500_.jpg	Electronics	ASUS	3990.00	1 Year Warranty	No Return 	\N
\.


--
-- Data for Name: product_image; Type: TABLE DATA; Schema: public; Owner: sourcepoint_admin
--

COPY public.product_image (id, product_id, image_url) FROM stdin;
1	4	https://m.media-amazon.com/images/I/512VvmHIA6L._SX679_.jpg
2	4	https://m.media-amazon.com/images/I/61JqXxqgKsL._SY879_.jpg
3	4	https://m.media-amazon.com/images/I/618xAJz8g+L._SY879_.jpg
4	5	https://m.media-amazon.com/images/I/61px9mMT2jL._SX679_.jpg
5	5	https://m.media-amazon.com/images/I/71srZ+m8BgL._SX679_.jpg
6	5	https://m.media-amazon.com/images/I/71srZ+m8BgL._SX679_.jpg
7	6	https://m.media-amazon.com/images/I/616jdfyhw8L._SX679_.jpg
10	8	https://m.media-amazon.com/images/I/31U2NBLuANL._SY300_SX300_QL70_FMwebp_.jpg
11	8	https://m.media-amazon.com/images/I/61MIqDgr+OL._SX679_.jpg
16	12	data:image/jpeg;base64,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
17	13	https://m.media-amazon.com/images/I/51hTNOwAeXL._SX679_.jpg
18	13	https://m.media-amazon.com/images/I/6159gDf5dsL._SX679_.jpg
19	14	https://m.media-amazon.com/images/I/51JGTdLCcFL._SX679_.jpg
20	15	https://www.zoook.com/uploads/0635c859-dc85-4b37-abe1-73573e6f49a4.jpg
47	23	https://encrypted-tbn2.gstatic.com/shopping?q=tbn:ANd9GcTunXO-Z_fB3HkP-3AYoiM4s9h46Dn2cPu9b7hj0vev1Jikr-HhseWaJe_3RubdlzBT6VulUclG9-n9CLTCwW-OLSgOcmryFMoX5F2q5rVVWb4J6Xd8vsnF
48	36	https://m.media-amazon.com/images/I/61GJAFdM9pL._SL1500_.jpg
52	34	https://m.media-amazon.com/images/I/31+1OdrDX+L._SY300_SX300_QL70_FMwebp_.jpg
54	35	https://m.media-amazon.com/images/I/51aXvjzcukL._SX679_.jpg
56	39	https://m.media-amazon.com/images/I/11ICusapw3L._SX300_SY300_QL70_FMwebp_.jpg
57	40	https://m.media-amazon.com/images/I/61Qqg+T8nsL._SX679_.jpg
58	38	https://m.media-amazon.com/images/I/61bB+v8qJqL._SX679_.jpg
60	37	https://m.media-amazon.com/images/I/71Gu1ib5-RL._SX679_.jpg
62	24	https://m.media-amazon.com/images/I/41NVmSPAgAL._SY300_SX300_QL70_FMwebp_.jpg
63	27	https://m.media-amazon.com/images/I/71lJnttqcML._SX679_.jpg
64	26	https://m.media-amazon.com/images/I/71lJnttqcML._SX679_.jpg
65	17	https://m.media-amazon.com/images/I/3191Hq-8VTL._SY300_SX300_QL70_FMwebp_.jpg
66	21	https://m.media-amazon.com/images/I/419s7aoNgDL._SY300_SX300_QL70_FMwebp_.jpg
68	19	https://m.media-amazon.com/images/I/61pUul1oDlL._SX679_.jpg
69	20	https://m.media-amazon.com/images/I/51jw+QLOqtL._SX679_.jpg
70	25	https://m.media-amazon.com/images/I/51FNnHjzhQL._SX679_.jpg
74	30	https://m.media-amazon.com/images/I/31MCV0u8S0L._SY300_SX300_QL70_FMwebp_.jpg
75	31	https://m.media-amazon.com/images/I/31IuSqZMTlL._SY300_SX300_QL70_FMwebp_.jpg
76	32	https://m.media-amazon.com/images/I/41XtZ6GsNvL._SY300_SX300_QL70_FMwebp_.jpg
78	33	https://m.media-amazon.com/images/I/317And2NgDL._SY300_SX300_QL70_FMwebp_.jpg
81	10	https://m.media-amazon.com/images/I/51Q4hNlIU6L._SX679_.jpg
82	7	https://m.media-amazon.com/images/I/51+jHZifmkL._SX679_.jpg
83	7	https://m.media-amazon.com/images/I/81rIYxjiCnL._SX679_.jpg
85	18	https://m.media-amazon.com/images/I/31IKVQPJ5nL._SX300_SY300_QL70_FMwebp_.jpg
86	16	https://m.media-amazon.com/images/I/513ugd16C6L._SX679_.jpg
87	16	https://m.media-amazon.com/images/I/61MEsBeFVUL._SX679_.jpg
88	41	https://headsetsindia.com/wp-content/uploads/2020/06/evolve_40c.jpg
89	29	https://m.media-amazon.com/images/I/614z32X4dQL._SX679_.jpg
90	9	https://m.media-amazon.com/images/I/61PduSmu8GL._SX679_.jpg
91	22	https://m.media-amazon.com/images/I/611HaDOkqBL._SX679_.jpg
92	28	https://store.storeimages.cdn-apple.com/4668/as-images.apple.com/is/MHJA3
93	44	https://m.media-amazon.com/images/I/61aptYfSR1L._SL1500_.jpg
94	43	https://m.media-amazon.com/images/I/71p3nAWeK-L._SX679_.jpg
95	42	https://m.media-amazon.com/images/I/41ESrLytBiL._SY300_SX300_QL70_FMwebp_.jpg
96	45	https://m.media-amazon.com/images/I/41xmptJWOpL._SY695_.jpg
97	45	https://m.media-amazon.com/images/I/41tVnOjVBnL._SY695_.jpg
98	45	https://m.media-amazon.com/images/I/41rgi33c3mL._SY695_.jpg
99	46	https://m.media-amazon.com/images/I/614e5ApDfYL._SY695_.jpg
100	46	https://m.media-amazon.com/images/I/614e5ApDfYL._SY695_.jpg
101	46	https://m.media-amazon.com/images/I/71fsz9hoAoL._SY695_.jpg
102	47	https://redtape.com/cdn/shop/files/RSL0493A_1_jpg.jpg?v=1756809947
103	47	https://redtape.com/cdn/shop/files/RSL0493A_2_jpg.jpg?v=1756809947
104	48	https://m.media-amazon.com/images/I/51OWsRcefyL._SY695_.jpg
105	48	https://m.media-amazon.com/images/I/419lcdSdL-L._SY695_.jpg
106	49	https://m.media-amazon.com/images/I/41p21QJY+1L._SY695_.jpg
107	49	https://m.media-amazon.com/images/I/512ccuafATL._SY695_.jpg
108	50	https://m.media-amazon.com/images/I/81+lJdiF5wL._SX695_.jpg
109	50	https://m.media-amazon.com/images/I/71Bj8fnnnLL._SY695_.jpg
110	50	https://m.media-amazon.com/images/I/61Jl1+MOOIL._SY695_.jpg
111	51	https://m.media-amazon.com/images/I/61TugbK016L._SY695_.jpg
112	51	https://m.media-amazon.com/images/I/61ANThpYqrL._SY695_.jpg
113	52	https://m.media-amazon.com/images/I/81pOibH5ICL._SX695_.jpg
114	52	https://m.media-amazon.com/images/I/81DThYKnQkL._SX695_.jpg
115	53	https://m.media-amazon.com/images/I/71QLuq4itnL._SX695_.jpg
116	53	https://m.media-amazon.com/images/I/71IwFhJofhL._SX695_.jpg
117	53	https://m.media-amazon.com/images/I/619PUTi8YsL._SX695_.jpg
118	54	https://m.media-amazon.com/images/I/61ANbUDel-L._SL1500_.jpg
119	55	https://m.media-amazon.com/images/I/71SArYWuiAS._SL1500_.jpg
\.


--
-- Data for Name: project; Type: TABLE DATA; Schema: public; Owner: sourcepoint_admin
--

COPY public.project (id, name, description, start_date, end_date, budget, status) FROM stdin;
2	TIBCO_CTR_Migration_47542	Extension to TRB 	2025-08-06	2025-11-20	1300000.00	Testing
4	RTS_Ecommerse	This implemation is to add core agnostic capability to TRAM complied API's owned by Toll	2025-10-07	2025-10-31	450000.00	Development
5	MSR_Legacy_CGR_Migration	Project involves multi stage enhancement starting from API proxy migration from Apigee to OKAPI Evolve . 	2026-03-09	2026-10-31	4500000.00	Planning
3	WRD_Finance_03	Code And Platform Migration for Existing Legacy Infra . Currently Scope is remain at Finance and Proposed model will provide new capability of Freehand intergation to Visa, Mastercard	2025-10-31	2026-03-28	6800000.00	Development
1	Tibco Integration	Project Aims to add new capability in exisitng featured	2025-09-12	2025-11-12	2490000.00	Completed
\.


--
-- Data for Name: seller_inventory; Type: TABLE DATA; Schema: public; Owner: sourcepoint_admin
--

COPY public.seller_inventory (id, seller_id, product_id, stock) FROM stdin;
5	19	16	5
6	17	8	2
8	17	14	1
12	17	12	3
7	17	5	6
3	20	16	4
1	20	28	9
14	17	41	1
11	17	16	4
10	17	7	2
15	19	10	1
4	19	28	12
16	17	43	1
\.


--
-- Data for Name: stock_request; Type: TABLE DATA; Schema: public; Owner: sourcepoint_admin
--

COPY public.stock_request (id, seller_id, product_id, quantity, status, request_date, response_date, admin_note) FROM stdin;
1	20	9	5	Approved	2025-12-19 10:23:01.807434	2025-12-19 10:29:47.881105	
2	20	16	5	Approved	2025-12-19 10:42:14.325922	2025-12-19 10:42:59.753087	approved with rational
3	19	16	5	Approved	2025-12-19 13:35:01.554133	2025-12-19 13:35:46.467971	Approved with Rational
4	19	28	1	Approved	2025-12-20 04:11:26.850734	2025-12-20 04:11:52.824426	
5	19	28	5	Approved	2025-12-28 11:49:06.846506	2025-12-28 11:50:41.264471	\N
7	19	10	1	Approved	2025-12-28 12:08:25.396995	2025-12-28 12:08:51.405007	\N
6	19	28	1	Approved	2025-12-28 12:05:23.787289	2025-12-28 12:12:15.331434	\N
\.


--
-- Data for Name: transaction; Type: TABLE DATA; Schema: public; Owner: sourcepoint_admin
--

COPY public.transaction (id, description, amount, date, category, project_id) FROM stdin;
1	Initial Funding #RT8472538	1250000.00	2026-01-01	funding	5
2	Project Agreement 	460000.00	2025-12-15	expense	5
3	Asset Allocation	370000.00	2026-01-05	expense	5
\.


--
-- Data for Name: user; Type: TABLE DATA; Schema: public; Owner: sourcepoint_admin
--

COPY public."user" (id, username, email, password_hash, role, is_approved, avatar_url, problem_statement_id, test_start_time, test_end_time, is_active, reminder_sent, test_completed, moderator_id, mobile_number, primary_skill, primary_skill_experience, secondary_skill, secondary_skill_experience, resume_filename, secret_question, secret_answer_hash, meeting_link) FROM stdin;
8	Ujjwal	patleujjwal25@gmail.com	$2b$12$aF97l85sA9hFuR1QCplKHuutiGO7LGUl.I7xu3fhPSyd7RGYuapiy	candidate	t	https://api.dicebear.com/8.x/initials/svg?seed=Ujjwal	\N	\N	\N	t	f	f	\N	7020350064	Java Full Stack Developer	3	Kafka	2	8_ujjwalPatle02.pdf	\N	\N	\N
10	Archis Mehta	gp223296@gmail.com	$2b$12$QV/DTcnonml5hlFGRiKrAO2FzgSpFQtL3/zNnKevHH2x6Ky.TXVBO	developer	t	https://api.dicebear.com/8.x/initials/svg?seed=Archis Mehta	\N	\N	\N	t	f	f	\N	8793301099	\N	\N	\N	\N	\N	\N	\N	\N
14	Ankita Thakur	k.ankita037@gmail.com	$2b$12$hSO6h0m51r.r4ADPNhNT4OHWgb.6IfWT7yd.83rQlpN2nQjviEUEK	candidate	t	https://api.dicebear.com/8.x/initials/svg?seed=9809Ankita@	\N	\N	\N	f	f	f	\N	9082653821	Nodejs	3.8	Javascript	3.8	14_Ankita.pdf	In what city were you born?	$2b$12$NsiRK/qAptQ5jrbQ3Js94efUumlvo4B9ATlQOPq01zbz3TBxe3RTa	\N
18	Ritikesh Chavan	ritikeshchavan@gmail.com	$2b$12$0o1k3NKi8jm6/J3Dl7uWQOfyD5QEX8/Ou7COE1jbUKnAxeTMyqGIy	buyer	t	https://api.dicebear.com/8.x/initials/svg?seed=Ritikesh Chavan	\N	\N	\N	t	f	f	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N
6	Lalit Barhate	calalitbarhate@gmail.com	$2b$12$hp.rMI7h2zatD0nL9/6squEKGZwP4Rx2IMcvx1UxN/1LoWtj.jOx2	moderator	t	https://api.dicebear.com/8.x/initials/svg?seed=Lalit_Moderator	\N	\N	\N	t	f	f	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N
5	Amit Bharadwaj	abhardwaj96.ab@gmail.com	$2b$12$7KrAPXkEbhi9FemYizqegeGGB8htY2gO9GXD0ItLnx603EJzuWjOm	candidate	t	https://api.dicebear.com/8.x/initials/svg?seed=Amit Bharadwaj	\N	\N	\N	t	f	f	\N	\N	\N	\N	\N	\N	\N	\N	\N	
9	Gaurav Patil	gaurav2239396@gmail.com	$2b$12$o/FULK5w8dkhk.AVrLCGJOEQFKFNCu3Vm1oaZB1d9E/86shB02kbS	developer	t	https://api.dicebear.com/8.x/initials/svg?seed=gaurav_test	\N	\N	\N	t	f	f	\N	8793301099	\N	\N	\N	\N	\N	\N	\N	\N
20	Gaurav_SL370	gp2229396@gmail.com	$2b$12$1rLgRgZYaPzo.GM8V28nYePZMSRyONQxgBosportGvoyvJCtmTdJq	seller	t	https://api.dicebear.com/8.x/initials/svg?seed=Seller_New	\N	\N	\N	t	f	f	\N	00000	\N	\N	\N	\N	\N	\N	\N	\N
1	Admin	gp2239396@gmail.com	$2b$12$O6SmrCndaioXdngxaSyZyOdsOqeoQZ7CZEPbyRAwogcab3tuuKWFa	admin	t	https://api.dicebear.com/8.x/initials/svg?seed=Admin	\N	\N	\N	t	f	f	\N		\N	\N	\N	\N	\N	\N	\N	\N
25	dt	gp2279396@gmail.com	$2b$12$cs0HPuxRCwjAB2GKvn.cN.mX82bDnKGsy8dMBC5KoDcrRHi43OgDG	developer	t	https://api.dicebear.com/7.x/initials/svg?seed=dt	\N	\N	\N	f	f	f	\N	8779308036	java	1-3	\N	\N	\N	tt	$2b$12$Lr531UadzCy9XN3msqm9sevDBTMvUYJpe7pu11N5C9yStOZCaKiNe	\N
23	Test1	gp2259396@gmail.com	$2b$12$4Rgspgaoy8Y0Cb9cnBSo.utGkTbGOok57kwUJPe9jCsByvDPPzGc2	seller	t	https://api.dicebear.com/7.x/initials/svg?seed=Test1	\N	\N	\N	t	f	f	\N	8793301099		0-1	\N	\N	\N	t	$2b$12$5UpmI952NygEjojPro1obOkT795AOuYYc9LzhB4cQY8GfEW9ukgKS	\N
22	Test	gp2249396@gmail.com	$2b$12$AuHFfsaulUKftdMOrEeWFOcTjuCTbcmqayyQd7h3tCesxgOq3i2jC	recruiter	t	https://api.dicebear.com/7.x/initials/svg?seed=Test	\N	\N	\N	f	f	f	\N	8779308036		0-1	\N	\N	\N	t	$2b$12$lw1YdkJzQYFK9hAielSEVeqQXHA6ayIVX/hSU5pw.m153Wj5RHrKu	\N
28	admin	admin@test.com	$2b$12$U3hyO6ep5yuUXW4WRG8bFO..UpgAMLuf363qCGc3jE/RU0dp5nyI6	admin	t	https://api.dicebear.com/8.x/initials/svg?seed=User	\N	\N	\N	t	f	f	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N
24	Hiring_Central	gp2269396@gmail.com	$2b$12$xYIY8qQSFrft6DewssEoN.iIaf7sB1vZwkC70S5y9266wkQr8yOwi	recruiter	t	https://api.dicebear.com/7.x/initials/svg?seed=recruiter test	\N	\N	\N	t	f	f	\N	8793301099		0-1	\N	\N	\N	tr	$2b$12$UYlSr9Lu/4OCwftcMWlbw.7Xhd6Ux4/.QTnxdx8qN6MOjug6erQCq	\N
4	Moderator_Gaurav	pgaurav702@gmail.com	$2b$12$9gbCeGG8TFKHPiWzp6n0W.aND4mp7UgMRwqmcKXMArhEYmNuYvRDa	moderator	t	https://api.dicebear.com/8.x/initials/svg?seed=Gaurav_Moderator	\N	\N	\N	t	f	f	\N						\N	\N	\N	\N
3	Ruchita Umalkar	ruchitaumalkar@gmail.com	$2b$12$9.lnI4KK.lVQXneh/PbsTOjoeaRw6XM7ljDhHiQ//Obj90.asd4WS	candidate	t	https://api.dicebear.com/8.x/initials/svg?seed=Ruchita_Umalkar	1	2026-01-23 13:39:00	2026-01-23 13:41:00	t	f	t	\N	\N					https://res.cloudinary.com/dh9vjtajb/raw/upload/v1766909970/resumes/resume_3	\N	\N	
13	Ankita Kumari	k.ankita98@gmail.com	$2b$12$Q9HeXBAS67XQ2Vvbf6aSnOKZF/nfwFbyJUcM2IyvF38Qc0bY0awOK	candidate	t	https://api.dicebear.com/8.x/initials/svg?seed=ankita98	\N	\N	\N	f	f	f	\N	9082653821	\N	\N	\N	\N	\N	\N	\N	\N
2	Nitya Nayar	nityanayar16@gmail.com	$2b$12$.sm7t5jfGSwAtz7YZ0L6UOjp1VFTLCHVW31IJDWSQ7L59MXGU5UBS	developer	t	https://api.dicebear.com/8.x/initials/svg?seed=Nitya_Nayar	\N	\N	\N	t	f	f	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N
19	Seller_SL898	pranavsingh.imf@gmail.com	$2b$12$s5xnutKIMshLUr04bqJSy.5wa3qZZiIOJlBNJ/HK722LYbw1ZhDHG	seller	t	https://api.dicebear.com/8.x/initials/svg?seed=Pranav Receuiter	\N	\N	\N	t	f	f	\N	8793301099	\N	\N	\N	\N	\N	\N	\N	\N
12	Bhavesh Patil	patilbhavesh1223@gmail.com	$2b$12$LM6BLTo2STNWN4.Fsof1L..1QvexQpT92WJa664r7d9KecPH.JXU.	candidate	t	https://api.dicebear.com/8.x/initials/svg?seed=bhaveshpatil_23	3	2025-10-24 13:50:00	2025-10-24 13:53:00	t	f	t	6	7709954599	\N	\N	\N	\N	\N	\N	\N	
7	Pooja Devrukhkar	poojadevrukhkar1998@gmail.com	$2b$12$ML42.fbHXqV2g5NMumQgReBQzWkQh5o0u4cHG2Mu51rDzC/ujhIDe	candidate	t	https://api.dicebear.com/8.x/initials/svg?seed=Pooja	\N	\N	\N	t	f	f	\N	9619945475	\N	\N	\N	\N	\N	What is your favorite book?	$2b$12$XHM3MbQ7hq7Rsg7vtYvTW.QFlQnh0.dFWfrE5aseVKXctNhsbtcD.	
17	Seller_SL450	jayeshbarhate592@gmail.com	$2b$12$qEQb98O.ezZomRs1JRbgv.Es9m8CE//t3FtwDlcpUs374zjTSBIJW	seller	t	https://api.dicebear.com/8.x/initials/svg?seed=Jayesh Barhate	\N	\N	\N	t	f	f	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N
29	Vivek Patil	vivekpatil3636@gmail.com	$2b$12$ATRX1jspgH1KfPb4TEEAruvb9lIgiN2LeTx5LDnJDKRJWEchJ2jua	candidate	t	https://api.dicebear.com/8.x/initials/svg?seed=VivekP	\N	\N	\N	t	f	f	\N	\N	Angular ,React	4+	NodeJs	4+	https://res.cloudinary.com/dh9vjtajb/raw/upload/v1767542544/resumes/resume_29	What is my bestie name	$2b$12$zBB8wINzBhuZrv4OfvTfv.iutvmbF9KItteeZ2lmphLa/nHVfJfVO	\N
15	Vivan Santra	vivansantra@gmail.com	$2b$12$5sOUSd95ZCSdw9Gf25v8E.4Yjs0Osf98bai1xRyNlJKBZoyxqb/Z.	buyer	t	https://api.dicebear.com/8.x/initials/svg?seed=Vivan_buyer	\N	\N	\N	t	f	f	\N	8793301099	\N	\N	\N	\N	\N	\N	\N	\N
16	Nikita Umalkar	nikitaumalkar98@gmail.com	$2b$12$t4mC/LBabHBEJzRb82yw6uJvdf3SNSD.XLnmcWXMPNmVAAmq/NVxG	buyer	t	https://api.dicebear.com/8.x/initials/svg?seed=Nikita	\N	\N	\N	t	f	f	\N	9403260465	\N	\N	\N	\N	\N	\N	\N	\N
30	TestCandidateBot	test_candidate_automation@example.com	dummy_hash	candidate	t	https://api.dicebear.com/8.x/initials/svg?seed=User	1	2026-01-23 15:39:58.155156	2026-01-23 13:39:58.155156	t	f	t	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N
\.


--
-- Name: activity_log_id_seq; Type: SEQUENCE SET; Schema: public; Owner: sourcepoint_admin
--

SELECT pg_catalog.setval('public.activity_log_id_seq', 814, true);


--
-- Name: activity_update_id_seq; Type: SEQUENCE SET; Schema: public; Owner: sourcepoint_admin
--

SELECT pg_catalog.setval('public.activity_update_id_seq', 1, true);


--
-- Name: affiliate_ad_id_seq; Type: SEQUENCE SET; Schema: public; Owner: sourcepoint_admin
--

SELECT pg_catalog.setval('public.affiliate_ad_id_seq', 1, false);


--
-- Name: brd_id_seq; Type: SEQUENCE SET; Schema: public; Owner: sourcepoint_admin
--

SELECT pg_catalog.setval('public.brd_id_seq', 2, true);


--
-- Name: cart_id_seq; Type: SEQUENCE SET; Schema: public; Owner: sourcepoint_admin
--

SELECT pg_catalog.setval('public.cart_id_seq', 15, true);


--
-- Name: cart_item_id_seq; Type: SEQUENCE SET; Schema: public; Owner: sourcepoint_admin
--

SELECT pg_catalog.setval('public.cart_item_id_seq', 26, true);


--
-- Name: chat_history_id_seq; Type: SEQUENCE SET; Schema: public; Owner: sourcepoint_admin
--

SELECT pg_catalog.setval('public.chat_history_id_seq', 22, true);


--
-- Name: code_snippet_id_seq; Type: SEQUENCE SET; Schema: public; Owner: sourcepoint_admin
--

SELECT pg_catalog.setval('public.code_snippet_id_seq', 1, true);


--
-- Name: code_test_submission_id_seq; Type: SEQUENCE SET; Schema: public; Owner: sourcepoint_admin
--

SELECT pg_catalog.setval('public.code_test_submission_id_seq', 7, true);


--
-- Name: emi_payment_id_seq; Type: SEQUENCE SET; Schema: public; Owner: sourcepoint_admin
--

SELECT pg_catalog.setval('public.emi_payment_id_seq', 187, true);


--
-- Name: emi_plan_id_seq; Type: SEQUENCE SET; Schema: public; Owner: sourcepoint_admin
--

SELECT pg_catalog.setval('public.emi_plan_id_seq', 9, true);


--
-- Name: feedback_id_seq; Type: SEQUENCE SET; Schema: public; Owner: sourcepoint_admin
--

SELECT pg_catalog.setval('public.feedback_id_seq', 2, true);


--
-- Name: invoice_id_seq; Type: SEQUENCE SET; Schema: public; Owner: sourcepoint_admin
--

SELECT pg_catalog.setval('public.invoice_id_seq', 50, true);


--
-- Name: invoice_item_id_seq; Type: SEQUENCE SET; Schema: public; Owner: sourcepoint_admin
--

SELECT pg_catalog.setval('public.invoice_item_id_seq', 79, true);


--
-- Name: job_application_id_seq; Type: SEQUENCE SET; Schema: public; Owner: sourcepoint_admin
--

SELECT pg_catalog.setval('public.job_application_id_seq', 6, true);


--
-- Name: job_opening_id_seq; Type: SEQUENCE SET; Schema: public; Owner: sourcepoint_admin
--

SELECT pg_catalog.setval('public.job_opening_id_seq', 7, true);


--
-- Name: message_id_seq; Type: SEQUENCE SET; Schema: public; Owner: sourcepoint_admin
--

SELECT pg_catalog.setval('public.message_id_seq', 5, true);


--
-- Name: moderator_assignment_history_id_seq; Type: SEQUENCE SET; Schema: public; Owner: sourcepoint_admin
--

SELECT pg_catalog.setval('public.moderator_assignment_history_id_seq', 6, true);


--
-- Name: order_id_seq; Type: SEQUENCE SET; Schema: public; Owner: sourcepoint_admin
--

SELECT pg_catalog.setval('public.order_id_seq', 21, true);


--
-- Name: order_item_id_seq; Type: SEQUENCE SET; Schema: public; Owner: sourcepoint_admin
--

SELECT pg_catalog.setval('public.order_item_id_seq', 26, true);


--
-- Name: problem_statement_id_seq; Type: SEQUENCE SET; Schema: public; Owner: sourcepoint_admin
--

SELECT pg_catalog.setval('public.problem_statement_id_seq', 3, true);


--
-- Name: product_id_seq; Type: SEQUENCE SET; Schema: public; Owner: sourcepoint_admin
--

SELECT pg_catalog.setval('public.product_id_seq', 55, true);


--
-- Name: product_image_id_seq; Type: SEQUENCE SET; Schema: public; Owner: sourcepoint_admin
--

SELECT pg_catalog.setval('public.product_image_id_seq', 119, true);


--
-- Name: project_id_seq; Type: SEQUENCE SET; Schema: public; Owner: sourcepoint_admin
--

SELECT pg_catalog.setval('public.project_id_seq', 5, true);


--
-- Name: seller_inventory_id_seq; Type: SEQUENCE SET; Schema: public; Owner: sourcepoint_admin
--

SELECT pg_catalog.setval('public.seller_inventory_id_seq', 16, true);


--
-- Name: stock_request_id_seq; Type: SEQUENCE SET; Schema: public; Owner: sourcepoint_admin
--

SELECT pg_catalog.setval('public.stock_request_id_seq', 7, true);


--
-- Name: transaction_id_seq; Type: SEQUENCE SET; Schema: public; Owner: sourcepoint_admin
--

SELECT pg_catalog.setval('public.transaction_id_seq', 3, true);


--
-- Name: user_id_seq; Type: SEQUENCE SET; Schema: public; Owner: sourcepoint_admin
--

SELECT pg_catalog.setval('public.user_id_seq', 30, true);


--
-- Name: activity_log activity_log_pkey; Type: CONSTRAINT; Schema: public; Owner: sourcepoint_admin
--

ALTER TABLE ONLY public.activity_log
    ADD CONSTRAINT activity_log_pkey PRIMARY KEY (id);


--
-- Name: activity_update activity_update_pkey; Type: CONSTRAINT; Schema: public; Owner: sourcepoint_admin
--

ALTER TABLE ONLY public.activity_update
    ADD CONSTRAINT activity_update_pkey PRIMARY KEY (id);


--
-- Name: affiliate_ad affiliate_ad_ad_name_key; Type: CONSTRAINT; Schema: public; Owner: sourcepoint_admin
--

ALTER TABLE ONLY public.affiliate_ad
    ADD CONSTRAINT affiliate_ad_ad_name_key UNIQUE (ad_name);


--
-- Name: affiliate_ad affiliate_ad_pkey; Type: CONSTRAINT; Schema: public; Owner: sourcepoint_admin
--

ALTER TABLE ONLY public.affiliate_ad
    ADD CONSTRAINT affiliate_ad_pkey PRIMARY KEY (id);


--
-- Name: alembic_version alembic_version_pkc; Type: CONSTRAINT; Schema: public; Owner: sourcepoint_admin
--

ALTER TABLE ONLY public.alembic_version
    ADD CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num);


--
-- Name: brd brd_pkey; Type: CONSTRAINT; Schema: public; Owner: sourcepoint_admin
--

ALTER TABLE ONLY public.brd
    ADD CONSTRAINT brd_pkey PRIMARY KEY (id);


--
-- Name: brd brd_project_id_key; Type: CONSTRAINT; Schema: public; Owner: sourcepoint_admin
--

ALTER TABLE ONLY public.brd
    ADD CONSTRAINT brd_project_id_key UNIQUE (project_id);


--
-- Name: candidate_contacts candidate_contacts_pkey; Type: CONSTRAINT; Schema: public; Owner: sourcepoint_admin
--

ALTER TABLE ONLY public.candidate_contacts
    ADD CONSTRAINT candidate_contacts_pkey PRIMARY KEY (candidate_id, developer_id);


--
-- Name: cart_item cart_item_pkey; Type: CONSTRAINT; Schema: public; Owner: sourcepoint_admin
--

ALTER TABLE ONLY public.cart_item
    ADD CONSTRAINT cart_item_pkey PRIMARY KEY (id);


--
-- Name: cart cart_pkey; Type: CONSTRAINT; Schema: public; Owner: sourcepoint_admin
--

ALTER TABLE ONLY public.cart
    ADD CONSTRAINT cart_pkey PRIMARY KEY (id);


--
-- Name: chat_history chat_history_pkey; Type: CONSTRAINT; Schema: public; Owner: sourcepoint_admin
--

ALTER TABLE ONLY public.chat_history
    ADD CONSTRAINT chat_history_pkey PRIMARY KEY (id);


--
-- Name: code_snippet code_snippet_pkey; Type: CONSTRAINT; Schema: public; Owner: sourcepoint_admin
--

ALTER TABLE ONLY public.code_snippet
    ADD CONSTRAINT code_snippet_pkey PRIMARY KEY (id);


--
-- Name: code_test_submission code_test_submission_pkey; Type: CONSTRAINT; Schema: public; Owner: sourcepoint_admin
--

ALTER TABLE ONLY public.code_test_submission
    ADD CONSTRAINT code_test_submission_pkey PRIMARY KEY (id);


--
-- Name: emi_payment emi_payment_pkey; Type: CONSTRAINT; Schema: public; Owner: sourcepoint_admin
--

ALTER TABLE ONLY public.emi_payment
    ADD CONSTRAINT emi_payment_pkey PRIMARY KEY (id);


--
-- Name: emi_plan emi_plan_pkey; Type: CONSTRAINT; Schema: public; Owner: sourcepoint_admin
--

ALTER TABLE ONLY public.emi_plan
    ADD CONSTRAINT emi_plan_pkey PRIMARY KEY (id);


--
-- Name: feedback feedback_pkey; Type: CONSTRAINT; Schema: public; Owner: sourcepoint_admin
--

ALTER TABLE ONLY public.feedback
    ADD CONSTRAINT feedback_pkey PRIMARY KEY (id);


--
-- Name: invoice invoice_invoice_number_key; Type: CONSTRAINT; Schema: public; Owner: sourcepoint_admin
--

ALTER TABLE ONLY public.invoice
    ADD CONSTRAINT invoice_invoice_number_key UNIQUE (invoice_number);


--
-- Name: invoice_item invoice_item_pkey; Type: CONSTRAINT; Schema: public; Owner: sourcepoint_admin
--

ALTER TABLE ONLY public.invoice_item
    ADD CONSTRAINT invoice_item_pkey PRIMARY KEY (id);


--
-- Name: invoice invoice_pkey; Type: CONSTRAINT; Schema: public; Owner: sourcepoint_admin
--

ALTER TABLE ONLY public.invoice
    ADD CONSTRAINT invoice_pkey PRIMARY KEY (id);


--
-- Name: job_application job_application_pkey; Type: CONSTRAINT; Schema: public; Owner: sourcepoint_admin
--

ALTER TABLE ONLY public.job_application
    ADD CONSTRAINT job_application_pkey PRIMARY KEY (id);


--
-- Name: job_opening job_opening_job_id_key; Type: CONSTRAINT; Schema: public; Owner: sourcepoint_admin
--

ALTER TABLE ONLY public.job_opening
    ADD CONSTRAINT job_opening_job_id_key UNIQUE (job_id);


--
-- Name: job_opening job_opening_pkey; Type: CONSTRAINT; Schema: public; Owner: sourcepoint_admin
--

ALTER TABLE ONLY public.job_opening
    ADD CONSTRAINT job_opening_pkey PRIMARY KEY (id);


--
-- Name: learning_content learning_content_pkey; Type: CONSTRAINT; Schema: public; Owner: sourcepoint_admin
--

ALTER TABLE ONLY public.learning_content
    ADD CONSTRAINT learning_content_pkey PRIMARY KEY (id);


--
-- Name: message message_pkey; Type: CONSTRAINT; Schema: public; Owner: sourcepoint_admin
--

ALTER TABLE ONLY public.message
    ADD CONSTRAINT message_pkey PRIMARY KEY (id);


--
-- Name: moderator_assignment_history moderator_assignment_history_pkey; Type: CONSTRAINT; Schema: public; Owner: sourcepoint_admin
--

ALTER TABLE ONLY public.moderator_assignment_history
    ADD CONSTRAINT moderator_assignment_history_pkey PRIMARY KEY (id);


--
-- Name: order_item order_item_pkey; Type: CONSTRAINT; Schema: public; Owner: sourcepoint_admin
--

ALTER TABLE ONLY public.order_item
    ADD CONSTRAINT order_item_pkey PRIMARY KEY (id);


--
-- Name: order order_order_number_key; Type: CONSTRAINT; Schema: public; Owner: sourcepoint_admin
--

ALTER TABLE ONLY public."order"
    ADD CONSTRAINT order_order_number_key UNIQUE (order_number);


--
-- Name: order order_pkey; Type: CONSTRAINT; Schema: public; Owner: sourcepoint_admin
--

ALTER TABLE ONLY public."order"
    ADD CONSTRAINT order_pkey PRIMARY KEY (id);


--
-- Name: problem_statement problem_statement_pkey; Type: CONSTRAINT; Schema: public; Owner: sourcepoint_admin
--

ALTER TABLE ONLY public.problem_statement
    ADD CONSTRAINT problem_statement_pkey PRIMARY KEY (id);


--
-- Name: product_image product_image_pkey; Type: CONSTRAINT; Schema: public; Owner: sourcepoint_admin
--

ALTER TABLE ONLY public.product_image
    ADD CONSTRAINT product_image_pkey PRIMARY KEY (id);


--
-- Name: product product_pkey; Type: CONSTRAINT; Schema: public; Owner: sourcepoint_admin
--

ALTER TABLE ONLY public.product
    ADD CONSTRAINT product_pkey PRIMARY KEY (id);


--
-- Name: product product_product_code_key; Type: CONSTRAINT; Schema: public; Owner: sourcepoint_admin
--

ALTER TABLE ONLY public.product
    ADD CONSTRAINT product_product_code_key UNIQUE (product_code);


--
-- Name: project project_pkey; Type: CONSTRAINT; Schema: public; Owner: sourcepoint_admin
--

ALTER TABLE ONLY public.project
    ADD CONSTRAINT project_pkey PRIMARY KEY (id);


--
-- Name: seller_inventory seller_inventory_pkey; Type: CONSTRAINT; Schema: public; Owner: sourcepoint_admin
--

ALTER TABLE ONLY public.seller_inventory
    ADD CONSTRAINT seller_inventory_pkey PRIMARY KEY (id);


--
-- Name: stock_request stock_request_pkey; Type: CONSTRAINT; Schema: public; Owner: sourcepoint_admin
--

ALTER TABLE ONLY public.stock_request
    ADD CONSTRAINT stock_request_pkey PRIMARY KEY (id);


--
-- Name: transaction transaction_pkey; Type: CONSTRAINT; Schema: public; Owner: sourcepoint_admin
--

ALTER TABLE ONLY public.transaction
    ADD CONSTRAINT transaction_pkey PRIMARY KEY (id);


--
-- Name: user user_email_key; Type: CONSTRAINT; Schema: public; Owner: sourcepoint_admin
--

ALTER TABLE ONLY public."user"
    ADD CONSTRAINT user_email_key UNIQUE (email);


--
-- Name: user user_pkey; Type: CONSTRAINT; Schema: public; Owner: sourcepoint_admin
--

ALTER TABLE ONLY public."user"
    ADD CONSTRAINT user_pkey PRIMARY KEY (id);


--
-- Name: user user_username_key; Type: CONSTRAINT; Schema: public; Owner: sourcepoint_admin
--

ALTER TABLE ONLY public."user"
    ADD CONSTRAINT user_username_key UNIQUE (username);


--
-- Name: ix_activity_update_timestamp; Type: INDEX; Schema: public; Owner: sourcepoint_admin
--

CREATE INDEX ix_activity_update_timestamp ON public.activity_update USING btree ("timestamp");


--
-- Name: ix_code_snippet_timestamp; Type: INDEX; Schema: public; Owner: sourcepoint_admin
--

CREATE INDEX ix_code_snippet_timestamp ON public.code_snippet USING btree ("timestamp");


--
-- Name: ix_code_test_submission_submitted_at; Type: INDEX; Schema: public; Owner: sourcepoint_admin
--

CREATE INDEX ix_code_test_submission_submitted_at ON public.code_test_submission USING btree (submitted_at);


--
-- Name: ix_job_application_applied_at; Type: INDEX; Schema: public; Owner: sourcepoint_admin
--

CREATE INDEX ix_job_application_applied_at ON public.job_application USING btree (applied_at);


--
-- Name: ix_job_opening_created_at; Type: INDEX; Schema: public; Owner: sourcepoint_admin
--

CREATE INDEX ix_job_opening_created_at ON public.job_opening USING btree (created_at);


--
-- Name: ix_message_recipient_id; Type: INDEX; Schema: public; Owner: sourcepoint_admin
--

CREATE INDEX ix_message_recipient_id ON public.message USING btree (recipient_id);


--
-- Name: ix_message_sender_id; Type: INDEX; Schema: public; Owner: sourcepoint_admin
--

CREATE INDEX ix_message_sender_id ON public.message USING btree (sender_id);


--
-- Name: ix_message_timestamp; Type: INDEX; Schema: public; Owner: sourcepoint_admin
--

CREATE INDEX ix_message_timestamp ON public.message USING btree ("timestamp");


--
-- Name: ix_order_created_at; Type: INDEX; Schema: public; Owner: sourcepoint_admin
--

CREATE INDEX ix_order_created_at ON public."order" USING btree (created_at);


--
-- Name: ix_order_status; Type: INDEX; Schema: public; Owner: sourcepoint_admin
--

CREATE INDEX ix_order_status ON public."order" USING btree (status);


--
-- Name: ix_product_category; Type: INDEX; Schema: public; Owner: sourcepoint_admin
--

CREATE INDEX ix_product_category ON public.product USING btree (category);


--
-- Name: ix_product_seller_id; Type: INDEX; Schema: public; Owner: sourcepoint_admin
--

CREATE INDEX ix_product_seller_id ON public.product USING btree (seller_id);


--
-- Name: ix_product_stock; Type: INDEX; Schema: public; Owner: sourcepoint_admin
--

CREATE INDEX ix_product_stock ON public.product USING btree (stock);


--
-- Name: activity_log activity_log_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: sourcepoint_admin
--

ALTER TABLE ONLY public.activity_log
    ADD CONSTRAINT activity_log_user_id_fkey FOREIGN KEY (user_id) REFERENCES public."user"(id);


--
-- Name: activity_update activity_update_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: sourcepoint_admin
--

ALTER TABLE ONLY public.activity_update
    ADD CONSTRAINT activity_update_user_id_fkey FOREIGN KEY (user_id) REFERENCES public."user"(id);


--
-- Name: brd brd_project_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: sourcepoint_admin
--

ALTER TABLE ONLY public.brd
    ADD CONSTRAINT brd_project_id_fkey FOREIGN KEY (project_id) REFERENCES public.project(id);


--
-- Name: candidate_contacts candidate_contacts_candidate_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: sourcepoint_admin
--

ALTER TABLE ONLY public.candidate_contacts
    ADD CONSTRAINT candidate_contacts_candidate_id_fkey FOREIGN KEY (candidate_id) REFERENCES public."user"(id);


--
-- Name: candidate_contacts candidate_contacts_developer_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: sourcepoint_admin
--

ALTER TABLE ONLY public.candidate_contacts
    ADD CONSTRAINT candidate_contacts_developer_id_fkey FOREIGN KEY (developer_id) REFERENCES public."user"(id);


--
-- Name: cart_item cart_item_cart_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: sourcepoint_admin
--

ALTER TABLE ONLY public.cart_item
    ADD CONSTRAINT cart_item_cart_id_fkey FOREIGN KEY (cart_id) REFERENCES public.cart(id);


--
-- Name: cart_item cart_item_product_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: sourcepoint_admin
--

ALTER TABLE ONLY public.cart_item
    ADD CONSTRAINT cart_item_product_id_fkey FOREIGN KEY (product_id) REFERENCES public.product(id);


--
-- Name: cart cart_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: sourcepoint_admin
--

ALTER TABLE ONLY public.cart
    ADD CONSTRAINT cart_user_id_fkey FOREIGN KEY (user_id) REFERENCES public."user"(id);


--
-- Name: chat_history chat_history_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: sourcepoint_admin
--

ALTER TABLE ONLY public.chat_history
    ADD CONSTRAINT chat_history_user_id_fkey FOREIGN KEY (user_id) REFERENCES public."user"(id);


--
-- Name: code_snippet code_snippet_recipient_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: sourcepoint_admin
--

ALTER TABLE ONLY public.code_snippet
    ADD CONSTRAINT code_snippet_recipient_id_fkey FOREIGN KEY (recipient_id) REFERENCES public."user"(id);


--
-- Name: code_snippet code_snippet_sender_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: sourcepoint_admin
--

ALTER TABLE ONLY public.code_snippet
    ADD CONSTRAINT code_snippet_sender_id_fkey FOREIGN KEY (sender_id) REFERENCES public."user"(id);


--
-- Name: code_test_submission code_test_submission_candidate_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: sourcepoint_admin
--

ALTER TABLE ONLY public.code_test_submission
    ADD CONSTRAINT code_test_submission_candidate_id_fkey FOREIGN KEY (candidate_id) REFERENCES public."user"(id);


--
-- Name: code_test_submission code_test_submission_recipient_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: sourcepoint_admin
--

ALTER TABLE ONLY public.code_test_submission
    ADD CONSTRAINT code_test_submission_recipient_id_fkey FOREIGN KEY (recipient_id) REFERENCES public."user"(id);


--
-- Name: emi_payment emi_payment_plan_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: sourcepoint_admin
--

ALTER TABLE ONLY public.emi_payment
    ADD CONSTRAINT emi_payment_plan_id_fkey FOREIGN KEY (plan_id) REFERENCES public.emi_plan(id);


--
-- Name: emi_plan emi_plan_borrower_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: sourcepoint_admin
--

ALTER TABLE ONLY public.emi_plan
    ADD CONSTRAINT emi_plan_borrower_id_fkey FOREIGN KEY (borrower_id) REFERENCES public."user"(id);


--
-- Name: emi_plan emi_plan_lender_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: sourcepoint_admin
--

ALTER TABLE ONLY public.emi_plan
    ADD CONSTRAINT emi_plan_lender_id_fkey FOREIGN KEY (lender_id) REFERENCES public."user"(id);


--
-- Name: feedback feedback_candidate_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: sourcepoint_admin
--

ALTER TABLE ONLY public.feedback
    ADD CONSTRAINT feedback_candidate_id_fkey FOREIGN KEY (candidate_id) REFERENCES public."user"(id);


--
-- Name: feedback feedback_moderator_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: sourcepoint_admin
--

ALTER TABLE ONLY public.feedback
    ADD CONSTRAINT feedback_moderator_id_fkey FOREIGN KEY (moderator_id) REFERENCES public."user"(id);


--
-- Name: invoice invoice_admin_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: sourcepoint_admin
--

ALTER TABLE ONLY public.invoice
    ADD CONSTRAINT invoice_admin_id_fkey FOREIGN KEY (admin_id) REFERENCES public."user"(id);


--
-- Name: invoice_item invoice_item_invoice_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: sourcepoint_admin
--

ALTER TABLE ONLY public.invoice_item
    ADD CONSTRAINT invoice_item_invoice_id_fkey FOREIGN KEY (invoice_id) REFERENCES public.invoice(id);


--
-- Name: job_application job_application_job_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: sourcepoint_admin
--

ALTER TABLE ONLY public.job_application
    ADD CONSTRAINT job_application_job_id_fkey FOREIGN KEY (job_id) REFERENCES public.job_opening(id);


--
-- Name: job_application job_application_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: sourcepoint_admin
--

ALTER TABLE ONLY public.job_application
    ADD CONSTRAINT job_application_user_id_fkey FOREIGN KEY (user_id) REFERENCES public."user"(id);


--
-- Name: message message_recipient_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: sourcepoint_admin
--

ALTER TABLE ONLY public.message
    ADD CONSTRAINT message_recipient_id_fkey FOREIGN KEY (recipient_id) REFERENCES public."user"(id);


--
-- Name: message message_sender_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: sourcepoint_admin
--

ALTER TABLE ONLY public.message
    ADD CONSTRAINT message_sender_id_fkey FOREIGN KEY (sender_id) REFERENCES public."user"(id);


--
-- Name: moderator_assignment_history moderator_assignment_history_candidate_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: sourcepoint_admin
--

ALTER TABLE ONLY public.moderator_assignment_history
    ADD CONSTRAINT moderator_assignment_history_candidate_id_fkey FOREIGN KEY (candidate_id) REFERENCES public."user"(id);


--
-- Name: moderator_assignment_history moderator_assignment_history_moderator_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: sourcepoint_admin
--

ALTER TABLE ONLY public.moderator_assignment_history
    ADD CONSTRAINT moderator_assignment_history_moderator_id_fkey FOREIGN KEY (moderator_id) REFERENCES public."user"(id);


--
-- Name: moderator_assignment_history moderator_assignment_history_problem_statement_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: sourcepoint_admin
--

ALTER TABLE ONLY public.moderator_assignment_history
    ADD CONSTRAINT moderator_assignment_history_problem_statement_id_fkey FOREIGN KEY (problem_statement_id) REFERENCES public.problem_statement(id);


--
-- Name: order_item order_item_order_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: sourcepoint_admin
--

ALTER TABLE ONLY public.order_item
    ADD CONSTRAINT order_item_order_id_fkey FOREIGN KEY (order_id) REFERENCES public."order"(id);


--
-- Name: order order_seller_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: sourcepoint_admin
--

ALTER TABLE ONLY public."order"
    ADD CONSTRAINT order_seller_id_fkey FOREIGN KEY (seller_id) REFERENCES public."user"(id);


--
-- Name: order order_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: sourcepoint_admin
--

ALTER TABLE ONLY public."order"
    ADD CONSTRAINT order_user_id_fkey FOREIGN KEY (user_id) REFERENCES public."user"(id);


--
-- Name: problem_statement problem_statement_created_by_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: sourcepoint_admin
--

ALTER TABLE ONLY public.problem_statement
    ADD CONSTRAINT problem_statement_created_by_id_fkey FOREIGN KEY (created_by_id) REFERENCES public."user"(id);


--
-- Name: product_image product_image_product_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: sourcepoint_admin
--

ALTER TABLE ONLY public.product_image
    ADD CONSTRAINT product_image_product_id_fkey FOREIGN KEY (product_id) REFERENCES public.product(id);


--
-- Name: product product_seller_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: sourcepoint_admin
--

ALTER TABLE ONLY public.product
    ADD CONSTRAINT product_seller_id_fkey FOREIGN KEY (seller_id) REFERENCES public."user"(id);


--
-- Name: seller_inventory seller_inventory_product_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: sourcepoint_admin
--

ALTER TABLE ONLY public.seller_inventory
    ADD CONSTRAINT seller_inventory_product_id_fkey FOREIGN KEY (product_id) REFERENCES public.product(id);


--
-- Name: seller_inventory seller_inventory_seller_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: sourcepoint_admin
--

ALTER TABLE ONLY public.seller_inventory
    ADD CONSTRAINT seller_inventory_seller_id_fkey FOREIGN KEY (seller_id) REFERENCES public."user"(id);


--
-- Name: stock_request stock_request_product_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: sourcepoint_admin
--

ALTER TABLE ONLY public.stock_request
    ADD CONSTRAINT stock_request_product_id_fkey FOREIGN KEY (product_id) REFERENCES public.product(id);


--
-- Name: stock_request stock_request_seller_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: sourcepoint_admin
--

ALTER TABLE ONLY public.stock_request
    ADD CONSTRAINT stock_request_seller_id_fkey FOREIGN KEY (seller_id) REFERENCES public."user"(id);


--
-- Name: transaction transaction_project_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: sourcepoint_admin
--

ALTER TABLE ONLY public.transaction
    ADD CONSTRAINT transaction_project_id_fkey FOREIGN KEY (project_id) REFERENCES public.project(id);


--
-- Name: user user_moderator_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: sourcepoint_admin
--

ALTER TABLE ONLY public."user"
    ADD CONSTRAINT user_moderator_id_fkey FOREIGN KEY (moderator_id) REFERENCES public."user"(id);


--
-- Name: user user_problem_statement_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: sourcepoint_admin
--

ALTER TABLE ONLY public."user"
    ADD CONSTRAINT user_problem_statement_id_fkey FOREIGN KEY (problem_statement_id) REFERENCES public.problem_statement(id);


--
-- Name: activity_update; Type: ROW SECURITY; Schema: public; Owner: sourcepoint_admin
--

ALTER TABLE public.activity_update ENABLE ROW LEVEL SECURITY;

--
-- Name: affiliate_ad; Type: ROW SECURITY; Schema: public; Owner: sourcepoint_admin
--

ALTER TABLE public.affiliate_ad ENABLE ROW LEVEL SECURITY;

--
-- Name: brd; Type: ROW SECURITY; Schema: public; Owner: sourcepoint_admin
--

ALTER TABLE public.brd ENABLE ROW LEVEL SECURITY;

--
-- Name: candidate_contacts; Type: ROW SECURITY; Schema: public; Owner: sourcepoint_admin
--

ALTER TABLE public.candidate_contacts ENABLE ROW LEVEL SECURITY;

--
-- Name: code_snippet; Type: ROW SECURITY; Schema: public; Owner: sourcepoint_admin
--

ALTER TABLE public.code_snippet ENABLE ROW LEVEL SECURITY;

--
-- Name: code_test_submission; Type: ROW SECURITY; Schema: public; Owner: sourcepoint_admin
--

ALTER TABLE public.code_test_submission ENABLE ROW LEVEL SECURITY;

--
-- Name: feedback; Type: ROW SECURITY; Schema: public; Owner: sourcepoint_admin
--

ALTER TABLE public.feedback ENABLE ROW LEVEL SECURITY;

--
-- Name: invoice; Type: ROW SECURITY; Schema: public; Owner: sourcepoint_admin
--

ALTER TABLE public.invoice ENABLE ROW LEVEL SECURITY;

--
-- Name: invoice_item; Type: ROW SECURITY; Schema: public; Owner: sourcepoint_admin
--

ALTER TABLE public.invoice_item ENABLE ROW LEVEL SECURITY;

--
-- Name: job_application; Type: ROW SECURITY; Schema: public; Owner: sourcepoint_admin
--

ALTER TABLE public.job_application ENABLE ROW LEVEL SECURITY;

--
-- Name: job_opening; Type: ROW SECURITY; Schema: public; Owner: sourcepoint_admin
--

ALTER TABLE public.job_opening ENABLE ROW LEVEL SECURITY;

--
-- Name: learning_content; Type: ROW SECURITY; Schema: public; Owner: sourcepoint_admin
--

ALTER TABLE public.learning_content ENABLE ROW LEVEL SECURITY;

--
-- Name: message; Type: ROW SECURITY; Schema: public; Owner: sourcepoint_admin
--

ALTER TABLE public.message ENABLE ROW LEVEL SECURITY;

--
-- Name: moderator_assignment_history; Type: ROW SECURITY; Schema: public; Owner: sourcepoint_admin
--

ALTER TABLE public.moderator_assignment_history ENABLE ROW LEVEL SECURITY;

--
-- Name: problem_statement; Type: ROW SECURITY; Schema: public; Owner: sourcepoint_admin
--

ALTER TABLE public.problem_statement ENABLE ROW LEVEL SECURITY;

--
-- Name: project; Type: ROW SECURITY; Schema: public; Owner: sourcepoint_admin
--

ALTER TABLE public.project ENABLE ROW LEVEL SECURITY;

--
-- Name: transaction; Type: ROW SECURITY; Schema: public; Owner: sourcepoint_admin
--

ALTER TABLE public.transaction ENABLE ROW LEVEL SECURITY;

--
-- Name: user; Type: ROW SECURITY; Schema: public; Owner: sourcepoint_admin
--

ALTER TABLE public."user" ENABLE ROW LEVEL SECURITY;

--
-- PostgreSQL database dump complete
--

\unrestrict kqO8E5XeiZYUDUhIKkYJvajOjESFI5ihR8nkwkF4bYbD6aDxxa4rx64i0rCAHGM

