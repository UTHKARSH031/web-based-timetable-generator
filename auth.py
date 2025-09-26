# auth.py - Authentication System for Smart Timetable Scheduler
# SIH 2025 Project (ID: 25028) - Complete Implementation

from functools import wraps
from flask import request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity, create_access_token
from models import User, db
from datetime import datetime, timedelta
import secrets
import hashlib

class AuthenticationManager:
    """Centralized authentication management"""
    
    @staticmethod
    def generate_access_token(user_id, expires_delta=None):
        """Generate JWT access token for user"""
        if expires_delta is None:
            expires_delta = timedelta(hours=24)  # Default 24 hour expiry
        
        return create_access_token(
            identity=user_id, 
            expires_delta=expires_delta
        )
    
    @staticmethod
    def authenticate_user(username, password):
        """Authenticate user with username/password"""
        user = User.query.filter_by(username=username).first()
        
        if user and user.check_password(password):
            return user
        return None
    
    @staticmethod
    def authenticate_by_email(email, password):
        """Authenticate user with email/password"""
        user = User.query.filter_by(email=email).first()
        
        if user and user.check_password(password):
            return user
        return None
    
    @staticmethod
    def get_current_user():
        """Get current authenticated user"""
        try:
            current_user_id = get_jwt_identity()
            if current_user_id:
                return User.query.get(current_user_id)
        except:
            pass
        return None
    
    @staticmethod
    def create_user(username, email, password, role='admin', department_id=None):
        """Create new user account"""
        # Check if username already exists
        if User.query.filter_by(username=username).first():
            raise ValueError("Username already exists")
        
        # Check if email already exists
        if User.query.filter_by(email=email).first():
            raise ValueError("Email already exists")
        
        # Create new user
        new_user = User(
            username=username,
            email=email,
            role=role,
            department_id=department_id
        )
        new_user.set_password(password)
        
        db.session.add(new_user)
        db.session.commit()
        
        return new_user
    
    @staticmethod
    def change_password(user_id, old_password, new_password):
        """Change user password"""
        user = User.query.get(user_id)
        if not user:
            raise ValueError("User not found")
        
        if not user.check_password(old_password):
            raise ValueError("Current password is incorrect")
        
        user.set_password(new_password)
        db.session.commit()
        
        return True
    
    @staticmethod
    def reset_password(username_or_email, new_password):
        """Reset user password (admin only)"""
        user = (User.query.filter_by(username=username_or_email).first() or 
                User.query.filter_by(email=username_or_email).first())
        
        if not user:
            raise ValueError("User not found")
        
        user.set_password(new_password)
        db.session.commit()
        
        return True

class PermissionManager:
    """Role-based permission management"""
    
    # Define role hierarchy (higher number = more permissions)
    ROLE_HIERARCHY = {
        'faculty': 1,
        'reviewer': 2,
        'admin': 3
    }
    
    # Define permissions for each role
    PERMISSIONS = {
        'faculty': [
            'view_own_schedule',
            'view_own_subjects',
            'update_availability',
            'request_leave',
            'view_lab_sessions'
        ],
        'reviewer': [
            'view_own_schedule',
            'view_own_subjects',
            'update_availability',
            'request_leave',
            'view_lab_sessions',
            'review_timetables',
            'approve_schedules',
            'view_all_schedules',
            'generate_reports'
        ],
        'admin': [
            'view_own_schedule',
            'view_own_subjects',
            'update_availability',
            'request_leave',
            'view_lab_sessions',
            'review_timetables',
            'approve_schedules',
            'view_all_schedules',
            'generate_reports',
            'manage_users',
            'manage_departments',
            'manage_faculty',
            'manage_subjects',
            'manage_batches',
            'manage_classrooms',
            'manage_laboratories',
            'generate_timetables',
            'manage_system_settings',
            'delete_data',
            'export_data',
            'view_analytics'
        ]
    }
    
    @staticmethod
    def has_permission(user, permission):
        """Check if user has specific permission"""
        if not user or not user.role:
            return False
        
        user_permissions = PermissionManager.PERMISSIONS.get(user.role, [])
        return permission in user_permissions
    
    @staticmethod
    def has_role_or_higher(user, required_role):
        """Check if user has required role or higher"""
        if not user or not user.role:
            return False
        
        user_level = PermissionManager.ROLE_HIERARCHY.get(user.role, 0)
        required_level = PermissionManager.ROLE_HIERARCHY.get(required_role, 999)
        
        return user_level >= required_level
    
    @staticmethod
    def get_user_permissions(user):
        """Get all permissions for user"""
        if not user or not user.role:
            return []
        
        return PermissionManager.PERMISSIONS.get(user.role, [])
    
    @staticmethod
    def can_access_resource(user, resource_type, resource_id=None):
        """Check if user can access specific resource"""
        if not user:
            return False
        
        # Admin can access everything
        if user.role == 'admin':
            return True
        
        # Department-based access control
        if resource_type in ['faculty', 'subjects', 'batches', 'classrooms', 'laboratories']:
            if user.department_id:
                # Users can access resources from their department
                if resource_type == 'faculty':
                    from models import Faculty
                    resource = Faculty.query.get(resource_id) if resource_id else None
                elif resource_type == 'subjects':
                    from models import Subject
                    resource = Subject.query.get(resource_id) if resource_id else None
                # Add more resource type checks as needed
                
                if resource and hasattr(resource, 'department_id'):
                    return resource.department_id == user.department_id
        
        # Faculty can only access their own data
        if user.role == 'faculty':
            if resource_type == 'faculty' and resource_id:
                from models import Faculty
                faculty = Faculty.query.filter_by(email=user.email).first()
                return faculty and faculty.id == resource_id
        
        return False

