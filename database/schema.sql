CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    wallet_address VARCHAR(34) UNIQUE NOT NULL,
    usage_count INTEGER DEFAULT 0,
    usage_limit INTEGER DEFAULT 10,
    payment_status VARCHAR(10) DEFAULT 'free',
    subscription_type VARCHAR(20) DEFAULT 'free',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE transactions (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    tx_id VARCHAR(64) UNIQUE NOT NULL,
    amount DECIMAL(18,6) NOT NULL,
    status VARCHAR(20) DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE TABLE subscription_plans (
    id SERIAL PRIMARY KEY,
    name VARCHAR(20) NOT NULL,
    trx_amount INTEGER NOT NULL,
    usage_limit INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

INSERT INTO subscription_plans (name, trx_amount, usage_limit) VALUES
    ('basic', 100000, 1000),
    ('premium', 300000, 5000),
    ('unlimited', 1000000, 15000); 