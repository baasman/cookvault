from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import List, Optional

from sqlalchemy import (
    String,
    Text,
    Integer,
    DateTime,
    ForeignKey,
    Float,
    Boolean,
    Table,
    Column,
    text,
    Numeric,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app import db


class UserRecipeCollection(db.Model):
    """Track which recipes users have added to their personal collections"""
    __tablename__ = 'user_recipe_collections'
    
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id"), primary_key=True)
    recipe_id: Mapped[int] = mapped_column(ForeignKey("recipe.id"), primary_key=True)
    added_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    notes: Mapped[Optional[str]] = mapped_column(Text)

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="recipe_collections")
    recipe: Mapped["Recipe"] = relationship("Recipe", back_populates="user_collections")

    def to_dict(self) -> dict:
        return {
            "user_id": self.user_id,
            "recipe_id": self.recipe_id,
            "added_at": self.added_at.isoformat() if self.added_at else None,
            "notes": self.notes,
        }


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

recipe_group_memberships = Table(
    "recipe_group_memberships",
    db.Model.metadata,
    Column("recipe_id", Integer, ForeignKey("recipe.id"), primary_key=True),
    Column("group_id", Integer, ForeignKey("recipe_group.id"), primary_key=True),
    Column("added_at", DateTime, default=datetime.utcnow),
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
    
    # Purchase-related fields
    is_purchasable: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    price: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2))
    purchase_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    
    # User relationship
    user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("user.id"))
    
    recipes: Mapped[List["Recipe"]] = relationship(
        "Recipe", back_populates="cookbook"
    )
    user: Mapped[Optional["User"]] = relationship(
        "User", back_populates="cookbooks"
    )
    purchases: Mapped[List["CookbookPurchase"]] = relationship(
        "CookbookPurchase", back_populates="cookbook", cascade="all, delete-orphan"
    )
    
    def is_available_for_purchase(self) -> bool:
        """Check if cookbook is available for purchase."""
        return self.is_purchasable and self.price is not None and self.price > 0

    def increment_purchase_count(self) -> None:
        """Increment the purchase count when a purchase is made."""
        self.purchase_count += 1

    def to_dict(self, current_user_id: Optional[int] = None) -> dict:
        result = {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "author": self.author,
            "publication_date": self.publication_date.isoformat() if self.publication_date else None,
            "isbn": self.isbn,
            "publisher": self.publisher,
            "cover_image_url": self.cover_image_url,
            "is_purchasable": self.is_purchasable,
            "price": float(self.price) if self.price else None,
            "purchase_count": self.purchase_count,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "recipe_count": len(self.recipes)
        }
        
        # Include purchase status if current user is provided
        if current_user_id and self.is_purchasable:
            has_purchased = any(
                purchase.user_id == current_user_id and purchase.has_access()
                for purchase in self.purchases
            )
            result["has_purchased"] = has_purchased
            result["is_available_for_purchase"] = self.is_available_for_purchase() and not has_purchased
        
        return result


class RecipeGroup(db.Model):
    """User-created recipe groups for organization"""
    __tablename__ = 'recipe_group'
    
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    cover_image_url: Mapped[Optional[str]] = mapped_column(String(500))
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id"), nullable=False)
    is_private: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )
    
    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="recipe_groups")
    recipes: Mapped[List["Recipe"]] = relationship(
        "Recipe", 
        secondary=recipe_group_memberships, 
        back_populates="groups"
    )
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "cover_image_url": self.cover_image_url,
            "user_id": self.user_id,
            "is_private": self.is_private,
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