# Decorators for authentication and authorization
def token_required(f):
    """Decorator to require valid JWT token"""
    @wraps(f)
    @jwt_required()
    def decorated(*args, **kwargs):
        return f(*args, **kwargs)
    return decorated

def admin_required(f):
    """Decorator to require admin role"""
    @wraps(f)
    @jwt_required()
    def decorated(*args, **kwargs):
        current_user = AuthenticationManager.get_current_user()
        if not current_user or current_user.role != 'admin':
            return jsonify({'success': False, 'message': 'Admin privileges required'}), 403
        return f(*args, **kwargs)
    return decorated

def reviewer_or_admin_required(f):
    """Decorator to require reviewer or admin role"""
    @wraps(f)
    @jwt_required()
    def decorated(*args, **kwargs):
        current_user = AuthenticationManager.get_current_user()
        if not current_user or not PermissionManager.has_role_or_higher(current_user, 'reviewer'):
            return jsonify({'success': False, 'message': 'Reviewer or admin privileges required'}), 403
        return f(*args, **kwargs)
    return decorated

def permission_required(permission):
    """Decorator to require specific permission"""
    def decorator(f):
        @wraps(f)
        @jwt_required()
        def decorated(*args, **kwargs):
            current_user = AuthenticationManager.get_current_user()
            if not current_user or not PermissionManager.has_permission(current_user, permission):
                return jsonify({'success': False, 'message': f'Permission required: {permission}'}), 403
            return f(*args, **kwargs)
        return decorated
    return decorator

def department_access_required(f):
    """Decorator to require department-based access"""
    @wraps(f)
    @jwt_required()
    def decorated(*args, **kwargs):
        current_user = AuthenticationManager.get_current_user()
        if not current_user:
            return jsonify({'success': False, 'message': 'Authentication required'}), 401
        
        # Admin has access to all departments
        if current_user.role == 'admin':
            return f(*args, **kwargs)
        
        # Check if user has department association
        if not current_user.department_id:
            return jsonify({'success': False, 'message': 'Department association required'}), 403
        
        return f(*args, **kwargs)
    return decorated

class SessionManager:
    """Manage user sessions and security"""
    
    @staticmethod
    def generate_csrf_token():
        """Generate CSRF token for form protection"""
        return secrets.token_urlsafe(32)
    
    @staticmethod
    def validate_csrf_token(token, expected_token):
        """Validate CSRF token"""
        return secrets.compare_digest(token, expected_token)
    
    @staticmethod
    def log_user_activity(user_id, activity_type, details=None):
        """Log user activity for security monitoring"""
        # This could be extended to store in database or external logging service
        current_app.logger.info(
            f"User {user_id} performed {activity_type}: {details or 'No details'}"
        )
    
    @staticmethod
    def check_rate_limit(user_id, action_type, limit_per_minute=60):
        """Basic rate limiting check"""
        # This is a simplified version - in production, use Redis or similar
        # For now, just return True (no rate limiting)
        return True
    
    @staticmethod
    def generate_api_key(user_id):
        """Generate API key for programmatic access"""
        # Combine user ID with timestamp and random data
        data = f"{user_id}:{datetime.now().isoformat()}:{secrets.token_urlsafe(16)}"
        return hashlib.sha256(data.encode()).hexdigest()
    
    @staticmethod
    def validate_api_key(api_key):
        """Validate API key (simplified version)"""
        # In production, store API keys in database with expiry
        # For now, just return None
        return None

