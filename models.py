from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, time
from werkzeug.security import generate_password_hash, check_password_hash
import json

db = SQLAlchemy()

class User(db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), default='admin')  # admin, reviewer, faculty
    department_id = db.Column(db.Integer, db.ForeignKey('departments.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'role': self.role,
            'department': self.department.name if self.department else None
        }

class Department(db.Model):
    __tablename__ = 'departments'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    code = db.Column(db.String(10), unique=True, nullable=False)
    shift_preference = db.Column(db.String(20), default='both')  # morning, evening, both
    max_classes_per_day = db.Column(db.Integer, default=8)  # PDF constraint
    lab_duration_multiplier = db.Column(db.Float, default=2.0)  # Labs are typically 2x longer
    
    # Relationships
    users = db.relationship('User', backref='department', lazy=True)
    classrooms = db.relationship('Classroom', backref='department', lazy=True)
    laboratories = db.relationship('Laboratory', backref='department', lazy=True)
    faculty = db.relationship('Faculty', backref='department', lazy=True)
    batches = db.relationship('Batch', backref='department', lazy=True)

class Semester(db.Model):
    __tablename__ = 'semesters'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    year = db.Column(db.Integer, nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    program_type = db.Column(db.String(10), default='UG')  # UG, PG
    start_date = db.Column(db.Date)
    end_date = db.Column(db.Date)
    
    # Relationships
    subjects = db.relationship('Subject', backref='semester', lazy=True)
    batches = db.relationship('Batch', backref='semester', lazy=True)
    timetables = db.relationship('Timetable', backref='semester', lazy=True)

class Classroom(db.Model):
    __tablename__ = 'classrooms'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    capacity = db.Column(db.Integer, nullable=False)  # PDF parameter
    room_type = db.Column(db.String(20), default='lecture')  # lecture, seminar, tutorial
    equipment = db.Column(db.Text)  # JSON string of available equipment
    is_available = db.Column(db.Boolean, default=True)  # PDF parameter
    department_id = db.Column(db.Integer, db.ForeignKey('departments.id'))
    shift_availability = db.Column(db.String(20), default='both')  # morning, evening, both
    floor_number = db.Column(db.Integer, default=1)
    building = db.Column(db.String(50))
    
    # Relationships
    schedule_entries = db.relationship('ScheduleEntry', backref='classroom', lazy=True)
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'capacity': self.capacity,
            'room_type': self.room_type,
            'equipment': json.loads(self.equipment) if self.equipment else [],
            'is_available': self.is_available,
            'shift_availability': self.shift_availability,
            'floor_number': self.floor_number,
            'building': self.building,
            'department': self.department.name if self.department else None
        }

class Laboratory(db.Model):
    __tablename__ = 'laboratories'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    capacity = db.Column(db.Integer, nullable=False)  # PDF parameter
    lab_type = db.Column(db.String(30), nullable=False)  # computer, physics, chemistry, biology, engineering
    equipment = db.Column(db.Text)  # JSON string of available equipment and software
    safety_requirements = db.Column(db.Text)  # Safety protocols and requirements
    is_available = db.Column(db.Boolean, default=True)  # PDF parameter
    department_id = db.Column(db.Integer, db.ForeignKey('departments.id'))
    shift_availability = db.Column(db.String(20), default='both')
    setup_time_minutes = db.Column(db.Integer, default=15)  # Time needed between sessions
    cleanup_time_minutes = db.Column(db.Integer, default=15)
    floor_number = db.Column(db.Integer, default=1)
    building = db.Column(db.String(50))
    requires_technician = db.Column(db.Boolean, default=False)
    
    # Relationships
    lab_sessions = db.relationship('LabSession', backref='laboratory', lazy=True)
    schedule_entries = db.relationship('ScheduleEntry', backref='laboratory', lazy=True)
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'capacity': self.capacity,
            'lab_type': self.lab_type,
            'equipment': json.loads(self.equipment) if self.equipment else [],
            'safety_requirements': self.safety_requirements,
            'is_available': self.is_available,
            'shift_availability': self.shift_availability,
            'setup_time_minutes': self.setup_time_minutes,
            'cleanup_time_minutes': self.cleanup_time_minutes,
            'requires_technician': self.requires_technician,
            'department': self.department.name if self.department else None
        }

