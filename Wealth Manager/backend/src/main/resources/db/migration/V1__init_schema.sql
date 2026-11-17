CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(120) NOT NULL,
    email VARCHAR(180) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    age INTEGER NOT NULL CHECK (age >= 18),
    marital_status VARCHAR(40) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE monthly_finance (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    month DATE NOT NULL CHECK (month = date_trunc('month', month)::date),
    salary NUMERIC(15,2) NOT NULL CHECK (salary >= 0),
    bonus NUMERIC(15,2) NOT NULL CHECK (bonus >= 0),
    freelance_income NUMERIC(15,2) NOT NULL CHECK (freelance_income >= 0),
    other_income NUMERIC(15,2) NOT NULL CHECK (other_income >= 0),
    emi NUMERIC(15,2) NOT NULL CHECK (emi >= 0),
    rent NUMERIC(15,2) NOT NULL CHECK (rent >= 0),
    grocery NUMERIC(15,2) NOT NULL CHECK (grocery >= 0),
    food NUMERIC(15,2) NOT NULL CHECK (food >= 0),
    utilities NUMERIC(15,2) NOT NULL CHECK (utilities >= 0),
    fuel NUMERIC(15,2) NOT NULL CHECK (fuel >= 0),
    entertainment NUMERIC(15,2) NOT NULL CHECK (entertainment >= 0),
    shopping NUMERIC(15,2) NOT NULL CHECK (shopping >= 0),
    travel NUMERIC(15,2) NOT NULL CHECK (travel >= 0),
    insurance NUMERIC(15,2) NOT NULL CHECK (insurance >= 0),
    medical NUMERIC(15,2) NOT NULL CHECK (medical >= 0),
    miscellaneous NUMERIC(15,2) NOT NULL CHECK (miscellaneous >= 0),
    sip_monthly_contribution NUMERIC(15,2) NOT NULL CHECK (sip_monthly_contribution >= 0),
    sip_current_value NUMERIC(15,2) NOT NULL CHECK (sip_current_value >= 0),
    stock_investment_amount NUMERIC(15,2) NOT NULL CHECK (stock_investment_amount >= 0),
    stock_current_value NUMERIC(15,2) NOT NULL CHECK (stock_current_value >= 0),
    epf_value NUMERIC(15,2) NOT NULL CHECK (epf_value >= 0),
    ppf_value NUMERIC(15,2) NOT NULL CHECK (ppf_value >= 0),
    nps_value NUMERIC(15,2) NOT NULL CHECK (nps_value >= 0),
    fixed_deposit_value NUMERIC(15,2) NOT NULL CHECK (fixed_deposit_value >= 0),
    other_investments NUMERIC(15,2) NOT NULL CHECK (other_investments >= 0),
    savings_account_balance NUMERIC(15,2) NOT NULL CHECK (savings_account_balance >= 0),
    emergency_fund_balance NUMERIC(15,2) NOT NULL CHECK (emergency_fund_balance >= 0),
    house_fund_balance NUMERIC(15,2) NOT NULL CHECK (house_fund_balance >= 0),
    home_loan NUMERIC(15,2) NOT NULL CHECK (home_loan >= 0),
    personal_loan NUMERIC(15,2) NOT NULL CHECK (personal_loan >= 0),
    vehicle_loan NUMERIC(15,2) NOT NULL CHECK (vehicle_loan >= 0),
    credit_card_outstanding NUMERIC(15,2) NOT NULL CHECK (credit_card_outstanding >= 0),
    other_loan NUMERIC(15,2) NOT NULL CHECK (other_loan >= 0),
    total_income NUMERIC(15,2) NOT NULL,
    total_expenses NUMERIC(15,2) NOT NULL,
    total_savings NUMERIC(15,2) NOT NULL,
    savings_rate NUMERIC(8,2) NOT NULL,
    net_worth NUMERIC(15,2) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uk_monthly_finance_user_month UNIQUE (user_id, month)
);

CREATE INDEX idx_monthly_finance_user_month ON monthly_finance(user_id, month);
CREATE INDEX idx_monthly_finance_user_created ON monthly_finance(user_id, created_at);

CREATE TABLE goals (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    goal_type VARCHAR(40) NOT NULL CHECK (goal_type IN ('EMERGENCY_FUND','HOUSE_PURCHASE','CAR_PURCHASE','RETIREMENT_FUND','VACATION','CHILD_EDUCATION','CUSTOM')),
    goal_name VARCHAR(160) NOT NULL,
    target_amount NUMERIC(15,2) NOT NULL CHECK (target_amount > 0),
    current_amount NUMERIC(15,2) NOT NULL CHECK (current_amount >= 0),
    target_date DATE NOT NULL,
    monthly_contribution NUMERIC(15,2) NOT NULL CHECK (monthly_contribution >= 0),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CHECK (current_amount <= target_amount)
);

CREATE INDEX idx_goals_user_type ON goals(user_id, goal_type);

CREATE TABLE investments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    investment_type VARCHAR(40) NOT NULL CHECK (investment_type IN ('MUTUAL_FUND','STOCK','FD','PPF','EPF','NPS','OTHER')),
    investment_name VARCHAR(160) NOT NULL,
    invested_amount NUMERIC(15,2) NOT NULL CHECK (invested_amount >= 0),
    current_value NUMERIC(15,2) NOT NULL CHECK (current_value >= 0),
    quantity NUMERIC(15,4) CHECK (quantity >= 0),
    average_price NUMERIC(15,2) CHECK (average_price >= 0),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_investments_user_type ON investments(user_id, investment_type);

CREATE TABLE loans (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    loan_name VARCHAR(160) NOT NULL,
    outstanding_amount NUMERIC(15,2) NOT NULL CHECK (outstanding_amount >= 0),
    interest_rate NUMERIC(8,2) NOT NULL CHECK (interest_rate >= 0 AND interest_rate <= 100),
    emi NUMERIC(15,2) NOT NULL CHECK (emi > 0),
    remaining_tenure_months INTEGER NOT NULL CHECK (remaining_tenure_months > 0),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_loans_user ON loans(user_id);

CREATE TABLE reports (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    month DATE NOT NULL CHECK (month = date_trunc('month', month)::date),
    income_total NUMERIC(15,2) NOT NULL,
    expense_total NUMERIC(15,2) NOT NULL,
    savings_total NUMERIC(15,2) NOT NULL,
    investment_total NUMERIC(15,2) NOT NULL,
    net_worth NUMERIC(15,2) NOT NULL,
    goal_progress_average NUMERIC(8,2) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uk_reports_user_month UNIQUE (user_id, month)
);

CREATE INDEX idx_reports_user_month ON reports(user_id, month);

