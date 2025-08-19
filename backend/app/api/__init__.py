from flask import Blueprint

bp = Blueprint("api", __name__)

from app.api import recipes, auth, cookbooks, public, recipe_groups, payments