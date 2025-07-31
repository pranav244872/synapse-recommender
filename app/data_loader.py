# app/data_loader.py

import os
import logging
import numpy as np # Import numpy
from typing import Tuple, List, Dict
import pandas as pd
from sqlalchemy import create_engine, select, func
from sqlalchemy.orm import sessionmaker

from app.models import User, Skill, UserSkill, Task, TaskRequiredSkill

# --- Sigmoid Function for Dynamic Weighting ---
def get_implicit_weight(task_count: float, k: float = 0.5, midpoint: float = 10.0) -> float:
    """
    Calculates the weight for implicit ratings using a sigmoid function.
    
    Args:
        task_count: The number of tasks a user has completed.
        k: The steepness of the curve.
        midpoint: The number of tasks where weight is 0.5.

    Returns:
        A weight between 0 and 1.
    """
    if task_count == 0:
        return 0.0 # A user with zero completed tasks has 0% weight on implicit skills.
    return 1 / (1 + np.exp(-k * (task_count - midpoint)))


def load_data_for_engine() -> Tuple[pd.DataFrame, List[int], Dict[Tuple[int, int], float]]:
    """
    Fetches and processes data using a dynamic weighting system for ratings.
    """
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        logging.error("DATABASE_URL environment variable not set.")
        raise ValueError("DATABASE_URL is not configured.")

    engine = create_engine(db_url)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()

    try:
        # --- Part 1: Fetch Raw Data ---
        
        # 1a. Fetch Explicit Ratings (unchanged)
        logging.info("Fetching explicit ratings...")
        proficiency_query = select(UserSkill.user_id, UserSkill.skill_id, UserSkill.proficiency)
        explicit_df = pd.read_sql(proficiency_query, session.bind)
        proficiency_map = {'beginner': 2.0, 'intermediate': 3.5, 'expert': 5.0}
        explicit_df['explicit_rating'] = explicit_df['proficiency'].map(proficiency_map) #type: ignore
        
        # 1b. Fetch Implicit Ratings (unchanged)
        logging.info("Fetching implicit ratings...")
        completed_tasks_query = select(Task.assignee_id.label('user_id'), TaskRequiredSkill.skill_id) \
            .join(TaskRequiredSkill, Task.id == TaskRequiredSkill.task_id) \
            .where(Task.status == 'done', Task.assignee_id.isnot(None))
        implicit_df = pd.read_sql(completed_tasks_query, session.bind)
        # We value completion highly, but we also group to get a raw count of experience
        implicit_df = implicit_df.groupby(['user_id', 'skill_id']).size().reset_index(name='implicit_strength') #type: ignore
        implicit_df['implicit_rating'] = 5.0 # A completed task always implies high proficiency
        logging.info(f"Found {len(implicit_df)} implicit user-skill experiences.")

        # 1c. NEW: Fetch total completed task count per user (our 'experience' metric)
        logging.info("Fetching user experience (total completed tasks)...")
        experience_query = select(Task.assignee_id.label('user_id'), func.count(Task.id).label('task_count')) \
            .where(Task.status == 'done', Task.assignee_id.isnot(None)) \
            .group_by(Task.assignee_id)
        experience_df = pd.read_sql(experience_query, session.bind)
        logging.info(f"Calculated experience for {len(experience_df)} users.")

        # --- Part 2: Combine and Apply Dynamic Weighting ---
        
        # 2a. Merge explicit and implicit ratings into a single DataFrame
        ratings_df = pd.merge(
            explicit_df[['user_id', 'skill_id', 'explicit_rating']],
            implicit_df[['user_id', 'skill_id', 'implicit_rating']],
            on=['user_id', 'skill_id'],
            how='outer'
        )

        # 2b. Merge in the user's total experience
        ratings_df = pd.merge(ratings_df, experience_df, on='user_id', how='left')
        ratings_df['task_count'] = ratings_df['task_count'].fillna(0) # Users with no tasks get 0

        # 2c. Apply the dynamic weighting logic
        def calculate_dynamic_rating(row):
            task_count = row['task_count']
            explicit_rating = row['explicit_rating'] if pd.notna(row['explicit_rating']) else 0
            implicit_rating = row['implicit_rating'] if pd.notna(row['implicit_rating']) else 0

            # If a user only has one type of rating, use that.
            if explicit_rating == 0: return implicit_rating
            if implicit_rating == 0: return explicit_rating

            # If both exist, apply dynamic weighting
            implicit_weight = get_implicit_weight(task_count)
            explicit_weight = 1.0 - implicit_weight
            
            return (explicit_weight * explicit_rating) + (implicit_weight * implicit_rating)

        logging.info("Applying dynamic weighting to calculate final ratings...")
        ratings_df['rating'] = ratings_df.apply(calculate_dynamic_rating, axis=1)
        
        # Final DataFrame for the engine
        final_ratings_df = ratings_df[['user_id', 'skill_id', 'rating']].copy()
        final_ratings_df.dropna(inplace=True) # Ensure no NaN ratings
        logging.info(f"Generated {len(final_ratings_df)} dynamically weighted ratings.")

        # --- Part 3: Load Available Users and Create Map (Unchanged) ---
        
        actual_ratings_map = {
            (row.user_id, row.skill_id): row.rating # type: ignore
            for row in final_ratings_df.itertuples()
        }

        logging.info("--- Loading Available Users ---")
        available_users_query = select(User.id).where(User.availability == 'available')
        available_users_df = pd.read_sql(available_users_query, session.bind)
        available_user_ids = available_users_df['id'].tolist()
        logging.info(f"Found {len(available_user_ids)} available users.")

        return final_ratings_df, available_user_ids, actual_ratings_map

    except Exception as e:
        logging.error(f"Failed to load data from database: {e}", exc_info=True)
        return pd.DataFrame(), [], {}
    finally:
        session.close()