class Faculty(db.Model):
    __tablename__ = 'faculty'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)  # PDF parameter
    email = db.Column(db.String(120), unique=True)
    employee_id = db.Column(db.String(20), unique=True)
    department_id = db.Column(db.Integer, db.ForeignKey('departments.id'))
    designation = db.Column(db.String(50), default='Assistant Professor')
    max_hours_per_day = db.Column(db.Integer, default=6)  # PDF constraint
    max_hours_per_week = db.Column(db.Integer, default=30)
    preferred_shift = db.Column(db.String(20), default='both')  # morning, evening, both
    specialization = db.Column(db.String(200))
    is_visiting = db.Column(db.Boolean, default=False)
    can_teach_labs = db.Column(db.Boolean, default=True)
    lab_specializations = db.Column(db.Text)  # JSON array of lab types faculty can handle
    average_leaves_per_month = db.Column(db.Float, default=2.0)  # PDF constraint
    research_hours_per_week = db.Column(db.Integer, default=0)  # Research time allocation
    
    # Relationships
    subjects = db.relationship('Subject', backref='faculty_member', lazy=True)
    schedule_entries = db.relationship('ScheduleEntry', backref='faculty', lazy=True)
    availabilities = db.relationship('FacultyAvailability', backref='faculty', lazy=True)
    leaves = db.relationship('FacultyLeave', backref='faculty', lazy=True)
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'email': self.email,
            'employee_id': self.employee_id,
            'designation': self.designation,
            'max_hours_per_day': self.max_hours_per_day,
            'max_hours_per_week': self.max_hours_per_week,
            'preferred_shift': self.preferred_shift,
            'specialization': self.specialization,
            'is_visiting': self.is_visiting,
            'can_teach_labs': self.can_teach_labs,
            'lab_specializations': json.loads(self.lab_specializations) if self.lab_specializations else [],
            'average_leaves_per_month': self.average_leaves_per_month,
            'department': self.department.name if self.department else None
        }

class Subject(db.Model):
    __tablename__ = 'subjects'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)  # PDF parameter
    code = db.Column(db.String(20), unique=True, nullable=False)
    credits = db.Column(db.Integer, default=3)
    theory_hours_per_week = db.Column(db.Integer, default=3)  # PDF parameter
    lab_hours_per_week = db.Column(db.Integer, default=0)
    tutorial_hours_per_week = db.Column(db.Integer, default=0)
    duration_minutes = db.Column(db.Integer, default=60)
    lab_duration_minutes = db.Column(db.Integer, default=120)  # Labs typically longer
    subject_type = db.Column(db.String(20), default='theory')  # theory, lab, practical, theory+lab
    is_elective = db.Column(db.Boolean, default=False)
    is_interdisciplinary = db.Column(db.Boolean, default=False)  # NEP 2020 support
    prerequisites = db.Column(db.Text)  # JSON string of prerequisite subject codes
    lab_requirements = db.Column(db.Text)  # JSON string of required lab equipment/software
    faculty_id = db.Column(db.Integer, db.ForeignKey('faculty.id'))  # PDF parameter
    lab_faculty_id = db.Column(db.Integer, db.ForeignKey('faculty.id'))  # Separate lab instructor
    semester_id = db.Column(db.Integer, db.ForeignKey('semesters.id'))  # PDF parameter
    min_students = db.Column(db.Integer, default=10)  # Minimum students for electives
    max_students = db.Column(db.Integer, default=60)  # Maximum students per class
    requires_continuous_slots = db.Column(db.Boolean, default=False)  # For back-to-back classes
    
    # Relationships
    schedule_entries = db.relationship('ScheduleEntry', backref='subject', lazy=True)
    lab_sessions = db.relationship('LabSession', backref='subject', lazy=True)
    electives = db.relationship('Elective', backref='subject', lazy=True)
    special_classes = db.relationship('SpecialClass', backref='subject', lazy=True)
    lab_faculty = db.relationship('Faculty', foreign_keys=[lab_faculty_id], backref='lab_subjects')
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'code': self.code,
            'credits': self.credits,
            'theory_hours_per_week': self.theory_hours_per_week,
            'lab_hours_per_week': self.lab_hours_per_week,
            'tutorial_hours_per_week': self.tutorial_hours_per_week,
            'subject_type': self.subject_type,
            'is_elective': self.is_elective,
            'is_interdisciplinary': self.is_interdisciplinary,
            'lab_requirements': json.loads(self.lab_requirements) if self.lab_requirements else [],
            'faculty_name': self.faculty_member.name if self.faculty_member else None,
            'lab_faculty_name': self.lab_faculty.name if self.lab_faculty else None,
            'prerequisites': json.loads(self.prerequisites) if self.prerequisites else [],
            'requires_continuous_slots': self.requires_continuous_slots
        }

