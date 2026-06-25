-- Schema

CREATE DATABASE IF NOT EXISTS resort_db
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

USE resort_db;

-- Room types
CREATE TABLE IF NOT EXISTS room_types (
    room_type_id INT          AUTO_INCREMENT PRIMARY KEY,
    type_name    VARCHAR(100) NOT NULL,
    capacity     INT          NOT NULL CHECK (capacity > 0),
    price        DECIMAL(10, 2) NOT NULL CHECK (price >= 0)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Individual rooms
CREATE TABLE IF NOT EXISTS rooms (
    room_id      INT          AUTO_INCREMENT PRIMARY KEY,
    room_number  VARCHAR(20)  NOT NULL UNIQUE,
    room_type_id INT          NOT NULL,
    status       ENUM('available', 'occupied', 'maintenance') NOT NULL DEFAULT 'available',
    INDEX idx_rooms_type_status (room_type_id, status),
    CONSTRAINT fk_rooms_room_type
        FOREIGN KEY (room_type_id) REFERENCES room_types (room_type_id)
        ON DELETE RESTRICT ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Guests
CREATE TABLE IF NOT EXISTS guests (
    guest_id  INT          AUTO_INCREMENT PRIMARY KEY,
    full_name VARCHAR(100) NOT NULL,
    email     VARCHAR(150) NOT NULL UNIQUE,
    phone     VARCHAR(20)  NOT NULL,
    created_at TIMESTAMP   NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Reservations
CREATE TABLE IF NOT EXISTS reservations (
    reservation_id     INT  AUTO_INCREMENT PRIMARY KEY,
    room_id            INT  NOT NULL,
    guest_id           INT  NOT NULL,
    check_in_date      DATE NOT NULL,
    check_out_date     DATE NOT NULL,
    checkout_time      TIME,
    reservation_status ENUM('pending', 'active', 'completed', 'cancelled') NOT NULL DEFAULT 'pending',
    created_at         TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT chk_dates CHECK (check_out_date > check_in_date),
    INDEX idx_res_room_status_dates  (room_id,   reservation_status, check_in_date, check_out_date),
    INDEX idx_res_guest_status_dates (guest_id,  reservation_status, check_in_date, check_out_date),
    CONSTRAINT fk_res_room
        FOREIGN KEY (room_id)  REFERENCES rooms  (room_id)  ON DELETE RESTRICT ON UPDATE CASCADE,
    CONSTRAINT fk_res_guest
        FOREIGN KEY (guest_id) REFERENCES guests (guest_id) ON DELETE RESTRICT ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Seed data
INSERT IGNORE INTO room_types (type_name, capacity, price) VALUES
    ('Super Deluxe (Single)', 1, 3300.00),
    ('Super Deluxe (Twin)',   2, 3600.00),
    ('Super Deluxe (Triple)', 3, 4000.00);

INSERT IGNORE INTO rooms (room_number, room_type_id, status) VALUES
    ('101', 1, 'available'),
    ('102', 1, 'available'),
    ('103', 1, 'available'),
    ('104', 2, 'available'),
    ('201', 1, 'available'),
    ('202', 1, 'available'),
    ('203', 3, 'available'),
    ('204', 2, 'available'),
    ('205', 2, 'available'),
    ('301', 1, 'available'),
    ('302', 1, 'available'),
    ('303', 3, 'available'),
    ('304', 2, 'available'),
    ('305', 2, 'available');