#!/usr/bin/env python3
"""
Database Management CLI Tool for 990 PY Manager
Provides utilities for managing MongoDB database

Usage:
    python db_manager.py --help
    python db_manager.py --status
    python db_manager.py --stats
    python db_manager.py --clear-logs
    python db_manager.py --export-jobs output.json
"""

import argparse
import json
from datetime import datetime, timedelta
from mongo_utils import get_db_manager
from config import config
from bson import json_util


class DatabaseManager:
    """Database management utilities"""
    
    def __init__(self):
        self.db_manager = get_db_manager()
        self.connected = False
    
    def connect(self):
        """Connect to MongoDB"""
        print(f"Connecting to MongoDB...")
        print(f"URI: {config.MONGODB_URI}")
        print(f"Database: {config.MONGODB_DB_NAME}")
        
        self.connected = self.db_manager.connect(config.MONGODB_DB_NAME)
        
        if self.connected:
            print("✅ Connected successfully!\n")
            return True
        else:
            print("❌ Connection failed!\n")
            return False
    
    def show_status(self):
        """Show database connection status and basic info"""
        if not self.connect():
            return
        
        print("=" * 60)
        print("DATABASE STATUS")
        print("=" * 60)
        
        try:
            # Get database stats
            db_stats = self.db_manager.db.command('dbStats')
            
            print(f"Database Name: {self.db_manager.db.name}")
            print(f"Collections: {len(self.db_manager.db.list_collection_names())}")
            print(f"Data Size: {db_stats.get('dataSize', 0) / 1024 / 1024:.2f} MB")
            print(f"Storage Size: {db_stats.get('storageSize', 0) / 1024 / 1024:.2f} MB")
            print(f"Indexes: {db_stats.get('indexes', 0)}")
            print(f"Objects: {db_stats.get('objects', 0)}")
            
            print("\n" + "=" * 60)
            print("COLLECTIONS")
            print("=" * 60)
            
            for collection_name in self.db_manager.db.list_collection_names():
                count = self.db_manager.db[collection_name].count_documents({})
                print(f"  {collection_name}: {count} documents")
            
            print()
            
        except Exception as e:
            print(f"Error getting status: {str(e)}")
    
    def show_stats(self):
        """Show analytics and statistics"""
        if not self.connect():
            return
        
        print("=" * 60)
        print("ANALYTICS SUMMARY")
        print("=" * 60)
        
        # Get analytics for different periods
        periods = [7, 30, 90]
        
        for days in periods:
            analytics = self.db_manager.get_analytics_summary(days=days)
            
            print(f"\nLast {days} days:")
            print(f"  Total Jobs: {analytics.get('total_jobs', 0)}")
            print(f"  Completed Jobs: {analytics.get('completed_jobs', 0)}")
            print(f"  Files Processed: {analytics.get('total_files_processed', 0)}")
            print(f"  Average Success Rate: {analytics.get('average_success_rate', 0):.2f}%")
        
        print("\n" + "=" * 60)
        print("RECENT ACTIVITY")
        print("=" * 60)
        
        recent_jobs = self.db_manager.get_recent_jobs(limit=5)
        
        if recent_jobs:
            for i, job in enumerate(recent_jobs, 1):
                print(f"\n{i}. Job ID: {job['_id']}")
                print(f"   Status: {job['status']}")
                print(f"   Files: {job['processed_files']}/{job['total_files']}")
                print(f"   Success Rate: {job.get('success_rate', 0):.1f}%")
                print(f"   Created: {job['created_at'].strftime('%Y-%m-%d %H:%M:%S')}")
        else:
            print("\nNo recent jobs found.")
        
        print()
    
    def clear_old_logs(self, days=30):
        """Clear audit logs older than specified days"""
        if not self.connect():
            return
        
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        print(f"Clearing audit logs older than {days} days...")
        print(f"Cutoff date: {cutoff_date.strftime('%Y-%m-%d %H:%M:%S')}")
        
        try:
            result = self.db_manager.db[self.db_manager.AUDIT_LOGS].delete_many({
                'timestamp': {'$lt': cutoff_date}
            })
            
            print(f"✅ Deleted {result.deleted_count} old log entries\n")
            
        except Exception as e:
            print(f"❌ Error clearing logs: {str(e)}\n")
    
    def export_jobs(self, output_file, days=30):
        """Export processing jobs to JSON file"""
        if not self.connect():
            return
        
        print(f"Exporting jobs from last {days} days...")
        
        try:
            start_date = datetime.utcnow() - timedelta(days=days)
            
            jobs = list(self.db_manager.db[self.db_manager.PROCESSING_JOBS].find({
                'created_at': {'$gte': start_date}
            }))
            
            # Convert to JSON-serializable format
            jobs_json = json.loads(json_util.dumps(jobs))
            
            with open(output_file, 'w') as f:
                json.dump(jobs_json, f, indent=2)
            
            print(f"✅ Exported {len(jobs)} jobs to {output_file}\n")
            
        except Exception as e:
            print(f"❌ Error exporting jobs: {str(e)}\n")
    
    def create_indexes(self):
        """Create/recreate all indexes"""
        if not self.connect():
            return
        
        print("Creating indexes...")
        
        try:
            self.db_manager._create_indexes()
            print("✅ Indexes created successfully\n")
            
        except Exception as e:
            print(f"❌ Error creating indexes: {str(e)}\n")
    
    def show_sessions(self, active_only=False):
        """Show user sessions"""
        if not self.connect():
            return
        
        print("=" * 60)
        print("USER SESSIONS")
        print("=" * 60)
        
        try:
            query = {}
            if active_only:
                # Sessions active in last 24 hours
                cutoff = datetime.utcnow() - timedelta(hours=24)
                query['last_activity'] = {'$gte': cutoff}
            
            sessions = list(self.db_manager.db[self.db_manager.USER_SESSIONS].find(query).sort('last_activity', -1))
            
            if sessions:
                for i, session in enumerate(sessions, 1):
                    print(f"\n{i}. Session ID: {session['session_id']}")
                    print(f"   Created: {session['created_at'].strftime('%Y-%m-%d %H:%M:%S')}")
                    print(f"   Last Activity: {session['last_activity'].strftime('%Y-%m-%d %H:%M:%S')}")
                    
                    # Calculate duration
                    duration = session['last_activity'] - session['created_at']
                    hours = duration.total_seconds() / 3600
                    print(f"   Duration: {hours:.1f} hours")
            else:
                print("\nNo sessions found.")
            
            print()
            
        except Exception as e:
            print(f"Error showing sessions: {str(e)}")
    
    def cleanup_old_data(self, days=90):
        """Cleanup old analytics and completed jobs"""
        if not self.connect():
            return
        
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        print(f"Cleaning up data older than {days} days...")
        print(f"Cutoff date: {cutoff_date.strftime('%Y-%m-%d %H:%M:%S')}")
        
        try:
            # Cleanup old analytics
            result1 = self.db_manager.db[self.db_manager.ANALYTICS].delete_many({
                'date': {'$lt': cutoff_date}
            })
            print(f"✅ Deleted {result1.deleted_count} old analytics entries")
            
            # Cleanup old completed jobs
            result2 = self.db_manager.db[self.db_manager.PROCESSING_JOBS].delete_many({
                'completed_at': {'$lt': cutoff_date},
                'status': 'completed'
            })
            print(f"✅ Deleted {result2.deleted_count} old completed jobs")
            
            # Cleanup old audit logs
            result3 = self.db_manager.db[self.db_manager.AUDIT_LOGS].delete_many({
                'timestamp': {'$lt': cutoff_date}
            })
            print(f"✅ Deleted {result3.deleted_count} old audit logs")
            
            print()
            
        except Exception as e:
            print(f"❌ Error during cleanup: {str(e)}\n")


