# config.py - Configuration file for Smart Timetable Scheduler


import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Config:
    """Base configuration class for the Smart Timetable Scheduler"""
    
    # Flask Configuration
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'smart-timetable-scheduler-secret-key-2025'
    
    # Database Configuration
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///timetable_scheduler.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ECHO = False  # Set to True for SQL debugging
    
    # JWT Configuration
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY') or 'jwt-secret-key-for-sih-2025'
    JWT_ACCESS_TOKEN_EXPIRES = False  # Tokens don't expire
    JWT_ALGORITHM = 'HS256'
    
    # Application Settings
    DEBUG = os.environ.get('DEBUG', 'False').lower() == 'true'
    TESTING = False
    
    # Genetic Algorithm Parameters
    GA_POPULATION_SIZE = int(os.environ.get('GA_POPULATION_SIZE', 50))
    GA_GENERATIONS = int(os.environ.get('GA_GENERATIONS', 100))
    GA_MUTATION_RATE = float(os.environ.get('GA_MUTATION_RATE', 0.1))
    GA_CROSSOVER_RATE = float(os.environ.get('GA_CROSSOVER_RATE', 0.8))
    GA_TOURNAMENT_SIZE = int(os.environ.get('GA_TOURNAMENT_SIZE', 3))
    GA_ELITE_SIZE = int(os.environ.get('GA_ELITE_SIZE', 5))
    
    # Time Slot Configuration (Based on PDF requirements)
    WORKING_DAYS = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']
    
    # Standard time slots (can be customized per institution)
    TIME_SLOTS = [
        ('09:00', '10:00'),  # Slot 1
        ('10:00', '11:00'),  # Slot 2
        ('11:00', '12:00'),  # Slot 3
        ('12:00', '13:00'),  # Slot 4
        ('13:00', '14:00'),  # Lunch break (optional)
        ('14:00', '15:00'),  # Slot 5
        ('15:00', '16:00'),  # Slot 6
        ('16:00', '17:00'),  # Slot 7
        ('17:00', '18:00')   # Slot 8
    ]
    
    # Extended time slots for laboratories (2-3 hour sessions)
    LAB_TIME_SLOTS = [
        ('09:00', '12:00'),  # Morning lab session (3 hours)
        ('10:00', '12:00'),  # Morning lab session (2 hours)
        ('14:00', '17:00'),  # Afternoon lab session (3 hours)
        ('15:00', '17:00'),  # Afternoon lab session (2 hours)
        ('09:00', '11:00'),  # Short morning lab (2 hours)
        ('14:00', '16:00'),  # Short afternoon lab (2 hours)
    ]
    
    # Scheduling Constraints (From PDF requirements)
    MAX_CLASSES_PER_DAY = int(os.environ.get('MAX_CLASSES_PER_DAY', 8))
    MAX_CONTINUOUS_CLASSES = int(os.environ.get('MAX_CONTINUOUS_CLASSES', 3))
    MIN_BREAK_BETWEEN_CLASSES = int(os.environ.get('MIN_BREAK_BETWEEN_CLASSES', 0))  # minutes
    
    # Faculty Constraints (From PDF requirements)
    DEFAULT_MAX_FACULTY_HOURS_PER_DAY = int(os.environ.get('DEFAULT_MAX_FACULTY_HOURS_PER_DAY', 6))
    DEFAULT_MAX_FACULTY_HOURS_PER_WEEK = int(os.environ.get('DEFAULT_MAX_FACULTY_HOURS_PER_WEEK', 30))
    DEFAULT_FACULTY_LEAVES_PER_MONTH = float(os.environ.get('DEFAULT_FACULTY_LEAVES_PER_MONTH', 2.0))
    
    # Classroom and Laboratory Constraints
    MIN_CLASSROOM_UTILIZATION = float(os.environ.get('MIN_CLASSROOM_UTILIZATION', 0.6))  # 60%
    MAX_CLASSROOM_UTILIZATION = float(os.environ.get('MAX_CLASSROOM_UTILIZATION', 0.85)) # 85%
    MIN_LAB_UTILIZATION = float(os.environ.get('MIN_LAB_UTILIZATION', 0.5))  # 50%
    MAX_LAB_UTILIZATION = float(os.environ.get('MAX_LAB_UTILIZATION', 0.75))  # 75%
    
    # Laboratory-specific settings
    DEFAULT_LAB_DURATION_MINUTES = int(os.environ.get('DEFAULT_LAB_DURATION_MINUTES', 120))  # 2 hours
    DEFAULT_LAB_SETUP_TIME = int(os.environ.get('DEFAULT_LAB_SETUP_TIME', 15))  # minutes
    DEFAULT_LAB_CLEANUP_TIME = int(os.environ.get('DEFAULT_LAB_CLEANUP_TIME', 15))  # minutes
    MAX_LAB_GROUP_SIZE = int(os.environ.get('MAX_LAB_GROUP_SIZE', 25))
    
    # Shift Configuration
    MORNING_SHIFT_START = '09:00'
    MORNING_SHIFT_END = '14:00'
    EVENING_SHIFT_START = '14:00'
    EVENING_SHIFT_END = '18:00'
    
    # Optimization Weights (Fine-tuned for PDF requirements)
    OPTIMIZATION_WEIGHTS = {
        # Hard constraints (from PDF requirements)
        'room_conflicts': 200,
        'faculty_conflicts': 200,
        'batch_conflicts': 200,
        'lab_conflicts': 180,
        'capacity_violations': 160,
        'shift_violations': 140,
        'max_classes_per_day': 120,
        'faculty_availability_violations': 150,
        'special_class_violations': 300,  # Fixed slots from PDF
        
        # Lab-specific constraints
        'lab_duration_violations': 100,
        'lab_equipment_conflicts': 120,
        'lab_safety_violations': 140,
        'technician_availability': 80,
        
        # Optimization goals (from PDF requirements)
        'classroom_utilization': 50,     # Maximize utilization
        'lab_utilization': 60,
        'faculty_load_balance': 40,      # Minimize workload
        'elective_sync_violations': 70,
        'interdisciplinary_bonus': 30,
        'continuous_slot_bonus': 20
    }
    
    # Email Configuration (for notifications)
    MAIL_SERVER = os.environ.get('MAIL_SERVER', 'smtp.gmail.com')
    MAIL_PORT = int(os.environ.get('MAIL_PORT', 587))
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS', 'True').lower() == 'true'
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
    MAIL_DEFAULT_SENDER = os.environ.get('MAIL_DEFAULT_SENDER', 'noreply@timetable-scheduler.edu')

class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True
    SQLALCHEMY_ECHO = True

class ProductionConfig(Config):
    """Production configuration"""
    DEBUG = False
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'postgresql://user:pass@localhost/timetable_prod'

# Configuration dictionary
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}

def get_config_by_name(config_name):
    """Get configuration class by name"""
    return config.get(config_name, config['default'])