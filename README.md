# Synapse Recommender Engine

This repository contains the **recommendation engine microservice** used by the larger [Synapse](https://github.com/your-org/synapse) system for intelligent engineering talent allocation.

---

## 🧠 Purpose

The engine identifies the most suitable engineers for a task by combining:

* **Explicit skills**: What engineers claim they know (e.g., "expert in Python")
* **Implicit skills**: What they've demonstrated through completed tasks

It dynamically adjusts the weight of these signals based on experience, ensuring both **new talent** and **veterans** are fairly evaluated.

---

## ⚙️ Functionality

The engine follows a **three-stage pipeline**:

1. **Candidate Generation**
   Filters for available engineers with at least one matching skill.

2. **Feature Scoring**
   Calculates:

   * **Skill coverage**: How many required skills are met
   * **Proficiency**: Weighted skill ratings using explicit/implicit evidence
   * **Collaborative affinity**: Similarity to engineers who’ve succeeded in similar tasks (via SVD)

3. **Final Ranking**
   Combines these features to produce a ranked list of best-fit engineers.

---

## 🧪 Testing

To populate the system with realistic test data, run:

```bash
python scripts/seed_data.py
```

This script creates sample users, tasks, and skills, including predefined personas to verify recommendation behavior in common allocation scenarios.
