# scripts/seed_data.py

import os
import sys
import logging
import random
from datetime import datetime, timedelta, timezone

import bcrypt
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from app.models import Team, User, Skill, Project, Task, UserSkill, TaskRequiredSkill

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
_ = load_dotenv()

# =================================================================================
# --- 🧑‍💻 PERSONA & TASK DEFINITIONS FOR RIGOROUS TESTING ---
# =================================================================================

PERSONAS = {
    "priya": {"name": "Priya Patel", "archetype": "Veteran Full-Stack Generalist"},
    "leo": {"name": "Leo Chen", "archetype": "New Frontend Specialist"},
    "maria": {"name": "Maria Garcia", "archetype": "Pure Backend Specialist"},
    "sam": {"name": "Sam Jones", "archetype": "T-Shaped DevOps Engineer"},
}

TASK_TEMPLATES = {
    "Full-Stack Feature": {"skills": ["Python", "React", "PostgreSQL"]},
    "UI Component Build": {"skills": ["React", "TypeScript", "Tailwind CSS"]},
    "API Endpoint Creation": {"skills": ["Go", "PostgreSQL", "Docker"]},
    "Infrastructure Migration": {"skills": ["Kubernetes", "Terraform", "AWS"]},
    "CI/CD Scripting": {"skills": ["CI/CD", "Python"]},
    "Cross-Functional Dashboard": {"skills": ["React", "Pandas"]}
}

# =================================================================================

def clear_data(session: Session):
    logging.info("Clearing existing transactional data...")
    session.execute(text("TRUNCATE TABLE invitations, task_required_skills, user_skills, tasks, projects, users, teams RESTART IDENTITY CASCADE"))
    session.commit()
    logging.info("Transactional data cleared successfully.")

def seed_data():
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        logging.error("DATABASE_URL environment variable not set.")
        return

    engine = create_engine(db_url)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()

    try:
        clear_data(session)

        # 1. Fetch skills
        logging.info("Fetching existing skills from DB...")
        all_skills = session.query(Skill).all()
        skills_map = {skill.skill_name: skill for skill in all_skills}
        logging.info(f"Loaded {len(skills_map)} skills.")

        # 2. Create Teams
        logging.info("Seeding teams...")
        hashed_password = bcrypt.hashpw("password".encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        team_names = ["Backend Titans", "Frontend Wizards", "Data Mavericks", "Cloud Sentinels"]
        teams = {name: Team(team_name=name) for name in team_names}
        session.add_all(teams.values())
        session.flush()

        # 3. Define Engineer Archetypes
        archetypes = {
            "Veteran Full-Stack Generalist": {"team": teams["Backend Titans"], "skills": [("Python", "expert"), ("React", "intermediate"), ("PostgreSQL", "expert"), ("Docker", "intermediate")]},
            "New Frontend Specialist": {"team": teams["Frontend Wizards"], "skills": [("React", "expert"), ("TypeScript", "expert"), ("Tailwind CSS", "expert"), ("Next.js", "intermediate")]},
            "Pure Backend Specialist": {"team": teams["Backend Titans"], "skills": [("Go", "expert"), ("PostgreSQL", "expert"), ("Docker", "expert"), ("Redis", "intermediate")]},
            "T-Shaped DevOps Engineer": {"team": teams["Cloud Sentinels"], "skills": [("AWS", "expert"), ("Kubernetes", "expert"), ("Terraform", "expert"), ("Python", "intermediate"), ("CI/CD", "expert")]},
        }

        # 4. Seed Specific Personas
        logging.info("--- Seeding Specific Test Personas ---")
        for key, persona_info in PERSONAS.items():
            archetype_name = persona_info["archetype"]
            archetype_config = archetypes[archetype_name]
            user = User(
                name=persona_info["name"],
                email=f"{persona_info['name'].lower().replace(' ', '.')}@synapse.com",
                password_hash=hashed_password, role='engineer', team=archetype_config["team"]
            )
            session.add(user)
            logging.info(f"Created Persona: {user.name} ({archetype_name})")
            
            for skill_name, prof in archetype_config["skills"]:
                session.add(UserSkill(user=user, skill=skills_map[skill_name], proficiency=prof))
        session.commit()

        # 5. Seed a large number of other engineers for model training data
        logging.info("--- Seeding Additional Engineers for Data Richness ---")
        used_emails = set(p[0] for p in session.query(User.email).all())

        NUM_EXTRA_ENGINEERS = 40
        generated_count = 0
        max_attempts = NUM_EXTRA_ENGINEERS * 5

        for i in range(max_attempts):
            if generated_count >= NUM_EXTRA_ENGINEERS:
                break
            
            rand_num = random.randint(100, 9999)
            email = f"user.{rand_num}@synapse.com"
            if email in used_emails:
                continue
            
            archetype_name = random.choice(list(archetypes.keys()))
            config = archetypes[archetype_name]
            user = User(name=f"User-{rand_num}", email=email, password_hash=hashed_password, role='engineer', team=config["team"])
            session.add(user)
            session.flush()

            for skill, prof in config["skills"]:
                session.add(UserSkill(user=user, skill=skills_map[skill], proficiency=prof))

            used_emails.add(email)
            generated_count += 1
        
        session.commit()
        
        # 6. Seed Projects and a Realistic Task History
        logging.info("--- Seeding Realistic Task History for Personas ---")
        proj_apollo = Project(project_name="Project Apollo")
        proj_gemini = Project(project_name="Project Gemini")
        session.add_all([proj_apollo, proj_gemini])
        session.flush()

        task_assignments = [
            {"assignee_name": "Priya Patel", "template": "Full-Stack Feature", "count": 25},
            {"assignee_name": "Leo Chen", "template": "UI Component Build", "count": 2},
            {"assignee_name": "Maria Garcia", "template": "API Endpoint Creation", "count": 12},
            {"assignee_name": "Sam Jones", "template": "Infrastructure Migration", "count": 10},
            {"assignee_name": "Sam Jones", "template": "CI/CD Scripting", "count": 4},
        ]

        for assignment in task_assignments:
            user_name = assignment["assignee_name"]
            user = session.query(User).filter_by(name=user_name).one()
            
            template = TASK_TEMPLATES[assignment["template"]]
            logging.info(f"Assigning {assignment['count']} '{assignment['template']}' tasks to {user.name}...")

            for i in range(assignment["count"]):
                task = Task(
                    project_id=random.choice([proj_apollo.id, proj_gemini.id]),
                    title=f"{assignment['template']} Task #{i+1}",
                    status='done', assignee_id=user.id,
                    completed_at=datetime.now(timezone.utc) - timedelta(days=random.randint(5, 100))
                )
                session.add(task)
                for skill_name in template["skills"]:
                    session.add(TaskRequiredSkill(task=task, skill=skills_map[skill_name]))

        session.commit()
        logging.info("Seeding complete. Database contains a realistic, testable dataset.")

    except Exception as e:
        logging.error(f"An error occurred: {e}", exc_info=True)
        session.rollback()
    finally:
        session.close()

if __name__ == "__main__":
    seed_data()