class MultiRecipeJob(db.Model):
    """Manages multi-image recipe processing jobs"""
    __tablename__ = 'multi_recipe_job'
    
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id"), nullable=False)
    status: Mapped[ProcessingStatus] = mapped_column(default=ProcessingStatus.PENDING)
    total_images: Mapped[int] = mapped_column(Integer, nullable=False)
    processed_images: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    
    # Final combined recipe data
    recipe_id: Mapped[Optional[int]] = mapped_column(ForeignKey("recipe.id"))
    combined_ocr_text: Mapped[Optional[str]] = mapped_column(Text)
    
    error_message: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    
    # Relationships
    user: Mapped["User"] = relationship("User")
    recipe: Mapped[Optional["Recipe"]] = relationship("Recipe")
    processing_jobs: Mapped[List["ProcessingJob"]] = relationship(
        "ProcessingJob", back_populates="multi_job"
    )
    
    def get_progress_percentage(self) -> float:
        """Calculate completion percentage"""
        if self.total_images == 0:
            return 0.0
        return (self.processed_images / self.total_images) * 100
    
    def is_complete(self) -> bool:
        """Check if all images have been processed"""
        return self.processed_images >= self.total_images
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "status": self.status.value,
            "total_images": self.total_images,
            "processed_images": self.processed_images,
            "progress_percentage": self.get_progress_percentage(),
            "recipe_id": self.recipe_id,
            "error_message": self.error_message,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }


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
    
    # Privacy settings
    is_public: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    published_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    
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
        "RecipeImage", 
        back_populates="recipe", 
        cascade="all, delete-orphan",
        order_by="RecipeImage.image_order"
    )
    processing_jobs: Mapped[List["ProcessingJob"]] = relationship(
        "ProcessingJob", back_populates="recipe"
    )
    user: Mapped[Optional["User"]] = relationship(
        "User", back_populates="recipes"
    )
    user_collections: Mapped[List["UserRecipeCollection"]] = relationship(
        "UserRecipeCollection", back_populates="recipe", cascade="all, delete-orphan"
    )
    user_notes: Mapped[List["RecipeNote"]] = relationship(
        "RecipeNote", back_populates="recipe", cascade="all, delete-orphan"
    )
    comments: Mapped[List["RecipeComment"]] = relationship(
        "RecipeComment", back_populates="recipe", cascade="all, delete-orphan"
    )
    groups: Mapped[List["RecipeGroup"]] = relationship(
        "RecipeGroup", 
        secondary=recipe_group_memberships, 
        back_populates="recipes"
    )

    def get_status(self) -> str:
        """Get the status of the recipe based on its processing jobs."""
        if not self.processing_jobs:
            return "imported"
        
        # Get the most recent processing job
        latest_job = max(self.processing_jobs, key=lambda job: job.created_at)
        return latest_job.status.value if latest_job.status else "imported"
    
    def publish(self) -> None:
        """Publish the recipe to make it public."""
        self.is_public = True
        self.published_at = datetime.utcnow()
    
    def unpublish(self) -> None:
        """Unpublish the recipe to make it private."""
        self.is_public = False
        self.published_at = None
    
    def can_be_viewed_by(self, user_id: Optional[int] = None, is_admin: bool = False) -> bool:
        """Check if a recipe can be viewed by a given user."""
        # Public recipes can be viewed by anyone
        if self.is_public:
            return True
        
        # Admins can view all recipes
        if is_admin:
            return True
        
        # Recipe owner can always view their own recipes
        if self.user_id == user_id:
            return True
        
        # If recipe belongs to a purchasable cookbook, check purchase status
        if self.cookbook and self.cookbook.is_purchasable and user_id:
            from app.models.user import User
            user = User.query.get(user_id)
            if user and user.has_purchased_cookbook(self.cookbook.id):
                return True
        
        # Private recipes can only be viewed by their owner (already checked above)
        return False
    
    def has_full_access(self, user_id: Optional[int] = None, is_admin: bool = False) -> bool:
        """Check if a user has full access to recipe content (vs preview access)."""
        # Admins have full access to everything
        if is_admin:
            return True
        
        # Recipe owner always has full access
        if self.user_id == user_id:
            return True
        
        # Public recipes have full access for everyone
        if self.is_public:
            return True
        
        # For purchasable cookbook recipes, check if user has purchased
        if self.cookbook and self.cookbook.is_purchasable and user_id:
            from app.models.user import User
            user = User.query.get(user_id)
            if user and user.has_purchased_cookbook(self.cookbook.id):
                return True
            # User can see the recipe exists but doesn't have full access
            return False
        
        # For non-purchasable cookbook recipes, if they can view it, they have full access
        return self.can_be_viewed_by(user_id, is_admin)
    
    def is_in_user_collection(self, user_id: int) -> bool:
        """Check if this recipe is in a user's collection."""
        if not user_id:
            return False
        
        # User's own recipes are automatically considered "in collection"
        if self.user_id == user_id:
            return True
        
        # Check if explicitly added to collection
        collection_item = UserRecipeCollection.query.filter_by(
            user_id=user_id,
            recipe_id=self.id
        ).first()
        
        return collection_item is not None
    
    @classmethod
    def get_public_recipes(cls, limit: Optional[int] = None, offset: int = 0):
        """Get all public recipes with optional pagination."""
        query = cls.query.filter(cls.is_public == True).order_by(cls.published_at.desc())
        
        if limit:
            query = query.limit(limit).offset(offset)
        
        return query.all()
    
    @classmethod
    def get_user_public_recipes(cls, user_id: int, limit: Optional[int] = None, offset: int = 0):
        """Get all public recipes by a specific user."""
        query = cls.query.filter(
            cls.user_id == user_id,
            cls.is_public == True
        ).order_by(cls.published_at.desc())
        
        if limit:
            query = query.limit(limit).offset(offset)
        
        return query.all()

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

    def to_dict(self, include_user: bool = False, current_user_id: Optional[int] = None, is_admin: bool = False) -> dict:
        # Check if user has full access to recipe content
        has_full_access = self.has_full_access(current_user_id, is_admin)
        
        # Base recipe information (always available)
        result = {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "cookbook": self.cookbook.to_dict(current_user_id) if self.cookbook else None,
            "page_number": self.page_number,
            "status": self.get_status(),
            "prep_time": self.prep_time,
            "cook_time": self.cook_time,
            "servings": self.servings,
            "difficulty": self.difficulty,
            "source": self.source,
            "is_public": self.is_public,
            "published_at": self.published_at.isoformat() if self.published_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "user_id": self.user_id,
            "has_full_access": has_full_access,
        }
        
        # Restricted content (only for users with full access)
        if has_full_access:
            result.update({
                "ingredients": self.get_recipe_ingredients(),
                "instructions": [
                    instruction.to_dict() for instruction in self.recipe_instructions
                ],
                "tags": [tag.to_dict() for tag in self.recipe_tags],
                "images": [image.to_dict() for image in self.images],
            })
        else:
            # Limited preview content for paywall
            result.update({
                "ingredients": [],  # Empty for paywall
                "instructions": [],  # Empty for paywall
                "tags": [tag.to_dict() for tag in self.recipe_tags],  # Tags still visible
                "images": [image.to_dict() for image in self.images[:1]] if self.images else [],  # Only first image
                "paywall_message": f"Purchase the cookbook '{self.cookbook.title}' to view the full recipe including ingredients and instructions." if self.cookbook and self.cookbook.is_purchasable else None
            })
        
        # Include user information for public recipes or when explicitly requested
        if include_user and self.user:
            result["user"] = {
                "id": self.user.id,
                "username": self.user.username,
                "first_name": self.user.first_name,
                "last_name": self.user.last_name,
            }
        
        # Include collection status if current user is provided
        if current_user_id:
            result["is_in_collection"] = self.is_in_user_collection(current_user_id)
            
            # Include recipe owner's note for this recipe if it exists
            user_note = None
            for note in self.user_notes:
                if note.user_id == self.user_id:  # Recipe owner's note, not current user's note
                    user_note = note.to_dict()
                    break
            result["user_note"] = user_note
            
            # Include groups that this recipe belongs to (only for the current user's groups)
            user_groups = []
            for group in self.groups:
                if group.user_id == current_user_id:
                    user_groups.append({
                        "id": group.id,
                        "name": group.name,
                        "description": group.description
                    })
            result["groups"] = user_groups
        
        return result


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
    
    # Multi-image support fields
    image_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    page_number: Mapped[Optional[int]] = mapped_column(Integer)

    uploaded_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    # Add index for recipe_id + image_order for efficient ordering queries
    __table_args__ = (db.Index('idx_recipe_image_order', 'recipe_id', 'image_order'),)

    recipe: Mapped[Optional["Recipe"]] = relationship("Recipe", back_populates="images")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "recipe_id": self.recipe_id,
            "filename": self.filename,
            "original_filename": self.original_filename,
            "file_size": self.file_size,
            "content_type": self.content_type,
            "image_order": self.image_order,
            "page_number": self.page_number,
            "uploaded_at": self.uploaded_at.isoformat() if self.uploaded_at else None,
        }


