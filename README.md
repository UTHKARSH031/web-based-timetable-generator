# Smart Timetable Scheduler - SIH 2025

**A comprehensive timetable scheduling system with advanced optimization, laboratory management, and multi-shift support developed for Smart India Hackathon 2025 (Project ID: 25028).**

##  Overview

The Smart Timetable Scheduler is a full-featured web application built with Flask that addresses complex institutional scheduling requirements. It incorporates advanced genetic algorithms, constraint satisfaction, and multi-objective optimization to generate optimal timetables while handling real-world constraints like faculty availability, laboratory requirements, and resource utilization.

## Key Features

###  **Laboratory Management System**
- Dedicated laboratory scheduling with equipment validation
- Lab-specific time slots (2-3 hour sessions)
- Safety protocol enforcement and technician requirements
- Setup/cleanup time buffers between sessions
- Equipment and software requirements tracking

###  **Advanced Optimization Engine**
- Genetic Algorithm-based timetable generation
- Multi-objective optimization with configurable weights
- PDF constraint compliance (fixed slots, maximum classes per day)
- Conflict detection and resolution suggestions
- Multiple solution alternatives generation

###  **Multi-Shift Support**
- Morning and evening shift scheduling
- Cross-shift resource sharing optimization
- Shift-specific faculty and classroom assignments

###  **Role-Based Authentication**
- JWT token-based security
- Multi-tier permission system (Admin, Reviewer, Faculty)
- Department-based access control
- Session management and CSRF protection

###  **Review & Approval Workflow**
- Timetable review and approval process
- Priority issue tracking
- Suggested changes documentation
- Status-based workflow management

###  **Analytics & Reporting**
- Comprehensive utilization reports
- Faculty workload analysis
- Resource optimization insights
- Conflict analysis and resolution tracking

##  Architecture

### Core Components

```
├── app.py                 # Main Flask application and configuration
├── models.py             # SQLAlchemy database models
├── routes.py             # API endpoints and request handlers
├── auth.py               # Authentication and authorization logic
├── scheduler_engine.py   # Advanced optimization algorithms
├── Config.py             # Configuration and settings
└── utils.py              # Utility functions
```

### Database Models

**Core Entities:**
- `User` - System users with role-based permissions
- `Department` - Academic departments with preferences
- `Semester` - Academic semesters and programs
- `Faculty` - Teaching staff with availability and constraints
- `Subject` - Courses with theory and lab components
- `Batch` - Student groups with scheduling requirements

**Scheduling Entities:**
- `Classroom` - Physical classroom resources
- `Laboratory` - Lab facilities with equipment tracking
- `ScheduleEntry` - Individual timetable slots
- `Timetable` - Complete schedule solutions
- `SpecialClass` - Fixed time slot requirements

**Management Entities:**
- `FacultyLeave` - Leave management with substitutions
- `LabSession` - Laboratory session definitions
- `Elective` - Elective course management
- `ScheduleConflict` - Conflict tracking and resolution

##  Quick Start

### Prerequisites
- Python 3.8+
- Flask and dependencies
- SQLAlchemy compatible database

### Installation

1. **Clone the repository**
```bash
git clone <repository-url>
cd smart-timetable-scheduler
```

2. **Create virtual environment**
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies**
```bash
pip install flask flask-sqlalchemy flask-jwt-extended flask-cors python-dotenv werkzeug ortools numpy
```

4. **Set up environment variables** (optional)
```bash
# Create .env file with your configurations
FLASK_ENV=development
DATABASE_URL=sqlite:///scheduler.db
SECRET_KEY=your-secret-key
JWT_SECRET_KEY=your-jwt-secret
```

5. **Initialize database**
```bash
python app.py
# Or use Flask CLI
flask init-db
```

6. **Run the application**
```bash
python app.py
```

The application will start on `http://localhost:5500`

### Default Credentials
- **Username:** `admin`
- **Password:** `admin123`

##  API Endpoints

### Authentication
- `POST /api/login` - User authentication
- `POST /api/register` - User registration (Admin only)

### Resource Management
- `GET/POST /api/departments` - Department management
- `GET/POST /api/faculty` - Faculty management
- `GET/POST /api/subjects` - Subject management
- `GET/POST /api/batches` - Student batch management
- `GET/POST /api/classrooms` - Classroom management
- `GET/POST /api/laboratories` - Laboratory management

### Scheduling
- `POST /api/generate-advanced-timetable` - Generate optimized timetables
- `GET /api/timetables` - Retrieve timetables
- `GET /api/conflicts/{timetable_id}` - View scheduling conflicts
- `PUT /api/conflicts/{conflict_id}/resolve` - Resolve conflicts

