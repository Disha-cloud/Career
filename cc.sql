DROP DATABASE IF EXISTS cc;
CREATE DATABASE cc;
USE cc;

-- Counsellor table with authentication
CREATE TABLE counsellors (
    id INT AUTO_INCREMENT PRIMARY KEY,
    email VARCHAR(100) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    first_name VARCHAR(100) NOT NULL,
    last_name VARCHAR(100),
    specialization VARCHAR(100),
    qualification TEXT,
    years_of_experience INT,
    bio TEXT,
    availability_status BOOLEAN,
    rating DECIMAL(3, 2),
    date_registered DATETIME DEFAULT CURRENT_TIMESTAMP,
    last_login DATETIME DEFAULT NULL
);

-- Student table with authentication
CREATE TABLE student (
    id INT AUTO_INCREMENT PRIMARY KEY,
    email VARCHAR(100) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    first_name VARCHAR(100) NOT NULL,
    last_name VARCHAR(100),
    phone VARCHAR(20),
    dob DATE,
    address TEXT,
    education_level VARCHAR(100),
    interests TEXT,
    counsellor_id INT,
    course VARCHAR(100),
    quiz_result VARCHAR(100) DEFAULT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    date_registered DATETIME DEFAULT CURRENT_TIMESTAMP,
    last_login DATETIME DEFAULT NULL,
    FOREIGN KEY (counsellor_id) REFERENCES counsellors(id) ON DELETE SET NULL
);

-- Administrator table
CREATE TABLE administrators (
    id INT AUTO_INCREMENT PRIMARY KEY,
    email VARCHAR(100) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    first_name VARCHAR(100) NOT NULL,
    last_name VARCHAR(100),
    department VARCHAR(100),
    role_description TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    date_registered DATETIME DEFAULT CURRENT_TIMESTAMP,
    last_login DATETIME DEFAULT NULL
);

-- Grievances
CREATE TABLE grievances (
    id INT AUTO_INCREMENT PRIMARY KEY,
    student_id INT NOT NULL,
    subject VARCHAR(200) NOT NULL,
    description TEXT NOT NULL,
    status ENUM('Pending', 'In Progress', 'Resolved') DEFAULT 'Pending',
    response TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (student_id) REFERENCES student(id) ON DELETE CASCADE
);

-- Counsellor assignment logs
CREATE TABLE counsellor_assignment_logs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    student_id INT NOT NULL,
    old_counsellor_id INT,
    new_counsellor_id INT NOT NULL,
    reason TEXT,
    assigned_by_id INT NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (student_id) REFERENCES student(id) ON DELETE CASCADE,
    FOREIGN KEY (old_counsellor_id) REFERENCES counsellors(id) ON DELETE SET NULL,
    FOREIGN KEY (new_counsellor_id) REFERENCES counsellors(id) ON DELETE CASCADE,
    FOREIGN KEY (assigned_by_id) REFERENCES administrators(id)
);

-- Appointment requests
CREATE TABLE appointment_requests (
    id INTEGER PRIMARY KEY AUTO_INCREMENT,
    student_id INTEGER NOT NULL,
    counsellor_id INTEGER NOT NULL,
    appointment_type VARCHAR(100) NOT NULL,
    preferred_date DATE NOT NULL,
    preferred_time TIME NOT NULL,
    mode VARCHAR(10) NOT NULL CHECK (mode IN ('online', 'offline', 'phone')),
    notes TEXT,
    status VARCHAR(10) NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'approved', 'rejected')),
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (student_id) REFERENCES student(id) ON DELETE CASCADE,
    FOREIGN KEY (counsellor_id) REFERENCES counsellors(id) ON DELETE CASCADE
);