class ProcessingJob(db.Model):
    id: Mapped[int] = mapped_column(primary_key=True)
    recipe_id: Mapped[Optional[int]] = mapped_column(ForeignKey("recipe.id"))
    image_id: Mapped[int] = mapped_column(ForeignKey("recipe_image.id"), nullable=False)
    cookbook_id: Mapped[Optional[int]] = mapped_column(ForeignKey("cookbook.id"))
    page_number: Mapped[Optional[int]] = mapped_column(Integer)

    # Multi-image support fields
    is_multi_image: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    multi_job_id: Mapped[Optional[int]] = mapped_column(ForeignKey("multi_recipe_job.id"))
    image_order: Mapped[Optional[int]] = mapped_column(Integer)  # Order within multi-image job

    status: Mapped[ProcessingStatus] = mapped_column(default=ProcessingStatus.PENDING)
    error_message: Mapped[Optional[str]] = mapped_column(Text)

    ocr_text: Mapped[Optional[str]] = mapped_column(Text)
    processed_data: Mapped[Optional[str]] = mapped_column(Text)

    # OCR Quality Metadata
    ocr_method: Mapped[Optional[str]] = mapped_column(String(20))  # 'traditional' or 'llm'
    ocr_quality_score: Mapped[Optional[int]] = mapped_column(Integer)  # 1-10 quality score
    ocr_fallback_used: Mapped[Optional[bool]] = mapped_column(db.Boolean, default=False)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime)

    recipe: Mapped[Optional["Recipe"]] = relationship(
        "Recipe", back_populates="processing_jobs"
    )
    image: Mapped["RecipeImage"] = relationship("RecipeImage")
    multi_job: Mapped[Optional["MultiRecipeJob"]] = relationship(
        "MultiRecipeJob", back_populates="processing_jobs"
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "recipe_id": self.recipe_id,
            "image_id": self.image_id,
            "is_multi_image": self.is_multi_image,
            "multi_job_id": self.multi_job_id,
            "image_order": self.image_order,
            "status": self.status.value,
            "error_message": self.error_message,
            "ocr_method": self.ocr_method,
            "ocr_quality_score": self.ocr_quality_score,
            "ocr_fallback_used": self.ocr_fallback_used,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "completed_at": (
                self.completed_at.isoformat() if self.completed_at else None
            ),
        }


