from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import *
from scheduler_engine import AdvancedTimetableOptimizer
from config import Config
from datetime import datetime, timedelta
import json

api = Blueprint('api', __name__)

# Utility Functions
def convert_day_to_number(day_name):
    """Convert day name to number"""
    days = {'Monday': 1, 'Tuesday': 2, 'Wednesday': 3, 'Thursday': 4, 'Friday': 5, 'Saturday': 6, 'Sunday': 7}
    return days.get(day_name, 1)

def convert_day_to_name(day_number):
    """Convert day number to name"""
    days = {1: 'Monday', 2: 'Tuesday', 3: 'Wednesday', 4: 'Thursday', 5: 'Friday', 6: 'Saturday', 7: 'Sunday'}
    return days.get(day_number, 'Monday')

# ===== AUTHENTICATION ROUTES =====

@api.route('/login', methods=['POST'])
def login():
    """User login with JWT token generation"""
    try:
        data = request.get_json()
        username = data.get('username')
        password = data.get('password')
        
        if not username or not password:
            return jsonify({'success': False, 'message': 'Username and password required'}), 400
        
        user = User.query.filter_by(username=username).first()
        
        if user and user.check_password(password):
            from flask_jwt_extended import create_access_token
            access_token = create_access_token(identity=user.id)
            return jsonify({
                'success': True,
                'access_token': access_token,
                'user': user.to_dict()
            })
        else:
            return jsonify({'success': False, 'message': 'Invalid credentials'}), 401
            
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@api.route('/register', methods=['POST'])
@jwt_required()
def register():
    """User registration (admin only)"""
    try:
        current_user_id = get_jwt_identity()
        current_user = User.query.get(current_user_id)
        
        if current_user.role != 'admin':
            return jsonify({'success': False, 'message': 'Admin privileges required'}), 403
        
        data = request.get_json()
        
        # Check if user already exists
        existing_user = User.query.filter_by(username=data['username']).first()
        if existing_user:
            return jsonify({'success': False, 'message': 'Username already exists'}), 400
        
        existing_email = User.query.filter_by(email=data['email']).first()
        if existing_email:
            return jsonify({'success': False, 'message': 'Email already exists'}), 400
        
        # Create new user
        new_user = User(
            username=data['username'],
            email=data['email'],
            role=data.get('role', 'admin'),
            department_id=data.get('department_id')
        )
        new_user.set_password(data['password'])
        
        db.session.add(new_user)
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'User registered successfully', 'user': new_user.to_dict()}), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

# ===== DEPARTMENT MANAGEMENT =====

@api.route('/departments', methods=['GET', 'POST'])
@jwt_required()
def handle_departments():
    """Get all departments or create new department"""
    try:
        if request.method == 'GET':
            departments = Department.query.all()
            return jsonify({'success': True, 'departments': [dept.to_dict() for dept in departments]})
        
        elif request.method == 'POST':
            data = request.get_json()
            
            # Check if department code already exists
            existing_dept = Department.query.filter_by(code=data['code']).first()
            if existing_dept:
                return jsonify({'success': False, 'message': 'Department code already exists'}), 400
            
            new_department = Department(
                name=data['name'],
                code=data['code'],
                shift_preference=data.get('shift_preference', 'both'),
                max_classes_per_day=data.get('max_classes_per_day', 8),
                lab_duration_multiplier=data.get('lab_duration_multiplier', 2.0)
            )
            
            db.session.add(new_department)
            db.session.commit()
            
            return jsonify({'success': True, 'message': 'Department created successfully', 'department': new_department.to_dict()}), 201
            
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

@api.route('/departments/<int:dept_id>', methods=['GET', 'PUT', 'DELETE'])
@jwt_required()
def handle_department(dept_id):
    """Get, update, or delete specific department"""
    try:
        department = Department.query.get_or_404(dept_id)
        
        if request.method == 'GET':
            return jsonify({'success': True, 'department': department.to_dict()})
        
        elif request.method == 'PUT':
            data = request.get_json()
            
            department.name = data.get('name', department.name)
            department.shift_preference = data.get('shift_preference', department.shift_preference)
            department.max_classes_per_day = data.get('max_classes_per_day', department.max_classes_per_day)
            department.lab_duration_multiplier = data.get('lab_duration_multiplier', department.lab_duration_multiplier)
            
            db.session.commit()
            return jsonify({'success': True, 'message': 'Department updated successfully', 'department': department.to_dict()})
        
        elif request.method == 'DELETE':
            db.session.delete(department)
            db.session.commit()
            return jsonify({'success': True, 'message': 'Department deleted successfully'})
            
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

# ===== SEMESTER MANAGEMENT =====

@api.route('/semesters', methods=['GET', 'POST'])
@jwt_required()
def handle_semesters():
    """Get all semesters or create new semester"""
    try:
        if request.method == 'GET':
            semesters = Semester.query.all()
            return jsonify({'success': True, 'semesters': [sem.to_dict() for sem in semesters]})
        
        elif request.method == 'POST':
            data = request.get_json()
            
            new_semester = Semester(
                name=data['name'],
                year=data['year'],
                is_active=data.get('is_active', True),
                program_type=data.get('program_type', 'UG'),
                start_date=datetime.strptime(data['start_date'], '%Y-%m-%d').date() if data.get('start_date') else None,
                end_date=datetime.strptime(data['end_date'], '%Y-%m-%d').date() if data.get('end_date') else None
            )
            
            db.session.add(new_semester)
            db.session.commit()
            
            return jsonify({'success': True, 'message': 'Semester created successfully', 'semester': new_semester.to_dict()}), 201
            
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

# ===== CLASSROOM MANAGEMENT =====

