"""
Script to create a test run in MongoDB
Run this once to create your first run for testing
"""
from app import app
from models import Run
from datetime import datetime

def create_test_run():
    with app.app_context():
        # Check if any runs exist
        existing_runs = Run.objects().count()
        
        if existing_runs > 0:
            print(f"✓ Database already has {existing_runs} run(s)")
            for run in Run.objects():
                print(f"  - {run.name} (ID: {run.id}, Status: {run.status})")
            return
        
        # Create a new test run
        print("Creating test run...")
        run = Run(
            name="Test Run - R&M FY2025-26",
            status='draft',
            capitalization_threshold=5000.0,
            materiality=25000.0,
            fy_start='2025-07-01',
            fy_end='2026-06-30',
            allowed_accounts=['Repair & Maintenance', 'Repairs', 'Maintenance'],
            metrics={}
        )
        run.save()
        
        print(f"✓ Test run created successfully!")
        print(f"  Run ID: {run.id}")
        print(f"  Name: {run.name}")
        print(f"  Status: {run.status}")
        print(f"\nYou can now upload files to this run!")

if __name__ == '__main__':
    try:
        create_test_run()
    except Exception as e:
        print(f"✗ Error: {str(e)}")
        print("\nMake sure MongoDB is running!")
        print("Check with: mongosh")