class Batch(db.Model):
    __tablename__ = 'batches'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    student_count = db.Column(db.Integer, nullable=False)  # PDF parameter
    department_id = db.Column(db.Integer, db.ForeignKey('departments.id'))
    semester_id = db.Column(db.Integer, db.ForeignKey('semesters.id'))  # PDF parameter
    shift = db.Column(db.String(20), default='morning')  # morning, evening - PDF multi-shift support
    batch_type = db.Column(db.String(20), default='regular')  # regular, honors, research
    year_of_admission = db.Column(db.Integer)
    program_type = db.Column(db.String(10), default='UG')  # UG, PG
    max_classes_per_day = db.Column(db.Integer, default=6)  # PDF constraint
    lab_group_size = db.Column(db.Integer, default=15)  # Smaller groups for labs
    
    # Relationships
    schedule_entries = db.relationship('ScheduleEntry', backref='batch', lazy=True)
    lab_sessions = db.relationship('LabSession', backref='batch', lazy=True)
    electives = db.relationship('Elective', backref='batch', lazy=True)
    special_classes = db.relationship('SpecialClass', backref='batch', lazy=True)
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'student_count': self.student_count,
            'shift': self.shift,
            'batch_type': self.batch_type,
            'year_of_admission': self.year_of_admission,
            'program_type': self.program_type,
            'max_classes_per_day': self.max_classes_per_day,
            'lab_group_size': self.lab_group_size,
            'department': self.department.name if self.department else None
        }

class SpecialClass(db.Model):
    __tablename__ = 'special_classes'
    
    id = db.Column(db.Integer, primary_key=True)
    subject_id = db.Column(db.Integer, db.ForeignKey('subjects.id'), nullable=False)
    batch_id = db.Column(db.Integer, db.ForeignKey('batches.id'), nullable=False)
    day_of_week = db.Column(db.Integer, nullable=False)
    start_time = db.Column(db.Time, nullable=False)
    end_time = db.Column(db.Time, nullable=False)
    is_fixed = db.Column(db.Boolean, default=True)  # PDF constraint - fixed slots
    class_type = db.Column(db.String(50), default='special')  # exam, seminar, guest_lecture, etc.
    description = db.Column(db.String(200))
    recurring = db.Column(db.Boolean, default=False)  # If it repeats weekly
    priority = db.Column(db.Integer, default=1)  # 1=highest priority
    
    def to_dict(self):
        return {
            'id': self.id,
            'subject_name': self.subject.name,
            'batch_name': self.batch.name,
            'day_of_week': self.day_of_week,
            'start_time': str(self.start_time),
            'end_time': str(self.end_time),
            'is_fixed': self.is_fixed,
            'class_type': self.class_type,
            'description': self.description,
            'recurring': self.recurring,
            'priority': self.priority
        }

class Elective(db.Model):
    __tablename__ = 'electives'
    
    id = db.Column(db.Integer, primary_key=True)
    subject_id = db.Column(db.Integer, db.ForeignKey('subjects.id'), nullable=False)
    batch_id = db.Column(db.Integer, db.ForeignKey('batches.id'), nullable=False)
    enrolled_students = db.Column(db.Integer, default=0)
    min_enrollment = db.Column(db.Integer, default=10)
    max_enrollment = db.Column(db.Integer, default=60)
    is_active = db.Column(db.Boolean, default=True)
    registration_deadline = db.Column(db.Date)
    priority_level = db.Column(db.Integer, default=1)  # 1=high, 2=medium, 3=low
    
    def to_dict(self):
        return {
            'id': self.id,
            'subject_name': self.subject.name,
            'subject_code': self.subject.code,
            'batch_name': self.batch.name,
            'enrolled_students': self.enrolled_students,
            'min_enrollment': self.min_enrollment,
            'max_enrollment': self.max_enrollment,
            'is_active': self.is_active,
            'priority_level': self.priority_level
        }

class FacultyAvailability(db.Model):
    __tablename__ = 'faculty_availability'
    
    id = db.Column(db.Integer, primary_key=True)
    faculty_id = db.Column(db.Integer, db.ForeignKey('faculty.id'), nullable=False)
    day_of_week = db.Column(db.Integer, nullable=False)  # 1=Monday, 7=Sunday
    available_start = db.Column(db.Time, nullable=False)
    available_end = db.Column(db.Time, nullable=False)
    shift = db.Column(db.String(20), default='both')  # morning, evening, both
    is_preferred = db.Column(db.Boolean, default=True)
    unavailability_reason = db.Column(db.String(100))  # research, meeting, leave, etc.
    can_teach_labs = db.Column(db.Boolean, default=True)
    
    def to_dict(self):
        return {
            'id': self.id,
            'faculty_name': self.faculty.name,
            'day_of_week': self.day_of_week,
            'available_start': str(self.available_start),
            'available_end': str(self.available_end),
            'shift': self.shift,
            'is_preferred': self.is_preferred,
            'unavailability_reason': self.unavailability_reason,
            'can_teach_labs': self.can_teach_labs
        }

