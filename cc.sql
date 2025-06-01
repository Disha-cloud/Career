DROP DATABASE IF EXISTS cc;
CREATE DATABASE cc;
USE cc;



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
    availability_status BOOLEAN DEFAULT TRUE,
    rating DECIMAL(3, 2),
    date_registered DATETIME DEFAULT CURRENT_TIMESTAMP,
    last_login DATETIME DEFAULT NULL,
    is_active BOOLEAN DEFAULT TRUE
);

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

CREATE TABLE appointment_requests (
    id INTEGER PRIMARY KEY AUTO_INCREMENT,
    student_id INTEGER NOT NULL,
    counsellor_id INTEGER NOT NULL,
    appointment_type VARCHAR(100) NOT NULL,
    preferred_date DATE NOT NULL,
    preferred_time TIME NOT NULL,
    mode ENUM('online', 'offline', 'phone') NOT NULL,
    notes TEXT,
    status ENUM('pending', 'approved', 'rejected') DEFAULT 'pending',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (student_id) REFERENCES student(id) ON DELETE CASCADE,
    FOREIGN KEY (counsellor_id) REFERENCES counsellors(id) ON DELETE CASCADE
);

CREATE TABLE appointments (
    id INT AUTO_INCREMENT PRIMARY KEY,
    student_id INT NOT NULL,
    counsellor_id INT NOT NULL,
    appointment_date DATE NOT NULL,
    start_time TIME NOT NULL,
    end_time TIME NOT NULL,
    appointment_type VARCHAR(100) NOT NULL,
    status ENUM('scheduled', 'completed', 'cancelled', 'rescheduled') DEFAULT 'scheduled',
    mode ENUM('online', 'offline', 'phone') NOT NULL,
    meeting_link VARCHAR(255),
    location VARCHAR(255),
    FOREIGN KEY (student_id) REFERENCES student(id) ON DELETE CASCADE,
    FOREIGN KEY (counsellor_id) REFERENCES counsellors(id) ON DELETE CASCADE
);

CREATE TABLE feedback (
    feedback_id INT AUTO_INCREMENT PRIMARY KEY,
    student_id INT,
    counsellor_id INT,
    rating INT CHECK (rating BETWEEN 1 AND 5),
    comments TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (student_id) REFERENCES student(id),
    FOREIGN KEY (counsellor_id) REFERENCES counsellors(id)
);

CREATE TABLE counsellor_schedules (
    schedule_id INT AUTO_INCREMENT PRIMARY KEY,
    counsellor_id INT,
    day_of_week ENUM('Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'),
    start_time TIME,
    end_time TIME,
    is_recurring BOOLEAN DEFAULT TRUE,
    FOREIGN KEY (counsellor_id) REFERENCES counsellors(id) ON DELETE CASCADE,
    UNIQUE KEY unique_schedule (counsellor_id, day_of_week)
);

CREATE TABLE notifications (
    notification_id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT,
    user_type ENUM('student', 'counsellor', 'admin') NOT NULL,
    message TEXT NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    read_status BOOLEAN DEFAULT FALSE,
    notification_type ENUM('general', 'appointment', 'resource', 'payment', 'grievance', 'appointment_request', 'feedback', 'event') NOT NULL,
    related_entity_id INT
);

CREATE TABLE messages (
    message_id INT AUTO_INCREMENT PRIMARY KEY,
    sender_id INT NOT NULL,
    recipient_id INT NOT NULL,
    sender_type ENUM('student', 'counsellor') NOT NULL,
    recipient_type ENUM('student', 'counsellor') NOT NULL,
    message_text TEXT NOT NULL,
    sent_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    is_read BOOLEAN DEFAULT FALSE
);

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

CREATE TABLE goal_milestones (
    milestone_id INT AUTO_INCREMENT PRIMARY KEY,
    goal_id INT,
    milestone_title VARCHAR(255),
    due_date DATE,
    status ENUM('pending', 'completed') DEFAULT 'pending',
    FOREIGN KEY (goal_id) REFERENCES career_goals(goal_id) ON DELETE CASCADE
);

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