def main():
    parser = argparse.ArgumentParser(
        description='Database Management Tool for 990 PY Manager',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument('--status', action='store_true',
                       help='Show database connection status and info')
    
    parser.add_argument('--stats', action='store_true',
                       help='Show analytics and statistics')
    
    parser.add_argument('--clear-logs', type=int, metavar='DAYS',
                       help='Clear audit logs older than DAYS (default: 30)',
                       nargs='?', const=30)
    
    parser.add_argument('--export-jobs', type=str, metavar='FILE',
                       help='Export processing jobs to JSON file')
    
    parser.add_argument('--days', type=int, default=30,
                       help='Number of days for export (default: 30)')
    
    parser.add_argument('--create-indexes', action='store_true',
                       help='Create/recreate database indexes')
    
    parser.add_argument('--sessions', action='store_true',
                       help='Show all user sessions')
    
    parser.add_argument('--active-sessions', action='store_true',
                       help='Show active user sessions (last 24 hours)')
    
    parser.add_argument('--cleanup', type=int, metavar='DAYS',
                       help='Cleanup old data (older than DAYS)',
                       nargs='?', const=90)
    
    args = parser.parse_args()
    
    # If no arguments provided, show help
    if not any(vars(args).values()):
        parser.print_help()
        return
    
    manager = DatabaseManager()
    
    if args.status:
        manager.show_status()
    
    if args.stats:
        manager.show_stats()
    
    if args.clear_logs is not None:
        manager.clear_old_logs(days=args.clear_logs)
    
    if args.export_jobs:
        manager.export_jobs(args.export_jobs, days=args.days)
    
    if args.create_indexes:
        manager.create_indexes()
    
    if args.sessions:
        manager.show_sessions(active_only=False)
    
    if args.active_sessions:
        manager.show_sessions(active_only=True)
    
    if args.cleanup is not None:
        manager.cleanup_old_data(days=args.cleanup)


if __name__ == '__main__':
    main()