"""
Celery tasks module for cookbook-creator.

This module contains async tasks for recipe processing.
"""
from app.tasks.recipe_tasks import process_single_recipe_task, process_multi_recipe_task

__all__ = ['process_single_recipe_task', 'process_multi_recipe_task']
