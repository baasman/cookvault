from datetime import datetime
from enum import Enum
from typing import List, Optional

from sqlalchemy import (
    String,
    Text,
    Integer,
    DateTime,
    ForeignKey,
    Float,
    Table,
    Column,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app import db


recipe_ingredients = Table(
    "recipe_ingredients",
    db.Model.metadata,
    Column("recipe_id", Integer, ForeignKey("recipe.id"), primary_key=True),
    Column("ingredient_id", Integer, ForeignKey("ingredient.id"), primary_key=True),
    Column("quantity", Float),
    Column("unit", String(50)),
    Column("preparation", String(100)),
    Column("optional", db.Boolean, default=False),
    Column("order", Integer, default=0),
)


class Cookbook(db.Model):
    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    author: Mapped[Optional[str]] = mapped_column(String(200))
    publication_date: Mapped[Optional[datetime]] = mapped_column(DateTime)
    isbn: Mapped[Optional[str]] = mapped_column(String(20))
    publisher: Mapped[Optional[str]] = mapped_column(String(200))
    cover_image_url: Mapped[Optional[str]] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )
    
    # User relationship
    user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("user.id"))
    
    recipes: Mapped[List["Recipe"]] = relationship(
        "Recipe", back_populates="cookbook"
    )
    user: Mapped[Optional["User"]] = relationship(
        "User", back_populates="cookbooks"
    )
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "author": self.author,
            "publication_date": self.publication_date.isoformat() if self.publication_date else None,
            "isbn": self.isbn,
            "publisher": self.publisher,
            "cover_image_url": self.cover_image_url,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "recipe_count": len(self.recipes)
        }


