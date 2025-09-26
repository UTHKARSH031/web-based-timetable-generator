import random
import numpy as np
from datetime import datetime, time, timedelta
from ortools.sat.python import cp_model
from models import *
from config import Config
import json

class AdvancedTimetableOptimizer:
    """Advanced Timetable Optimizer addressing all PDF constraints"""
    
    def __init__(self, semester_id):
        self.semester_id = semester_id
        self.load_data()
        self.initialize_parameters()
        self.conflicts = []
        self.lab_scheduling_rules = self.load_lab_rules()
    
    def load_data(self):
        """Load all required data with lab support"""
        self.classrooms = Classroom.query.filter_by(is_available=True).all()  # PDF parameter
        self.laboratories = Laboratory.query.filter_by(is_available=True).all()
        self.faculty = Faculty.query.all()  # PDF parameter
        self.subjects = Subject.query.filter_by(semester_id=self.semester_id).all()  # PDF parameter
        self.batches = Batch.query.filter_by(semester_id=self.semester_id).all()  # PDF parameter
        self.electives = Elective.query.join(Subject).filter(Subject.semester_id == self.semester_id).all()
        self.special_classes = SpecialClass.query.join(Subject).filter(Subject.semester_id == self.semester_id).all()  # PDF fixed slots
        self.faculty_availability = FacultyAvailability.query.all()
        self.faculty_leaves = FacultyLeave.query.filter(
            FacultyLeave.start_date <= datetime.now().date(),
            FacultyLeave.end_date >= datetime.now().date(),
            FacultyLeave.is_approved == True
        ).all()  # PDF leaves constraint
        self.lab_sessions = LabSession.query.join(Subject).filter(Subject.semester_id == self.semester_id).all()
        
        # Create lookup dictionaries
        self.faculty_availability_map = {}
        for avail in self.faculty_availability:
            if avail.faculty_id not in self.faculty_availability_map:
                self.faculty_availability_map[avail.faculty_id] = []
            self.faculty_availability_map[avail.faculty_id].append(avail)
        
        self.faculty_leaves_map = {}
        for leave in self.faculty_leaves:
            if leave.faculty_id not in self.faculty_leaves_map:
                self.faculty_leaves_map[leave.faculty_id] = []
            self.faculty_leaves_map[leave.faculty_id].append(leave)
        
        self.time_slots = Config.TIME_SLOTS
        self.working_days = Config.WORKING_DAYS
    
    def load_lab_rules(self):
        """Load laboratory-specific scheduling rules"""
        return {
            'min_lab_duration': Config.DEFAULT_LAB_DURATION_MINUTES,
            'setup_buffer': Config.DEFAULT_LAB_SETUP_TIME,
            'max_consecutive_lab_hours': 4,
            'lab_group_size_limit': Config.MAX_LAB_GROUP_SIZE,
            'requires_technician_subjects': ['engineering', 'chemistry', 'physics'],
            'preferred_lab_timings': {
                'computer': ['morning', 'evening'],
                'chemistry': ['morning'],
                'physics': ['morning', 'afternoon'],
                'biology': ['morning']
            }
        }
    
    def initialize_parameters(self):
        """Initialize enhanced parameters based on PDF constraints"""
        self.population_size = Config.GA_POPULATION_SIZE
        self.generations = Config.GA_GENERATIONS
        self.mutation_rate = Config.GA_MUTATION_RATE
        self.crossover_rate = Config.GA_CROSSOVER_RATE
        
        # Use optimization weights from config
        self.weights = Config.OPTIMIZATION_WEIGHTS
    
    def create_comprehensive_schedule(self):
        """Create schedule with all PDF constraints and lab support"""
        schedule = []
        
        # Step 1: Schedule all special/fixed classes first (PDF requirement)
        print("Scheduling special/fixed classes...")
        for special in self.special_classes:
            venue = self.get_suitable_venue(special.subject, special.batch)
            if venue:
                schedule.append({
                    'subject_id': special.subject_id,
                    'batch_id': special.batch_id,
                    'faculty_id': special.subject.faculty_id,
                    'venue_id': venue['id'],
                    'venue_type': venue['type'],
                    'day': self.convert_day_number_to_name(special.day_of_week),
                    'start_time': special.start_time.strftime('%H:%M'),
                    'end_time': special.end_time.strftime('%H:%M'),
                    'is_fixed': True,  # PDF constraint
                    'shift': self.get_time_shift(special.start_time),
                    'class_type': special.class_type,
                    'priority': special.priority
                })
        
        # Step 2: Schedule laboratory sessions
        print("Scheduling laboratory sessions...")
        lab_schedule = self.schedule_lab_sessions()
        schedule.extend(lab_schedule)
        
        # Step 3: Schedule electives (synchronized across batches)
        print("Scheduling elective subjects...")
        elective_schedule = self.schedule_electives_advanced()
        schedule.extend(elective_schedule)
        
        # Step 4: Schedule regular theory classes
        print("Scheduling regular theory classes...")
        theory_schedule = self.schedule_theory_classes(schedule)
        schedule.extend(theory_schedule)
        
        # Step 5: Validate and adjust for max classes per day constraint (PDF)
        schedule = self.enforce_max_classes_per_day(schedule)
        
        return schedule
    
    def enforce_max_classes_per_day(self, schedule):
        """Enforce maximum classes per day constraint from PDF"""
        adjusted_schedule = []
        batch_daily_count = {}
        
        # Sort schedule by priority (fixed classes first)
        schedule.sort(key=lambda x: (not x.get('is_fixed', False), x.get('priority', 99)))
        
        for entry in schedule:
            batch_id = entry['batch_id']
            day = entry['day']
            
            # Initialize tracking
            if batch_id not in batch_daily_count:
                batch_daily_count[batch_id] = {}
            if day not in batch_daily_count[batch_id]:
                batch_daily_count[batch_id][day] = 0
            
            batch = next((b for b in self.batches if b.id == batch_id), None)
            max_classes = batch.max_classes_per_day if batch else Config.MAX_CLASSES_PER_DAY  # PDF constraint
            
            # Check if adding this class would exceed the limit
            if batch_daily_count[batch_id][day] < max_classes:
                adjusted_schedule.append(entry)
                batch_daily_count[batch_id][day] += 1
            elif entry.get('is_fixed', False):
                # Fixed classes must be scheduled regardless (PDF requirement)
                adjusted_schedule.append(entry)
                batch_daily_count[batch_id][day] += 1
                self.conflicts.append({
                    'type': 'max_classes_exceeded',
                    'batch_id': batch_id,
                    'day': day,
                    'count': batch_daily_count[batch_id][day],
                    'limit': max_classes,
                    'reason': 'Fixed class caused limit exceeded'
                })
            else:
                # Try to reschedule to another day
                rescheduled = self.reschedule_to_different_day(entry, batch_daily_count, max_classes)
                if rescheduled:
                    adjusted_schedule.append(rescheduled)
                    batch_daily_count[batch_id][rescheduled['day']] += 1
                else:
                    self.conflicts.append({
                        'type': 'max_classes_exceeded',
                        'subject': entry.get('subject_id'),
                        'batch_id': batch_id,
                        'day': day,
                        'reason': 'Could not reschedule within daily limit'
                    })
        
        return adjusted_schedule
    
    def calculate_comprehensive_fitness(self, schedule):
        """Enhanced fitness calculation with all PDF constraints and lab support"""
        fitness_score = 1000.0  # Start with higher base score
        
        # Hard constraints from PDF
        fitness_score -= self.check_room_conflicts(schedule) * self.weights['room_conflicts']
        fitness_score -= self.check_faculty_conflicts(schedule) * self.weights['faculty_conflicts'] 
        fitness_score -= self.check_batch_conflicts(schedule) * self.weights['batch_conflicts']
        fitness_score -= self.check_capacity_violations(schedule) * self.weights['capacity_violations']
        fitness_score -= self.check_shift_violations(schedule) * self.weights['shift_violations']
        fitness_score -= self.check_max_classes_per_day_violations(schedule) * self.weights['max_classes_per_day']
        fitness_score -= self.check_faculty_availability_violations(schedule) * self.weights['faculty_availability_violations']
        fitness_score -= self.check_special_class_violations(schedule) * self.weights['special_class_violations']
        
        # Lab-specific constraints
        fitness_score -= self.check_lab_conflicts(schedule) * self.weights['lab_conflicts']
        fitness_score -= self.check_lab_duration_violations(schedule) * self.weights['lab_duration_violations']
        
        # Elective constraints
        fitness_score -= self.check_elective_sync_violations(schedule) * self.weights['elective_sync_violations']
        
        # Optimization goals from PDF
        fitness_score += self.calculate_classroom_utilization_score(schedule) * self.weights['classroom_utilization']
        fitness_score += self.calculate_lab_utilization_score(schedule) * self.weights['lab_utilization']
        fitness_score += self.calculate_faculty_load_balance_score(schedule) * self.weights['faculty_load_balance']
        
        return max(0, fitness_score)
    
    def check_max_classes_per_day_violations(self, schedule):
        """Check violations of maximum classes per day constraint from PDF"""
        violations = 0
        batch_daily_count = {}
        
        for entry in schedule:
            batch_id = entry['batch_id']
            day = entry['day']
            
            if batch_id not in batch_daily_count:
                batch_daily_count[batch_id] = {}
            if day not in batch_daily_count[batch_id]:
                batch_daily_count[batch_id][day] = 0
            
            batch_daily_count[batch_id][day] += 1
        
        for batch_id, daily_counts in batch_daily_count.items():
            batch = next((b for b in self.batches if b.id == batch_id), None)
            max_classes = batch.max_classes_per_day if batch else Config.MAX_CLASSES_PER_DAY
            
            for day, count in daily_counts.items():
                if count > max_classes:
                    violations += (count - max_classes)
        
        return violations
    
    def calculate_classroom_utilization_score(self, schedule):
        """Calculate classroom utilization score (PDF requirement - maximize utilization)"""
        room_usage = {}
        total_slots = len(self.working_days) * len(self.time_slots)
        
        for entry in schedule:
            if entry.get('venue_type') == 'classroom':
                room_id = entry['venue_id']
                if room_id not in room_usage:
                    room_usage[room_id] = 0
                room_usage[room_id] += 1
        
        if not room_usage:
            return 0
        
        total_rooms = len(self.classrooms)
        total_possible_usage = total_rooms * total_slots
        actual_usage = sum(room_usage.values())
        utilization_rate = actual_usage / total_possible_usage if total_possible_usage > 0 else 0
        
        # Optimal utilization based on config
        min_util = Config.MIN_CLASSROOM_UTILIZATION
        max_util = Config.MAX_CLASSROOM_UTILIZATION
        
        if min_util <= utilization_rate <= max_util:
            return 20
        elif min_util * 0.8 <= utilization_rate <= max_util * 1.1:
            return 15
        else:
            return 5
    
    def calculate_faculty_load_balance_score(self, schedule):
        """Calculate faculty workload balance score (PDF requirement - minimize workload)"""
        faculty_hours = {}
        faculty_daily_hours = {}
        
        for entry in schedule:
            faculty_id = entry['faculty_id']
            day = entry['day']
            
            # Calculate session duration
            start_time = datetime.strptime(entry['start_time'], '%H:%M')
            end_time = datetime.strptime(entry['end_time'], '%H:%M')
            duration_hours = (end_time - start_time).seconds / 3600
            
            # Track total weekly hours
            if faculty_id not in faculty_hours:
                faculty_hours[faculty_id] = 0
            faculty_hours[faculty_id] += duration_hours
            
            # Track daily hours
            if faculty_id not in faculty_daily_hours:
                faculty_daily_hours[faculty_id] = {}
            if day not in faculty_daily_hours[faculty_id]:
                faculty_daily_hours[faculty_id][day] = 0
            faculty_daily_hours[faculty_id][day] += duration_hours
        
        violations = 0
        balance_score = 0
        
        for faculty_id, weekly_hours in faculty_hours.items():
            faculty = next((f for f in self.faculty if f.id == faculty_id), None)
            if not faculty:
                continue
            
            # Check weekly hour limits (PDF constraint)
            if weekly_hours > faculty.max_hours_per_week:
                violations += (weekly_hours - faculty.max_hours_per_week)
            
            # Check daily hour limits (PDF constraint)
            for day, daily_hours in faculty_daily_hours.get(faculty_id, {}).items():
                if daily_hours > faculty.max_hours_per_day:
                    violations += (daily_hours - faculty.max_hours_per_day)
        
        # Calculate balance (lower standard deviation is better)
        if faculty_hours:
            hours_list = list(faculty_hours.values())
            avg_hours = sum(hours_list) / len(hours_list)
            variance = sum((h - avg_hours) ** 2 for h in hours_list) / len(hours_list)
            std_dev = variance ** 0.5
            
            # Lower standard deviation gets higher score
            if std_dev < 2:
                balance_score = 20
            elif std_dev < 4:
                balance_score = 15
            elif std_dev < 6:
                balance_score = 10
            else:
                balance_score = 5
        
        return balance_score - violations
    
    def optimize_with_comprehensive_constraints(self):
        """Main optimization with all PDF constraints and lab support"""
        print(f"Starting comprehensive optimization for semester {self.semester_id}")
        print(f"Subjects: {len(self.subjects)} (Theory: {sum(1 for s in self.subjects if s.theory_hours_per_week > 0)}, "
              f"Lab: {sum(1 for s in self.subjects if s.lab_hours_per_week > 0)})")
        print(f"Venues: {len(self.classrooms)} classrooms, {len(self.laboratories)} laboratories")
        print(f"Faculty: {len(self.faculty)}, Batches: {len(self.batches)}")
        
        # Generate initial population with comprehensive constraints
        population = []
        for i in range(self.population_size):
            individual = self.create_comprehensive_schedule()
            population.append(individual)
            if i % 10 == 0:
                print(f"Generated {i+1}/{self.population_size} initial schedules")
        
        best_fitness_history = []
        best_individual = None
        best_fitness = 0
        
        for generation in range(self.generations):
            # Calculate fitness for all individuals
            fitness_scores = []
            for individual in population:
                fitness = self.calculate_comprehensive_fitness(individual)
                fitness_scores.append(fitness)
            
            # Track best solution
            current_best_fitness = max(fitness_scores) if fitness_scores else 0
            current_best_index = np.argmax(fitness_scores) if fitness_scores else 0
            
            if current_best_fitness > best_fitness:
                best_fitness = current_best_fitness
                best_individual = population[current_best_index].copy()
            
            best_fitness_history.append(current_best_fitness)
            
            if generation % 10 == 0:
                avg_fitness = np.mean(fitness_scores) if fitness_scores else 0
                print(f"Generation {generation}: Best={current_best_fitness:.2f}, Avg={avg_fitness:.2f}")
            
            # Early stopping for excellent solutions
            if current_best_fitness >= 900.0:
                print(f"Excellent solution found at generation {generation}")
                break
            
            # Evolution process with elitism
            new_population = []
            
            # Keep best individuals (elitism)
            elite_count = max(1, self.population_size // 10)
            elite_indices = np.argsort(fitness_scores)[-elite_count:]
            for idx in elite_indices:
                new_population.append(population[idx].copy())
            
            # Generate rest of population
            while len(new_population) < self.population_size:
                parent1 = self.tournament_selection(population, fitness_scores)
                parent2 = self.tournament_selection(population, fitness_scores)
                
                offspring1, offspring2 = self.enhanced_crossover(parent1, parent2)
                offspring1 = self.comprehensive_mutation(offspring1)
                offspring2 = self.comprehensive_mutation(offspring2)
                
                new_population.extend([offspring1, offspring2])
            
            population = new_population[:self.population_size]
        
        # Final result
        if best_individual is None:
            best_individual = population[0] if population else []
            best_fitness = self.calculate_comprehensive_fitness(best_individual)
        
        print(f"Optimization completed. Best fitness: {best_fitness:.2f}")
        print(f"Total conflicts detected: {len(self.conflicts)}")
        
        return best_individual, best_fitness
    
    def generate_multiple_optimized_solutions(self, num_solutions=3):
        """Generate multiple solution alternatives as required by PDF"""
        solutions = []
        
        for i in range(num_solutions):
            print(f"\n=== Generating Solution {i+1}/{num_solutions} ===")
            
            # Vary parameters slightly for diversity
            original_mutation_rate = self.mutation_rate
            original_population_size = self.population_size
            
            # Introduce variation
            self.mutation_rate = original_mutation_rate + (i * 0.02)
            self.population_size = original_population_size + (i * 5)
            
            # Generate solution
            solution, fitness = self.optimize_with_comprehensive_constraints()
            
            # Calculate additional metrics for PDF requirements
            metrics = self.calculate_solution_metrics(solution)
            
            solutions.append({
                'schedule': solution,
                'fitness': fitness,
                'metrics': metrics,
                'conflicts': self.conflicts.copy()
            })
            
            # Reset parameters
            self.mutation_rate = original_mutation_rate
            self.population_size = original_population_size
            self.conflicts = []  # Reset conflicts for next solution
        
        # Sort solutions by fitness (best first) - PDF requirement for multiple options
        solutions.sort(key=lambda x: x['fitness'], reverse=True)
        
        return solutions
    
    def calculate_solution_metrics(self, schedule):
        """Calculate comprehensive metrics for PDF reporting"""
        metrics = {
            'total_classes_scheduled': len(schedule),
            'theory_classes': len([s for s in schedule if s.get('class_type') == 'theory']),
            'lab_classes': len([s for s in schedule if s.get('class_type') == 'lab']),
            'elective_classes': len([s for s in schedule if s.get('is_elective', False)]),
            'fixed_classes': len([s for s in schedule if s.get('is_fixed', False)]),
            'classroom_utilization': 0,
            'lab_utilization': 0,
            'faculty_load_balance': 0,
            'max_classes_per_day_violations': 0,
            'conflict_summary': {}
        }
        
        # Calculate utilization rates
        classroom_usage = len([s for s in schedule if s.get('venue_type') == 'classroom'])
        lab_usage = len([s for s in schedule if s.get('venue_type') == 'laboratory'])
        
        total_classroom_slots = len(self.classrooms) * len(self.working_days) * len(self.time_slots)
        total_lab_slots = len(self.laboratories) * len(self.working_days) * len(self.time_slots)
        
        metrics['classroom_utilization'] = (classroom_usage / total_classroom_slots * 100) if total_classroom_slots > 0 else 0
        metrics['lab_utilization'] = (lab_usage / total_lab_slots * 100) if total_lab_slots > 0 else 0
        
        # Faculty workload analysis
        faculty_hours = {}
        for entry in schedule:
            faculty_id = entry['faculty_id']
            start_time = datetime.strptime(entry['start_time'], '%H:%M')
            end_time = datetime.strptime(entry['end_time'], '%H:%M')
            duration_hours = (end_time - start_time).seconds / 3600
            
            if faculty_id not in faculty_hours:
                faculty_hours[faculty_id] = 0
            faculty_hours[faculty_id] += duration_hours
        
        if faculty_hours:
            hours_list = list(faculty_hours.values())
            avg_hours = sum(hours_list) / len(hours_list)
            variance = sum((h - avg_hours) ** 2 for h in hours_list) / len(hours_list)
            metrics['faculty_load_balance'] = variance ** 0.5  # Standard deviation
        
        # Conflict summary
        conflict_types = {}
        for conflict in self.conflicts:
            conflict_type = conflict.get('type', 'unknown')
            if conflict_type not in conflict_types:
                conflict_types[conflict_type] = 0
            conflict_types[conflict_type] += 1
        
        metrics['conflict_summary'] = conflict_types
        metrics['total_conflicts'] = len(self.conflicts)
        
        return metrics
    
    # Utility methods (need to implement missing ones)
    def tournament_selection(self, population, fitness_scores, tournament_size=3):
        """Tournament selection for genetic algorithm"""
        tournament_indices = random.sample(range(len(population)), min(tournament_size, len(population)))
        tournament_fitness = [fitness_scores[i] for i in tournament_indices]
        winner_index = tournament_indices[np.argmax(tournament_fitness)]
        return population[winner_index]
    
    def enhanced_crossover(self, parent1, parent2):
        """Enhanced crossover for schedule entries"""
        if random.random() > self.crossover_rate or len(parent1) == 0 or len(parent2) == 0:
            return parent1.copy(), parent2.copy()
        
        crossover_point = random.randint(1, min(len(parent1), len(parent2)) - 1)
        offspring1 = parent1[:crossover_point] + parent2[crossover_point:]
        offspring2 = parent2[:crossover_point] + parent1[crossover_point:]
        
        return offspring1, offspring2
    
    def comprehensive_mutation(self, individual):
        """Comprehensive mutation for schedule entries"""
        if len(individual) == 0:
            return individual
        
        for i in range(len(individual)):
            if random.random() < self.mutation_rate:
                # Skip fixed classes (PDF constraint)
                if individual[i].get('is_fixed', False):
                    continue
                
                # Random mutation type
                mutation_type = random.choice(['day', 'time', 'venue'])
                
                if mutation_type == 'day':
                    individual[i]['day'] = random.choice(self.working_days)
                elif mutation_type == 'time':
                    new_slot = random.choice(self.time_slots)
                    individual[i]['start_time'] = new_slot[0]
                    individual[i]['end_time'] = new_slot[1]
                elif mutation_type == 'venue':
                    # Find alternative venue
                    if individual[i].get('class_type') == 'lab':
                        if self.laboratories:
                            individual[i]['venue_id'] = random.choice(self.laboratories).id
                            individual[i]['venue_type'] = 'laboratory'
                    else:
                        if self.classrooms:
                            individual[i]['venue_id'] = random.choice(self.classrooms).id
                            individual[i]['venue_type'] = 'classroom'
        
        return individual
    
    # Additional required methods (simplified implementations)
    def schedule_lab_sessions(self):
        return []  # Placeholder
    
    def schedule_electives_advanced(self):
        return []  # Placeholder
    
    def schedule_theory_classes(self, existing_schedule):
        return []  # Placeholder
    
    def reschedule_to_different_day(self, entry, batch_daily_count, max_classes):
        return None  # Placeholder
    
    def check_room_conflicts(self, schedule):
        return 0  # Placeholder
    
    def check_faculty_conflicts(self, schedule):
        return 0  # Placeholder
    
    def check_batch_conflicts(self, schedule):
        return 0  # Placeholder
    
    def check_capacity_violations(self, schedule):
        return 0  # Placeholder
    
    def check_shift_violations(self, schedule):
        return 0  # Placeholder
    
    def check_faculty_availability_violations(self, schedule):
        return 0  # Placeholder
    
    def check_special_class_violations(self, schedule):
        return 0  # Placeholder
    
    def check_lab_conflicts(self, schedule):
        return 0  # Placeholder
    
    def check_lab_duration_violations(self, schedule):
        return 0  # Placeholder
    
    def check_elective_sync_violations(self, schedule):
        return 0  # Placeholder
    
    def calculate_lab_utilization_score(self, schedule):
        return 0  # Placeholder
    
    def get_suitable_venue(self, subject, batch):
        return {'id': 1, 'type': 'classroom'}  # Placeholder
    
    def convert_day_number_to_name(self, day_number):
        days = {1: 'Monday', 2: 'Tuesday', 3: 'Wednesday', 4: 'Thursday', 5: 'Friday'}
        return days.get(day_number, 'Monday')
    
    def get_time_shift(self, time_obj):
        hour = time_obj.hour if hasattr(time_obj, 'hour') else int(str(time_obj).split(':')[0])
        return 'morning' if hour < 14 else 'evening'