@api.route('/classrooms', methods=['GET', 'POST'])
@jwt_required()
def handle_classrooms():
    """Get all classrooms or create new classroom"""
    try:
        if request.method == 'GET':
            department_id = request.args.get('department_id')
            available_only = request.args.get('available_only', 'false').lower() == 'true'
            
            query = Classroom.query
            if department_id:
                query = query.filter_by(department_id=department_id)
            if available_only:
                query = query.filter_by(is_available=True)
            
            classrooms = query.all()
            return jsonify({'success': True, 'classrooms': [room.to_dict() for room in classrooms]})
        
        elif request.method == 'POST':
            data = request.get_json()
            
            new_classroom = Classroom(
                name=data['name'],
                capacity=data['capacity'],
                room_type=data.get('room_type', 'lecture'),
                equipment=json.dumps(data.get('equipment', [])),
                is_available=data.get('is_available', True),
                department_id=data.get('department_id'),
                shift_availability=data.get('shift_availability', 'both'),
                floor_number=data.get('floor_number', 1),
                building=data.get('building')
            )
            
            db.session.add(new_classroom)
            db.session.commit()
            
            return jsonify({'success': True, 'message': 'Classroom created successfully', 'classroom': new_classroom.to_dict()}), 201
            
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

# ===== LABORATORY MANAGEMENT (LABS MODE FOCUS) =====

@api.route('/laboratories', methods=['GET', 'POST'])
@jwt_required()
def handle_laboratories():
    """Get all laboratories or create new laboratory - ENHANCED FOR LABS MODE"""
    try:
        if request.method == 'GET':
            department_id = request.args.get('department_id')
            lab_type = request.args.get('lab_type')
            available_only = request.args.get('available_only', 'false').lower() == 'true'
            
            query = Laboratory.query
            if department_id:
                query = query.filter_by(department_id=department_id)
            if lab_type:
                query = query.filter_by(lab_type=lab_type)
            if available_only:
                query = query.filter_by(is_available=True)
            
            laboratories = query.all()
            return jsonify({'success': True, 'laboratories': [lab.to_dict() for lab in laboratories]})
        
        elif request.method == 'POST':
            data = request.get_json()
            
            new_laboratory = Laboratory(
                name=data['name'],
                capacity=data['capacity'],
                lab_type=data['lab_type'],
                equipment=json.dumps(data.get('equipment', [])),
                safety_requirements=data.get('safety_requirements'),
                is_available=data.get('is_available', True),
                department_id=data.get('department_id'),
                shift_availability=data.get('shift_availability', 'both'),
                setup_time_minutes=data.get('setup_time_minutes', Config.DEFAULT_LAB_SETUP_TIME),
                cleanup_time_minutes=data.get('cleanup_time_minutes', Config.DEFAULT_LAB_CLEANUP_TIME),
                floor_number=data.get('floor_number', 1),
                building=data.get('building'),
                requires_technician=data.get('requires_technician', False)
            )
            
            db.session.add(new_laboratory)
            db.session.commit()
            
            return jsonify({'success': True, 'message': 'Laboratory created successfully', 'laboratory': new_laboratory.to_dict()}), 201
            
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

@api.route('/laboratories/<int:lab_id>', methods=['GET', 'PUT', 'DELETE'])
@jwt_required()
def handle_laboratory(lab_id):
    """Get, update, or delete specific laboratory"""
    try:
        laboratory = Laboratory.query.get_or_404(lab_id)
        
        if request.method == 'GET':
            return jsonify({'success': True, 'laboratory': laboratory.to_dict()})
        
        elif request.method == 'PUT':
            data = request.get_json()
            
            laboratory.name = data.get('name', laboratory.name)
            laboratory.capacity = data.get('capacity', laboratory.capacity)
            laboratory.lab_type = data.get('lab_type', laboratory.lab_type)
            laboratory.equipment = json.dumps(data.get('equipment', json.loads(laboratory.equipment or '[]')))
            laboratory.safety_requirements = data.get('safety_requirements', laboratory.safety_requirements)
            laboratory.is_available = data.get('is_available', laboratory.is_available)
            laboratory.shift_availability = data.get('shift_availability', laboratory.shift_availability)
            laboratory.setup_time_minutes = data.get('setup_time_minutes', laboratory.setup_time_minutes)
            laboratory.cleanup_time_minutes = data.get('cleanup_time_minutes', laboratory.cleanup_time_minutes)
            laboratory.requires_technician = data.get('requires_technician', laboratory.requires_technician)
            
            db.session.commit()
            return jsonify({'success': True, 'message': 'Laboratory updated successfully', 'laboratory': laboratory.to_dict()})
        
        elif request.method == 'DELETE':
            db.session.delete(laboratory)
            db.session.commit()
            return jsonify({'success': True, 'message': 'Laboratory deleted successfully'})
            
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