INSERT INTO counsellors (
    first_name, last_name, email, password_hash, specialization, qualification,
    years_of_experience, bio, availability_status, rating, date_registered, is_active
) VALUES
('John', 'Doe', 'c1@example.com', 'pbkdf2:sha256:600000$f6Mv5oQIZnEFru6r$d2475f0b4b9707a14301c3c58a3ace3fdb357eb508a4bd66ea164e0988a19c81', 'Technology', 'MSc Computer Science', 10, 'Experienced technology counsellor.', TRUE, 4.5, NOW(), TRUE),
('Jane', 'Smith', 'c2@example.com', 'pbkdf2:sha256:600000$f6Mv5oQIZnEFru6r$d2475f0b4b9707a14301c3c58a3ace3fdb357eb508a4bd66ea164e0988a19c81', 'Healthcare', 'MD Medicine', 8, 'Healthcare career counsellor.', TRUE, 4.6, NOW(), TRUE),
('Emily', 'Brown', 'c3@example.com', 'pbkdf2:sha256:600000$f6Mv5oQIZnEFru6r$d2475f0b4b9707a14301c3c58a3ace3fdb357eb508a4bd66ea164e0988a19c81', 'Education', 'PhD Education', 12, 'Expert in academic counseling.', TRUE, 4.8, NOW(), TRUE),
('Michael', 'Johnson', 'c4@example.com', 'pbkdf2:sha256:600000$f6Mv5oQIZnEFru6r$d2475f0b4b9707a14301c3c58a3ace3fdb357eb508a4bd66ea164e0988a19c81', 'Engineering', 'MEng Mechanical Engineering', 15, 'Specialized in engineering career paths.', TRUE, 4.7, NOW(), TRUE),
('Sarah', 'Davis', 'c5@example.com', 'pbkdf2:sha256:600000$f6Mv5oQIZnEFru6r$d2475f0b4b9707a14301c3c58a3ace3fdb357eb508a4bd66ea164e0988a19c81', 'Finance', 'MBA Finance', 9, 'Finance career advisor.', TRUE, 4.4, NOW(), TRUE),
('David', 'Wilson', 'c6@example.com', 'pbkdf2:sha256:600000$f6Mv5oQIZnEFru6r$d2475f0b4b9707a14301c3c58a3ace3fdb357eb508a4bd66ea164e0988a19c81', 'Arts', 'MA Fine Arts', 7, 'Career counselor for creative arts.', TRUE, 4.3, NOW(), TRUE);

INSERT INTO administrators (
    email, password_hash, first_name, last_name, department, role_description, is_active, date_registered
) VALUES
('admin@example.com', 'pbkdf2:sha256:600000$f6Mv5oQIZnEFru6r$d2475f0b4b9707a14301c3c58a3ace3fdb357eb508a4bd66ea164e0988a19c81', 'Admin', 'User', 'IT', 'Superuser for the system', TRUE, NOW());

INSERT INTO student (
    email, password_hash, first_name, last_name, phone, dob, address, education_level,
    interests, counsellor_id, course, quiz_result, is_active, date_registered
) VALUES
('student1@example.com', 'pbkdf2:sha256:600000$f6Mv5oQIZnEFru6r$d2475f0b4b9707a14301c3c58a3ace3fdb357eb508a4bd66ea164e0988a19c81', 'Alice', 'Student', '9876543210', '2004-08-15', '123 Main St', 'High School', 'Science, Robotics', 1, 'BSc Physics', 'A', TRUE, NOW()),
('student2@example.com', 'pbkdf2:sha256:600000$f6Mv5oQIZnEFru6r$d2475f0b4b9707a14301c3c58a3ace3fdb357eb508a4bd66ea164e0988a19c81', 'Bob', 'Student', '9123456780', '2003-12-01', '456 Park Ave', 'Undergraduate', 'Business, Finance', 2, 'BBA', 'B', TRUE, NOW()),
('student3@example.com', 'pbkdf2:sha256:600000$f6Mv5oQIZnEFru6r$d2475f0b4b9707a14301c3c58a3ace3fdb357eb508a4bd66ea164e0988a19c81', 'Emma', 'Garcia', '9234567890', '2002-03-22', '789 Elm St', 'High School', 'Math, Programming', 3, 'BSc Computer Science', 'A-', TRUE, NOW()),
('student4@example.com', 'pbkdf2:sha256:600000$f6Mv5oQIZnEFru6r$d2475f0b4b9707a14301c3c58a3ace3fdb357eb508a4bd66ea164e0988a19c81', 'Liam', 'Rodriguez', '9345678901', '2003-07-19', '101 Oak Dr', 'Undergraduate', 'Engineering, Robotics', 4, 'BEng Mechanical', 'B+', TRUE, NOW()),
('student5@example.com', 'pbkdf2:sha256:600000$f6Mv5oQIZnEFru6r$d2475f0b4b9707a14301c3c58a3ace3fdb357eb508a4bd66ea164e0988a19c81', 'Olivia', 'Martinez', '9456789012', '2004-01-30', '202 Pine Rd', 'High School', 'Finance, Economics', 5, 'BBA Finance', 'A', TRUE, NOW()),
('student6@example.com', 'pbkdf2:sha256:600000$f6Mv5oQIZnEFru6r$d2475f0b4b9707a14301c3c58a3ace3fdb357eb508a4bd66ea164e0988a19c81', 'Noah', 'Hernandez', '9567890123', '2002-11-05', '303 Cedar Ln', 'Undergraduate', 'Art, Design', 6, 'BA Fine Arts', 'B', TRUE, NOW());

