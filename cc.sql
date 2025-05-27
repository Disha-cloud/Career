DROP DATABASE IF EXISTS cc;
CREATE DATABASE cc;
USE cc;

-- Counsellors table with authentication
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
    location VARCHAR(255),
    FOREIGN KEY (student_id) REFERENCES student(id) ON DELETE CASCADE,
    FOREIGN KEY (counsellor_id) REFERENCES counsellors(id) ON DELETE CASCADE
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


-- Notifications
CREATE TABLE notifications (
    notification_id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT,
    message TEXT NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    read_status BOOLEAN DEFAULT FALSE,
    notification_type ENUM('general', 'appointment', 'resource', 'payment', 'grievance', 'appointment_request') NOT NULL,
    related_entity_id INT,
    FOREIGN KEY (user_id) REFERENCES student(id) ON DELETE CASCADE
);

-- Messages
CREATE TABLE messages (
    message_id INT AUTO_INCREMENT PRIMARY KEY,
    sender_id INT,
    recipient_id INT,
    sender_type ENUM('student', 'counsellor') NOT NULL,
    recipient_type ENUM('student', 'counsellor') NOT NULL,
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

-- Tasks
CREATE TABLE tasks (
    task_id INT AUTO_INCREMENT PRIMARY KEY,
    student_id INT NOT NULL,
    title VARCHAR(200) NOT NULL,
    description TEXT,
    due_date DATE,
    priority VARCHAR(20) NOT NULL,
    category VARCHAR(50) NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'Pending',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (student_id) REFERENCES student(id)
);