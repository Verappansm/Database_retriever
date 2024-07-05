#use this code in sql workbench to create the database and tables

CREATE DATABASE sales_inventory;
USE sales_inventory;

CREATE TABLE addresses (
    address_id INT AUTO_INCREMENT PRIMARY KEY,
    street VARCHAR(100) NOT NULL,
    city VARCHAR(50) NOT NULL,
    state VARCHAR(50) NOT NULL,
    zip_code VARCHAR(10) NOT NULL,
    country VARCHAR(50) NOT NULL
);

CREATE TABLE employees (
    employee_id INT AUTO_INCREMENT PRIMARY KEY,
    first_name VARCHAR(50) NOT NULL,
    last_name VARCHAR(50) NOT NULL,
    phone_no VARCHAR(15) NOT NULL,
    email VARCHAR(100) NOT NULL,
    UNIQUE (email)
);

CREATE TABLE clients (
    company_id INT AUTO_INCREMENT PRIMARY KEY,
    company_name VARCHAR(100) NOT NULL,
    address_id INT NOT NULL,
    FOREIGN KEY (address_id) REFERENCES addresses(address_id)
);

CREATE TABLE pocs (
    poc_id INT AUTO_INCREMENT PRIMARY KEY,
    poc_name VARCHAR(100) NOT NULL,
    phone_no VARCHAR(15) NOT NULL,
    email VARCHAR(100) NOT NULL,
    UNIQUE (email)
);

CREATE TABLE branches (
    branch_id INT AUTO_INCREMENT PRIMARY KEY,
    company_id INT NOT NULL,
    address_id INT NOT NULL,
    employee_id INT NOT NULL,
    poc_id INT NOT NULL,
    FOREIGN KEY (company_id) REFERENCES clients(company_id),
    FOREIGN KEY (address_id) REFERENCES addresses(address_id),
    FOREIGN KEY (employee_id) REFERENCES employees(employee_id),
    FOREIGN KEY (poc_id) REFERENCES pocs(poc_id)
);

CREATE TABLE categories (
    category_id INT AUTO_INCREMENT PRIMARY KEY,
    category_name VARCHAR(50) NOT NULL,
    UNIQUE (category_name)
);

CREATE TABLE products (
    product_id INT AUTO_INCREMENT PRIMARY KEY,
    category_id INT NOT NULL,
    product_name VARCHAR(100) NOT NULL,
    price DECIMAL(10,2) NOT NULL,
    quantity_left INT NOT NULL,
    quantity_sold INT NOT NULL,
    FOREIGN KEY (category_id) REFERENCES categories(category_id),
    CHECK (price >= 0),
    CHECK (quantity_left >= 0),
    CHECK (quantity_sold >= 0)
);
CREATE TABLE orders (
    order_id INT AUTO_INCREMENT PRIMARY KEY,
    branch_id INT NOT NULL,
    order_date DATE NOT NULL,
    discount DECIMAL(5,2) NOT NULL,
    FOREIGN KEY (branch_id) REFERENCES branches(branch_id)
);

CREATE TABLE order_items (
    order_item_id INT AUTO_INCREMENT PRIMARY KEY,
    order_id INT NOT NULL,
    product_id INT NOT NULL,
    quantity INT NOT NULL,
    price DECIMAL(10,2) NOT NULL,
    FOREIGN KEY (order_id) REFERENCES orders(order_id),
    FOREIGN KEY (product_id) REFERENCES products(product_id),
    CHECK (quantity > 0),
    CHECK (price >= 0)
);

CREATE TABLE billing (
    billing_id INT AUTO_INCREMENT PRIMARY KEY,
    order_id INT NOT NULL,
    billing_date DATE NOT NULL,
    total_amount DECIMAL(10,2) NOT NULL,
    FOREIGN KEY (order_id) REFERENCES orders(order_id)
);

INSERT INTO addresses (street, city, state, zip_code, country)
VALUES
('123 Main St', 'Springfield', 'IL', '62701', 'USA'),
('456 Elm St', 'Lincoln', 'NE', '68508', 'USA'),
('789 Oak St', 'Madison', 'WI', '53703', 'USA');

