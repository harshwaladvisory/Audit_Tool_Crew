"""
Test script to verify MongoDB connection and setup
Run this to diagnose any issues: python test_mongodb.py
"""
import sys

print("=" * 60)
print("R&M TestWork Agent - MongoDB Connection Test")
print("=" * 60)

# Test 1: Check if MongoDB packages are installed
print("\n[1/5] Checking MongoDB packages...")
try:
    import mongoengine
    import pymongo
    from flask_mongoengine import MongoEngine
    print("✓ MongoDB packages installed")
    print(f"  - mongoengine version: {mongoengine.__version__}")
    print(f"  - pymongo version: {pymongo.__version__}")
except ImportError as e:
    print(f"✗ Missing package: {e}")
    print("\nRun: pip install flask-mongoengine mongoengine pymongo")
    sys.exit(1)

# Test 2: Check if MongoDB server is running
print("\n[2/5] Checking MongoDB server...")
try:
    from pymongo import MongoClient
    client = MongoClient('mongodb://localhost:27017/', serverSelectionTimeoutMS=2000)
    client.server_info()
    print("✓ MongoDB server is running")
except Exception as e:
    print(f"✗ MongoDB server not accessible: {e}")
    print("\nMake sure MongoDB is installed and running")
    print("Check with: mongosh")
    sys.exit(1)

# Test 3: Import app and models
print("\n[3/5] Importing application...")
try:
    from app import app, db
    from models import Run, GLPopulation, TBMapping, Sample, AuditLog
    print("✓ Application imports successful")
except Exception as e:
    print(f"✗ Import error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test 4: Test database connection
print("\n[4/5] Testing database connection...")
try:
    with app.app_context():
        # Try to count runs
        run_count = Run.objects().count()
        print(f"✓ Database connected successfully")
        print(f"  - Current run count: {run_count}")
except Exception as e:
    print(f"✗ Database connection error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test 5: Test creating a run
print("\n[5/5] Testing run creation...")
try:
    with app.app_context():
        # Check if test run already exists
        test_run = Run.objects(name__contains="Test Connection").first()
        
        if test_run:
            print(f"✓ Test run already exists: {test_run.name} (ID: {test_run.id})")
        else:
            # Create test run
            test_run = Run(
                name="Test Connection Run",
                status='draft',
                capitalization_threshold=5000.0,
                materiality=25000.0,
                fy_start='2025-07-01',
                fy_end='2026-06-30',
                allowed_accounts=['Repair & Maintenance', 'Repairs', 'Maintenance']
            )
            test_run.save()
            print(f"✓ Test run created successfully!")
            print(f"  - Run ID: {test_run.id}")
            print(f"  - Name: {test_run.name}")
        
        # List all runs
        print("\n📋 All Runs in Database:")
        all_runs = Run.objects()
        if all_runs.count() == 0:
            print("  No runs found")
        else:
            for run in all_runs:
                print(f"  - {run.name}")
                print(f"    ID: {run.id}")
                print(f"    Status: {run.status}")
                print(f"    Created: {run.created_at}")
                
                # Check for GL data
                gl_count = GLPopulation.objects(run=run).count()
                tb_count = TBMapping.objects(run=run).count()
                print(f"    GL Records: {gl_count}")
                print(f"    TB Records: {tb_count}")
                print()
        
except Exception as e:
    print(f"✗ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Success!
print("=" * 60)
print("✓✓✓ All tests passed! MongoDB setup is working correctly")
print("=" * 60)
print("\n🚀 You can now run: python main.py")
print("   Then go to: http://localhost:8564\n")