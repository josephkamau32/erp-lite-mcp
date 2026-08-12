CREATE TABLE sales_orders (
    order_id VARCHAR(50) PRIMARY KEY,
    customer_name VARCHAR(255) NOT NULL,
    status VARCHAR(50) NOT NULL,
    order_date DATE NOT NULL,
    total_value DECIMAL(10, 2) NOT NULL
);

CREATE TABLE inventory_items (
    material_id VARCHAR(50) PRIMARY KEY,
    description VARCHAR(255) NOT NULL,
    quantity_on_hand INT NOT NULL,
    reorder_point INT NOT NULL,
    warehouse VARCHAR(50) NOT NULL
);

CREATE TABLE purchase_requisitions (
    requisition_id VARCHAR(50) PRIMARY KEY,
    material_id VARCHAR(50) NOT NULL,
    quantity INT NOT NULL,
    requested_by VARCHAR(100) NOT NULL,
    status VARCHAR(50) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    approved_at TIMESTAMP NULL,
    FOREIGN KEY (material_id) REFERENCES inventory_items(material_id)
);

-- Seed Data for sales_orders
INSERT INTO sales_orders (order_id, customer_name, status, order_date, total_value) VALUES
('SO-1001', 'Acme Corp', 'open', '2026-08-01', 15000.00),
('SO-1002', 'Globex', 'closed', '2026-07-28', 2500.50),
('SO-1003', 'Initech', 'open', '2026-08-10', 8900.00),
('SO-1004', 'Stark Industries', 'open', '2026-08-11', 45000.00),
('SO-1005', 'Wayne Enterprises', 'closed', '2026-07-15', 12000.00);

-- Seed Data for inventory_items
INSERT INTO inventory_items (material_id, description, quantity_on_hand, reorder_point, warehouse) VALUES
('MAT-001', 'Steel Widget', 500, 100, 'WH-North'),
('MAT-002', 'Copper Coil', 80, 150, 'WH-South'),
('MAT-003', 'Titanium Bolt', 1200, 500, 'WH-North'),
('MAT-004', 'Aluminum Casing', 45, 100, 'WH-East'),
('MAT-005', 'Silicon Wafer', 250, 300, 'WH-West');

-- Seed Data for purchase_requisitions
INSERT INTO purchase_requisitions (requisition_id, material_id, quantity, requested_by, status, created_at, approved_at) VALUES
('PR-2001', 'MAT-002', 200, 'Alice Smith', 'approved', '2026-08-05 10:00:00', '2026-08-06 14:30:00'),
('PR-2002', 'MAT-004', 150, 'Bob Jones', 'pending_approval', '2026-08-11 09:15:00', NULL),
('PR-2003', 'MAT-005', 100, 'Charlie Brown', 'pending_approval', '2026-08-12 08:00:00', NULL);