-- Appointments
CREATE TABLE appointments (
    id INT AUTO_INCREMENT PRIMARY KEY,
    student_id INT NOT NULL,
    counsellor_id INT NOT NULL,
    appointment_date DATE NOT NULL,
    start_time TIME NOT NULL,
    end_time TIME,
    status ENUM('scheduled', 'completed', 'cancelled', 'rescheduled') DEFAULT 'scheduled',
    mode ENUM('online', 'offline', 'phone') NOT NULL,
    meeting_link VARCHAR(255),
    location VARCHAR(255),
    is_free BOOLEAN DEFAULT FALSE,
    fee DECIMAL(10,2),
    payment_status ENUM('paid', 'pending', 'not_required') DEFAULT 'not_required',
    FOREIGN KEY (student_id) REFERENCES student(id) ON DELETE CASCADE,
    FOREIGN KEY (counsellor_id) REFERENCES counsellors(id) ON DELETE CASCADE
);

-- Counselling sessions
CREATE TABLE counselling_sessions (
    session_id INT AUTO_INCREMENT PRIMARY KEY,
    appointment_id INT,
    notes TEXT,
    recommendations TEXT,
    resources TEXT,
    follow_up_date DATE,
    session_duration INT,
    FOREIGN KEY (appointment_id) REFERENCES appointments(id)
);

-- Feedback
CREATE TABLE feedback (
    feedback_id INT AUTO_INCREMENT PRIMARY KEY,
    session_id INT,
    student_id INT,
    counsellor_id INT,
    rating INT CHECK (rating BETWEEN 1 AND 5),
    comments TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (session_id) REFERENCES counselling_sessions(session_id),
    FOREIGN KEY (student_id) REFERENCES student(id),
    FOREIGN KEY (counsellor_id) REFERENCES counsellors(id)
);

-- Counsellor schedules
CREATE TABLE counsellor_schedules (
    schedule_id INT AUTO_INCREMENT PRIMARY KEY,
    counsellor_id INT,
    day_of_week ENUM('Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'),
    start_time TIME,
    end_time TIME,
    is_recurring BOOLEAN DEFAULT TRUE,
    FOREIGN KEY (counsellor_id) REFERENCES counsellors(id) ON DELETE CASCADE
);

-- Career resources
CREATE TABLE career_resources (
    resource_id INT AUTO_INCREMENT PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    resource_type ENUM('document', 'video', 'link', 'other') NOT NULL,
    url VARCHAR(255),
    file_path VARCHAR(255),
    added_by INT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    is_public BOOLEAN DEFAULT TRUE,
    FOREIGN KEY (added_by) REFERENCES administrators(id)
);

-- Notifications
CREATE TABLE notifications (
    notification_id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT,
    message TEXT NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    read_status BOOLEAN DEFAULT FALSE,
    notification_type ENUM('general', 'appointment', 'resource', 'payment', 'grievance') NOT NULL,
    related_entity_id INT,
    FOREIGN KEY (user_id) REFERENCES student(id) ON DELETE CASCADE
);

-- Messages
CREATE TABLE messages (
    message_id INT AUTO_INCREMENT PRIMARY KEY,
    sender_id INT,
    recipient_id INT,
    message_text TEXT NOT NULL,
    sent_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    is_read BOOLEAN DEFAULT FALSE,
    FOREIGN KEY (sender_id) REFERENCES student(id),
    FOREIGN KEY (recipient_id) REFERENCES student(id)
);

-- Career goals
CREATE TABLE career_goals (
    goal_id INT AUTO_INCREMENT PRIMARY KEY,
    student_id INT,
    title VARCHAR(255),
    description TEXT,
    start_date DATE,
    target_date DATE,
    status ENUM('not_started', 'in_progress', 'completed') DEFAULT 'not_started',
    FOREIGN KEY (student_id) REFERENCES student(id) ON DELETE CASCADE
);

-- Student resource access
CREATE TABLE student_resource_access (
    access_id INT AUTO_INCREMENT PRIMARY KEY,
    student_id INT,
    resource_id INT,
    access_date DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (student_id) REFERENCES student(id) ON DELETE CASCADE,
    FOREIGN KEY (resource_id) REFERENCES career_resources(resource_id) ON DELETE CASCADE
);

