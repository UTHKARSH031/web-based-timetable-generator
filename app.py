# app.py - Main Flask Application for Smart Timetable Scheduler (Flask 2.2+ Compatible)
# SIH 2025 Project (ID: 25028) - Complete Implementation

from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager
from flask_cors import CORS
import os
from datetime import datetime

# Initialize extensions
db = SQLAlchemy()
jwt = JWTManager()

def create_app(config_name='development'):
    """Application factory pattern for creating Flask app"""
    app = Flask(__name__)
    
    # Basic configuration (inline to avoid import issues)
    if config_name == 'production':
        app.config.update({
            'SECRET_KEY': os.environ.get('SECRET_KEY', 'smart-timetable-scheduler-secret-key-2025'),
            'SQLALCHEMY_DATABASE_URI': os.environ.get('DATABASE_URL', 'sqlite:///production_database.db'),
            'SQLALCHEMY_TRACK_MODIFICATIONS': False,
            'JWT_SECRET_KEY': os.environ.get('JWT_SECRET_KEY', 'jwt-secret-string-2025'),
            'JWT_ACCESS_TOKEN_EXPIRES': False,
        })
    else:  # development
        app.config.update({
            'SECRET_KEY': 'smart-timetable-scheduler-secret-key-2025',
            'SQLALCHEMY_DATABASE_URI': 'sqlite:///database.db',
            'SQLALCHEMY_TRACK_MODIFICATIONS': False,
            'JWT_SECRET_KEY': 'jwt-secret-string-2025',
            'JWT_ACCESS_TOKEN_EXPIRES': False,
            'DEBUG': True
        })
    
    # Initialize extensions with app
    db.init_app(app)
    jwt.init_app(app)
    
    # CORS configuration
    CORS(app, resources={
        r"/api/*": {
            "origins": ["http://localhost:3000", "http://127.0.0.1:3000"],
            "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            "allow_headers": ["Content-Type", "Authorization"]
        }
    })
    
    # Import models after db initialization to avoid circular imports
    try:
        from models import User, Department, Semester
        print("✅ Models imported successfully")
    except ImportError as e:
        print(f"❌ Error importing models: {e}")
        print("⚠️  Creating basic User model...")
        
        # Basic User model if models.py doesn't exist
        class User(db.Model):
            id = db.Column(db.Integer, primary_key=True)
            username = db.Column(db.String(80), unique=True, nullable=False)
            email = db.Column(db.String(120), unique=True, nullable=False)
            password_hash = db.Column(db.String(200), nullable=False)
            role = db.Column(db.String(20), default='admin')
            
            def set_password(self, password):
                from werkzeug.security import generate_password_hash
                self.password_hash = generate_password_hash(password)
            
            def check_password(self, password):
                from werkzeug.security import check_password_hash
                return check_password_hash(self.password_hash, password)
    
    # Import and register routes
    try:
        from routes import api
        app.register_blueprint(api, url_prefix='/api')
        print("✅ Routes imported and registered successfully")
    except ImportError as e:
        print(f"❌ Error importing routes: {e}")
        print("⚠️  Running without API routes")
    
    # JWT Configuration
    @jwt.expired_token_loader
    def expired_token_callback(jwt_header, jwt_payload):
        return jsonify({'success': False, 'message': 'Token has expired'}), 401
    
    @jwt.invalid_token_loader
    def invalid_token_callback(error):
        return jsonify({'success': False, 'message': 'Invalid token'}), 401
    
    @jwt.unauthorized_loader
    def missing_token_callback(error):
        return jsonify({'success': False, 'message': 'Authorization token required'}), 401
    
    # Create database tables and seed data - FIXED FOR FLASK 2.2+
    def initialize_database():
        """Create database tables and seed initial data"""
        try:
            with app.app_context():
                db.create_all()
                print("✅ Database tables created successfully")
                
                # Seed default admin user if no users exist
                if User.query.count() == 0:
                    print("Creating default admin user...")
                    default_admin = User(
                        username='admin',
                        email='admin@timetable-scheduler.edu',
                        role='admin'
                    )
                    default_admin.set_password('admin123')
                    db.session.add(default_admin)
                    
                    # Create default data only if models exist
                    try:
                        # Create default department
                        default_dept = Department(
                            name='Computer Science and Engineering',
                            code='CSE',
                            shift_preference='both',
                            max_classes_per_day=8
                        )
                        db.session.add(default_dept)
                        
                        # Create default semester
                        default_semester = Semester(
                            name='Fall 2025',
                            year=2025,
                            is_active=True,
                            program_type='UG'
                        )
                        db.session.add(default_semester)
                        print("✅ Default department and semester created")
                    except Exception as e:
                        print(f"⚠️  Could not create default department/semester: {e}")
                    
                    db.session.commit()
                    print("✅ Default admin user created successfully")
        except Exception as e:
            print(f"❌ Error creating database tables: {e}")
    
    # Initialize database when app starts
    initialize_database()
    
    # Error handlers
    @app.errorhandler(404)
    def not_found(error):
        return jsonify({'success': False, 'message': 'Endpoint not found'}), 404
    
    @app.errorhandler(500)
    def internal_error(error):
        db.session.rollback()
        return jsonify({'success': False, 'message': 'Internal server error'}), 500
    
    @app.errorhandler(400)
    def bad_request(error):
        return jsonify({'success': False, 'message': 'Bad request'}), 400
    
    # Health check endpoint
    @app.route('/health')
    def health_check():
        """Health check endpoint"""
        return jsonify({
            'status': 'healthy',
            'timestamp': datetime.now().isoformat(),
            'version': '2.0.0',
            'app_name': 'Smart Timetable Scheduler',
            'features': {
                'labs_support': True,
                'pdf_constraints': True,
                'multi_shift': True,
                'conflict_resolution': True,
                'advanced_optimization': True,
                'review_workflow': True
            }
        })
    
    # Root endpoint
    @app.route('/')
    def index():
        """Root endpoint with API information"""
        return jsonify({
            'message': 'Smart Timetable Scheduler API - SIH 2025',
            'version': '2.0.0',
            'api_base': '/api',
            'health_check': '/health',
            'documentation': 'Complete implementation with lab support and PDF constraints',
            'endpoints': {
                'authentication': ['/api/login', '/api/register'],
                'departments': '/api/departments',
                'faculty': '/api/faculty',
                'subjects': '/api/subjects',
                'batches': '/api/batches',
                'classrooms': '/api/classrooms',
                'laboratories': '/api/laboratories',
                'lab_sessions': '/api/lab-sessions',
                'timetables': '/api/timetables',
                'generate': '/api/generate-advanced-timetable',
                'review': '/api/timetable-review'
            }
        })
    
    # Database initialization command
    @app.cli.command('init-db')
    def init_db_command():
        """Initialize the database with tables and seed data"""
        try:
            db.create_all()
            print("✅ Database tables created")
            
            # Check if admin user exists
            if not User.query.filter_by(username='admin').first():
                admin = User(
                    username='admin',
                    email='admin@timetable-scheduler.edu',
                    role='admin'
                )
                admin.set_password('admin123')
                db.session.add(admin)
                
                print("✅ Default admin user created:")
                print("   Username: admin")
                print("   Password: admin123")
            
            try:
                # Check if default department exists
                if not Department.query.filter_by(code='CSE').first():
                    dept = Department(
                        name='Computer Science and Engineering',
                        code='CSE',
                        shift_preference='both',
                        max_classes_per_day=8
                    )
                    db.session.add(dept)
                    print("✅ Default department 'CSE' created")
                
                # Check if default semester exists
                if not Semester.query.filter_by(name='Fall 2025').first():
                    semester = Semester(
                        name='Fall 2025',
                        year=2025,
                        is_active=True,
                        program_type='UG'
                    )
                    db.session.add(semester)
                    print("✅ Default semester 'Fall 2025' created")
            except Exception as e:
                print(f"⚠️  Could not create default data: {e}")
            
            db.session.commit()
            print("✅ Database initialization completed!")
        except Exception as e:
            print(f"❌ Error during database initialization: {e}")
    
    # Database reset command
    @app.cli.command('reset-db')
    def reset_db_command():
        """Reset the database (WARNING: This will delete all data)"""
        try:
            db.drop_all()
            db.create_all()
            print("✅ Database reset completed!")
        except Exception as e:
            print(f"❌ Error during database reset: {e}")
    
    return app

