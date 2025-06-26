-- Mitch Quick - Auction Flipping Tracker
-- Complete SQL Schema for Supabase PostgreSQL

-- Note: The 'users' table is managed by Supabase Auth automatically
-- No need to create it manually

-- Create ENUM for item status
CREATE TYPE item_status AS ENUM ('watch', 'won', 'listed', 'sold');

-- Auctions table
CREATE TABLE auction (
    id SERIAL PRIMARY KEY,
    title VARCHAR(200) NOT NULL,
    date DATE NOT NULL,
    location VARCHAR(200),
    url TEXT,
    notes TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Partners table
CREATE TABLE partner (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(120),
    created_at TIMESTAMP DEFAULT NOW()
);

-- Items table
CREATE TABLE item (
    id SERIAL PRIMARY KEY,
    auction_id INTEGER REFERENCES auction(id) ON DELETE CASCADE,
    lot_number VARCHAR(50),
    title VARCHAR(200) NOT NULL,
    description TEXT,
    planned_max_bid DECIMAL(10,2),
    target_resale_price DECIMAL(10,2),
    status item_status DEFAULT 'watch',
    purchase_price DECIMAL(10,2),
    refurb_cost DECIMAL(10,2) DEFAULT 0,
    list_date DATE,
    list_channel VARCHAR(100),
    sale_date DATE,
    sale_price DECIMAL(10,2),
    sale_fees DECIMAL(10,2) DEFAULT 0,
    shipping_cost DECIMAL(10,2) DEFAULT 0,
    multiple_pieces BOOLEAN DEFAULT FALSE,
    pieces_total INTEGER,
    pieces_remaining INTEGER,
    ebay_suggested_price DECIMAL(10,2),
    ebay_price_updated TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Item Partners table
CREATE TABLE item_partner (
    id SERIAL PRIMARY KEY,
    item_id INTEGER REFERENCES item(id) ON DELETE CASCADE,
    partner_id INTEGER REFERENCES partner(id) ON DELETE CASCADE,
    pct_share DECIMAL(5,2) NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Item Expenses table
CREATE TABLE item_expense (
    id SERIAL PRIMARY KEY,
    item_id INTEGER REFERENCES item(id) ON DELETE CASCADE,
    description VARCHAR(200) NOT NULL,
    amount DECIMAL(10,2) NOT NULL,
    date DATE NOT NULL DEFAULT CURRENT_DATE,
    category VARCHAR(100),
    notes TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Item Sales table (note: table name is 'item_sales', not 'item_sale')
CREATE TABLE item_sales (
    id SERIAL PRIMARY KEY,
    item_id INTEGER REFERENCES item(id) ON DELETE CASCADE,
    pieces_sold INTEGER NOT NULL,
    sale_price_per_piece DECIMAL(10,2) NOT NULL,
    total_sale_amount DECIMAL(10,2) NOT NULL,
    sale_date DATE NOT NULL DEFAULT CURRENT_DATE,
    buyer_info VARCHAR(200),
    sale_channel VARCHAR(100),
    notes TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Create indexes for better performance
CREATE INDEX idx_item_auction_id ON item(auction_id);
CREATE INDEX idx_item_status ON item(status);
CREATE INDEX idx_item_partner_item_id ON item_partner(item_id);
CREATE INDEX idx_item_partner_partner_id ON item_partner(partner_id);
CREATE INDEX idx_item_expense_item_id ON item_expense(item_id);
CREATE INDEX idx_item_sales_item_id ON item_sales(item_id);

-- Create triggers for updated_at timestamps
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_auction_updated_at BEFORE UPDATE ON auction
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_item_updated_at BEFORE UPDATE ON item
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_item_expense_updated_at BEFORE UPDATE ON item_expense
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_item_sales_updated_at BEFORE UPDATE ON item_sales
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column(); 