class Tag(db.Model):
    id: Mapped[int] = mapped_column(primary_key=True)
    recipe_id: Mapped[int] = mapped_column(ForeignKey("recipe.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)

    recipe: Mapped["Recipe"] = relationship("Recipe", back_populates="recipe_tags")

    def to_dict(self) -> dict:
        return {"id": self.id, "name": self.name}


class Instruction(db.Model):
    id: Mapped[int] = mapped_column(primary_key=True)
    recipe_id: Mapped[int] = mapped_column(ForeignKey("recipe.id"), nullable=False)
    step_number: Mapped[int] = mapped_column(Integer, nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)

    recipe: Mapped["Recipe"] = relationship(
        "Recipe", back_populates="recipe_instructions"
    )

    def to_dict(self) -> dict:
        return {"id": self.id, "step_number": self.step_number, "text": self.text}


class ProcessingStatus(Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class Ingredient(db.Model):
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False, unique=True)
    category: Mapped[Optional[str]] = mapped_column(String(100))
    common_units: Mapped[Optional[str]] = mapped_column(String(200))
    nutritional_info: Mapped[Optional[str]] = mapped_column(Text)
    aliases: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    recipes: Mapped[List["Recipe"]] = relationship(
        "Recipe", secondary=recipe_ingredients, back_populates="ingredients"
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "category": self.category,
            "common_units": self.common_units.split(",") if self.common_units else [],
            "aliases": self.aliases.split(",") if self.aliases else [],
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class Recipe(db.Model):
    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    cookbook_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("cookbook.id"), nullable=True
    )
    page_number: Mapped[Optional[int]] = mapped_column(Integer)
    prep_time: Mapped[Optional[int]] = mapped_column(Integer)
    cook_time: Mapped[Optional[int]] = mapped_column(Integer)
    servings: Mapped[Optional[int]] = mapped_column(Integer)
    difficulty: Mapped[Optional[str]] = mapped_column(String(50))
    source: Mapped[Optional[str]] = mapped_column(String(200))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )
    
    # User relationship
    user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("user.id"))
    cookbook: Mapped[Optional["Cookbook"]] = relationship(
        "Cookbook", back_populates="recipes"
    )
    ingredients: Mapped[List["Ingredient"]] = relationship(
        "Ingredient", secondary=recipe_ingredients, back_populates="recipes"
    )
    recipe_tags: Mapped[List["Tag"]] = relationship(
        "Tag", back_populates="recipe", cascade="all, delete-orphan"
    )
    recipe_instructions: Mapped[List["Instruction"]] = relationship(
        "Instruction",
        back_populates="recipe",
        cascade="all, delete-orphan",
        order_by="Instruction.step_number",
    )
    images: Mapped[List["RecipeImage"]] = relationship(
        "RecipeImage", back_populates="recipe", cascade="all, delete-orphan"
    )
    processing_jobs: Mapped[List["ProcessingJob"]] = relationship(
        "ProcessingJob", back_populates="recipe"
    )
    user: Mapped[Optional["User"]] = relationship(
        "User", back_populates="recipes"
    )

    def get_status(self) -> str:
        """Get the status of the recipe based on its processing jobs."""
        if not self.processing_jobs:
            return "imported"
        
        # Get the most recent processing job
        latest_job = max(self.processing_jobs, key=lambda job: job.created_at)
        return latest_job.status.value if latest_job.status else "imported"

    def get_recipe_ingredients(self) -> List[dict]:
        result = db.session.execute(
            text(
                """
                SELECT i.id, i.name, i.category, ri.quantity, ri.unit, ri.preparation, ri.optional, ri."order"
                FROM ingredient i
                JOIN recipe_ingredients ri ON i.id = ri.ingredient_id
                WHERE ri.recipe_id = :recipe_id
                ORDER BY ri."order"
            """
            ),
            {"recipe_id": self.id},
        ).fetchall()

        return [
            {
                "id": row.id,
                "name": row.name,
                "category": row.category,
                "quantity": row.quantity,
                "unit": row.unit,
                "preparation": row.preparation,
                "optional": row.optional,
                "order": row.order,
            }
            for row in result
        ]

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "cookbook": self.cookbook.to_dict() if self.cookbook else None,
            "page_number": self.page_number,
            "ingredients": self.get_recipe_ingredients(),
            "instructions": [
                instruction.to_dict() for instruction in self.recipe_instructions
            ],
            "tags": [tag.to_dict() for tag in self.recipe_tags],
            "images": [image.to_dict() for image in self.images],
            "status": self.get_status(),
            "prep_time": self.prep_time,
            "cook_time": self.cook_time,
            "servings": self.servings,
            "difficulty": self.difficulty,
            "source": self.source,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class RecipeImage(db.Model):
    id: Mapped[int] = mapped_column(primary_key=True)
    recipe_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("recipe.id"), nullable=True
    )
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    file_path: Mapped[str] = mapped_column(String(500), nullable=False)
    file_size: Mapped[int] = mapped_column(Integer, nullable=False)
    content_type: Mapped[str] = mapped_column(String(100), nullable=False)

    uploaded_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    recipe: Mapped[Optional["Recipe"]] = relationship("Recipe", back_populates="images")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "recipe_id": self.recipe_id,
            "filename": self.filename,
            "original_filename": self.original_filename,
            "file_size": self.file_size,
            "content_type": self.content_type,
            "uploaded_at": self.uploaded_at.isoformat() if self.uploaded_at else None,
        }


class ProcessingJob(db.Model):
    id: Mapped[int] = mapped_column(primary_key=True)
    recipe_id: Mapped[Optional[int]] = mapped_column(ForeignKey("recipe.id"))
    image_id: Mapped[int] = mapped_column(ForeignKey("recipe_image.id"), nullable=False)
    cookbook_id: Mapped[Optional[int]] = mapped_column(ForeignKey("cookbook.id"))
    page_number: Mapped[Optional[int]] = mapped_column(Integer)

    status: Mapped[ProcessingStatus] = mapped_column(default=ProcessingStatus.PENDING)
    error_message: Mapped[Optional[str]] = mapped_column(Text)

    ocr_text: Mapped[Optional[str]] = mapped_column(Text)
    processed_data: Mapped[Optional[str]] = mapped_column(Text)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime)

    recipe: Mapped[Optional["Recipe"]] = relationship(
        "Recipe", back_populates="processing_jobs"
    )
    image: Mapped["RecipeImage"] = relationship("RecipeImage")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "recipe_id": self.recipe_id,
            "image_id": self.image_id,
            "status": self.status.value,
            "error_message": self.error_message,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "completed_at": (
                self.completed_at.isoformat() if self.completed_at else None
            ),
        }
