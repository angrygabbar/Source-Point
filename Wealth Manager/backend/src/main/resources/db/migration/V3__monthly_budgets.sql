CREATE TABLE monthly_budgets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    month DATE NOT NULL CHECK (month = date_trunc('month', month)::date),
    category VARCHAR(40) NOT NULL CHECK (
        category IN (
            'EMI', 'RENT', 'GROCERY', 'FOOD', 'UTILITIES', 'FUEL',
            'ENTERTAINMENT', 'SHOPPING', 'TRAVEL', 'INSURANCE',
            'MEDICAL', 'MISCELLANEOUS'
        )
    ),
    limit_amount NUMERIC(15,2) NOT NULL CHECK (limit_amount > 0),
    alert_threshold_percentage NUMERIC(5,2) NOT NULL
        CHECK (alert_threshold_percentage >= 1 AND alert_threshold_percentage <= 100),
    notes VARCHAR(300),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uk_monthly_budgets_user_month_category UNIQUE (user_id, month, category)
);

CREATE INDEX idx_monthly_budgets_user_month ON monthly_budgets(user_id, month);

INSERT INTO monthly_budgets (
    id, user_id, month, category, limit_amount, alert_threshold_percentage, notes
) VALUES
('71111111-1111-1111-1111-111111111111','11111111-1111-1111-1111-111111111111','2026-05-01','EMI',40000,90,'Fixed debt payment'),
('72222222-2222-2222-2222-222222222222','11111111-1111-1111-1111-111111111111','2026-05-01','RENT',11000,95,'Monthly rent'),
('73333333-3333-3333-3333-333333333333','11111111-1111-1111-1111-111111111111','2026-05-01','GROCERY',7000,80,'Household essentials'),
('74444444-4444-4444-4444-444444444444','11111111-1111-1111-1111-111111111111','2026-05-01','FOOD',9000,80,'Dining and delivery'),
('75555555-5555-5555-5555-555555555555','11111111-1111-1111-1111-111111111111','2026-05-01','UTILITIES',3500,85,'Electricity, internet and phone'),
('76666666-6666-6666-6666-666666666666','11111111-1111-1111-1111-111111111111','2026-05-01','FUEL',4500,85,'Fuel and local transport'),
('77777777-7777-7777-7777-777777777777','11111111-1111-1111-1111-111111111111','2026-05-01','ENTERTAINMENT',3500,75,'Subscriptions and leisure'),
('78888888-8888-8888-8888-888888888888','11111111-1111-1111-1111-111111111111','2026-05-01','SHOPPING',5000,75,'Personal purchases'),
('79999999-9999-9999-9999-999999999999','11111111-1111-1111-1111-111111111111','2026-05-01','INSURANCE',3000,90,'Insurance premiums'),
('7aaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa','11111111-1111-1111-1111-111111111111','2026-05-01','MEDICAL',2500,80,'Medical buffer'),
('7bbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb','11111111-1111-1111-1111-111111111111','2026-05-01','MISCELLANEOUS',8000,75,'Unplanned monthly costs');