# Application factory functions
def create_production_app():
    """Create production app instance"""
    return create_app('production')

def create_development_app():
    """Create development app instance"""
    return create_app('development')

# Main application instance
app = create_app(os.environ.get('FLASK_ENV', 'development'))

if __name__ == '__main__':
    # Development server
    port = int(os.environ.get('PORT', 5500))
    debug = os.environ.get('FLASK_ENV') == 'development'
    
    print("=" * 60)
    print("🎓 Smart Timetable Scheduler - SIH 2025")
    print("=" * 60)
    print(f"🌐 Server starting on: http://127.0.0.1:{port}")
    print(f"🔧 Environment: {os.environ.get('FLASK_ENV', 'development')}")
    print(f"🐛 Debug mode: {debug}")
    print(f"📊 API Base URL: http://127.0.0.1:{port}/api")
    print(f"❤️  Health Check: http://127.0.0.1:{port}/health")
    print("=" * 60)
    print("🚀 Features Enabled:")
    print("   ✅ Laboratory Management System")
    print("   ✅ Multi-Shift Scheduling")
    print("   ✅ PDF Constraint Compliance")
    print("   ✅ Advanced Optimization Engine")
    print("   ✅ Review & Approval Workflow")
    print("   ✅ Conflict Detection & Resolution")
    print("=" * 60)
    print()
    print("📝 Default Login Credentials:")
    print("   Username: admin")
    print("   Password: admin123")
    print()
    print("🛠️  To initialize the database, run:")
    print("   flask init-db")
    print()
    print("Press Ctrl+C to stop the server")
    print("=" * 60)
    
    try:
        app.run(
            host='0.0.0.0',
            port=port,
            debug=debug,
            threaded=True
        )
    except Exception as e:
        print(f"❌ Error starting server: {e}")
        print("💡 Try running: pip install flask flask-sqlalchemy flask-jwt-extended flask-cors")