INSERT INTO employees (first_name, last_name, phone_no, email)
VALUES
('John', 'Doe', '1234567890', 'john.doe@example.com'),
('Jane', 'Smith', '0987654321', 'jane.smith@example.com'),
('Emily', 'Johnson', '1231231234', 'emily.johnson@example.com');

INSERT INTO clients (company_name, address_id)
VALUES
('Company A', 1),
('Company B', 2),
('Company C', 3);

INSERT INTO pocs (poc_name, phone_no, email)
VALUES
('Alice', '1234567890', 'alice@example.com'),
('Bob', '0987654321', 'bob@example.com'),
('Charlie', '1231231234', 'charlie@example.com');

INSERT INTO branches (company_id, address_id, employee_id, poc_id)
VALUES
(1, 1, 1, 1),
(1, 2, 2, 2),
(2, 3, 3, 3);

INSERT INTO categories (category_name)
VALUES
('Electronics'),
('Furniture'),
('Office Supplies');

INSERT INTO products (category_id, product_name, price, quantity_left, quantity_sold)
VALUES
(1, 'Laptop', 999.99, 100, 10),
(2, 'Office Chair', 199.99, 50, 5),
(3, 'Stapler', 19.99, 200, 25);

INSERT INTO orders (branch_id, order_date, discount)
VALUES
(1, '2024-07-01', 10.00),
(2, '2024-07-02', 5.00);

INSERT INTO order_items (order_id, product_id, quantity, price)
VALUES
(1, 1, 2, 999.99),
(1, 2, 1, 199.99),
(2, 3, 10, 19.99);

INSERT INTO billing (order_id, billing_date, total_amount)
VALUES
(1, '2024-07-03', 2099.97),
(2, '2024-07-04', 189.90);

USE sales_inventory;


INSERT INTO addresses (street, city, state, zip_code, country)
VALUES
('101 Maple St', 'Austin', 'TX', '73301', 'USA'),
('202 Pine St', 'Boston', 'MA', '02201', 'USA'),
('303 Cedar St', 'Denver', 'CO', '80201', 'USA');

INSERT INTO employees (first_name, last_name, phone_no, email)
VALUES
('Michael', 'Brown', '2345678901', 'michael.brown@example.com'),
('Sarah', 'Lee', '3456789012', 'sarah.lee@example.com'),
('David', 'Miller', '4567890123', 'david.miller@example.com');

INSERT INTO clients (company_name, address_id)
VALUES
('Company D', 4),
('Company E', 5),
('Company F', 6);

INSERT INTO pocs (poc_name, phone_no, email)
VALUES
('Daniel', '2345678901', 'daniel@example.com'),
('Olivia', '3456789012', 'olivia@example.com'),
('Sophia', '4567890123', 'sophia@example.com');

INSERT INTO branches (company_id, address_id, employee_id, poc_id)
VALUES
(3, 4, 4, 4),
(4, 5, 5, 5),
(5, 6, 6, 6);

INSERT INTO categories (category_name)
VALUES
('Software'),
('Hardware');

INSERT INTO products (category_id, product_name, price, quantity_left, quantity_sold)
VALUES
(4, 'Antivirus', 49.99, 300, 150),
(5, 'Printer', 149.99, 200, 100);

INSERT INTO orders (branch_id, order_date, discount)
VALUES
(3, '2024-05-01', 15.00),
(4, '2024-06-15', 20.00),
(5, '2024-05-20', 10.00);

INSERT INTO order_items (order_id, product_id, quantity, price)
VALUES
(3, 1, 1, 999.99),
(3, 3, 5, 19.99),
(4, 2, 2, 199.99),
(4, 5, 3, 149.99),
(5, 4, 10, 49.99);

INSERT INTO billing (order_id, billing_date, total_amount)
VALUES
(3, '2024-05-05', 1089.94),
(4, '2024-06-18', 569.97),
(5, '2024-05-25', 499.90);