INSERT INTO grievances (student_id, subject, description, status, response)
VALUES
(1, 'Delay in appointment', 'My appointment was delayed by 30 minutes.', 'Pending', NULL),
(2, 'Resource access issue', 'Unable to download career guide.', 'In Progress', 'We are looking into it.'),
(3, 'Scheduling Conflict', 'Appointment time overlaps with class.', 'Pending', NULL),
(4, 'Technical Issue', 'Unable to access online portal.', 'In Progress', 'Technical team is investigating.'),
(5, 'Counsellor Availability', 'Counsellor not available for preferred slot.', 'Pending', NULL),
(6, 'Course Material Issue', 'Missing course resources in portal.', 'Resolved', 'Resources uploaded successfully.');

INSERT INTO appointment_requests (student_id, counsellor_id, appointment_type, preferred_date, preferred_time, mode, notes, status)
VALUES
(1, 1, 'Career Guidance', '2024-06-01', '10:00:00', 'online', 'Need guidance on career path', 'pending'),
(2, 2, 'Resume Review', '2024-06-02', '14:00:00', 'offline', 'Want to review my resume', 'pending'),
(3, 3, 'Academic Guidance', '2024-06-03', '11:00:00', 'online', 'Need help with course selection', 'pending'),
(4, 4, 'Career Counseling', '2024-06-04', '15:00:00', 'offline', 'Discuss internship opportunities', 'approved'),
(5, 5, 'Resume Review', '2024-06-05', '13:00:00', 'phone', 'Need feedback on resume draft', 'pending'),
(6, 6, 'Portfolio Review', '2024-06-06', '16:00:00', 'online', 'Review art portfolio', 'rejected');

INSERT INTO appointments (student_id, counsellor_id, appointment_date, start_time, end_time, appointment_type, status, mode, meeting_link, location)
VALUES
(1, 1, '2025-05-25', '10:00:00', '11:00:00', 'Career Guidance', 'scheduled', 'online', 'https://meet.link/webinar', NULL),
(2, 2, '2025-05-26', '14:30:00', '15:30:00', 'Personal Counseling', 'scheduled', 'offline', NULL, 'Room 101'),
(3, 3, '2025-05-27', '11:00:00', '12:00:00', 'Academic Guidance', 'scheduled', 'online', 'https://meet.link/academic', NULL),
(4, 4, '2025-05-28', '15:30:00', '16:30:00', 'Career Counseling', 'completed', 'offline', NULL, 'Room 102'),
(5, 5, '2025-05-29', '13:00:00', '14:00:00', 'Resume Review', 'scheduled', 'phone', NULL, NULL),
(6, 6, '2025-05-30', '16:00:00', '17:00:00', 'Portfolio Review', 'cancelled', 'online', 'https://meet.link/portfolio', NULL);

INSERT INTO feedback (student_id, counsellor_id, rating, comments)
VALUES
(1, 1, 5, 'Very helpful session.'),
(2, 2, 4, 'Good advice, thank you.'),
(3, 3, 4, 'Very insightful session.'),
(4, 4, 5, 'Helped me understand my career path.'),
(5, 5, 3, 'Session was good but could be more detailed.'),
(6, 6, 4, 'Great feedback on my portfolio.');

INSERT INTO counsellor_schedules (counsellor_id, day_of_week, start_time, end_time, is_recurring)
VALUES
(1, 'Monday', '09:00:00', '12:00:00', TRUE),
(1, 'Tuesday', '09:00:00', '12:00:00', TRUE),
(2, 'Monday', '14:00:00', '17:00:00', TRUE),
(2, 'Wednesday', '14:00:00', '17:00:00', TRUE),
(3, 'Wednesday', '10:00:00', '13:00:00', TRUE),
(4, 'Thursday', '14:00:00', '17:00:00', TRUE),
(5, 'Friday', '09:00:00', '12:00:00', TRUE),
(6, 'Saturday', '11:00:00', '14:00:00', TRUE);

INSERT INTO notifications (user_id, user_type, message, notification_type, related_entity_id)
VALUES
(1, 'student', 'Your appointment is scheduled for 25 May.', 'appointment', 1),
(2, 'student', 'New career resource added: Resume Writing Guide.', 'resource', 1),
(3, 'student', 'Your appointment is confirmed for 27 May.', 'appointment', 3),
(4, 'student', 'New event: Engineering Career Fair.', 'event', 3),
(5, 'student', 'Reminder: Submit resume by 5 June.', 'general', NULL),
(6, 'student', 'Feedback submitted successfully.', 'feedback', 6);