class FacultyLeave(db.Model):
    __tablename__ = 'faculty_leaves'
    
    id = db.Column(db.Integer, primary_key=True)
    faculty_id = db.Column(db.Integer, db.ForeignKey('faculty.id'), nullable=False)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    leave_type = db.Column(db.String(30), default='casual')  # casual, medical, conference, research
    is_approved = db.Column(db.Boolean, default=False)
    substitute_faculty_id = db.Column(db.Integer, db.ForeignKey('faculty.id'))
    reason = db.Column(db.String(200))
    
    # Relationships
    substitute_faculty = db.relationship('Faculty', foreign_keys=[substitute_faculty_id], backref='substitute_assignments')
    
    def to_dict(self):
        return {
            'id': self.id,
            'faculty_name': self.faculty.name,
            'start_date': self.start_date.isoformat(),
            'end_date': self.end_date.isoformat(),
            'leave_type': self.leave_type,
            'is_approved': self.is_approved,
            'substitute_faculty': self.substitute_faculty.name if self.substitute_faculty else None,
            'reason': self.reason
        }

class LabSession(db.Model):
    __tablename__ = 'lab_sessions'
    
    id = db.Column(db.Integer, primary_key=True)
    subject_id = db.Column(db.Integer, db.ForeignKey('subjects.id'), nullable=False)
    batch_id = db.Column(db.Integer, db.ForeignKey('batches.id'), nullable=False)
    laboratory_id = db.Column(db.Integer, db.ForeignKey('laboratories.id'), nullable=False)
    session_name = db.Column(db.String(100), nullable=False)
    duration_minutes = db.Column(db.Integer, default=120)
    required_equipment = db.Column(db.Text)  # JSON string of required equipment
    software_requirements = db.Column(db.Text)  # JSON string of required software
    safety_protocols = db.Column(db.Text)
    group_size = db.Column(db.Integer, default=15)
    requires_technician = db.Column(db.Boolean, default=False)
    preparation_time_minutes = db.Column(db.Integer, default=30)
    
    def to_dict(self):
        return {
            'id': self.id,
            'subject_name': self.subject.name,
            'batch_name': self.batch.name,
            'laboratory_name': self.laboratory.name,
            'session_name': self.session_name,
            'duration_minutes': self.duration_minutes,
            'required_equipment': json.loads(self.required_equipment) if self.required_equipment else [],
            'software_requirements': json.loads(self.software_requirements) if self.software_requirements else [],
            'group_size': self.group_size,
            'requires_technician': self.requires_technician
        }

class Timetable(db.Model):
    __tablename__ = 'timetables'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    semester_id = db.Column(db.Integer, db.ForeignKey('semesters.id'))
    status = db.Column(db.String(20), default='draft')  # draft, under_review, approved, active, archived
    fitness_score = db.Column(db.Float, default=0.0)
    classroom_utilization = db.Column(db.Float, default=0.0)  # PDF requirement - maximize utilization
    lab_utilization = db.Column(db.Float, default=0.0)
    faculty_load_balance = db.Column(db.Float, default=0.0)  # PDF requirement - minimize workload
    conflict_count = db.Column(db.Integer, default=0)
    total_classes_scheduled = db.Column(db.Integer, default=0)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    approved_at = db.Column(db.DateTime)
    approved_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    review_comments = db.Column(db.Text)
    
    # Relationships
    schedule_entries = db.relationship('ScheduleEntry', backref='timetable', cascade='all, delete-orphan')
    creator = db.relationship('User', foreign_keys=[created_by], backref='created_timetables')
    approver = db.relationship('User', foreign_keys=[approved_by], backref='approved_timetables')
    conflicts = db.relationship('ScheduleConflict', backref='timetable', cascade='all, delete-orphan')
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'status': self.status,
            'fitness_score': self.fitness_score,
            'classroom_utilization': self.classroom_utilization,
            'lab_utilization': self.lab_utilization,
            'faculty_load_balance': self.faculty_load_balance,
            'conflict_count': self.conflict_count,
            'total_classes_scheduled': self.total_classes_scheduled,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'approved_at': self.approved_at.isoformat() if self.approved_at else None,
            'creator': self.creator.username if self.creator else None,
            'review_comments': self.review_comments
        }