@api.route('/laboratories/<int:lab_id>/availability', methods=['GET'])
@jwt_required()
def get_laboratory_availability(lab_id):
    """Get laboratory availability for scheduling"""
    try:
        laboratory = Laboratory.query.get_or_404(lab_id)
        
        # Get current schedule entries for this lab
        current_bookings = ScheduleEntry.query.filter_by(laboratory_id=lab_id).all()
        
        # Calculate available slots considering setup/cleanup time
        available_slots = []
        for day in Config.WORKING_DAYS:
            day_number = convert_day_to_number(day)
            
            # Get bookings for this day
            day_bookings = [booking for booking in current_bookings if booking.day_of_week == day_number]
            
            # Generate available slots for lab (considering extended durations)
            for lab_slot in Config.LAB_TIME_SLOTS:
                start_time = datetime.strptime(lab_slot[0], '%H:%M').time()
                end_time = datetime.strptime(lab_slot[1], '%H:%M').time()
                
                # Check if slot conflicts with existing bookings (including setup/cleanup)
                is_available = True
                for booking in day_bookings:
                    booking_start = booking.start_time
                    booking_end = booking.end_time
                    
                    # Add buffer time for lab sessions
                    buffer_start = (datetime.combine(datetime.today(), booking_start) - timedelta(minutes=laboratory.setup_time_minutes)).time()
                    buffer_end = (datetime.combine(datetime.today(), booking_end) + timedelta(minutes=laboratory.cleanup_time_minutes)).time()
                    
                    if not (end_time <= buffer_start or start_time >= buffer_end):
                        is_available = False
                        break
                
                if is_available:
                    available_slots.append({
                        'day': day,
                        'start_time': lab_slot[0],
                        'end_time': lab_slot[1],
                        'duration_minutes': (datetime.strptime(lab_slot[1], '%H:%M') - datetime.strptime(lab_slot[0], '%H:%M')).seconds // 60
                    })
        
        return jsonify({
            'success': True,
            'laboratory': laboratory.to_dict(),
            'available_slots': available_slots,
            'current_bookings': [booking.to_dict() for booking in current_bookings]
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

# ===== LAB SESSIONS MANAGEMENT (LABS MODE FOCUS) =====

@api.route('/lab-sessions', methods=['GET', 'POST'])
@jwt_required()
def handle_lab_sessions():
    """Get all lab sessions or create new lab session - ENHANCED FOR LABS MODE"""
    try:
        if request.method == 'GET':
            subject_id = request.args.get('subject_id')
            batch_id = request.args.get('batch_id')
            laboratory_id = request.args.get('laboratory_id')
            semester_id = request.args.get('semester_id')
            
            query = LabSession.query
            if subject_id:
                query = query.filter_by(subject_id=subject_id)
            if batch_id:
                query = query.filter_by(batch_id=batch_id)
            if laboratory_id:
                query = query.filter_by(laboratory_id=laboratory_id)
            if semester_id:
                query = query.join(Subject).filter(Subject.semester_id == semester_id)
            
            lab_sessions = query.all()
            return jsonify({'success': True, 'lab_sessions': [session.to_dict() for session in lab_sessions]})
        
        elif request.method == 'POST':
            data = request.get_json()
            
            # Validate that lab has required equipment
            laboratory = Laboratory.query.get(data['laboratory_id'])
            if not laboratory:
                return jsonify({'success': False, 'message': 'Laboratory not found'}), 404
            
            required_equipment = data.get('required_equipment', [])
            lab_equipment = json.loads(laboratory.equipment or '[]')
            
            missing_equipment = [eq for eq in required_equipment if eq not in lab_equipment]
            if missing_equipment:
                return jsonify({
                    'success': False, 
                    'message': f'Laboratory missing required equipment: {missing_equipment}',
                    'missing_equipment': missing_equipment
                }), 400
            
            new_lab_session = LabSession(
                subject_id=data['subject_id'],
                batch_id=data['batch_id'],
                laboratory_id=data['laboratory_id'],
                session_name=data['session_name'],
                duration_minutes=data.get('duration_minutes', Config.DEFAULT_LAB_DURATION_MINUTES),
                required_equipment=json.dumps(required_equipment),
                software_requirements=json.dumps(data.get('software_requirements', [])),
                safety_protocols=data.get('safety_protocols'),
                group_size=data.get('group_size', Config.MAX_LAB_GROUP_SIZE),
                requires_technician=data.get('requires_technician', False),
                preparation_time_minutes=data.get('preparation_time_minutes', 30)
            )
            
            db.session.add(new_lab_session)
            db.session.commit()
            
            return jsonify({'success': True, 'message': 'Lab session created successfully', 'lab_session': new_lab_session.to_dict()}), 201
            
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

@api.route('/lab-sessions/<int:session_id>', methods=['GET', 'PUT', 'DELETE'])
@jwt_required()
def handle_lab_session(session_id):
    """Get, update, or delete specific lab session"""
    try:
        lab_session = LabSession.query.get_or_404(session_id)
        
        if request.method == 'GET':
            return jsonify({'success': True, 'lab_session': lab_session.to_dict()})
        
        elif request.method == 'PUT':
            data = request.get_json()
            
            lab_session.session_name = data.get('session_name', lab_session.session_name)
            lab_session.duration_minutes = data.get('duration_minutes', lab_session.duration_minutes)
            lab_session.required_equipment = json.dumps(data.get('required_equipment', json.loads(lab_session.required_equipment or '[]')))
            lab_session.software_requirements = json.dumps(data.get('software_requirements', json.loads(lab_session.software_requirements or '[]')))
            lab_session.safety_protocols = data.get('safety_protocols', lab_session.safety_protocols)
            lab_session.group_size = data.get('group_size', lab_session.group_size)
            lab_session.requires_technician = data.get('requires_technician', lab_session.requires_technician)
            lab_session.preparation_time_minutes = data.get('preparation_time_minutes', lab_session.preparation_time_minutes)
            
            db.session.commit()
            return jsonify({'success': True, 'message': 'Lab session updated successfully', 'lab_session': lab_session.to_dict()})
        
        elif request.method == 'DELETE':
            db.session.delete(lab_session)
            db.session.commit()
            return jsonify({'success': True, 'message': 'Lab session deleted successfully'})
            
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

# ===== FACULTY MANAGEMENT =====

@api.route('/faculty', methods=['GET', 'POST'])
@jwt_required()
def handle_faculty():
    """Get all faculty or create new faculty member"""
    try:
        if request.method == 'GET':
            department_id = request.args.get('department_id')
            can_teach_labs = request.args.get('can_teach_labs', 'false').lower() == 'true'
            
            query = Faculty.query
            if department_id:
                query = query.filter_by(department_id=department_id)
            if can_teach_labs:
                query = query.filter_by(can_teach_labs=True)
            
            faculty = query.all()
            return jsonify({'success': True, 'faculty': [f.to_dict() for f in faculty]})
        
        elif request.method == 'POST':
            data = request.get_json()
            
            # Check if employee_id already exists
            if data.get('employee_id'):
                existing_faculty = Faculty.query.filter_by(employee_id=data['employee_id']).first()
                if existing_faculty:
                    return jsonify({'success': False, 'message': 'Employee ID already exists'}), 400
            
            new_faculty = Faculty(
                name=data['name'],
                email=data.get('email'),
                employee_id=data.get('employee_id'),
                department_id=data.get('department_id'),
                designation=data.get('designation', 'Assistant Professor'),
                max_hours_per_day=data.get('max_hours_per_day', Config.DEFAULT_MAX_FACULTY_HOURS_PER_DAY),
                max_hours_per_week=data.get('max_hours_per_week', Config.DEFAULT_MAX_FACULTY_HOURS_PER_WEEK),
                preferred_shift=data.get('preferred_shift', 'both'),
                specialization=data.get('specialization'),
                is_visiting=data.get('is_visiting', False),
                can_teach_labs=data.get('can_teach_labs', True),
                lab_specializations=json.dumps(data.get('lab_specializations', [])),
                average_leaves_per_month=data.get('average_leaves_per_month', Config.DEFAULT_FACULTY_LEAVES_PER_MONTH),
                research_hours_per_week=data.get('research_hours_per_week', 0)
            )
            
            db.session.add(new_faculty)
            db.session.commit()
            
            return jsonify({'success': True, 'message': 'Faculty member created successfully', 'faculty': new_faculty.to_dict()}), 201
            
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

# ===== FACULTY LEAVES MANAGEMENT (PDF CONSTRAINT) =====

@api.route('/faculty-leaves', methods=['GET', 'POST'])
@jwt_required()
def handle_faculty_leaves():
    """Get all faculty leaves or create new leave request - PDF CONSTRAINT SUPPORT"""
    try:
        if request.method == 'GET':
            faculty_id = request.args.get('faculty_id')
            month = request.args.get('month')  # Format: YYYY-MM
            is_approved = request.args.get('is_approved')
            
            query = FacultyLeave.query
            if faculty_id:
                query = query.filter_by(faculty_id=faculty_id)
            if month:
                year, month_num = map(int, month.split('-'))
                start_date = datetime(year, month_num, 1).date()
                if month_num == 12:
                    end_date = datetime(year + 1, 1, 1).date() - timedelta(days=1)
                else:
                    end_date = datetime(year, month_num + 1, 1).date() - timedelta(days=1)
                query = query.filter(FacultyLeave.start_date <= end_date, FacultyLeave.end_date >= start_date)
            if is_approved is not None:
                query = query.filter_by(is_approved=is_approved.lower() == 'true')
            
            leaves = query.all()
            return jsonify({'success': True, 'leaves': [leave.to_dict() for leave in leaves]})
        
        elif request.method == 'POST':
            data = request.get_json()
            
            # Validate dates
            start_date = datetime.strptime(data['start_date'], '%Y-%m-%d').date()
            end_date = datetime.strptime(data['end_date'], '%Y-%m-%d').date()
            
            if end_date < start_date:
                return jsonify({'success': False, 'message': 'End date must be after start date'}), 400
            
            # Check for overlapping leaves
            faculty_id = data['faculty_id']
            overlapping_leaves = FacultyLeave.query.filter(
                FacultyLeave.faculty_id == faculty_id,
                FacultyLeave.start_date <= end_date,
                FacultyLeave.end_date >= start_date,
                FacultyLeave.is_approved == True
            ).first()
            
            if overlapping_leaves:
                return jsonify({'success': False, 'message': 'Leave dates overlap with existing approved leave'}), 400
            
            new_leave = FacultyLeave(
                faculty_id=faculty_id,
                start_date=start_date,
                end_date=end_date,
                leave_type=data.get('leave_type', 'casual'),
                is_approved=data.get('is_approved', False),
                substitute_faculty_id=data.get('substitute_faculty_id'),
                reason=data.get('reason')
            )
            
            db.session.add(new_leave)
            db.session.commit()
            
            return jsonify({'success': True, 'message': 'Faculty leave request created successfully', 'leave': new_leave.to_dict()}), 201
            
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

@api.route('/faculty-leaves/<int:leave_id>/approve', methods=['PUT'])
@jwt_required()
def approve_faculty_leave(leave_id):
    """Approve or reject faculty leave request"""
    try:
        leave = FacultyLeave.query.get_or_404(leave_id)
        data = request.get_json()
        
        leave.is_approved = data.get('is_approved', True)
        leave.substitute_faculty_id = data.get('substitute_faculty_id')
        
        db.session.commit()
        
        status = 'approved' if leave.is_approved else 'rejected'
        return jsonify({'success': True, 'message': f'Leave request {status} successfully', 'leave': leave.to_dict()})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

# ===== FACULTY AVAILABILITY MANAGEMENT =====

@api.route('/faculty-availability', methods=['GET', 'POST'])
@jwt_required()
def handle_faculty_availability():
    """Get all faculty availability or create new availability"""
    try:
        if request.method == 'GET':
            faculty_id = request.args.get('faculty_id')
            can_teach_labs = request.args.get('can_teach_labs', 'false').lower() == 'true'
            
            query = FacultyAvailability.query
            if faculty_id:
                query = query.filter_by(faculty_id=faculty_id)
            if can_teach_labs:
                query = query.filter_by(can_teach_labs=True)
            
            availabilities = query.all()
            return jsonify({'success': True, 'availabilities': [avail.to_dict() for avail in availabilities]})
        
        elif request.method == 'POST':
            data = request.get_json()
            
            new_availability = FacultyAvailability(
                faculty_id=data['faculty_id'],
                day_of_week=data['day_of_week'],
                available_start=datetime.strptime(data['available_start'], '%H:%M').time(),
                available_end=datetime.strptime(data['available_end'], '%H:%M').time(),
                shift=data.get('shift', 'both'),
                is_preferred=data.get('is_preferred', True),
                unavailability_reason=data.get('unavailability_reason'),
                can_teach_labs=data.get('can_teach_labs', True)
            )
            
            db.session.add(new_availability)
            db.session.commit()
            
            return jsonify({'success': True, 'message': 'Faculty availability created successfully', 'availability': new_availability.to_dict()}), 201
            
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

# ===== SUBJECT MANAGEMENT =====

@api.route('/subjects', methods=['GET', 'POST'])
@jwt_required()
def handle_subjects():
    """Get all subjects or create new subject"""
    try:
        if request.method == 'GET':
            semester_id = request.args.get('semester_id')
            subject_type = request.args.get('subject_type')
            has_lab = request.args.get('has_lab', 'false').lower() == 'true'
            
            query = Subject.query
            if semester_id:
                query = query.filter_by(semester_id=semester_id)
            if subject_type:
                query = query.filter_by(subject_type=subject_type)
            if has_lab:
                query = query.filter(Subject.lab_hours_per_week > 0)
            
            subjects = query.all()
            return jsonify({'success': True, 'subjects': [subj.to_dict() for subj in subjects]})
        
        elif request.method == 'POST':
            data = request.get_json()
            
            # Check if subject code already exists
            existing_subject = Subject.query.filter_by(code=data['code']).first()
            if existing_subject:
                return jsonify({'success': False, 'message': 'Subject code already exists'}), 400
            
            new_subject = Subject(
                name=data['name'],
                code=data['code'],
                credits=data.get('credits', 3),
                theory_hours_per_week=data.get('theory_hours_per_week', 3),
                lab_hours_per_week=data.get('lab_hours_per_week', 0),
                tutorial_hours_per_week=data.get('tutorial_hours_per_week', 0),
                duration_minutes=data.get('duration_minutes', 60),
                lab_duration_minutes=data.get('lab_duration_minutes', Config.DEFAULT_LAB_DURATION_MINUTES),
                subject_type=data.get('subject_type', 'theory'),
                is_elective=data.get('is_elective', False),
                is_interdisciplinary=data.get('is_interdisciplinary', False),
                prerequisites=json.dumps(data.get('prerequisites', [])),
                lab_requirements=json.dumps(data.get('lab_requirements', [])),
                faculty_id=data.get('faculty_id'),
                lab_faculty_id=data.get('lab_faculty_id'),
                semester_id=data['semester_id'],
                min_students=data.get('min_students', 10),
                max_students=data.get('max_students', 60),
                requires_continuous_slots=data.get('requires_continuous_slots', False)
            )
            
            db.session.add(new_subject)
            db.session.commit()
            
            return jsonify({'success': True, 'message': 'Subject created successfully', 'subject': new_subject.to_dict()}), 201
            
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

# ===== BATCH MANAGEMENT =====

@api.route('/batches', methods=['GET', 'POST'])
@jwt_required()
def handle_batches():
    """Get all batches or create new batch"""
    try:
        if request.method == 'GET':
            semester_id = request.args.get('semester_id')
            department_id = request.args.get('department_id')
            shift = request.args.get('shift')
            
            query = Batch.query
            if semester_id:
                query = query.filter_by(semester_id=semester_id)
            if department_id:
                query = query.filter_by(department_id=department_id)
            if shift:
                query = query.filter_by(shift=shift)
            
            batches = query.all()
            return jsonify({'success': True, 'batches': [batch.to_dict() for batch in batches]})
        
        elif request.method == 'POST':
            data = request.get_json()
            
            new_batch = Batch(
                name=data['name'],
                student_count=data['student_count'],
                department_id=data['department_id'],
                semester_id=data['semester_id'],
                shift=data.get('shift', 'morning'),
                batch_type=data.get('batch_type', 'regular'),
                year_of_admission=data.get('year_of_admission'),
                program_type=data.get('program_type', 'UG'),
                max_classes_per_day=data.get('max_classes_per_day', Config.MAX_CLASSES_PER_DAY),
                lab_group_size=data.get('lab_group_size', Config.MAX_LAB_GROUP_SIZE)
            )
            
            db.session.add(new_batch)
            db.session.commit()
            
            return jsonify({'success': True, 'message': 'Batch created successfully', 'batch': new_batch.to_dict()}), 201
            
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

# ===== SPECIAL CLASSES MANAGEMENT (PDF CONSTRAINT) =====

@api.route('/special-classes', methods=['GET', 'POST'])
@jwt_required()
def handle_special_classes():
    """Get all special classes or create new special class - PDF FIXED SLOTS SUPPORT"""
    try:
        if request.method == 'GET':
            subject_id = request.args.get('subject_id')
            batch_id = request.args.get('batch_id')
            is_fixed = request.args.get('is_fixed', 'true').lower() == 'true'
            
            query = SpecialClass.query
            if subject_id:
                query = query.filter_by(subject_id=subject_id)
            if batch_id:
                query = query.filter_by(batch_id=batch_id)
            if is_fixed:
                query = query.filter_by(is_fixed=True)
            
            special_classes = query.all()
            return jsonify({'success': True, 'special_classes': [sc.to_dict() for sc in special_classes]})
        
        elif request.method == 'POST':
            data = request.get_json()
            
            new_special_class = SpecialClass(
                subject_id=data['subject_id'],
                batch_id=data['batch_id'],
                day_of_week=data['day_of_week'],
                start_time=datetime.strptime(data['start_time'], '%H:%M').time(),
                end_time=datetime.strptime(data['end_time'], '%H:%M').time(),
                is_fixed=data.get('is_fixed', True),
                class_type=data.get('class_type', 'special'),
                description=data.get('description'),
                recurring=data.get('recurring', False),
                priority=data.get('priority', 1)
            )
            
            db.session.add(new_special_class)
            db.session.commit()
            
            return jsonify({'success': True, 'message': 'Special class created successfully', 'special_class': new_special_class.to_dict()}), 201
            
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

# ===== ELECTIVES MANAGEMENT =====

@api.route('/electives', methods=['GET', 'POST'])
@jwt_required()
def handle_electives():
    """Get all electives or create new elective"""
    try:
        if request.method == 'GET':
            semester_id = request.args.get('semester_id')
            batch_id = request.args.get('batch_id')
            is_active = request.args.get('is_active', 'true').lower() == 'true'
            
            query = Elective.query
            if semester_id:
                query = query.join(Subject).filter(Subject.semester_id == semester_id)
            if batch_id:
                query = query.filter_by(batch_id=batch_id)
            if is_active:
                query = query.filter_by(is_active=True)
            
            electives = query.all()
            return jsonify({'success': True, 'electives': [elective.to_dict() for elective in electives]})
        
        elif request.method == 'POST':
            data = request.get_json()
            
            new_elective = Elective(
                subject_id=data['subject_id'],
                batch_id=data['batch_id'],
                enrolled_students=data.get('enrolled_students', 0),
                min_enrollment=data.get('min_enrollment', 10),
                max_enrollment=data.get('max_enrollment', 60),
                is_active=data.get('is_active', True),
                registration_deadline=datetime.strptime(data['registration_deadline'], '%Y-%m-%d').date() if data.get('registration_deadline') else None,
                priority_level=data.get('priority_level', 1)
            )
            
            db.session.add(new_elective)
            db.session.commit()
            
            return jsonify({'success': True, 'message': 'Elective registration created successfully', 'elective': new_elective.to_dict()}), 201
            
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

# ===== TIMETABLE GENERATION (ADVANCED WITH LABS) =====

@api.route('/generate-advanced-timetable', methods=['POST'])
@jwt_required()
def generate_advanced_timetable():
    """Generate multiple optimized timetable options with lab support - PDF REQUIREMENT"""
    try:
        data = request.get_json()
        semester_id = data.get('semester_id')
        num_alternatives = data.get('num_alternatives', 3)
        
        if not semester_id:
            return jsonify({'success': False, 'message': 'Semester ID required'}), 400
        
        # Initialize the advanced optimizer with lab support
        optimizer = AdvancedTimetableOptimizer(semester_id)
        
        # Generate multiple solutions as per PDF requirement
        solutions = optimizer.generate_multiple_optimized_solutions(num_alternatives)
        
        timetable_options = []
        current_user_id = get_jwt_identity()
        
        for i, sol_data in enumerate(solutions):
            # Create timetable record
            timetable = Timetable(
                name=f"Advanced Timetable Option {i+1} - {datetime.now().strftime('%Y%m%d_%H%M')}",
                semester_id=semester_id,
                fitness_score=sol_data['fitness'],
                classroom_utilization=sol_data['metrics']['classroom_utilization'],
                lab_utilization=sol_data['metrics']['lab_utilization'],
                faculty_load_balance=sol_data['metrics']['faculty_load_balance'],
                conflict_count=sol_data['metrics']['total_conflicts'],
                total_classes_scheduled=sol_data['metrics']['total_classes_scheduled'],
                created_by=current_user_id,
                status='draft'
            )
            
            db.session.add(timetable)
            db.session.flush()  # Get the ID
            
            # Create schedule entries
            for entry in sol_data['schedule']:
                schedule_entry = ScheduleEntry(
                    timetable_id=timetable.id,
                    subject_id=entry['subject_id'],
                    faculty_id=entry['faculty_id'],
                    classroom_id=entry['venue_id'] if entry.get('venue_type') == 'classroom' else None,
                    laboratory_id=entry['venue_id'] if entry.get('venue_type') == 'laboratory' else None,
                    batch_id=entry['batch_id'],
                    day_of_week=convert_day_to_number(entry['day']),
                    start_time=datetime.strptime(entry['start_time'], '%H:%M').time(),
                    end_time=datetime.strptime(entry['end_time'], '%H:%M').time(),
                    is_fixed=entry.get('is_fixed', False),
                    shift=entry.get('shift', 'morning'),
                    class_type=entry.get('class_type', 'theory'),
                    requires_setup=entry.get('setup_time', 0) > 0,
                    setup_time_minutes=entry.get('setup_time', 0)
                )
                db.session.add(schedule_entry)
            
            # Create conflict records
            for conflict_data in sol_data['conflicts']:
                conflict = ScheduleConflict(
                    timetable_id=timetable.id,
                    conflict_type=conflict_data.get('type', 'unknown'),
                    severity='high',
                    description=json.dumps(conflict_data),
                    suggested_solution=json.dumps([]),  # Can be enhanced with actual suggestions
                    is_resolved=False,
                    auto_resolvable=conflict_data.get('type') in ['room_change', 'time_change']
                )
                db.session.add(conflict)
            
            timetable_options.append({
                'id': timetable.id,
                'name': timetable.name,
                'fitness_score': round(sol_data['fitness'], 2),
                'classroom_utilization': round(sol_data['metrics']['classroom_utilization'], 2),
                'lab_utilization': round(sol_data['metrics']['lab_utilization'], 2),
                'faculty_load_balance': round(sol_data['metrics']['faculty_load_balance'], 2),
                'conflict_count': sol_data['metrics']['total_conflicts'],
                'total_classes': sol_data['metrics']['total_classes_scheduled'],
                'theory_classes': sol_data['metrics']['theory_classes'],
                'lab_classes': sol_data['metrics']['lab_classes'],
                'status': timetable.status
            })
        
        db.session.commit()
        
        return jsonify({
            'success': True, 
            'message': f'{len(solutions)} advanced timetable options generated with lab support',
            'options': timetable_options,
            'generation_details': {
                'semester_id': semester_id,
                'total_solutions': len(solutions),
                'optimization_completed': True,
                'lab_support_enabled': True
            }
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

# ===== TIMETABLE MANAGEMENT =====

@api.route('/timetables', methods=['GET'])
@jwt_required()
def get_timetables():
    """Get all timetables with filtering options"""
    try:
        semester_id = request.args.get('semester_id')
        status = request.args.get('status')
        
        query = Timetable.query
        if semester_id:
            query = query.filter_by(semester_id=semester_id)
        if status:
            query = query.filter_by(status=status)
        
        timetables = query.order_by(Timetable.created_at.desc()).all()
        return jsonify({'success': True, 'timetables': [tt.to_dict() for tt in timetables]})
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@api.route('/timetables/<int:timetable_id>', methods=['GET', 'PUT', 'DELETE'])
@jwt_required()
def handle_timetable(timetable_id):
    """Get, update, or delete specific timetable"""
    try:
        timetable = Timetable.query.get_or_404(timetable_id)
        
        if request.method == 'GET':
            # Include schedule entries and conflicts
            schedule_entries = [entry.to_dict() for entry in timetable.schedule_entries]
            conflicts = [conflict.to_dict() for conflict in timetable.conflicts]
            
            result = timetable.to_dict()
            result['schedule_entries'] = schedule_entries
            result['conflicts'] = conflicts
            
            return jsonify({'success': True, 'timetable': result})
        
        elif request.method == 'PUT':
            data = request.get_json()
            
            timetable.name = data.get('name', timetable.name)
            timetable.status = data.get('status', timetable.status)
            timetable.review_comments = data.get('review_comments', timetable.review_comments)
            
            if data.get('status') == 'approved':
                timetable.approved_by = get_jwt_identity()
                timetable.approved_at = datetime.utcnow()
            
            db.session.commit()
            return jsonify({'success': True, 'message': 'Timetable updated successfully', 'timetable': timetable.to_dict()})
        
        elif request.method == 'DELETE':
            db.session.delete(timetable)
            db.session.commit()
            return jsonify({'success': True, 'message': 'Timetable deleted successfully'})
            
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

# ===== TIMETABLE REVIEW WORKFLOW (PDF REQUIREMENT) =====

@api.route('/timetable-review', methods=['POST'])
@jwt_required()
def create_timetable_review():
    """Create timetable review - PDF REQUIREMENT"""
    try:
        data = request.get_json()
        current_user_id = get_jwt_identity()
        
        timetable = Timetable.query.get_or_404(data['timetable_id'])
        
        review = TimetableReview(
            timetable_id=data['timetable_id'],
            reviewer_id=current_user_id,
            review_status=data.get('review_status', 'pending'),
            comments=data.get('comments'),
            priority_issues=json.dumps(data.get('priority_issues', [])),
            suggested_changes=json.dumps(data.get('suggested_changes', []))
        )
        
        db.session.add(review)
        
        # Update timetable status based on review
        if data.get('review_status') == 'approved':
            timetable.status = 'approved'
            timetable.approved_by = current_user_id
            timetable.approved_at = datetime.utcnow()
        elif data.get('review_status') == 'rejected':
            timetable.status = 'rejected'
        elif data.get('review_status') == 'changes_requested':
            timetable.status = 'under_review'
        
        timetable.review_comments = data.get('comments')
        
        db.session.commit()
        
        return jsonify({
            'success': True, 
            'message': f'Timetable review submitted with status: {data.get("review_status")}',
            'review': review.to_dict()
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

@api.route('/timetable-reviews/<int:timetable_id>', methods=['GET'])
@jwt_required()
def get_timetable_reviews(timetable_id):
    """Get all reviews for a specific timetable"""
    try:
        reviews = TimetableReview.query.filter_by(timetable_id=timetable_id).order_by(TimetableReview.reviewed_at.desc()).all()
        return jsonify({'success': True, 'reviews': [review.to_dict() for review in reviews]})
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

# ===== COMPREHENSIVE REPORTING AND ANALYTICS =====

@api.route('/comprehensive-utilization-report/<int:semester_id>', methods=['GET'])
@jwt_required()
def get_comprehensive_utilization_report(semester_id):
    """Get comprehensive utilization report with lab analytics - PDF REQUIREMENT"""
    try:
        approved_timetables = Timetable.query.filter_by(semester_id=semester_id, status='approved').all()
        
        if not approved_timetables:
            return jsonify({'success': False, 'message': 'No approved timetables found for this semester'}), 404
        
        timetable = approved_timetables[0]  # Use the most recent approved timetable
        schedule_entries = ScheduleEntry.query.filter_by(timetable_id=timetable.id).all()
        
        # Classroom utilization analysis
        classroom_usage = {}
        classroom_hours = {}
        
        # Laboratory utilization analysis
        lab_usage = {}
        lab_hours = {}
        
        # Faculty workload analysis
        faculty_workload = {}
        
        for entry in schedule_entries:
            # Calculate duration
            start_time = datetime.combine(datetime.today(), entry.start_time)
            end_time = datetime.combine(datetime.today(), entry.end_time)
            duration_hours = (end_time - start_time).seconds / 3600
            
            # Classroom statistics
            if entry.classroom_id:
                room_id = entry.classroom_id
                if room_id not in classroom_usage:
                    classroom_usage[room_id] = {'name': entry.classroom.name, 'sessions': 0, 'hours': 0}
                classroom_usage[room_id]['sessions'] += 1
                classroom_usage[room_id]['hours'] += duration_hours
            
            # Laboratory statistics
            if entry.laboratory_id:
                lab_id = entry.laboratory_id
                if lab_id not in lab_usage:
                    lab_usage[lab_id] = {
                        'name': entry.laboratory.name, 
                        'type': entry.laboratory.lab_type,
                        'sessions': 0, 
                        'hours': 0,
                        'avg_group_size': 0
                    }
                lab_usage[lab_id]['sessions'] += 1
                lab_usage[lab_id]['hours'] += duration_hours
            
            # Faculty workload
            faculty_id = entry.faculty_id
            if faculty_id not in faculty_workload:
                faculty_workload[faculty_id] = {
                    'name': entry.faculty.name,
                    'theory_hours': 0,
                    'lab_hours': 0,
                    'total_hours': 0,
                    'daily_hours': {},
                    'classes_per_day': {}
                }
            
            day_name = convert_day_to_name(entry.day_of_week)
            if day_name not in faculty_workload[faculty_id]['daily_hours']:
                faculty_workload[faculty_id]['daily_hours'][day_name] = 0
                faculty_workload[faculty_id]['classes_per_day'][day_name] = 0
            
            faculty_workload[faculty_id]['daily_hours'][day_name] += duration_hours
            faculty_workload[faculty_id]['classes_per_day'][day_name] += 1
            faculty_workload[faculty_id]['total_hours'] += duration_hours
            
            if entry.class_type == 'lab':
                faculty_workload[faculty_id]['lab_hours'] += duration_hours
            else:
                faculty_workload[faculty_id]['theory_hours'] += duration_hours
        
        # Calculate utilization percentages
        total_classrooms = Classroom.query.filter_by(is_available=True).count()
        total_labs = Laboratory.query.filter_by(is_available=True).count()
        total_working_slots = len(Config.WORKING_DAYS) * len(Config.TIME_SLOTS)
        
        classroom_utilization_rate = (len(classroom_usage) / total_classrooms * 100) if total_classrooms > 0 else 0
        lab_utilization_rate = (len(lab_usage) / total_labs * 100) if total_labs > 0 else 0
        
        # Generate detailed report
        report = {
            'semester_id': semester_id,
            'timetable_id': timetable.id,
            'generation_date': datetime.now().isoformat(),
            'summary': {
                'total_classes_scheduled': len(schedule_entries),
                'theory_classes': len([e for e in schedule_entries if e.class_type == 'theory']),
                'lab_classes': len([e for e in schedule_entries if e.class_type == 'lab']),
                'classroom_utilization_rate': round(classroom_utilization_rate, 2),
                'lab_utilization_rate': round(lab_utilization_rate, 2),
                'total_faculty_involved': len(faculty_workload)
            },
            'classroom_utilization': {
                'total_available': total_classrooms,
                'utilized': len(classroom_usage),
                'utilization_rate': round(classroom_utilization_rate, 2),
                'details': list(classroom_usage.values())
            },
            'laboratory_utilization': {
                'total_available': total_labs,
                'utilized': len(lab_usage),
                'utilization_rate': round(lab_utilization_rate, 2),
                'details': list(lab_usage.values()),
                'by_lab_type': {}
            },
            'faculty_workload': {
                'total_faculty': len(faculty_workload),
                'details': list(faculty_workload.values()),
                'workload_distribution': {
                    'underloaded': len([f for f in faculty_workload.values() if f['total_hours'] < 15]),
                    'optimal': len([f for f in faculty_workload.values() if 15 <= f['total_hours'] <= 25]),
                    'overloaded': len([f for f in faculty_workload.values() if f['total_hours'] > 25])
                }
            },
            'conflicts': {
                'total_conflicts': timetable.conflict_count,
                'resolved_conflicts': len([c for c in timetable.conflicts if c.is_resolved]),
                'pending_conflicts': len([c for c in timetable.conflicts if not c.is_resolved])
            },
            'recommendations': []
        }
        
        # Add lab type breakdown
        for lab_id, usage in lab_usage.items():
            lab_type = usage['type']
            if lab_type not in report['laboratory_utilization']['by_lab_type']:
                report['laboratory_utilization']['by_lab_type'][lab_type] = {
                    'count': 0,
                    'total_sessions': 0,
                    'total_hours': 0
                }
            report['laboratory_utilization']['by_lab_type'][lab_type]['count'] += 1
            report['laboratory_utilization']['by_lab_type'][lab_type]['total_sessions'] += usage['sessions']
            report['laboratory_utilization']['by_lab_type'][lab_type]['total_hours'] += usage['hours']
        
        # Generate recommendations
        if classroom_utilization_rate < 60:
            report['recommendations'].append("Classroom utilization is below optimal. Consider consolidating classes or reducing classroom inventory.")
        
        if lab_utilization_rate < 50:
            report['recommendations'].append("Laboratory utilization is below optimal. Consider scheduling additional lab sessions or practical exercises.")
        
        overloaded_faculty = [f for f in faculty_workload.values() if f['total_hours'] > 30]
        if overloaded_faculty:
            report['recommendations'].append(f"{len(overloaded_faculty)} faculty members are overloaded. Consider redistributing workload or hiring additional faculty.")
        
        return jsonify({'success': True, 'report': report})
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

# ===== CONFLICT MANAGEMENT =====

@api.route('/conflicts/<int:timetable_id>', methods=['GET'])
@jwt_required()
def get_timetable_conflicts(timetable_id):
    """Get all conflicts for a specific timetable"""
    try:
        conflicts = ScheduleConflict.query.filter_by(timetable_id=timetable_id).order_by(ScheduleConflict.severity.desc()).all()
        
        conflict_summary = {
            'total': len(conflicts),
            'by_type': {},
            'by_severity': {'critical': 0, 'high': 0, 'medium': 0, 'low': 0},
            'resolved': 0,
            'auto_resolvable': 0
        }
        
        for conflict in conflicts:
            # Count by type
            if conflict.conflict_type not in conflict_summary['by_type']:
                conflict_summary['by_type'][conflict.conflict_type] = 0
            conflict_summary['by_type'][conflict.conflict_type] += 1
            
            # Count by severity
            conflict_summary['by_severity'][conflict.severity] += 1
            
            # Count resolved
            if conflict.is_resolved:
                conflict_summary['resolved'] += 1
            
            # Count auto-resolvable
            if conflict.auto_resolvable:
                conflict_summary['auto_resolvable'] += 1
        
        return jsonify({
            'success': True, 
            'conflicts': [conflict.to_dict() for conflict in conflicts],
            'summary': conflict_summary
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@api.route('/conflicts/<int:conflict_id>/resolve', methods=['PUT'])
@jwt_required()
def resolve_conflict(conflict_id):
    """Mark conflict as resolved"""
    try:
        conflict = ScheduleConflict.query.get_or_404(conflict_id)
        data = request.get_json()
        
        conflict.is_resolved = True
        conflict.suggested_solution = json.dumps(data.get('solution', []))
        
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Conflict marked as resolved', 'conflict': conflict.to_dict()})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

# ===== DASHBOARD AND ANALYTICS =====

@api.route('/dashboard-stats', methods=['GET'])
@jwt_required()
def get_dashboard_stats():
    """Get dashboard statistics"""
    try:
        stats = {
            'departments': Department.query.count(),
            'faculty': Faculty.query.count(),
            'subjects': Subject.query.count(),
            'batches': Batch.query.count(),
            'classrooms': Classroom.query.filter_by(is_available=True).count(),
            'laboratories': Laboratory.query.filter_by(is_available=True).count(),
            'timetables': {
                'total': Timetable.query.count(),
                'draft': Timetable.query.filter_by(status='draft').count(),
                'approved': Timetable.query.filter_by(status='approved').count(),
                'under_review': Timetable.query.filter_by(status='under_review').count()
            },
            'lab_statistics': {
                'total_labs': Laboratory.query.count(),
                'by_type': {}
            },
            'recent_activities': []
        }
        
        # Lab statistics by type
        lab_types = db.session.query(Laboratory.lab_type, db.func.count(Laboratory.id)).group_by(Laboratory.lab_type).all()
        for lab_type, count in lab_types:
            stats['lab_statistics']['by_type'][lab_type] = count
        
        # Recent activities (last 10 timetables)
        recent_timetables = Timetable.query.order_by(Timetable.created_at.desc()).limit(10).all()
        for tt in recent_timetables:
            stats['recent_activities'].append({
                'type': 'timetable_created',
                'description': f'Timetable "{tt.name}" created',
                'timestamp': tt.created_at.isoformat() if tt.created_at else None,
                'status': tt.status
            })
        
        return jsonify({'success': True, 'stats': stats})
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

# ===== HEALTH CHECK =====

@api.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'version': '2.0.0',
        'features': {
            'labs_support': True,
            'pdf_constraints': True,
            'multi_shift': True,
            'conflict_resolution': True,
            'advanced_optimization': True
        }
    })

# Error handlers
@api.errorhandler(404)
def not_found(error):
    return jsonify({'success': False, 'message': 'Resource not found'}), 404

@api.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return jsonify({'success': False, 'message': 'Internal server error'}), 500