class RecipeNote(db.Model):
    """User's personal notes for recipes"""
    __tablename__ = 'recipe_notes'
    
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id"), nullable=False)
    recipe_id: Mapped[int] = mapped_column(ForeignKey("recipe.id"), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )
    
    # Add unique constraint so each user can have only one note per recipe
    __table_args__ = (db.UniqueConstraint('user_id', 'recipe_id', name='unique_user_recipe_note'),)
    
    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="recipe_notes")
    recipe: Mapped["Recipe"] = relationship("Recipe", back_populates="user_notes")
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "recipe_id": self.recipe_id,
            "content": self.content,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class RecipeComment(db.Model):
    """Comments on recipes by users"""
    __tablename__ = 'recipe_comments'
    
    id: Mapped[int] = mapped_column(primary_key=True)
    recipe_id: Mapped[int] = mapped_column(ForeignKey("recipe.id"), nullable=False)
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id"), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )
    
    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="recipe_comments")
    recipe: Mapped["Recipe"] = relationship("Recipe", back_populates="comments")
    
    def to_dict(self, include_user: bool = True) -> dict:
        result = {
            "id": self.id,
            "recipe_id": self.recipe_id,
            "user_id": self.user_id,
            "content": self.content,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
        
        # Include user information for display
        if include_user and self.user:
            result["user"] = {
                "id": self.user.id,
                "username": self.user.username,
                "first_name": self.user.first_name,
                "last_name": self.user.last_name,
            }
        
        return result