### Laboratory Features
- `GET/POST /api/lab-sessions` - Lab session management
- `GET /api/laboratories/{lab_id}/availability` - Lab availability

### Analytics
- `GET /api/dashboard-stats` - Dashboard statistics
- `GET /api/comprehensive-utilization-report/{semester_id}` - Detailed reports

##  Configuration

### Key Configuration Options (Config.py)

```python
# Genetic Algorithm Parameters
GA_POPULATION_SIZE = 50
GA_GENERATIONS = 100
GA_MUTATION_RATE = 0.1

# Scheduling Constraints
MAX_CLASSES_PER_DAY = 8
DEFAULT_LAB_DURATION_MINUTES = 120
MIN_CLASSROOM_UTILIZATION = 0.6

# Time Slots
WORKING_DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
TIME_SLOTS = [
    ("09:00", "10:00"),
    ("10:00", "11:00"),
    # ... more slots
]
```

### Environment Variables
- `FLASK_ENV` - Environment (development/production)
- `DATABASE_URL` - Database connection string
- `SECRET_KEY` - Flask secret key
- `JWT_SECRET_KEY` - JWT signing key

##  Laboratory Management Features

### Equipment Validation
```python
# Laboratory with equipment requirements
laboratory = Laboratory(
    name="Computer Lab 1",
    lab_type="computer",
    equipment=["Computers", "Projector", "Whiteboard"],
    safety_requirements="Standard electrical safety"
)
```

### Time Slot Management
```python
# Lab-specific extended time slots
LAB_TIME_SLOTS = [
    ("09:00", "12:00"),  # 3-hour session
    ("14:00", "17:00"),  # 3-hour session
]
```

##  Optimization Engine

### Genetic Algorithm Features
- **Multi-objective fitness function** with configurable weights
- **Constraint satisfaction** for hard requirements
- **Elitism** to preserve best solutions
- **Tournament selection** for parent selection
- **Multiple solution generation** for alternatives

### Fitness Components
- Room conflict minimization
- Faculty availability optimization
- Classroom utilization maximization
- Laboratory utilization optimization
- Faculty workload balancing

##  Security Features

### Authentication
- JWT token-based authentication
- Password hashing with Werkzeug
- Role-based access control
- Department-level resource isolation

### Input Validation
- XSS prevention
- Input sanitization
- CSRF token validation
- Rate limiting capabilities

##  Reporting & Analytics

### Utilization Reports
- Classroom utilization rates
- Laboratory usage analytics
- Faculty workload distribution
- Resource optimization recommendations

### Conflict Analysis
- Automatic conflict detection
- Resolution suggestions
- Priority-based conflict handling
- Historical conflict tracking

##  Development

### Database Management
```bash
# Initialize database
flask init-db

# Reset database (WARNING: Deletes all data)
flask reset-db
```

### Adding New Features
1. **Models**: Add new database models in `models.py`
2. **Routes**: Implement API endpoints in `routes.py`
3. **Logic**: Add business logic in appropriate modules
4. **Tests**: Create tests for new functionality

##  Production Deployment

### Configuration
```python
# Production config
class ProductionConfig(Config):
    DEBUG = False
    DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'postgresql://user:pass@localhost/timetable_prod'
```

### Deployment Checklist
- [ ] Set production environment variables
- [ ] Configure production database
- [ ] Set up reverse proxy (nginx/Apache)
- [ ] Enable HTTPS
- [ ] Configure logging
- [ ] Set up monitoring

##  Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit changes (`git commit -m 'Add AmazingFeature'`)
4. Push to branch (`git push origin feature/AmazingFeature`)
5. Open Pull Request

##  License

This project is developed for Smart India Hackathon 2025. Please refer to the competition guidelines for usage rights.

##  Support

For technical support or questions:
- Create an issue in the repository
- Check the API documentation at `/api`
- Review the health check endpoint at `/health`

##  Future Enhancements

- [ ] Machine learning-based preference learning
- [ ] Mobile application support
- [ ] Real-time collaboration features
- [ ] Advanced reporting dashboard
- [ ] Integration with external calendar systems
- [ ] Automated conflict resolution
- [ ] Multi-language support

---

**Built  for Smart India Hackathon 2025**

*Project ID: 25028 - Advanced Timetable Scheduling with Laboratory Management*

##  Author

N.Uthkarsh Sai  
BTech AI & Data Science  
Amrita Vishwa Vidyapeetham