class ScheduleEntry(db.Model):
    __tablename__ = 'schedule_entries'
    
    id = db.Column(db.Integer, primary_key=True)
    timetable_id = db.Column(db.Integer, db.ForeignKey('timetables.id'), nullable=False)
    subject_id = db.Column(db.Integer, db.ForeignKey('subjects.id'), nullable=False)
    faculty_id = db.Column(db.Integer, db.ForeignKey('faculty.id'), nullable=False)
    classroom_id = db.Column(db.Integer, db.ForeignKey('classrooms.id'))
    laboratory_id = db.Column(db.Integer, db.ForeignKey('laboratories.id'))
    batch_id = db.Column(db.Integer, db.ForeignKey('batches.id'), nullable=False)
    day_of_week = db.Column(db.Integer, nullable=False)
    start_time = db.Column(db.Time, nullable=False)
    end_time = db.Column(db.Time, nullable=False)
    is_fixed = db.Column(db.Boolean, default=False)  # PDF constraint - special classes
    shift = db.Column(db.String(20), default='morning')
    class_type = db.Column(db.String(20), default='theory')  # theory, lab, tutorial, practical
    actual_students = db.Column(db.Integer, default=0)
    requires_setup = db.Column(db.Boolean, default=False)
    setup_time_minutes = db.Column(db.Integer, default=0)
    
    def to_dict(self):
        return {
            'id': self.id,
            'subject_name': self.subject.name,
            'subject_code': self.subject.code,
            'faculty_name': self.faculty.name,
            'venue_name': self.classroom.name if self.classroom else self.laboratory.name,
            'venue_type': 'classroom' if self.classroom else 'laboratory',
            'batch_name': self.batch.name,
            'day_of_week': self.day_of_week,
            'start_time': str(self.start_time),
            'end_time': str(self.end_time),
            'is_fixed': self.is_fixed,
            'shift': self.shift,
            'class_type': self.class_type,
            'actual_students': self.actual_students
        }

class ScheduleConflict(db.Model):
    __tablename__ = 'schedule_conflicts'
    
    id = db.Column(db.Integer, primary_key=True)
    timetable_id = db.Column(db.Integer, db.ForeignKey('timetables.id'), nullable=False)
    conflict_type = db.Column(db.String(50), nullable=False)  # room, faculty, batch, capacity, shift, lab_equipment
    entry1_id = db.Column(db.Integer, db.ForeignKey('schedule_entries.id'))
    entry2_id = db.Column(db.Integer, db.ForeignKey('schedule_entries.id'))
    severity = db.Column(db.String(20), default='high')  # low, medium, high, critical
    description = db.Column(db.String(200))
    suggested_solution = db.Column(db.Text)  # JSON string with suggestions - PDF requirement
    is_resolved = db.Column(db.Boolean, default=False)
    auto_resolvable = db.Column(db.Boolean, default=False)
    
    def to_dict(self):
        return {
            'id': self.id,
            'conflict_type': self.conflict_type,
            'severity': self.severity,
            'description': self.description,
            'suggested_solution': json.loads(self.suggested_solution) if self.suggested_solution else [],
            'is_resolved': self.is_resolved,
            'auto_resolvable': self.auto_resolvable
        }

class TimetableReview(db.Model):
    __tablename__ = 'timetable_reviews'
    
    id = db.Column(db.Integer, primary_key=True)
    timetable_id = db.Column(db.Integer, db.ForeignKey('timetables.id'), nullable=False)
    reviewer_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    review_status = db.Column(db.String(20), default='pending')  # PDF requirement - review workflow
    comments = db.Column(db.Text)
    reviewed_at = db.Column(db.DateTime, default=datetime.utcnow)
    priority_issues = db.Column(db.Text)  # JSON array of high priority issues
    suggested_changes = db.Column(db.Text)  # JSON array of suggested changes
    
    # Relationships
    timetable = db.relationship('Timetable', backref='reviews')
    reviewer = db.relationship('User', backref='reviews_conducted')
    
    def to_dict(self):
        return {
            'id': self.id,
            'timetable_name': self.timetable.name,
            'reviewer_name': self.reviewer.username,
            'review_status': self.review_status,
            'comments': self.comments,
            'reviewed_at': self.reviewed_at.isoformat(),
            'priority_issues': json.loads(self.priority_issues) if self.priority_issues else [],
            'suggested_changes': json.loads(self.suggested_changes) if self.suggested_changes else []
        }