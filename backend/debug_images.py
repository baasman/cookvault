#!/usr/bin/env python3
"""
Debug script to check image file paths and existence in production.
"""
import os
from pathlib import Path
from app import create_app
from app.models import RecipeImage

def debug_images():
    app = create_app()
    with app.app_context():
        print("=== IMAGE DEBUG INFO ===")
        print(f"Upload Folder Config: {app.config['UPLOAD_FOLDER']}")
        print(f"Upload Folder Type: {type(app.config['UPLOAD_FOLDER'])}")
        print(f"Upload Folder Resolved: {Path(app.config['UPLOAD_FOLDER']).resolve()}")
        print(f"Upload Folder Exists: {Path(app.config['UPLOAD_FOLDER']).exists()}")
        print(f"Current Working Directory: {Path.cwd()}")
        print(f"Script Location: {Path(__file__).parent}")
        print(f"Config File Location: {Path(__file__).parent / 'app' / 'config.py'}")
        
        # Check what the config construction gives us
        from pathlib import Path as ConfigPath
        import os
        config_path = ConfigPath(__file__).parent.parent / os.environ.get("UPLOAD_FOLDER", "uploads")
        print(f"Config construction result: {config_path}")
        print(f"Config construction resolved: {config_path.resolve()}")
        print(f"Config construction exists: {config_path.exists()}")
        
        if Path(app.config['UPLOAD_FOLDER']).exists():
            upload_files = list(Path(app.config['UPLOAD_FOLDER']).iterdir())
            print(f"Files in upload directory: {len(upload_files)}")
            for f in upload_files[:5]:  # Show first 5 files
                print(f"  - {f.name}")
        
        print("\n=== DATABASE IMAGES ===")
        images = RecipeImage.query.limit(3).all()
        print(f"Total images in DB: {RecipeImage.query.count()}")
        
        for img in images:
            print(f"\nImage ID: {img.id}")
            print(f"  Filename: {img.filename}")
            print(f"  DB file_path: {img.file_path}")
            print(f"  File exists at DB path: {Path(img.file_path).exists()}")
            
            # Check if file exists in upload folder with just filename
            upload_path = Path(app.config['UPLOAD_FOLDER']) / img.filename
            print(f"  Upload folder path: {upload_path}")
            print(f"  File exists in upload folder: {upload_path.exists()}")
            
            # Test what serve_image function would do
            print(f"  serve_image would look for: {upload_path}")
            
            # Check recipe association
            print(f"  Recipe ID: {img.recipe_id}")
            print(f"  Has recipe: {img.recipe is not None}")
            
        print("\n=== SERVE IMAGE SIMULATION ===")
        # Simulate what happens in serve_image
        if images:
            test_filename = images[0].filename
            print(f"Testing with filename: {test_filename}")
            
            upload_folder = Path(app.config["UPLOAD_FOLDER"])
            file_path = upload_folder / test_filename
            
            print(f"serve_image upload_folder: {upload_folder}")
            print(f"serve_image file_path: {file_path}")
            print(f"serve_image file_path resolved: {file_path.resolve()}")
            print(f"serve_image file exists check: {file_path.exists()}")
            
            # Security check simulation
            path_ok = str(file_path.resolve()).startswith(str(upload_folder.resolve()))
            print(f"Security check passes: {path_ok}")
            print(f"  file_path.resolve(): {file_path.resolve()}")
            print(f"  upload_folder.resolve(): {upload_folder.resolve()}")
            print(f"  startswith check: {str(file_path.resolve()).startswith(str(upload_folder.resolve()))}")

if __name__ == "__main__":
    debug_images()