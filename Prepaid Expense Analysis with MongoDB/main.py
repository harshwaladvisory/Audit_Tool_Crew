#!/usr/bin/env python
"""
Main entry point for Prepaid Expense Analysis application
"""

if __name__ == '__main__':
    from app import app
    
    print("=" * 60)
    print("Starting Prepaid Expense Analysis Application")
    print("=" * 60)
    print("Server will start at: http://localhost:8565")
    print("Press CTRL+C to quit")
    print("=" * 60)
    
    app.run(
        host='0.0.0.0',
        port=8565,
        debug=True
    )