INSERT INTO messages (sender_id, recipient_id, sender_type, recipient_type, message_text, is_read)
VALUES
(1, 2, 'student', 'student', 'Hi Bob, have you checked the new resource?', FALSE),
(2, 1, 'student', 'student', 'Yes, it was very helpful. Thanks!', TRUE),
(3, 4, 'student', 'student', 'Hey Liam, did you attend the webinar?', FALSE),
(4, 3, 'student', 'student', 'Yes, it was great! You should check it out.', TRUE),
(5, 6, 'student', 'student', 'Can you share your portfolio tips?', FALSE),
(6, 5, 'student', 'student', 'Sure, I’ll send them over soon.', TRUE);

INSERT INTO career_goals (student_id, title, description, start_date, target_date, status)
VALUES
(1, 'Get Internship', 'Secure a summer internship in IT.', '2025-05-01', '2025-07-01', 'in_progress'),
(2, 'Complete Certification', 'Finish finance certification course.', '2025-05-10', '2025-08-15', 'not_started'),
(3, 'Learn Python', 'Complete Python programming course.', '2025-05-15', '2025-08-15', 'in_progress'),
(4, 'Secure Job', 'Land a job in mechanical engineering.', '2025-06-01', '2025-12-01', 'not_started'),
(5, 'CFA Level 1', 'Pass CFA Level 1 exam.', '2025-05-20', '2025-11-30', 'in_progress'),
(6, 'Art Exhibition', 'Organize a personal art exhibition.', '2025-06-10', '2025-09-30', 'not_started');

INSERT INTO goal_milestones (goal_id, milestone_title, due_date, status)
VALUES
(1, 'Apply to companies', '2025-06-01', 'pending'),
(2, 'Complete course modules', '2025-07-15', 'pending'),
(3, 'Finish Python basics', '2025-06-15', 'pending'),
(4, 'Submit job applications', '2025-07-01', 'pending'),
(5, 'Complete CFA prep course', '2025-10-15', 'pending'),
(6, 'Secure exhibition venue', '2025-08-01', 'pending');

INSERT INTO events (title, description, event_type, counsellor_id, event_date, start_time, end_time, location, meeting_link, capacity, is_online)
VALUES
('Webinar: Future Careers', 'A webinar on emerging career trends.', 'webinar', 1, '2025-06-10', '11:00:00', '12:00:00', NULL, 'https://meet.link/webinar', 100, TRUE),
('Workshop: Resume Building', 'Hands-on workshop for resume writing.', 'workshop', 2, '2025-06-15', '14:00:00', '16:00:00', 'Lab 2', NULL, 40, FALSE),
('Seminar: Tech Trends', 'Explore latest tech industry trends.', 'seminar', 3, '2025-06-20', '10:00:00', '11:30:00', NULL, 'https://meet.link/techseminar', 80, TRUE),
('Q&A: Finance Careers', 'Live Q&A on finance career paths.', 'qna', 5, '2025-06-25', '13:00:00', '14:00:00', NULL, 'https://meet.link/financeqna', 50, TRUE),
('Workshop: Portfolio Design', 'Learn to create a professional portfolio.', 'workshop', 6, '2025-06-30', '15:00:00', '17:00:00', 'Lab 3', NULL, 30, FALSE),
('Webinar: Academic Success', 'Tips for academic excellence.', 'webinar', 3, '2025-07-05', '11:00:00', '12:00:00', NULL, 'https://meet.link/academicwebinar', 100, TRUE);

INSERT INTO event_registrations (event_id, student_id)
VALUES
(1, 1),
(2, 2),
(3, 3),
(4, 4),
(5, 5),
(6, 6);

INSERT INTO tasks (student_id, title, description, due_date, priority, category, status)
VALUES
(1, 'Complete Physics Assignment', 'Finish quantum mechanics problem set.', '2025-06-10', 'High', 'Academic', 'Pending'),
(2, 'Prepare Business Plan', 'Draft business plan for BBA project.', '2025-06-15', 'Medium', 'Academic', 'Pending'),
(3, 'Code Python Project', 'Develop a small Python application.', '2025-06-20', 'High', 'Project', 'In Progress'),
(4, 'Research Internships', 'Find engineering internship opportunities.', '2025-06-25', 'High', 'Career', 'Pending'),
(5, 'Study CFA Material', 'Review CFA Level 1 study guide.', '2025-06-30', 'Medium', 'Academic', 'In Progress'),
(6, 'Sketch Portfolio Pieces', 'Create initial sketches for portfolio.', '2025-07-05', 'Low', 'Creative', 'Pending');