class SecurityUtils:
    """Security-related utility functions"""
    
    @staticmethod
    def sanitize_input(data):
        """Basic input sanitization"""
        if isinstance(data, dict):
            return {key: SecurityUtils.sanitize_input(value) for key, value in data.items()}
        elif isinstance(data, list):
            return [SecurityUtils.sanitize_input(item) for item in data]
        elif isinstance(data, str):
            # Basic XSS prevention
            return data.replace('<', '&lt;').replace('>', '&gt;').replace('"', '&quot;')
        return data
    
    @staticmethod
    def validate_password_strength(password):
        """Validate password strength"""
        if len(password) < 8:
            return False, "Password must be at least 8 characters long"
        
        has_upper = any(c.isupper() for c in password)
        has_lower = any(c.islower() for c in password)
        has_digit = any(c.isdigit() for c in password)
        
        if not (has_upper and has_lower and has_digit):
            return False, "Password must contain uppercase, lowercase, and digit characters"
        
        return True, "Password meets requirements"
    
    @staticmethod
    def generate_secure_password(length=12):
        """Generate secure random password"""
        import string
        characters = string.ascii_letters + string.digits + "!@#$%^&*"
        return ''.join(secrets.choice(characters) for _ in range(length))
    
    @staticmethod
    def hash_sensitive_data(data):
        """Hash sensitive data for storage"""
        return hashlib.sha256(data.encode()).hexdigest()

# Authentication middleware
class AuthMiddleware:
    """Middleware for handling authentication across the application"""
    
    def __init__(self, app=None):
        self.app = app
        if app:
            self.init_app(app)
    
    def init_app(self, app):
        """Initialize authentication middleware"""
        app.before_request(self.before_request)
        app.after_request(self.after_request)
    
    def before_request(self):
        """Process request before route handler"""
        # Skip auth for health check and public endpoints
        if request.endpoint in ['health_check', 'index']:
            return
        
        # Skip auth for OPTIONS requests (CORS preflight)
        if request.method == 'OPTIONS':
            return
        
        # Add security headers
        request.start_time = datetime.now()
    
    def after_request(self, response):
        """Process response after route handler"""
        # Add security headers
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['X-XSS-Protection'] = '1; mode=block'
        
        # Log request if needed
        if hasattr(request, 'start_time'):
            duration = datetime.now() - request.start_time
            current_app.logger.info(
                f"{request.method} {request.path} - {response.status_code} - "
                f"{duration.total_seconds():.3f}s"
            )
        
        return response

# Error handlers for authentication
class AuthErrorHandlers:
    """Error handlers for authentication-related errors"""
    
    @staticmethod
    def expired_token_error():
        return jsonify({
            'success': False,
            'message': 'Token has expired',
            'error_code': 'TOKEN_EXPIRED'
        }), 401
    
    @staticmethod
    def invalid_token_error():
        return jsonify({
            'success': False,
            'message': 'Invalid token',
            'error_code': 'INVALID_TOKEN'
        }), 401
    
    @staticmethod
    def missing_token_error():
        return jsonify({
            'success': False,
            'message': 'Authorization token required',
            'error_code': 'MISSING_TOKEN'
        }), 401
    
    @staticmethod
    def insufficient_permissions_error():
        return jsonify({
            'success': False,
            'message': 'Insufficient permissions',
            'error_code': 'INSUFFICIENT_PERMISSIONS'
        }), 403
    
    @staticmethod
    def account_disabled_error():
        return jsonify({
            'success': False,
            'message': 'Account is disabled',
            'error_code': 'ACCOUNT_DISABLED'
        }), 403

# Initialize authentication system
def init_auth(app):
    """Initialize authentication system with Flask app"""
    # Set up JWT configuration
    app.config.setdefault('JWT_ACCESS_TOKEN_EXPIRES', timedelta(hours=24))
    app.config.setdefault('JWT_ALGORITHM', 'HS256')
    
    # Initialize middleware
    auth_middleware = AuthMiddleware(app)
    
    return auth_middleware
