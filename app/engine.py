# app/engine.py

import logging
from typing import List, Dict, Any, Set
from collections import defaultdict

from surprise import Dataset, Reader, SVD

from .data_loader import load_data_for_engine

class RecommendationEngine:
    """
    Implements a multi-stage hybrid recommendation system.

    1.  Candidate Generation: Filters for available users with at least one skill.
    2.  Feature Engineering: Calculates scores for coverage, proficiency, and affinity.
    3.  Ranking: Combines features into a final weighted score to rank candidates.
    """
    # --- RANKING WEIGHTS ---
    # These are tunable parameters that define the engine's priorities.
    WEIGHT_COVERAGE = 0.6    # Priority 1: Do they have the required skills?
    WEIGHT_PROFICIENCY = 0.3 # Priority 2: How good are they at the skills they have?
    WEIGHT_AFFINITY = 0.1    # Priority 3: Do they have latent talent for this work?

    def __init__(self):
        logging.info("Initializing RecommendationEngine...")
        # The data loader now provides the dynamically weighted ratings
        self.ratings_df, self.available_user_ids, self.actual_ratings_map = load_data_for_engine()

        if self.ratings_df.empty:
            logging.error("Ratings data is empty. Engine cannot be initialized.")
            self.model = None
            return

        # Initialize and train the SVD model for the Collaborative Affinity score
        reader = Reader(rating_scale=(1, 5))
        data = Dataset.load_from_df(self.ratings_df[['user_id', 'skill_id', 'rating']], reader)
        trainset = data.build_full_trainset()

        self.model = SVD(n_factors=50, n_epochs=20, random_state=42)
        self.model.fit(trainset)

        # Create a fast lookup map for user's skills
        self.user_skills_map = defaultdict(set)
        for user_id, skill_id in self.actual_ratings_map.keys():
            self.user_skills_map[user_id].add(skill_id)

        logging.info("RecommendationEngine initialized and model trained successfully.")

    def get_recommendations(self, skill_ids: List[int], limit: int) -> List[Dict[str, Any]]:
        if not self.model:
            return []

        required_skills: Set[int] = set(skill_ids)
        if not required_skills:
            return []

        # --- STAGE 1: CANDIDATE GENERATION ---
        candidate_pool: Set[int] = {
            user_id for user_id in self.available_user_ids 
            if not required_skills.isdisjoint(self.user_skills_map.get(user_id, set()))
        }

        logging.info(f"Stage 1: Generated a pool of {len(candidate_pool)} candidates.")

        # --- STAGE 2 & 3: FEATURE ENGINEERING & RANKING ---
        recommendations = []
        for user_id in candidate_pool:

            # -- Feature 1: Skill Coverage --
            matched_skills = required_skills.intersection(self.user_skills_map.get(user_id, set()))
            if not matched_skills:
                continue # Should not happen due to pool generation, but as a safeguard.

            skill_coverage_score = len(matched_skills) / len(required_skills)

            # -- Feature 2: Dynamic Proficiency Score --
            proficiency_scores = [self.actual_ratings_map.get((user_id, skill_id), 0) for skill_id in matched_skills]
            avg_proficiency_score = sum(proficiency_scores) / len(proficiency_scores) if proficiency_scores else 0

            # -- Feature 3: Collaborative Affinity Score --
            affinity_scores = [self.model.predict(uid=user_id, iid=skill_id).est for skill_id in required_skills]
            avg_affinity_score = sum(affinity_scores) / len(affinity_scores) if affinity_scores else 0

            # -- Final Weighted Score --
            final_score = (
                (self.WEIGHT_COVERAGE * skill_coverage_score) +
                (self.WEIGHT_PROFICIENCY * (avg_proficiency_score / 5.0)) + # Normalize to 0-1 scale
                (self.WEIGHT_AFFINITY * (avg_affinity_score / 5.0))   # Normalize to 0-1 scale
            )

            recommendations.append({
                'user_id': user_id, 
                'score': final_score,
                # Optional: return sub-scores for explainability
                'details': {
                    'skill_coverage': skill_coverage_score,
                    'avg_proficiency': avg_proficiency_score,
                    'affinity_score': avg_affinity_score
                }
            })

        # Sort by the final combined score
        recommendations.sort(key=lambda x: x['score'], reverse=True)
        if not recommendations:
            logging.warning(f"No suitable recommendations found for skill_ids: {list(required_skills)}")
            return []

        logging.info(f"Top recommendation (user {recommendations[0]['user_id']}) details: {recommendations[0]['details']}")

        return recommendations[:limit]