-- Goal milestones
CREATE TABLE goal_milestones (
    milestone_id INT AUTO_INCREMENT PRIMARY KEY,
    goal_id INT,
    milestone_title VARCHAR(255),
    due_date DATE,
    status ENUM('pending', 'completed') DEFAULT 'pending',
    FOREIGN KEY (goal_id) REFERENCES career_goals(goal_id) ON DELETE CASCADE
);

-- Events
CREATE TABLE events (
    event_id INT AUTO_INCREMENT PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    event_type ENUM('webinar', 'workshop', 'qna', 'seminar') NOT NULL,
    counsellor_id INT,
    event_date DATE NOT NULL,
    start_time TIME NOT NULL,
    end_time TIME,
    location VARCHAR(255),
    meeting_link VARCHAR(255),
    capacity INT,
    is_online BOOLEAN DEFAULT TRUE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (counsellor_id) REFERENCES counsellors(id)
);

-- Event registrations
CREATE TABLE event_registrations (
    registration_id INT AUTO_INCREMENT PRIMARY KEY,
    event_id INT,
    student_id INT,
    registered_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    reminder_sent BOOLEAN DEFAULT FALSE,
    attendance_status ENUM('registered', 'attended', 'missed') DEFAULT 'registered',
    FOREIGN KEY (event_id) REFERENCES events(event_id) ON DELETE CASCADE,
    FOREIGN KEY (student_id) REFERENCES student(id) ON DELETE CASCADE
);

-- Sample data: counsellors
INSERT INTO counsellors (
    first_name, last_name, email, password_hash, specialization, qualification,
    years_of_experience, bio, availability_status, rating, date_registered
) VALUES
('John', 'Doe', 'john.doe@example.com', 'pbkdf2:sha256:600000$abc$abc', 'Technology', 'MSc Computer Science', 10, 'Experienced technology counsellor.', TRUE, 4.5, NOW()),
('Jane', 'Smith', 'jane.smith@example.com', 'pbkdf2:sha256:600000$abc$abc', 'Healthcare', 'MD Medicine', 8, 'Healthcare career counsellor.', TRUE, 4.6, NOW()),
('Michael', 'Brown', 'michael.brown@example.com', 'pbkdf2:sha256:600000$abc$abc', 'Business', 'MBA Finance', 12, 'Business and finance counsellor.', TRUE, 4.9, NOW()),
('Aisha', 'Patel', 'aisha.patel@example.com', 'pbkdf2:sha256:600000$abc$abc', 'Engineering', 'BTech Mechanical Engineering', 7, 'Engineering career advisor.', TRUE, 4.7, NOW()),
('Padmavathi', 'Devarakonda', 'padma.devarakonda@example.com', 'pbkdf2:sha256:600000$abc$abc', 'Arts', 'MA Fine Arts', 15, 'Arts and creative careers expert.', TRUE, 4.8, NOW()),
('Ahmed', 'Khan', 'ahmed.khan@example.com', 'pbkdf2:sha256:600000$abc$abc', 'Science', 'PhD Physics', 11, 'Science and research specialist.', TRUE, 4.8, NOW()),
('Rachel', 'Lee', 'rachel.lee@example.com', 'pbkdf2:sha256:600000$abc$abc', 'Education', 'M.Ed.', 9, 'Education and teaching counsellor.', TRUE, 4.4, NOW()),
('Bharati', 'Trivedi', 'bharati.trivedi@example.com', 'pbkdf2:sha256:600000$abc$abc', 'Law', 'LLM Law', 20, 'Legal careers and law expert.', TRUE, 4.7, NOW());

-- Sample data: administrator
INSERT INTO administrators (
    email, password_hash, first_name, last_name, department, role_description, is_active, date_registered
) VALUES
('admin@example.com', 'pbkdf2:sha256:600000$abc$abc', 'Admin', 'User', 'IT', 'Superuser for the system', TRUE, NOW());
